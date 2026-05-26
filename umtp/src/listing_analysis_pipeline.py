import hashlib
import json
import re
from datetime import datetime, timezone

try:
    from src.alert_price_direction import (
        BELOW_OR_EQUAL,
        compute_target_buy_price_krw,
        is_listing_alert_match,
        passes_price_bounds,
        normalize_alert_price_direction,
    )
    from src.analysis_log import save_success_log
    from src.analysis_jobs import (
        create_analysis_jobs_for_rules,
        get_pending_analysis_jobs,
        mark_analysis_job_done,
        mark_analysis_job_failed,
        mark_analysis_job_started,
    )
    from src.db import get_connection
    from src.joongna_seen_products import (
        CHANGE_REASON_CONTENT_CHANGED,
        CHANGE_REASON_PRICE_CHANGED,
        CHANGE_REASON_TITLE_CHANGED,
        build_listing_content_snapshot,
        get_seen_product,
        mark_seen_product_analyzed,
        update_seen_product_content_snapshot,
    )
    from src.listing_page_parser import fetch_html, parse_joongna_listing_page
    from src.notification_worker import dispatch_alert_event_immediately
    from src.risk_analyzer import analyze_risk
    from src.spec_parser import parse_listing_title
    from src.user_fair_price import (
        is_user_fair_price_target_enabled,
        resolve_fair_price_for_user,
        resolve_fair_price_for_watch_rule,
    )
except ModuleNotFoundError:
    from alert_price_direction import (
        BELOW_OR_EQUAL,
        compute_target_buy_price_krw,
        is_listing_alert_match,
        passes_price_bounds,
        normalize_alert_price_direction,
    )
    from analysis_log import save_success_log
    from analysis_jobs import (
        create_analysis_jobs_for_rules,
        get_pending_analysis_jobs,
        mark_analysis_job_done,
        mark_analysis_job_failed,
        mark_analysis_job_started,
    )
    from db import get_connection
    from joongna_seen_products import (
        CHANGE_REASON_CONTENT_CHANGED,
        CHANGE_REASON_PRICE_CHANGED,
        CHANGE_REASON_TITLE_CHANGED,
        build_listing_content_snapshot,
        get_seen_product,
        mark_seen_product_analyzed,
        update_seen_product_content_snapshot,
    )
    from listing_page_parser import fetch_html, parse_joongna_listing_page
    from notification_worker import dispatch_alert_event_immediately
    from risk_analyzer import analyze_risk
    from spec_parser import parse_listing_title
    from user_fair_price import (
        is_user_fair_price_target_enabled,
        resolve_fair_price_for_user,
        resolve_fair_price_for_watch_rule,
    )
DUPLICATE_ENTRY_ERROR_CODE = 1062
ALERT_BODY_EXCERPT_MAX_LEN = 500

_MAC_PRODUCT_NAME_PATTERN = re.compile(
    r"(맥북에어|맥북|맥\s*미니|맥미니|맥\s*스튜디오|맥스튜디오|macbook(?:\s*air)?|mac\s*mini|mac\s*studio|macmini|macstudio)",
    flags=re.IGNORECASE,
)
_TITLE_CHIP_SPEC_PATTERN = re.compile(
    r"\bm\s*(?:1|2|3|4|5)\b|\bm\s*(?:2|4)\s*[-]?\s*pro\b",
    flags=re.IGNORECASE,
)
_TITLE_RAM_SPEC_PATTERN = re.compile(
    r"(?:\b(?:8|16|24|32|48|64)\s*(?:gb|g)\b|(?:8|16|24|32|48|64)\s*기가|램\s*(?:8|16|24|32|48|64)|(?:8|16|24|32|48|64)\s*램)",
    flags=re.IGNORECASE,
)
_TITLE_SSD_SPEC_PATTERN = re.compile(
    r"(?:\b(?:256|512|1024|2048|4096|8192)\s*(?:gb|g|ssd)\b|(?:256|512|1024|2048|4096|8192)\s*기가|\b(?:1|2|4|8)\s*(?:tb|t|테라)\b)",
    flags=re.IGNORECASE,
)


def _build_parse_failure_result(reason):
    return {
        "parse_success": False,
        "product_type": None,
        "chip": None,
        "screen_inch": None,
        "ram_gb": None,
        "ssd_gb": None,
        "parse_failure_reason": reason,
        "missing_fields": ["product_type", "chip", "ram_gb", "ssd_gb"],
    }


def _safe_parse_listing_from_title(title, self_check_fields=None):
    normalized_title = _normalize_optional_text(title)
    if normalized_title is None:
        return _build_parse_failure_result("title_missing")

    try:
        parsed_spec = parse_listing_title(normalized_title, self_check_fields=self_check_fields or {})
    except Exception:
        return _build_parse_failure_result("title_parse_exception")

    if isinstance(parsed_spec, dict):
        return parsed_spec

    return _build_parse_failure_result("title_parse_invalid_result")


def _contains_mac_product_name(title):
    normalized_title = _normalize_optional_text(title)
    if normalized_title is None:
        return False
    return bool(_MAC_PRODUCT_NAME_PATTERN.search(normalized_title))


def _title_has_explicit_core_specs(title):
    normalized_title = _normalize_optional_text(title)
    if normalized_title is None:
        return False

    return bool(
        _TITLE_CHIP_SPEC_PATTERN.search(normalized_title)
        and _TITLE_RAM_SPEC_PATTERN.search(normalized_title)
        and _TITLE_SSD_SPEC_PATTERN.search(normalized_title)
    )


def _is_title_product_name_only_spec_missing(title, parsed_spec):
    if not _contains_mac_product_name(title):
        return False

    if _title_has_explicit_core_specs(title):
        return False

    if not isinstance(parsed_spec, dict):
        return True

    missing_fields = parsed_spec.get("missing_fields")
    if isinstance(missing_fields, list):
        missing_set = {str(field) for field in missing_fields}
        if "chip" in missing_set or "ram_gb" in missing_set or "ssd_gb" in missing_set:
            return True

    return (
        _normalize_optional_text(parsed_spec.get("chip")) is None
        or _normalize_optional_int(parsed_spec.get("ram_gb")) is None
        or _normalize_optional_int(parsed_spec.get("ssd_gb")) is None
    )


def should_fetch_detail(listing, change_reason, title_parse_result, *, target_price_krw=None):
    normalized_reason = _normalize_optional_text(change_reason)
    normalized_title = _normalize_optional_text((listing or {}).get("title"))

    if normalized_reason == "unchanged":
        return False, "unchanged"

    if normalized_reason == "new":
        return True, "new"

    if _is_title_product_name_only_spec_missing(normalized_title, title_parse_result):
        return True, "product_only_spec_missing"

    parse_success = bool(title_parse_result.get("parse_success")) if isinstance(title_parse_result, dict) else False
    if not parse_success:
        return True, "title_parse_failed"

    if normalized_reason in {
        "sort_date_changed",
        "price_changed",
        "title_changed",
        "body_maybe_changed",
        "refresh_key_changed",
        "content_changed",
    }:
        return True, "changed_listing"

    return True, "conservative_default"


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_optional_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_watch_rule_id(value):
    normalized = _normalize_optional_int(value)
    if normalized is None:
        return None
    if normalized <= 0:
        return None
    return normalized


def _coerce_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        text = _normalize_optional_text(value)
        if text is None:
            return None

        parsed = None
        candidate = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            pass

        if parsed is None:
            for date_format in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
            ):
                try:
                    parsed = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    continue

        if parsed is None:
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed.replace(microsecond=0)


def _is_duplicate_entry_error(exc):
    error_code = getattr(exc, "errno", None)
    if error_code == DUPLICATE_ENTRY_ERROR_CODE:
        return True

    message = str(exc).lower()
    return "duplicate" in message and "entry" in message


def _build_listing_snapshot_from_job(job):
    return {
        "product_id": _normalize_optional_text(job.get("product_id")),
        "product_url": _normalize_optional_text(job.get("url")),
        "title": _normalize_optional_text(job.get("title")),
        "price": _normalize_optional_int(job.get("price_krw")),
        "search_keyword": _normalize_optional_text(job.get("search_keyword")),
        "user_id": _normalize_optional_text(job.get("user_id")),
        "watch_rule_id": _normalize_optional_watch_rule_id(job.get("watch_rule_id")),
        "sort_date": _coerce_datetime(job.get("sort_date")),
        "seller_store_seq": _normalize_optional_int(job.get("seller_store_seq")),
        "seller_store_name": _normalize_optional_text(job.get("seller_store_name")),
    }


def enqueue_analysis_for_product(product, watch_rules, trigger_reason):
    return create_analysis_jobs_for_rules(product, watch_rules, trigger_reason)


def _safe_json_loads(value, *, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    if isinstance(parsed, type(fallback)):
        return parsed
    return fallback


def _resolve_seller_info_for_alert(
    cursor,
    *,
    product_id,
    fallback_store_seq=None,
    fallback_store_name=None,
):
    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_product_id is None:
        return {
            "seller_store_seq": _normalize_optional_int(fallback_store_seq),
            "seller_store_name": _normalize_optional_text(fallback_store_name),
        }

    normalized_store_seq = _normalize_optional_int(fallback_store_seq)
    normalized_store_name = _normalize_optional_text(fallback_store_name)
    latest_raw_json = None

    try:
        cursor.execute(
            """
            SELECT seller_store_seq, seller_store_name, raw_json
            FROM search_results
            WHERE product_id = %s
            ORDER BY fetched_at DESC, id DESC
            LIMIT 1
            """,
            (normalized_product_id,),
        )
        row = cursor.fetchone()
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" not in lowered and "doesn't exist" not in lowered:
            raise
        try:
            cursor.execute(
                """
                SELECT raw_json
                FROM search_results
                WHERE product_id = %s
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
                """,
                (normalized_product_id,),
            )
            row = cursor.fetchone()
        except Exception as inner_exc:
            lowered_inner = str(inner_exc).lower()
            if "unknown column" in lowered_inner or "doesn't exist" in lowered_inner:
                row = None
            else:
                raise

    if isinstance(row, dict):
        normalized_store_seq = _normalize_optional_int(row.get("seller_store_seq")) or normalized_store_seq
        normalized_store_name = _normalize_optional_text(row.get("seller_store_name")) or normalized_store_name
        latest_raw_json = row.get("raw_json")
    elif isinstance(row, (tuple, list)):
        if len(row) >= 1:
            normalized_store_seq = _normalize_optional_int(row[0]) or normalized_store_seq
        if len(row) >= 2:
            normalized_store_name = _normalize_optional_text(row[1]) or normalized_store_name
        if len(row) >= 3:
            latest_raw_json = row[2]

    if normalized_store_seq is not None and normalized_store_name is not None:
        return {
            "seller_store_seq": normalized_store_seq,
            "seller_store_name": normalized_store_name,
        }

    raw_json_obj = _safe_json_loads(latest_raw_json, fallback={})
    if isinstance(raw_json_obj, dict):
        if normalized_store_seq is None:
            normalized_store_seq = _normalize_optional_int(
                raw_json_obj.get("seller_store_seq")
                or raw_json_obj.get("store_seq")
                or raw_json_obj.get("storeSeq")
            )
        if normalized_store_name is None:
            normalized_store_name = _normalize_optional_text(
                raw_json_obj.get("seller_store_name")
                or raw_json_obj.get("store_name")
                or raw_json_obj.get("storeName")
            )

    return {
        "seller_store_seq": normalized_store_seq,
        "seller_store_name": normalized_store_name,
    }


def _resolve_price_rules(cursor, user_id, parsed_spec, watch_rule_id=None):
    parse_success = bool(parsed_spec.get("parse_success")) if isinstance(parsed_spec, dict) else False
    if not parse_success:
        return None, None, None, None, None, None, "parse_failed", None

    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        return None, None, None, None, None, None, "user_id_missing", None

    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)

    try:
        if normalized_watch_rule_id is not None:
            resolved_fair_price = resolve_fair_price_for_watch_rule(
                cursor,
                normalized_user_id,
                normalized_watch_rule_id,
                parsed_spec,
            )
            if resolved_fair_price is None:
                return None, None, None, None, None, None, "watch_rule_spec_mismatch", "watch_rule"
        else:
            if not is_user_fair_price_target_enabled(cursor, normalized_user_id, parsed_spec):
                return None, None, None, None, None, None, "user_target_disabled", None
            resolved_fair_price = resolve_fair_price_for_user(cursor, normalized_user_id, parsed_spec)
    except ValueError:
        if normalized_watch_rule_id is not None:
            return None, None, None, None, None, None, "watch_rule_invalid", "watch_rule"
        return None, None, None, None, None, None, "fair_price_spec_invalid", None

    if resolved_fair_price is None:
        return None, None, None, None, None, None, "fair_price_missing", None

    fair_price_krw = _normalize_optional_int(resolved_fair_price.get("fair_price_krw"))
    alert_drop_rate_percent = _normalize_optional_float(
        resolved_fair_price.get("alert_drop_rate_percent")
    )
    target_buy_price_krw = _normalize_optional_int(resolved_fair_price.get("target_buy_price_krw"))
    alert_price_direction = normalize_alert_price_direction(resolved_fair_price.get("alert_price_direction"))
    min_price_krw = _normalize_optional_int(resolved_fair_price.get("min_price_krw"))
    max_price_krw = _normalize_optional_int(resolved_fair_price.get("max_price_krw"))
    price_source = _normalize_optional_text(resolved_fair_price.get("source"))

    if fair_price_krw is None or fair_price_krw <= 0 or alert_drop_rate_percent is None:
        return None, None, None, None, min_price_krw, max_price_krw, "fair_price_missing", price_source

    if target_buy_price_krw is None:
        target_buy_price_krw = compute_target_buy_price_krw(
            fair_price_krw,
            alert_drop_rate_percent,
        )

    if target_buy_price_krw is None:
        return None, None, None, None, min_price_krw, max_price_krw, "fair_price_missing", price_source

    return (
        fair_price_krw,
        target_buy_price_krw,
        alert_drop_rate_percent,
        alert_price_direction,
        min_price_krw,
        max_price_krw,
        None,
        price_source,
    )


def _build_alert_message(title, listing_price_krw, fair_price_krw, drop_rate_percent, url):
    drop_text = "정보 없음"
    if drop_rate_percent is not None:
        drop_text = f"{round(drop_rate_percent, 2)}%"

    return (
        "[UMTP 알림]\n"
        f"{title or '-'}\n\n"
        f"가격: {listing_price_krw:,}원\n"
        f"내가 생각한 시장가: {fair_price_krw:,}원\n"
        f"시장가와의 차이: {drop_text}\n\n"
        "URL:\n"
        f"{url}"
    )


def _build_content_changed_alert_message(*, title, url, changed_fields):
    field_label_map = {
        "title": "제목",
        "price": "가격",
        "body_text": "본문",
        "self_check": "셀프검수",
    }
    labels = []
    for field in changed_fields or []:
        label = field_label_map.get(_normalize_optional_text(field))
        if label and label not in labels:
            labels.append(label)
    changed_text = ", ".join(labels) if labels else "내용"
    return (
        "[내용변경알림]\n"
        f"{title or '-'}\n\n"
        f"변경 항목: {changed_text}\n\n"
        "URL:\n"
        f"{url}"
    )


def _build_alert_change_fingerprint(
    *,
    trigger_reason,
    sort_date,
    content_revision_hash,
    title,
    listing_price_krw,
):
    payload = {
        "trigger_reason": _normalize_optional_text(trigger_reason) or "",
        "sort_date": str(sort_date) if sort_date is not None else "",
        "content_revision_hash": _normalize_optional_text(content_revision_hash) or "",
        "title": _normalize_optional_text(title) or "",
        "price_krw": _normalize_optional_int(listing_price_krw),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_body_excerpt(description, max_len=ALERT_BODY_EXCERPT_MAX_LEN):
    normalized = _normalize_optional_text(description)
    if normalized is None:
        return None
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len].rstrip()}..."


def _evaluate_watch_rule_saved_window(cursor, *, user_id, watch_rule_id, sort_date):
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    if normalized_watch_rule_id is None:
        return True, None

    try:
        cursor.execute(
            """
            SELECT user_id, enabled, saved_at
            FROM user_fair_prices
            WHERE id = %s
            LIMIT 1
            """,
            (normalized_watch_rule_id,),
        )
        row = cursor.fetchone()
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" not in lowered:
            raise
        cursor.execute(
            """
            SELECT user_id, enabled, last_poll_requested_at
            FROM user_fair_prices
            WHERE id = %s
            LIMIT 1
            """,
            (normalized_watch_rule_id,),
        )
        row = cursor.fetchone()

    if not row:
        return False, "watch_rule_missing"

    if isinstance(row, dict):
        rule_user_id = _normalize_optional_text(row.get("user_id"))
        enabled = row.get("enabled")
        saved_at = row.get("saved_at")
        if saved_at is None:
            saved_at = row.get("last_poll_requested_at")
    else:
        row_values = tuple(row)
        rule_user_id = _normalize_optional_text(row_values[0]) if len(row_values) > 0 else None
        enabled = row_values[1] if len(row_values) > 1 else True
        saved_at = row_values[2] if len(row_values) > 2 else None

    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None or rule_user_id != normalized_user_id:
        return False, "watch_rule_user_mismatch"

    if enabled is not None and not bool(enabled):
        return False, "watch_rule_disabled"

    listing_sort_date = _coerce_datetime(sort_date)
    if listing_sort_date is None:
        return False, "sort_date_missing"

    saved_at_dt = _coerce_datetime(saved_at)
    if saved_at_dt is None:
        return False, "saved_at_missing"

    if listing_sort_date < saved_at_dt:
        return False, "sort_date_before_saved_at"

    return True, None


def _find_alert_event_by_identity(
    cursor,
    *,
    user_id,
    watch_rule_id,
    product_id,
    sort_date=None,
    change_fingerprint=None,
    include_sort_date=True,
):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_product_id = _normalize_optional_text(product_id)
    normalized_sort_date = _coerce_datetime(sort_date)
    normalized_change_fingerprint = _normalize_optional_text(change_fingerprint)

    if normalized_user_id is None or normalized_product_id is None:
        return None

    try:
        if normalized_change_fingerprint is not None:
            cursor.execute(
                """
                SELECT id
                FROM alert_events
                WHERE user_id = %s
                  AND (
                        (watch_rule_id IS NULL AND %s IS NULL)
                     OR watch_rule_id = %s
                  )
                  AND product_id = %s
                  AND change_fingerprint = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    normalized_user_id,
                    normalized_watch_rule_id,
                    normalized_watch_rule_id,
                    normalized_product_id,
                    normalized_change_fingerprint,
                ),
            )
        elif include_sort_date:
            cursor.execute(
                """
                SELECT id
                FROM alert_events
                WHERE user_id = %s
                  AND (
                        (watch_rule_id IS NULL AND %s IS NULL)
                     OR watch_rule_id = %s
                  )
                  AND product_id = %s
                  AND (
                        (sort_date IS NULL AND %s IS NULL)
                     OR sort_date = %s
                  )
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    normalized_user_id,
                    normalized_watch_rule_id,
                    normalized_watch_rule_id,
                    normalized_product_id,
                    normalized_sort_date,
                    normalized_sort_date,
                ),
            )
        else:
            cursor.execute(
                """
                SELECT id
                FROM alert_events
                WHERE user_id = %s
                  AND (
                        (watch_rule_id IS NULL AND %s IS NULL)
                     OR watch_rule_id = %s
                  )
                  AND product_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    normalized_user_id,
                    normalized_watch_rule_id,
                    normalized_watch_rule_id,
                    normalized_product_id,
                ),
            )
    except Exception as exc:
        if "unknown column" not in str(exc).lower():
            raise
        cursor.execute(
            """
            SELECT id
            FROM alert_events
            WHERE user_id = %s
              AND product_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                normalized_user_id,
                normalized_product_id,
            ),
        )
    return cursor.fetchone()


def maybe_create_alert_event(
    cursor,
    *,
    analysis_job_id,
    user_id,
    watch_rule_id=None,
    product_id,
    url,
    title,
    price_krw,
    fair_price_krw,
    target_price_krw,
    drop_rate_percent,
    trigger_reason,
    message,
    source=None,
    parsed_spec=None,
    alert_drop_rate_percent=None,
    alert_price_direction=None,
    risk_result=None,
    body_excerpt=None,
    body_text=None,
    sort_date=None,
    change_fingerprint=None,
    seller_store_seq=None,
    seller_store_name=None,
):
    parsed_spec = parsed_spec or {}
    risk_result = risk_result or {}

    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_product_id = _normalize_optional_text(product_id)
    normalized_sort_date = _coerce_datetime(sort_date)
    normalized_change_fingerprint = _normalize_optional_text(change_fingerprint)
    if normalized_change_fingerprint is None:
        normalized_change_fingerprint = _build_alert_change_fingerprint(
            trigger_reason=trigger_reason,
            sort_date=normalized_sort_date,
            content_revision_hash=None,
            title=title,
            listing_price_krw=price_krw,
        )

    duplicate = _find_alert_event_by_identity(
        cursor,
        user_id=normalized_user_id,
        watch_rule_id=normalized_watch_rule_id,
        product_id=normalized_product_id,
        sort_date=normalized_sort_date,
        change_fingerprint=normalized_change_fingerprint,
    )
    if duplicate is not None:
        return {
            "created": False,
            "reason": "duplicate_identity_alert",
            "alert_id": int(duplicate[0]) if isinstance(duplicate, (tuple, list)) else int(duplicate.get("id")),
        }

    try:
        cursor.execute(
            """
            INSERT INTO alert_events (
                user_id,
                watch_rule_id,
                analysis_job_id,
                product_id,
                seller_store_seq,
                seller_store_name,
                source,
                url,
                title,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                price_krw,
                fair_price_krw,
                target_price_krw,
                drop_rate_percent,
                alert_drop_rate_percent,
                alert_price_direction,
                risk_level,
                risk_score,
                risk_keywords,
                is_exchange_post,
                trade_type,
                body_excerpt,
                body_text,
                sort_date,
                analyzed_at,
                trigger_reason,
                change_fingerprint,
                message,
                status,
                send_attempts
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, 'pending', 0
            )
            """,
            (
                normalized_user_id,
                normalized_watch_rule_id,
                _normalize_optional_int(analysis_job_id),
                normalized_product_id,
                _normalize_optional_int(seller_store_seq),
                _normalize_optional_text(seller_store_name),
                _normalize_optional_text(source),
                _normalize_optional_text(url),
                _normalize_optional_text(title),
                _normalize_optional_text(parsed_spec.get("product_type")),
                _normalize_optional_text(parsed_spec.get("chip")),
                _normalize_optional_int(parsed_spec.get("screen_inch")),
                _normalize_optional_int(parsed_spec.get("ram_gb")),
                _normalize_optional_int(parsed_spec.get("ssd_gb")),
                _normalize_optional_int(price_krw),
                _normalize_optional_int(fair_price_krw),
                _normalize_optional_int(target_price_krw),
                _normalize_optional_float(drop_rate_percent),
                _normalize_optional_float(alert_drop_rate_percent),
                _normalize_optional_text(alert_price_direction),
                _normalize_optional_text(risk_result.get("risk_level")),
                _normalize_optional_int(risk_result.get("risk_score")),
                _normalize_optional_text(risk_result.get("risk_keywords_json")),
                bool(risk_result.get("is_exchange_post")) if risk_result.get("is_exchange_post") is not None else None,
                _normalize_optional_text(risk_result.get("trade_type")),
                _normalize_optional_text(body_excerpt),
                _normalize_optional_text(body_text),
                normalized_sort_date,
                _normalize_optional_text(trigger_reason),
                normalized_change_fingerprint,
                _normalize_optional_text(message),
            ),
        )
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" in lowered_exc:
            try:
                cursor.execute(
                    """
                    INSERT INTO alert_events (
                        user_id,
                        watch_rule_id,
                        analysis_job_id,
                        product_id,
                        seller_store_seq,
                        seller_store_name,
                        source,
                        url,
                        title,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        price_krw,
                        fair_price_krw,
                        target_price_krw,
                        drop_rate_percent,
                        alert_drop_rate_percent,
                        alert_price_direction,
                        risk_level,
                        risk_score,
                        risk_keywords,
                        is_exchange_post,
                        trade_type,
                        body_excerpt,
                        sort_date,
                        analyzed_at,
                        trigger_reason,
                        change_fingerprint,
                        message,
                        status,
                        send_attempts
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, 'pending', 0
                    )
                    """,
                    (
                        normalized_user_id,
                        normalized_watch_rule_id,
                        _normalize_optional_int(analysis_job_id),
                        normalized_product_id,
                        _normalize_optional_int(seller_store_seq),
                        _normalize_optional_text(seller_store_name),
                        _normalize_optional_text(source),
                        _normalize_optional_text(url),
                        _normalize_optional_text(title),
                        _normalize_optional_text(parsed_spec.get("product_type")),
                        _normalize_optional_text(parsed_spec.get("chip")),
                        _normalize_optional_int(parsed_spec.get("screen_inch")),
                        _normalize_optional_int(parsed_spec.get("ram_gb")),
                        _normalize_optional_int(parsed_spec.get("ssd_gb")),
                        _normalize_optional_int(price_krw),
                        _normalize_optional_int(fair_price_krw),
                        _normalize_optional_int(target_price_krw),
                        _normalize_optional_float(drop_rate_percent),
                        _normalize_optional_float(alert_drop_rate_percent),
                        _normalize_optional_text(alert_price_direction),
                        _normalize_optional_text(risk_result.get("risk_level")),
                        _normalize_optional_int(risk_result.get("risk_score")),
                        _normalize_optional_text(risk_result.get("risk_keywords_json")),
                        bool(risk_result.get("is_exchange_post"))
                        if risk_result.get("is_exchange_post") is not None
                        else None,
                        _normalize_optional_text(risk_result.get("trade_type")),
                        _normalize_optional_text(body_excerpt),
                        normalized_sort_date,
                        _normalize_optional_text(trigger_reason),
                        normalized_change_fingerprint,
                        _normalize_optional_text(message),
                    ),
                )
                return {
                    "created": True,
                    "alert_id": int(cursor.lastrowid),
                }
            except Exception as detail_exc:
                if "unknown column" not in str(detail_exc).lower():
                    raise

            cursor.execute(
                """
                INSERT INTO alert_events (
                    user_id,
                    analysis_job_id,
                    product_id,
                    url,
                    title,
                    price_krw,
                    fair_price_krw,
                    target_price_krw,
                    drop_rate_percent,
                    trigger_reason,
                    message,
                    status,
                    send_attempts
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 0)
                """,
                (
                    normalized_user_id,
                    _normalize_optional_int(analysis_job_id),
                    normalized_product_id,
                    _normalize_optional_text(url),
                    _normalize_optional_text(title),
                    _normalize_optional_int(price_krw),
                    _normalize_optional_int(fair_price_krw),
                    _normalize_optional_int(target_price_krw),
                    _normalize_optional_float(drop_rate_percent),
                    _normalize_optional_text(trigger_reason),
                    _normalize_optional_text(message),
                ),
            )
            return {
                "created": True,
                "alert_id": int(cursor.lastrowid),
            }

        if _is_duplicate_entry_error(exc):
            duplicate = _find_alert_event_by_identity(
                cursor,
                user_id=normalized_user_id,
                watch_rule_id=normalized_watch_rule_id,
                product_id=normalized_product_id,
                sort_date=normalized_sort_date,
                change_fingerprint=normalized_change_fingerprint,
            )
            if duplicate is None:
                duplicate = _find_alert_event_by_identity(
                    cursor,
                    user_id=normalized_user_id,
                    watch_rule_id=normalized_watch_rule_id,
                    product_id=normalized_product_id,
                    include_sort_date=False,
                )
            if duplicate is not None:
                return {
                    "created": False,
                    "reason": "duplicate_identity_alert",
                    "alert_id": int(duplicate[0]) if isinstance(duplicate, (tuple, list)) else int(duplicate.get("id")),
                }
        raise

    return {
        "created": True,
        "alert_id": int(cursor.lastrowid),
    }


def save_listing_analysis_result(
    cursor,
    *,
    analysis_job_id,
    watch_rule_id=None,
    trigger_reason,
    search_keyword,
    title,
    parsed_spec,
    body_text=None,
    listing_price_krw,
    fair_price_krw,
    is_alert_target,
    matched_watch_rule=None,
    alert_created,
):
    parsed_spec = parsed_spec or {}

    normalized_title = _normalize_optional_text(title) or "UNKNOWN"
    normalized_product_type = _normalize_optional_text(parsed_spec.get("product_type")) or "UNKNOWN"
    normalized_chip = _normalize_optional_text(parsed_spec.get("chip")) or "UNKNOWN"
    normalized_screen_inch = _normalize_optional_int(parsed_spec.get("screen_inch")) or 0
    normalized_ram_gb = _normalize_optional_int(parsed_spec.get("ram_gb")) or 0
    normalized_ssd_gb = _normalize_optional_int(parsed_spec.get("ssd_gb")) or 0
    normalized_listing_price_krw = _normalize_optional_int(listing_price_krw) or 0
    normalized_fair_price_krw = _normalize_optional_int(fair_price_krw) or 0

    diff_amount_krw = normalized_fair_price_krw - normalized_listing_price_krw
    diff_ratio = 0.0
    if normalized_fair_price_krw > 0:
        diff_ratio = (diff_amount_krw / normalized_fair_price_krw) * 100

    try:
        cursor.execute(
            """
            INSERT INTO listing_analysis_results (
                analysis_job_id,
                trigger_reason,
                search_keyword,
                title,
                body_text,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                listing_price_krw,
                fair_price_krw,
                diff_amount_krw,
                diff_ratio,
                is_alert_target,
                alert_created
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _normalize_optional_int(analysis_job_id),
                _normalize_optional_text(trigger_reason),
                _normalize_optional_text(search_keyword),
                normalized_title,
                _normalize_optional_text(body_text),
                normalized_product_type,
                normalized_chip,
                normalized_screen_inch,
                normalized_ram_gb,
                normalized_ssd_gb,
                normalized_listing_price_krw,
                normalized_fair_price_krw,
                diff_amount_krw,
                round(diff_ratio, 2),
                bool(is_alert_target),
                bool(alert_created),
            ),
        )
        return {
            "inserted": True,
            "analysis_result_id": int(cursor.lastrowid),
            "diff_ratio": round(diff_ratio, 2),
        }
    except Exception as exc:
        if "Unknown column" not in str(exc):
            raise

    try:
        cursor.execute(
            """
            INSERT INTO listing_analysis_results (
                analysis_job_id,
                trigger_reason,
                search_keyword,
                title,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                listing_price_krw,
                fair_price_krw,
                diff_amount_krw,
                diff_ratio,
                is_alert_target,
                alert_created
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _normalize_optional_int(analysis_job_id),
                _normalize_optional_text(trigger_reason),
                _normalize_optional_text(search_keyword),
                normalized_title,
                normalized_product_type,
                normalized_chip,
                normalized_screen_inch,
                normalized_ram_gb,
                normalized_ssd_gb,
                normalized_listing_price_krw,
                normalized_fair_price_krw,
                diff_amount_krw,
                round(diff_ratio, 2),
                bool(is_alert_target),
                bool(alert_created),
            ),
        )
        return {
            "inserted": True,
            "analysis_result_id": int(cursor.lastrowid),
            "diff_ratio": round(diff_ratio, 2),
        }
    except Exception as exc:
        if "Unknown column" not in str(exc):
            raise

    cursor.execute(
        """
        INSERT INTO listing_analysis_results (
            title,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            listing_price_krw,
            fair_price_krw,
            diff_amount_krw,
            diff_ratio,
            is_alert_target
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            normalized_title,
            normalized_product_type,
            normalized_chip,
            normalized_screen_inch,
            normalized_ram_gb,
            normalized_ssd_gb,
            normalized_listing_price_krw,
            normalized_fair_price_krw,
            diff_amount_krw,
            round(diff_ratio, 2),
            bool(is_alert_target),
        ),
    )
    return {
        "inserted": True,
        "analysis_result_id": int(cursor.lastrowid),
        "diff_ratio": round(diff_ratio, 2),
    }


def _mark_seen_product_status(product_id, status):
    normalized_product_id = _normalize_optional_int(product_id)
    if normalized_product_id is None:
        return

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        mark_seen_product_analyzed(cursor, normalized_product_id, status=status)
        connection.commit()
    except Exception as exc:
        print(f"[analysis_pipeline] seen analyzed 상태 갱신 실패: {exc}")
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def analyze_product_for_watch_rule(job):
    if not isinstance(job, dict):
        raise ValueError("invalid_job")

    job_id = _normalize_optional_int(job.get("id"))
    user_id = _normalize_optional_text(job.get("user_id"))
    watch_rule_id = _normalize_optional_watch_rule_id(job.get("watch_rule_id"))
    trigger_reason = _normalize_optional_text(job.get("trigger_reason"))
    product_id = _normalize_optional_text(job.get("product_id"))
    url = _normalize_optional_text(job.get("url"))
    search_keyword = _normalize_optional_text(job.get("search_keyword"))
    sort_date = _coerce_datetime(job.get("sort_date"))

    if not url:
        raise ValueError("analysis_job_url_missing")
    if user_id is None:
        raise ValueError("analysis_job_user_id_missing")

    listing_snapshot = _build_listing_snapshot_from_job(job)
    title = _normalize_optional_text(listing_snapshot.get("title"))
    listing_price_krw = _normalize_optional_int(listing_snapshot.get("price"))
    description = None
    self_check_fields = {}

    parsed_spec = _safe_parse_listing_from_title(title, self_check_fields=self_check_fields)
    parsing_source_text = f"{title or ''}".strip()
    risk_result = analyze_risk(parsing_source_text, self_check_fields=self_check_fields)

    detail_fetch_performed = False
    detail_fetch_reason = None
    detail_skipped_reason = None
    detail_fetch_error = None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            previous_seen_product = get_seen_product(cursor, product_id)
        except Exception:
            previous_seen_product = None

        (
            pre_fair_price_krw,
            pre_target_price_krw,
            pre_alert_drop_rate_percent,
            pre_alert_price_direction,
            pre_min_price_krw,
            pre_max_price_krw,
            pre_price_error_reason,
            pre_fair_price_source,
        ) = _resolve_price_rules(
            cursor,
            user_id,
            parsed_spec,
            watch_rule_id=watch_rule_id,
        )

        detail_fetch_needed, detail_decision_reason = should_fetch_detail(
            listing_snapshot,
            trigger_reason,
            parsed_spec,
            target_price_krw=pre_target_price_krw,
        )

        if detail_fetch_needed:
            detail_fetch_performed = True
            detail_fetch_reason = detail_decision_reason
            try:
                html = fetch_html(url)
                parsed_page = parse_joongna_listing_page(html)

                parsed_title = _normalize_optional_text(parsed_page.get("title"))
                if parsed_title is not None:
                    title = parsed_title

                description = _normalize_optional_text(parsed_page.get("description"))

                parsed_listing_price_krw = _normalize_optional_int(parsed_page.get("listing_price_krw"))
                if parsed_listing_price_krw is not None:
                    listing_price_krw = parsed_listing_price_krw

                self_check_fields = parsed_page.get("self_check_fields") or {}
                parsing_source_text = f"{title or ''} {description or ''}".strip()
                if parsing_source_text:
                    try:
                        parsed_spec = parse_listing_title(
                            parsing_source_text,
                            self_check_fields=self_check_fields,
                        )
                    except Exception:
                        parsed_spec = _build_parse_failure_result("detail_parse_exception")
                else:
                    parsed_spec = _build_parse_failure_result("detail_parse_empty")

                risk_result = analyze_risk(parsing_source_text, self_check_fields=self_check_fields)
            except Exception as detail_exc:
                detail_fetch_error = str(detail_exc)
                print(
                    "[analysis_pipeline] detail fetch 실패, 목록 정보로 fallback "
                    f"(product_id={product_id}, reason={detail_exc})"
                )
        else:
            detail_skipped_reason = detail_decision_reason

        content_snapshot = build_listing_content_snapshot(
            title=title,
            price_krw=listing_price_krw,
            body_text=description,
            self_check_fields=self_check_fields,
        )
        previous_body_hash = _normalize_optional_text((previous_seen_product or {}).get("last_body_hash"))
        previous_self_check_hash = _normalize_optional_text((previous_seen_product or {}).get("last_self_check_hash"))
        current_body_hash = _normalize_optional_text(content_snapshot.get("body_hash"))
        current_self_check_hash = _normalize_optional_text(content_snapshot.get("self_check_hash"))

        content_change_fields = []
        if trigger_reason == CHANGE_REASON_TITLE_CHANGED:
            content_change_fields.append("title")
        if trigger_reason == CHANGE_REASON_PRICE_CHANGED:
            content_change_fields.append("price")
        if previous_body_hash and current_body_hash and previous_body_hash != current_body_hash:
            content_change_fields.append("body_text")
        if (
            previous_self_check_hash
            and current_self_check_hash
            and previous_self_check_hash != current_self_check_hash
        ):
            content_change_fields.append("self_check")

        if (
            trigger_reason != "new"
            and (
                trigger_reason == CHANGE_REASON_CONTENT_CHANGED
                or len(content_change_fields) > 0
            )
        ):
            trigger_reason = CHANGE_REASON_CONTENT_CHANGED

        if product_id is not None:
            update_seen_product_content_snapshot(
                cursor,
                product_id,
                title=title,
                price_krw=listing_price_krw,
                body_text=description,
                self_check_fields=self_check_fields,
                changed_reason=trigger_reason,
            )

        if trigger_reason == "unchanged":
            return {
                "ok": True,
                "analysis_job_id": job_id,
                "watch_rule_id": watch_rule_id,
                "product_id": product_id,
                "url": url,
                "title": title,
                "listing_price_krw": listing_price_krw,
                "fair_price_krw": None,
                "target_price_krw": None,
                "drop_rate_percent": None,
                "alert_drop_rate_percent": None,
                "alert_price_direction": None,
                "min_price_krw": None,
                "max_price_krw": None,
                "matched_watch_rule": bool(parsed_spec.get("parse_success")) if isinstance(parsed_spec, dict) else False,
                "is_alert_target": False,
                "alert_created": False,
                "alert_event_id": None,
                "alert_dispatch_status": None,
                "alert_dispatch_reason": None,
                "alert_skip_reason": "unchanged_skip_analysis",
                "fair_price_source": pre_fair_price_source,
                "sort_date": sort_date,
                "saved_window_allowed": True,
                "analysis_skipped": True,
                "analysis_skip_reason": "unchanged",
                "detail_fetch_performed": detail_fetch_performed,
                "detail_fetch_reason": detail_fetch_reason,
                "detail_skipped_reason": detail_skipped_reason or "unchanged",
                "detail_fetch_error": detail_fetch_error,
                "content_change_fields": content_change_fields,
            }

        if detail_fetch_performed and detail_fetch_error is None:
            (
                fair_price_krw,
                target_price_krw,
                alert_drop_rate_percent,
                alert_price_direction,
                min_price_krw,
                max_price_krw,
                price_error_reason,
                fair_price_source,
            ) = _resolve_price_rules(
                cursor,
                user_id,
                parsed_spec,
                watch_rule_id=watch_rule_id,
            )
        else:
            fair_price_krw = pre_fair_price_krw
            target_price_krw = pre_target_price_krw
            alert_drop_rate_percent = pre_alert_drop_rate_percent
            alert_price_direction = pre_alert_price_direction
            min_price_krw = pre_min_price_krw
            max_price_krw = pre_max_price_krw
            price_error_reason = pre_price_error_reason
            fair_price_source = pre_fair_price_source

        matched_watch_rule = bool(parsed_spec.get("parse_success")) if isinstance(parsed_spec, dict) else False

        saved_window_allowed, saved_window_reason = _evaluate_watch_rule_saved_window(
            cursor,
            user_id=user_id,
            watch_rule_id=watch_rule_id,
            sort_date=sort_date,
        )

        drop_rate_percent = None
        if fair_price_krw is not None and fair_price_krw > 0 and listing_price_krw is not None:
            drop_rate_percent = ((fair_price_krw - listing_price_krw) / fair_price_krw) * 100

        is_alert_target = False
        alert_skip_reason = price_error_reason
        is_content_changed_alert = trigger_reason == CHANGE_REASON_CONTENT_CHANGED
        if not saved_window_allowed:
            is_alert_target = False
            alert_skip_reason = saved_window_reason or "sort_date_before_saved_at"
        elif (
            matched_watch_rule
            and fair_price_krw is not None
            and fair_price_krw > 0
            and listing_price_krw is not None
            and target_price_krw is not None
        ):
            is_alert_target = is_listing_alert_match(
                listing_price_krw,
                target_price_krw,
                alert_price_direction,
            )
            if is_alert_target and not passes_price_bounds(
                listing_price_krw,
                alert_price_direction,
                min_price_krw=min_price_krw,
                max_price_krw=max_price_krw,
            ):
                is_alert_target = False
                if (
                    normalize_alert_price_direction(alert_price_direction) == BELOW_OR_EQUAL
                    and min_price_krw is not None
                    and listing_price_krw < min_price_krw
                ):
                    alert_skip_reason = "below_min_price_bound"
                elif (
                    normalize_alert_price_direction(alert_price_direction) != BELOW_OR_EQUAL
                    and max_price_krw is not None
                    and listing_price_krw > max_price_krw
                ):
                    alert_skip_reason = "above_max_price_bound"
                else:
                    alert_skip_reason = "price_outside_bounds"
            elif not is_alert_target:
                if normalize_alert_price_direction(alert_price_direction) == BELOW_OR_EQUAL:
                    alert_skip_reason = "drop_rate_below_threshold"
                else:
                    alert_skip_reason = "price_below_threshold"
        elif alert_skip_reason is None:
            alert_skip_reason = "price_condition_missing"

        if is_content_changed_alert:
            is_alert_target = True
            alert_skip_reason = None

        alert_create_result = {
            "created": False,
            "alert_id": None,
        }
        alert_message = None
        alert_change_fingerprint = _build_alert_change_fingerprint(
            trigger_reason=trigger_reason,
            sort_date=sort_date,
            content_revision_hash=content_snapshot.get("content_revision_hash"),
            title=title,
            listing_price_krw=listing_price_krw,
        )
        if is_alert_target:
            seller_info = _resolve_seller_info_for_alert(
                cursor,
                product_id=product_id,
                fallback_store_seq=listing_snapshot.get("seller_store_seq"),
                fallback_store_name=listing_snapshot.get("seller_store_name"),
            )
            if is_content_changed_alert:
                alert_message = _build_content_changed_alert_message(
                    title=title,
                    url=url,
                    changed_fields=content_change_fields,
                )
            else:
                alert_message = _build_alert_message(
                    title=title,
                    listing_price_krw=listing_price_krw or 0,
                    fair_price_krw=fair_price_krw or 0,
                    drop_rate_percent=drop_rate_percent,
                    url=url,
                )
            risk_keywords = risk_result.get("risk_keywords")
            risk_keywords_json = None
            if isinstance(risk_keywords, list):
                try:
                    risk_keywords_json = json.dumps(risk_keywords, ensure_ascii=False)
                except Exception:
                    risk_keywords_json = None

            alert_create_result = maybe_create_alert_event(
                cursor,
                analysis_job_id=job_id,
                user_id=user_id,
                watch_rule_id=watch_rule_id,
                product_id=product_id,
                url=url,
                title=title,
                price_krw=listing_price_krw,
                fair_price_krw=fair_price_krw,
                target_price_krw=target_price_krw,
                drop_rate_percent=drop_rate_percent,
                trigger_reason=trigger_reason,
                message=alert_message,
                source="joongna",
                parsed_spec=parsed_spec,
                alert_drop_rate_percent=alert_drop_rate_percent,
                alert_price_direction=alert_price_direction,
                risk_result={
                    "risk_level": risk_result.get("risk_level"),
                    "risk_score": risk_result.get("risk_score"),
                    "risk_keywords_json": risk_keywords_json,
                    "is_exchange_post": risk_result.get("is_exchange_post"),
                    "trade_type": risk_result.get("trade_type"),
                },
                body_excerpt=_build_body_excerpt(description),
                body_text=_normalize_optional_text(description),
                sort_date=sort_date,
                change_fingerprint=alert_change_fingerprint,
                seller_store_seq=seller_info.get("seller_store_seq"),
                seller_store_name=seller_info.get("seller_store_name"),
            )

        result_save = save_listing_analysis_result(
            cursor,
            analysis_job_id=job_id,
            trigger_reason=trigger_reason,
            search_keyword=search_keyword,
            title=title,
            parsed_spec=parsed_spec,
            body_text=description,
            listing_price_krw=listing_price_krw,
            fair_price_krw=fair_price_krw,
            is_alert_target=is_alert_target,
            matched_watch_rule=matched_watch_rule,
            alert_created=bool(alert_create_result.get("created")),
        )

        save_success_log(
            cursor,
            user_id=user_id,
            url=url,
            source="joongna",
            title=_normalize_optional_text(title) or "UNKNOWN",
            listing_price_krw=listing_price_krw or 0,
            parsed_spec=parsed_spec,
            fair_price_krw=fair_price_krw or 0,
            diff_ratio=_normalize_optional_float(result_save.get("diff_ratio")) or 0.0,
            is_alert_target=bool(is_alert_target),
            risk_result=risk_result,
            body_text=description,
        )

        connection.commit()

        alert_dispatch_result = None
        created_alert_id = _normalize_optional_int(alert_create_result.get("alert_id"))
        if alert_create_result.get("created") and created_alert_id is not None:
            try:
                alert_dispatch_result = dispatch_alert_event_immediately(
                    created_alert_id,
                    fallback_alert={
                        "id": created_alert_id,
                        "analysis_job_id": job_id,
                        "user_id": user_id,
                        "product_id": product_id,
                        "title": title,
                        "url": url,
                        "price_krw": listing_price_krw,
                        "fair_price_krw": fair_price_krw,
                        "target_price_krw": target_price_krw,
                        "drop_rate_percent": drop_rate_percent,
                        "sort_date": sort_date,
                        "trigger_reason": trigger_reason,
                        "change_fingerprint": alert_change_fingerprint,
                        "message": alert_message,
                    },
                )
            except Exception as dispatch_exc:
                alert_dispatch_result = {
                    "status": "dispatch_exception",
                    "reason": str(dispatch_exc),
                }
                print(
                    "[analysis_pipeline] immediate alert dispatch failed: "
                    f"alert_id={created_alert_id}, error={dispatch_exc}"
                )

        return {
            "ok": True,
            "analysis_job_id": job_id,
            "watch_rule_id": watch_rule_id,
            "product_id": product_id,
            "url": url,
            "title": title,
            "listing_price_krw": listing_price_krw,
            "fair_price_krw": fair_price_krw,
            "target_price_krw": target_price_krw,
            "drop_rate_percent": drop_rate_percent,
            "alert_drop_rate_percent": alert_drop_rate_percent,
            "alert_price_direction": alert_price_direction,
            "min_price_krw": min_price_krw,
            "max_price_krw": max_price_krw,
            "matched_watch_rule": matched_watch_rule,
            "is_alert_target": is_alert_target,
            "alert_created": bool(alert_create_result.get("created")),
            "alert_event_id": alert_create_result.get("alert_id"),
            "alert_dispatch_status": (
                _normalize_optional_text(alert_dispatch_result.get("status"))
                if isinstance(alert_dispatch_result, dict)
                else None
            ),
            "alert_dispatch_reason": (
                _normalize_optional_text(alert_dispatch_result.get("reason"))
                if isinstance(alert_dispatch_result, dict)
                else None
            ),
            "alert_skip_reason": alert_skip_reason,
            "fair_price_source": fair_price_source,
            "sort_date": sort_date,
            "saved_window_allowed": saved_window_allowed,
            "detail_fetch_performed": detail_fetch_performed,
            "detail_fetch_reason": detail_fetch_reason,
            "detail_skipped_reason": detail_skipped_reason,
            "detail_fetch_error": detail_fetch_error,
            "analysis_skipped": False,
            "content_change_fields": content_change_fields,
        }
    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def process_analysis_job(job):
    job_id = _normalize_optional_int(job.get("id")) if isinstance(job, dict) else None
    if job_id is None:
        raise ValueError("invalid_job")

    started = mark_analysis_job_started(job_id)
    if not started:
        return {
            "ok": True,
            "skipped": True,
            "job_id": job_id,
            "reason": "job_not_pending",
        }

    try:
        result = analyze_product_for_watch_rule(job)
        mark_analysis_job_done(job_id)
        _mark_seen_product_status(job.get("product_id"), "analyzed")
        return {
            "ok": True,
            "job_id": job_id,
            "result": result,
        }
    except Exception as exc:
        mark_analysis_job_failed(job_id, str(exc))
        _mark_seen_product_status(job.get("product_id"), "analysis_failed")
        return {
            "ok": False,
            "job_id": job_id,
            "reason": str(exc),
        }


def process_pending_analysis_jobs(limit=20):
    jobs = get_pending_analysis_jobs(limit=limit)
    stats = {
        "fetched": len(jobs),
        "fetched_list_count": len(jobs),
        "done": 0,
        "skipped": 0,
        "failed": 0,
        "detail_fetch_count": 0,
        "detail_skipped_count": 0,
        "detail_fetch_reason_counts": {},
        "unchanged_detail_skipped_count": 0,
        "results": [],
    }

    for job in jobs:
        try:
            result = process_analysis_job(job)
            stats["results"].append(result)
            if result.get("skipped"):
                stats["skipped"] += 1
            elif result.get("ok"):
                stats["done"] += 1

                analysis_result = result.get("result")
                if isinstance(analysis_result, dict):
                    detail_fetch_performed = bool(analysis_result.get("detail_fetch_performed"))
                    if detail_fetch_performed:
                        stats["detail_fetch_count"] += 1
                        fetch_reason = _normalize_optional_text(analysis_result.get("detail_fetch_reason")) or "unknown"
                        reason_counts = stats.get("detail_fetch_reason_counts") or {}
                        reason_counts[fetch_reason] = int(reason_counts.get(fetch_reason, 0)) + 1
                        stats["detail_fetch_reason_counts"] = reason_counts
                    else:
                        stats["detail_skipped_count"] += 1
                        skip_reason = _normalize_optional_text(analysis_result.get("detail_skipped_reason"))
                        if skip_reason == "unchanged":
                            stats["unchanged_detail_skipped_count"] += 1
            else:
                stats["failed"] += 1
        except Exception as exc:
            job_id = _normalize_optional_int(job.get("id")) if isinstance(job, dict) else None
            if job_id is not None:
                try:
                    mark_analysis_job_failed(job_id, str(exc))
                except Exception:
                    pass
            stats["failed"] += 1
            stats["results"].append(
                {
                    "ok": False,
                    "job_id": job_id,
                    "reason": str(exc),
                }
            )

    return stats
