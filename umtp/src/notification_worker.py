import os
import json
import re
from datetime import datetime

from dotenv import load_dotenv

try:
    from src.alert_price_direction import ABOVE_OR_EQUAL, BELOW_OR_EQUAL, normalize_alert_price_direction
    from src.db import get_connection
    from src.push_token_service import (
        deactivate_user_push_token,
        list_active_user_push_tokens,
        mark_user_push_token_sent,
    )
    from src.telegram_notifier import send_telegram_alert
    from src.user_alert_settings import resolve_user_alert_delivery_policy
except ModuleNotFoundError:
    from alert_price_direction import ABOVE_OR_EQUAL, BELOW_OR_EQUAL, normalize_alert_price_direction
    from db import get_connection
    from push_token_service import (
        deactivate_user_push_token,
        list_active_user_push_tokens,
        mark_user_push_token_sent,
    )
    from telegram_notifier import send_telegram_alert
    from user_alert_settings import resolve_user_alert_delivery_policy

try:  # pragma: no cover - optional runtime dependency
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception:  # pragma: no cover
    firebase_admin = None
    credentials = None
    messaging = None


_FIREBASE_INIT_ATTEMPTED = False
_FIREBASE_INIT_ERROR = None
CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON = "condition_change_candidate_notice"


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_required_text(value, field_name):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ValueError(f"invalid_{field_name}")
    return normalized


def _normalize_optional_int(value, field_name):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field_name}") from exc


def _safe_int(value):
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


def _normalize_optional_bool(value):
    if value is None:
        return None
    return bool(value)


def _safe_json_loads(value, *, fallback):
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    if isinstance(decoded, type(fallback)):
        return decoded
    return fallback


def _parse_risk_keywords(value):
    keywords = _safe_json_loads(value, fallback=[])
    if isinstance(keywords, list):
        return [str(item) for item in keywords if isinstance(item, (str, int, float))]
    return []


def _build_alert_condition_label(alert_price_direction):
    if normalize_alert_price_direction(alert_price_direction) == ABOVE_OR_EQUAL:
        return "이 가격 이상이면 알림"
    return "이 가격 이하이면 알림"


def _build_formatted_risk_label(risk_level):
    normalized = _normalize_optional_text(risk_level)
    if normalized is None:
        return "정보 없음"
    normalized_upper = normalized.upper()
    if normalized_upper == "LOW":
        return "낮음"
    if normalized_upper == "MEDIUM":
        return "주의"
    if normalized_upper in {"HIGH", "EXCLUDE"}:
        return "위험"
    if normalized_upper == "NONE":
        return "낮음"
    return normalized


def _build_trade_type_flags(*, is_exchange_post, trade_type, risk_level):
    normalized_trade_type = (_normalize_optional_text(trade_type) or "").lower()
    normalized_risk_level = (_normalize_optional_text(risk_level) or "").upper()

    is_exchange = bool(is_exchange_post) or normalized_trade_type in {"exchange", "trade"}
    is_free = normalized_trade_type in {"free", "giveaway", "donation", "share"}
    is_suspicious = normalized_risk_level in {"HIGH", "EXCLUDE"}

    return {
        "is_exchange": is_exchange,
        "is_free": is_free,
        "is_suspicious": is_suspicious,
    }


def _build_body_excerpt(value, *, max_len=500):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len].rstrip()}..."


def _coerce_product_seq(value):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None

    digits = "".join(ch for ch in normalized if ch.isdigit())
    if not digits:
        return None

    try:
        parsed = int(digits)
    except (TypeError, ValueError):
        return None

    if parsed <= 0:
        return None
    return parsed


def _extract_product_seq_from_url(value):
    normalized_url = _normalize_optional_text(value)
    if normalized_url is None:
        return None

    match = re.search(r"/product/(\d+)", normalized_url)
    if not match:
        return None

    try:
        parsed = int(match.group(1))
    except (TypeError, ValueError):
        return None

    if parsed <= 0:
        return None
    return parsed


def _resolve_alert_product_id_for_image_lookup(alert):
    if not isinstance(alert, dict):
        return None

    normalized_product_id = _normalize_optional_text(alert.get("product_id"))
    if normalized_product_id is not None:
        return normalized_product_id

    seq_from_url = _extract_product_seq_from_url(alert.get("url"))
    if seq_from_url is None:
        return None
    return str(seq_from_url)


def _fetch_listing_image_urls(cursor, product_ids):
    if cursor is None or not hasattr(cursor, "execute") or not hasattr(cursor, "fetchall"):
        return {}

    sequence_ids = []
    for product_id in product_ids or []:
        seq = _coerce_product_seq(product_id)
        if seq is None:
            continue
        if seq not in sequence_ids:
            sequence_ids.append(seq)

    if not sequence_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(sequence_ids))
    query = (
        "SELECT seq, image_url "
        "FROM joongna_seen_products "
        f"WHERE seq IN ({placeholders})"
    )

    try:
        cursor.execute(query, tuple(sequence_ids))
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" in lowered or "doesn't exist" in lowered:
            return {}
        raise

    rows = cursor.fetchall() or []
    image_url_map = {}
    for row in rows:
        if isinstance(row, dict):
            seq = _coerce_product_seq(row.get("seq"))
            image_url = _normalize_optional_text(row.get("image_url"))
        else:
            seq = _coerce_product_seq(row[0]) if len(row) > 0 else None
            image_url = _normalize_optional_text(row[1]) if len(row) > 1 else None

        if seq is None or image_url is None:
            continue
        image_url_map[str(seq)] = image_url

    return image_url_map


def _resolve_listing_image_url(product_id, image_url_map):
    seq = _coerce_product_seq(product_id)
    if seq is None:
        return None
    return _normalize_optional_text((image_url_map or {}).get(str(seq)))


def _fetch_listing_image_url_by_product_id(product_id):
    normalized_seq = _coerce_product_seq(product_id)
    if normalized_seq is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT image_url
                FROM joongna_seen_products
                WHERE seq = %s
                LIMIT 1
                """,
                (normalized_seq,),
            )
            row = cursor.fetchone()
        except Exception as exc:
            lowered = str(exc).lower()
            if "unknown column" in lowered or "doesn't exist" in lowered:
                return None
            raise

        if not row:
            return None

        if isinstance(row, dict):
            return _normalize_optional_text(row.get("image_url"))
        if isinstance(row, (tuple, list)) and row:
            return _normalize_optional_text(row[0])
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _fetch_listing_title_by_product_id(product_id):
    normalized_seq = _coerce_product_seq(product_id)
    if normalized_seq is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT title, last_title
                FROM joongna_seen_products
                WHERE seq = %s
                LIMIT 1
                """,
                (normalized_seq,),
            )
            row = cursor.fetchone()
        except Exception as exc:
            lowered = str(exc).lower()
            if "unknown column" in lowered or "doesn't exist" in lowered:
                return None
            raise

        if not row:
            return None

        if isinstance(row, dict):
            return _normalize_optional_text(row.get("last_title")) or _normalize_optional_text(row.get("title"))
        if isinstance(row, (tuple, list)):
            last_title = _normalize_optional_text(row[1]) if len(row) > 1 else None
            title = _normalize_optional_text(row[0]) if len(row) > 0 else None
            return last_title or title
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _format_krw_display(value):
    normalized = _safe_int(value)
    if normalized is None:
        return "정보 없음"
    return f"{normalized:,}원"


def _format_percent_display(value):
    normalized = _normalize_optional_float(value)
    if normalized is None:
        return "정보 없음"
    return f"{normalized:.2f}%"


def _build_spec_summary(alert):
    tokens = []

    product_type = _normalize_optional_text(alert.get("product_type"))
    if product_type is not None:
        tokens.append(product_type)

    chip = _normalize_optional_text(alert.get("chip"))
    if chip is not None:
        tokens.append(chip)

    screen_inch = _safe_int(alert.get("screen_inch"))
    if screen_inch is not None:
        tokens.append(f"{screen_inch}인치")

    ram_gb = _safe_int(alert.get("ram_gb"))
    if ram_gb is not None:
        tokens.append(f"{ram_gb}GB")

    ssd_gb = _safe_int(alert.get("ssd_gb"))
    if ssd_gb is not None:
        tokens.append(f"{ssd_gb}GB SSD")

    if not tokens:
        return "분류 정보 없음"
    return " · ".join(tokens)


def _resolve_alert_condition_label_for_display(alert):
    explicit_label = _normalize_optional_text(alert.get("alert_condition_label"))
    if explicit_label is not None:
        return explicit_label
    return _build_alert_condition_label(alert.get("alert_price_direction"))


def _resolve_risk_label_for_display(alert):
    explicit_label = _normalize_optional_text(alert.get("formatted_risk_label"))
    if explicit_label is not None:
        return explicit_label
    return _build_formatted_risk_label(alert.get("risk_level"))


def _resolve_body_text_for_display(alert):
    body_text = _normalize_optional_text(alert.get("body_text"))
    if body_text is not None:
        return body_text

    body_excerpt = _normalize_optional_text(alert.get("body_excerpt"))
    if body_excerpt is not None:
        return body_excerpt

    return "본문 내용 없음"


def _resolve_url_for_display(alert):
    product_url = _normalize_optional_text(alert.get("product_url"))
    if product_url is not None:
        return product_url
    url = _normalize_optional_text(alert.get("url"))
    if url is not None:
        return url
    return "URL 정보 없음"


def _resolve_title_text_for_display(alert):
    title = _normalize_optional_text(alert.get("title"))
    if title is not None:
        return title
    return "제목 없음"


def _resolve_product_type_text_for_display(alert):
    product_type = _normalize_optional_text(alert.get("product_type"))
    return product_type or "분류 정보 없음"


def _resolve_chip_text_for_display(alert):
    chip = _normalize_optional_text(alert.get("chip"))
    return chip or "정보 없음"


def _resolve_screen_inch_text_for_display(alert):
    screen_inch = _safe_int(alert.get("screen_inch"))
    if screen_inch is None or screen_inch <= 0:
        return "정보 없음"
    return f"{screen_inch}인치"


def _resolve_ram_text_for_display(alert):
    ram_gb = _safe_int(alert.get("ram_gb"))
    if ram_gb is None or ram_gb <= 0:
        return "정보 없음"
    return f"{ram_gb}GB"


def _resolve_ssd_text_for_display(alert):
    ssd_gb = _safe_int(alert.get("ssd_gb"))
    if ssd_gb is None or ssd_gb <= 0:
        return "정보 없음"
    return f"{ssd_gb}GB"


def _resolve_risk_score_for_display(alert):
    risk_score = _safe_int(alert.get("risk_score"))
    if risk_score is None:
        return "정보 없음"
    return str(risk_score)


def _resolve_risk_keywords_text_for_display(alert):
    parsed_keywords = _parse_risk_keywords(alert.get("risk_keywords"))
    if not parsed_keywords:
        return "특이사항 없음"
    return ", ".join(parsed_keywords)


def _resolve_analyzed_at_text_for_display(alert):
    analyzed_at = alert.get("analyzed_at")
    if analyzed_at is not None:
        normalized = _normalize_optional_text(analyzed_at)
        return normalized or str(analyzed_at)

    created_at = alert.get("created_at")
    if created_at is not None:
        normalized = _normalize_optional_text(created_at)
        return normalized or str(created_at)

    return "분석 시각 정보 없음"


def _resolve_trade_flags_text_for_display(alert):
    trade_type_flags = alert.get("trade_type_flags")
    if isinstance(trade_type_flags, dict):
        is_exchange = bool(trade_type_flags.get("is_exchange"))
        is_free = bool(trade_type_flags.get("is_free"))
        is_suspicious = bool(trade_type_flags.get("is_suspicious"))
    else:
        flags = _build_trade_type_flags(
            is_exchange_post=_normalize_optional_bool(alert.get("is_exchange_post")),
            trade_type=_normalize_optional_text(alert.get("trade_type")),
            risk_level=_normalize_optional_text(alert.get("risk_level")),
        )
        is_exchange = bool(flags.get("is_exchange"))
        is_free = bool(flags.get("is_free"))
        is_suspicious = bool(flags.get("is_suspicious"))

    labels = []
    if is_exchange:
        labels.append("교환")
    if is_free:
        labels.append("나눔")
    if is_suspicious:
        labels.append("허위/의심")
    if not labels:
        return "특이사항 없음"
    return ", ".join(labels)


def _resolve_special_notes_text_for_display(alert, *, risk_label=None, risk_keywords_text=None, trade_flags_text=None):
    resolved_risk_label = risk_label or _resolve_risk_label_for_display(alert)
    resolved_risk_keywords_text = risk_keywords_text or _resolve_risk_keywords_text_for_display(alert)
    resolved_trade_flags_text = trade_flags_text or _resolve_trade_flags_text_for_display(alert)

    notes = []
    if resolved_risk_label in {"주의", "위험"}:
        notes.append(f"위험도 {resolved_risk_label}")
    if resolved_trade_flags_text not in {"특이사항 없음", "정보 없음"}:
        notes.append(f"거래 유형: {resolved_trade_flags_text}")
    if resolved_risk_keywords_text != "특이사항 없음":
        notes.append(f"위험 키워드: {resolved_risk_keywords_text}")

    if not notes:
        return "특이사항 없음"
    return " / ".join(notes)


def _build_telegram_detail_row(label, value):
    normalized_label = _normalize_optional_text(label) or "-"
    normalized_value = _normalize_optional_text(value) or "정보 없음"
    return f"{normalized_label}\n{normalized_value}"


def _fetch_latest_log_details(cursor, *, user_id, url):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_url = _normalize_optional_text(url)
    if normalized_user_id is None or normalized_url is None:
        return {}

    try:
        cursor.execute(
            """
            SELECT
                source,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                confidence_score,
                risk_level,
                risk_score,
                risk_keywords,
                is_exchange_post,
                trade_type,
                body_text,
                created_at
            FROM url_analysis_logs
            WHERE user_id = %s
              AND url = %s
              AND status = 'success'
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized_user_id, normalized_url),
        )
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" not in lowered_exc and "doesn't exist" not in lowered_exc:
            raise
        try:
            cursor.execute(
                """
                SELECT
                source,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                NULL AS body_text,
                created_at
            FROM url_analysis_logs
                WHERE user_id = %s
                  AND url = %s
                  AND status = 'success'
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_user_id, normalized_url),
            )
        except Exception:
            return {}

    row = cursor.fetchone()
    if not row:
        return {}
    return row


def _fetch_analysis_job_details(cursor, *, analysis_job_id):
    normalized_analysis_job_id = _safe_int(analysis_job_id)
    if normalized_analysis_job_id is None:
        return {}

    try:
        cursor.execute(
            """
            SELECT
                source,
                url,
                title,
                price_krw,
                sort_date,
                created_at
            FROM analysis_jobs
            WHERE id = %s
            LIMIT 1
            """,
            (normalized_analysis_job_id,),
        )
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" in lowered_exc or "doesn't exist" in lowered_exc:
            return {}
        raise

    row = cursor.fetchone()
    if not row:
        return {}
    return row


def _fetch_listing_result_details(cursor, *, analysis_job_id):
    normalized_analysis_job_id = _safe_int(analysis_job_id)
    if normalized_analysis_job_id is None:
        return {}

    try:
        cursor.execute(
            """
            SELECT
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                body_text,
                created_at
            FROM listing_analysis_results
            WHERE analysis_job_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized_analysis_job_id,),
        )
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" in lowered_exc or "doesn't exist" in lowered_exc:
            return {}
        raise

    row = cursor.fetchone()
    if not row:
        return {}
    return row


def _apply_missing_text_field(alert, key, *candidates):
    if _normalize_optional_text(alert.get(key)) is not None:
        return
    for candidate in candidates:
        normalized = _normalize_optional_text(candidate)
        if normalized is not None:
            alert[key] = normalized
            return


def _apply_missing_int_field(alert, key, *candidates, allow_zero=False):
    existing = _safe_int(alert.get(key))
    if existing is not None and (allow_zero or existing > 0):
        return

    for candidate in candidates:
        parsed = _safe_int(candidate)
        if parsed is None:
            continue
        if not allow_zero and parsed <= 0:
            continue
        alert[key] = parsed
        return


def _enrich_alert_for_display(alert):
    if not isinstance(alert, dict):
        return

    normalized_user_id = _normalize_optional_text(alert.get("user_id"))
    normalized_url = _normalize_optional_text(alert.get("url"))
    normalized_analysis_job_id = _safe_int(alert.get("analysis_job_id"))
    if normalized_user_id is None:
        return

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        analysis_job_detail = {}
        listing_result_detail = {}
        log_detail = {}

        if normalized_analysis_job_id is not None:
            analysis_job_detail = _fetch_analysis_job_details(
                cursor,
                analysis_job_id=normalized_analysis_job_id,
            )
            listing_result_detail = _fetch_listing_result_details(
                cursor,
                analysis_job_id=normalized_analysis_job_id,
            )

        if normalized_url is not None:
            log_detail = _fetch_latest_log_details(
                cursor,
                user_id=normalized_user_id,
                url=normalized_url,
            )

        _apply_missing_text_field(
            alert,
            "source",
            analysis_job_detail.get("source"),
            log_detail.get("source"),
            "joongna",
        )
        _apply_missing_text_field(alert, "url", analysis_job_detail.get("url"))
        _apply_missing_text_field(alert, "product_url", alert.get("url"), analysis_job_detail.get("url"))
        _apply_missing_text_field(alert, "title", analysis_job_detail.get("title"))
        _apply_missing_int_field(alert, "price_krw", analysis_job_detail.get("price_krw"), allow_zero=True)

        _apply_missing_text_field(
            alert,
            "product_type",
            listing_result_detail.get("product_type"),
            log_detail.get("product_type"),
        )
        _apply_missing_text_field(
            alert,
            "chip",
            listing_result_detail.get("chip"),
            log_detail.get("chip"),
        )
        _apply_missing_int_field(
            alert,
            "screen_inch",
            listing_result_detail.get("screen_inch"),
            log_detail.get("screen_inch"),
        )
        _apply_missing_int_field(
            alert,
            "ram_gb",
            listing_result_detail.get("ram_gb"),
            log_detail.get("ram_gb"),
        )
        _apply_missing_int_field(
            alert,
            "ssd_gb",
            listing_result_detail.get("ssd_gb"),
            log_detail.get("ssd_gb"),
        )

        _apply_missing_text_field(
            alert,
            "body_text",
            listing_result_detail.get("body_text"),
            log_detail.get("body_text"),
        )
        _apply_missing_text_field(alert, "body_excerpt", alert.get("body_text"))

        _apply_missing_text_field(alert, "risk_level", log_detail.get("risk_level"))
        _apply_missing_int_field(alert, "risk_score", log_detail.get("risk_score"), allow_zero=True)
        _apply_missing_text_field(alert, "risk_keywords", log_detail.get("risk_keywords"))
        if alert.get("is_exchange_post") is None and log_detail.get("is_exchange_post") is not None:
            alert["is_exchange_post"] = bool(log_detail.get("is_exchange_post"))
        _apply_missing_text_field(alert, "trade_type", log_detail.get("trade_type"))

        _apply_missing_text_field(
            alert,
            "analyzed_at",
            alert.get("analyzed_at"),
            log_detail.get("created_at"),
            listing_result_detail.get("created_at"),
            analysis_job_detail.get("created_at"),
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _fetch_alert_rows(
    cursor,
    *,
    normalized_user_id,
    normalized_limit,
    normalized_is_read,
    exclude_read_archive_cleared=False,
):
    read_filter_tokens = []
    if normalized_is_read == "0":
        read_filter_tokens.append("COALESCE(is_read, 0) = 0")
    elif normalized_is_read == "1":
        read_filter_tokens.append("COALESCE(is_read, 0) = 1")
        if exclude_read_archive_cleared:
            read_filter_tokens.append("COALESCE(is_read_archive_cleared, 0) = 0")

    read_filter_clause = ""
    if read_filter_tokens:
        read_filter_clause = " AND " + " AND ".join(read_filter_tokens)

    try:
        cursor.execute(
            f"""
            SELECT
                id,
                user_id,
                watch_rule_id,
                analysis_job_id,
                product_id,
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
                analyzed_at,
                trigger_reason,
                message,
                status,
                send_attempts,
                error_message,
                is_read,
                read_at,
                is_read_archive_cleared,
                read_archive_cleared_at,
                created_at,
                sent_at,
                updated_at
            FROM alert_events
            WHERE user_id = %s
            {read_filter_clause}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (normalized_user_id, normalized_limit),
        )
        return cursor.fetchall() or [], True
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" not in lowered_exc:
            raise
        try:
            cursor.execute(
                f"""
                SELECT
                    id,
                    user_id,
                    watch_rule_id,
                    analysis_job_id,
                    product_id,
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
                    NULL AS body_text,
                    analyzed_at,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    COALESCE(is_read, 0) AS is_read,
                    NULL AS read_at,
                    COALESCE(is_read_archive_cleared, 0) AS is_read_archive_cleared,
                    NULL AS read_archive_cleared_at,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE user_id = %s
                {read_filter_clause}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (normalized_user_id, normalized_limit),
            )
            return cursor.fetchall() or [], True
        except Exception as detail_exc:
            if "unknown column" not in str(detail_exc).lower():
                raise

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                NULL AS watch_rule_id,
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
                send_attempts,
                error_message,
                0 AS is_read,
                NULL AS read_at,
                0 AS is_read_archive_cleared,
                NULL AS read_archive_cleared_at,
                created_at,
                sent_at,
                updated_at
            FROM alert_events
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (normalized_user_id, normalized_limit),
        )
        rows = cursor.fetchall() or []
        if normalized_is_read == "1":
            return [], False
        return rows, False


def _normalize_limit(limit):
    normalized = _normalize_optional_int(limit, "limit")
    if normalized is None:
        return 20
    if normalized <= 0:
        raise ValueError("invalid_limit")
    return min(normalized, 200)


def _normalize_is_read_filter(value):
    normalized = (_normalize_optional_text(value) or "0").lower()
    if normalized in {"0", "false", "unread"}:
        return "0"
    if normalized in {"1", "true", "read"}:
        return "1"
    if normalized == "all":
        return "all"
    raise ValueError("invalid_is_read")


def _coerce_datetime_for_sort(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None

    text = normalized.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, pattern)
        except ValueError:
            continue
    return None


def _normalize_alert_id(alert_id):
    normalized = _normalize_optional_int(alert_id, "alert_id")
    if normalized is None or normalized <= 0:
        raise ValueError("invalid_alert_id")
    return normalized


def _normalize_alert_id_list(alert_event_ids):
    if not isinstance(alert_event_ids, (list, tuple, set)):
        raise ValueError("invalid_alert_event_ids")

    normalized_ids = []
    seen = set()
    for raw_value in alert_event_ids:
        parsed = _normalize_optional_int(raw_value, "alert_id")
        if parsed is None or parsed <= 0:
            raise ValueError("invalid_alert_event_id")
        if parsed in seen:
            continue
        seen.add(parsed)
        normalized_ids.append(parsed)
    return normalized_ids


def _telegram_configured():
    load_dotenv()
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    return bool(bot_token)


def _fcm_configured():
    load_dotenv()
    has_json = bool((os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip())
    has_file = bool((os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE") or "").strip())
    has_google_cred_file = bool((os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip())
    return has_json or has_file or has_google_cred_file


def _ensure_firebase_initialized():
    global _FIREBASE_INIT_ATTEMPTED, _FIREBASE_INIT_ERROR

    if _FIREBASE_INIT_ATTEMPTED:
        return _FIREBASE_INIT_ERROR is None, _FIREBASE_INIT_ERROR

    _FIREBASE_INIT_ATTEMPTED = True

    if firebase_admin is None or credentials is None:
        _FIREBASE_INIT_ERROR = "firebase_admin_not_installed"
        return False, _FIREBASE_INIT_ERROR

    try:
        if firebase_admin._apps:
            _FIREBASE_INIT_ERROR = None
            return True, None
    except Exception:
        pass

    load_dotenv()
    credential_json = _normalize_optional_text(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
    credential_file = _normalize_optional_text(os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE"))
    project_id = _normalize_optional_text(os.getenv("FIREBASE_PROJECT_ID"))

    options = {}
    if project_id is not None:
        options["projectId"] = project_id

    try:
        if credential_json is not None:
            credential_obj = credentials.Certificate(json.loads(credential_json))
            firebase_admin.initialize_app(credential=credential_obj, options=options or None)
        elif credential_file is not None:
            credential_obj = credentials.Certificate(credential_file)
            firebase_admin.initialize_app(credential=credential_obj, options=options or None)
        else:
            firebase_admin.initialize_app(options=options or None)

        _FIREBASE_INIT_ERROR = None
        return True, None
    except Exception as exc:
        _FIREBASE_INIT_ERROR = str(exc)
        return False, _FIREBASE_INIT_ERROR


def _is_unregistered_push_token_error(error_text):
    lowered = (error_text or "").lower()
    return (
        "unregistered" in lowered
        or "registration token is not a valid fcm registration token" in lowered
        or "requested entity was not found" in lowered
        or "notfound" in lowered
    )


def _build_push_notification_payload(alert):
    title = _normalize_optional_text(alert.get("title")) or "UMTP 새 매물 알림"
    listing_price_krw = _safe_int(alert.get("price_krw"))
    risk_level = _normalize_optional_text(alert.get("risk_level"))
    risk_label = _build_formatted_risk_label(risk_level)

    body = _normalize_optional_text(alert.get("body_excerpt"))
    if body is None:
        body = _normalize_optional_text(alert.get("message"))
    if body is None:
        segments = []
        if listing_price_krw is not None:
            segments.append(f"{listing_price_krw:,}원")
        if risk_label != "정보 없음":
            segments.append(f"위험도 {risk_label}")
        body = " · ".join(segments) if segments else "새로운 매물이 등록되었습니다."

    data_payload = {
        "alert_id": str(_safe_int(alert.get("id")) or ""),
        "listing_title": title,
        "listing_price_krw": str(listing_price_krw) if listing_price_krw is not None else "",
        "risk_level": _normalize_optional_text(alert.get("risk_level")) or "",
        "product_id": _normalize_optional_text(alert.get("product_id")) or "",
        "url": _normalize_optional_text(alert.get("url")) or "",
        "trigger_reason": _normalize_optional_text(alert.get("trigger_reason")) or "",
    }
    data_payload = {key: value for key, value in data_payload.items() if isinstance(value, str)}
    return title, body, data_payload


def _send_fcm_to_user(user_id, alert):
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        return {"sent": 0, "failed": 0, "reason": "invalid_user_id", "attempted": 0}

    push_tokens = list_active_user_push_tokens(normalized_user_id, platform="android")
    if not push_tokens:
        return {"sent": 0, "failed": 0, "reason": "no_active_push_tokens", "attempted": 0}

    if not _fcm_configured():
        return {"sent": 0, "failed": 0, "reason": "fcm_credentials_missing", "attempted": 0}

    ready, init_error = _ensure_firebase_initialized()
    if not ready:
        return {"sent": 0, "failed": len(push_tokens), "reason": init_error or "firebase_init_failed", "attempted": len(push_tokens)}

    title, body, data_payload = _build_push_notification_payload(alert)
    sent_count = 0
    failed_count = 0

    for token_row in push_tokens:
        token_id = token_row.get("id")
        token = _normalize_optional_text(token_row.get("token"))
        if token is None:
            failed_count += 1
            continue

        try:
            message = messaging.Message(  # type: ignore[union-attr]
                token=token,
                notification=messaging.Notification(title=title, body=body),  # type: ignore[union-attr]
                data=data_payload,
            )
            messaging.send(message)  # type: ignore[union-attr]
            if token_id is not None:
                mark_user_push_token_sent(token_id)
            sent_count += 1
        except Exception as exc:
            failed_count += 1
            error_text = str(exc)
            if token_id is not None and _is_unregistered_push_token_error(error_text):
                deactivate_user_push_token(token_id, error_message=error_text)

    if sent_count > 0:
        return {"sent": sent_count, "failed": failed_count, "reason": "fcm_sent", "attempted": len(push_tokens)}
    return {"sent": 0, "failed": failed_count, "reason": "fcm_send_failed", "attempted": len(push_tokens)}


def _build_telegram_message(alert):
    source = _normalize_optional_text(alert.get("source")) or "joongna"
    title = _resolve_title_text_for_display(alert)
    url = _resolve_url_for_display(alert)
    listing_image_url = _normalize_optional_text(alert.get("listing_image_url")) or "이미지 없음"
    listing_price_krw = _safe_int(alert.get("price_krw"))
    user_market_price_krw = _safe_int(alert.get("user_market_price_krw"))
    if user_market_price_krw is None:
        user_market_price_krw = _safe_int(alert.get("fair_price_krw"))
    alert_target_price_krw = _safe_int(alert.get("alert_target_price_krw"))
    if alert_target_price_krw is None:
        alert_target_price_krw = _safe_int(alert.get("target_price_krw"))

    price_gap_percent = _normalize_optional_float(alert.get("price_gap_percent"))
    if price_gap_percent is None:
        price_gap_percent = _normalize_optional_float(alert.get("diff_ratio"))
    if price_gap_percent is None:
        price_gap_percent = _normalize_optional_float(alert.get("drop_rate_percent"))

    risk_label = _resolve_risk_label_for_display(alert)
    risk_score = _resolve_risk_score_for_display(alert)
    risk_keywords_text = _resolve_risk_keywords_text_for_display(alert)
    alert_condition_label = _resolve_alert_condition_label_for_display(alert)
    body_text = _resolve_body_text_for_display(alert)
    analyzed_at_text = _resolve_analyzed_at_text_for_display(alert)
    trade_flags_text = _resolve_trade_flags_text_for_display(alert)
    special_notes_text = _resolve_special_notes_text_for_display(
        alert,
        risk_label=risk_label,
        risk_keywords_text=risk_keywords_text,
        trade_flags_text=trade_flags_text,
    )

    sections = [
        _build_telegram_detail_row("출처", source),
        _build_telegram_detail_row("게시글 제목", title),
        _build_telegram_detail_row("URL", url),
        _build_telegram_detail_row("대표 이미지", listing_image_url),
        _build_telegram_detail_row("제품 분류", _resolve_product_type_text_for_display(alert)),
        _build_telegram_detail_row("칩", _resolve_chip_text_for_display(alert)),
        _build_telegram_detail_row("화면 크기", _resolve_screen_inch_text_for_display(alert)),
        _build_telegram_detail_row("RAM", _resolve_ram_text_for_display(alert)),
        _build_telegram_detail_row("SSD", _resolve_ssd_text_for_display(alert)),
        _build_telegram_detail_row("등록 가격", _format_krw_display(listing_price_krw)),
        _build_telegram_detail_row("내가 생각한 시장가", _format_krw_display(user_market_price_krw)),
        _build_telegram_detail_row("알림 기준 가격", _format_krw_display(alert_target_price_krw)),
        _build_telegram_detail_row("시장가와의 차이", _format_percent_display(price_gap_percent)),
        _build_telegram_detail_row(
            "차이율 계산식",
            "(내가 생각한 시장가 - 등록 가격) / 내가 생각한 시장가 × 100",
        ),
        _build_telegram_detail_row("알림 조건", alert_condition_label),
        _build_telegram_detail_row("위험도", risk_label),
        _build_telegram_detail_row("위험 점수", risk_score),
        _build_telegram_detail_row("위험 키워드", risk_keywords_text),
        _build_telegram_detail_row("본문 내용", body_text),
        _build_telegram_detail_row("분석 시각", analyzed_at_text),
        _build_telegram_detail_row("교환/나눔/의심", trade_flags_text),
        _build_telegram_detail_row("특이사항", special_notes_text),
    ]

    return "거래 알림 피드\n\n" + "\n\n".join(sections)


def get_pending_alert_events(limit=20):
    normalized_limit = _normalize_limit(limit)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    watch_rule_id,
                    analysis_job_id,
                    product_id,
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
                    body_excerpt,
                    body_text,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (normalized_limit,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            try:
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        NULL AS watch_rule_id,
                        analysis_job_id,
                        product_id,
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
                        body_excerpt,
                        NULL AS body_text,
                        trigger_reason,
                        message,
                        status,
                        send_attempts,
                        error_message,
                        created_at,
                        sent_at,
                        updated_at
                    FROM alert_events
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (normalized_limit,),
                )
            except Exception as detail_exc:
                if "unknown column" not in str(detail_exc).lower():
                    raise
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        NULL AS watch_rule_id,
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
                        send_attempts,
                        error_message,
                        created_at,
                        sent_at,
                        updated_at
                    FROM alert_events
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (normalized_limit,),
                )
        return cursor.fetchall() or []
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _update_alert_event_status(alert_id, status, *, error_message=None, set_sent_at=False):
    normalized_alert_id = _normalize_alert_id(alert_id)
    normalized_status = _normalize_required_text(status, "status")
    normalized_error_message = _normalize_optional_text(error_message)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        if set_sent_at:
            cursor.execute(
                """
                UPDATE alert_events
                SET
                    status = %s,
                    error_message = %s,
                    sent_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_status, normalized_error_message, normalized_alert_id),
            )
        else:
            cursor.execute(
                """
                UPDATE alert_events
                SET
                    status = %s,
                    error_message = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_status, normalized_error_message, normalized_alert_id),
            )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_alert_event_sending(alert_id):
    normalized_alert_id = _normalize_alert_id(alert_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET
                status = 'sending',
                send_attempts = COALESCE(send_attempts, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'pending'
            """,
            (normalized_alert_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_alert_event_sent(alert_id):
    return _update_alert_event_status(alert_id, "sent", set_sent_at=True)


def mark_alert_event_app_only(alert_id):
    return _update_alert_event_status(alert_id, "app_only", set_sent_at=True)


def mark_alert_event_failed(alert_id, error_message):
    return _update_alert_event_status(alert_id, "failed", error_message=error_message, set_sent_at=False)


def send_alert_event(alert):
    if not isinstance(alert, dict):
        raise ValueError("invalid_alert")

    alert_id = _normalize_alert_id(alert.get("id"))
    user_id = _normalize_required_text(alert.get("user_id"), "user_id")
    delivery_policy = resolve_user_alert_delivery_policy(user_id)
    user_alert_enabled = bool(delivery_policy.get("enabled"))
    user_chat_id = _normalize_optional_text(delivery_policy.get("telegram_chat_id"))
    allow_global_fallback = bool(delivery_policy.get("allow_global_fallback"))

    if not user_alert_enabled:
        print(f"[notification_worker] delivery skipped: alerts disabled for user_id={user_id}")
        mark_alert_event_app_only(alert_id)
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "app_only",
            "reason": "alerts_disabled",
        }

    try:
        _enrich_alert_for_display(alert)
    except Exception:
        # Alert delivery should continue even when best-effort display enrichment fails.
        pass

    push_result = _send_fcm_to_user(user_id, alert)
    push_sent = int(push_result.get("sent", 0))
    push_attempted = int(push_result.get("attempted", 0))
    push_reason = _normalize_optional_text(push_result.get("reason"))

    telegram_status = "skipped"
    telegram_reason = None
    telegram_sent = False
    telegram_attempted = False

    telegram_ready = _telegram_configured()
    if not telegram_ready:
        telegram_reason = "telegram_bot_token_missing"
    elif user_chat_id is None and not allow_global_fallback:
        telegram_reason = "missing_telegram_chat_id"
    else:
        if user_chat_id is None and allow_global_fallback:
            print(
                f"[notification_worker] telegram fallback: using global chat id for user_id={user_id} "
                "(deprecated)"
            )

        telegram_attempted = True
        product_id_for_image_lookup = _resolve_alert_product_id_for_image_lookup(alert)
        listing_image_url = _fetch_listing_image_url_by_product_id(product_id_for_image_lookup)
        if _normalize_optional_text(alert.get("title")) is None:
            listing_title = _fetch_listing_title_by_product_id(product_id_for_image_lookup)
            if listing_title is not None:
                alert["title"] = listing_title
        if listing_image_url is None:
            listing_image_url = (
                _normalize_optional_text(alert.get("listing_image_url"))
                or _normalize_optional_text(alert.get("image_url"))
            )
        if listing_image_url is not None:
            alert["listing_image_url"] = listing_image_url

        telegram_message = _build_telegram_message(alert)
        sent_ok = send_telegram_alert(
            telegram_message,
            chat_id=user_chat_id,
            allow_global_fallback=allow_global_fallback,
            image_url=listing_image_url,
        )
        if sent_ok:
            telegram_status = "sent"
            telegram_reason = "telegram_sent"
            telegram_sent = True
        else:
            telegram_status = "failed"
            telegram_reason = "telegram_send_failed"

    if push_sent > 0 or telegram_sent:
        mark_alert_event_sent(alert_id)
        if push_sent > 0 and telegram_sent:
            reason = "push_and_telegram_sent"
        elif push_sent > 0:
            reason = "push_sent"
        else:
            reason = "telegram_sent"
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "sent",
            "reason": reason,
            "push_sent_count": push_sent,
            "push_reason": push_reason,
            "telegram_status": telegram_status,
            "telegram_reason": telegram_reason,
        }

    if push_attempted > 0 or telegram_attempted:
        failure_reason = telegram_reason or push_reason or "notification_send_failed"
        mark_alert_event_failed(alert_id, failure_reason)
        return {
            "ok": False,
            "alert_id": alert_id,
            "status": "failed",
            "reason": failure_reason,
            "push_sent_count": push_sent,
            "push_reason": push_reason,
            "telegram_status": telegram_status,
            "telegram_reason": telegram_reason,
        }

    mark_alert_event_app_only(alert_id)
    app_only_reason = telegram_reason or push_reason or "no_delivery_channel"
    return {
        "ok": True,
        "alert_id": alert_id,
        "status": "app_only",
        "reason": app_only_reason,
        "push_reason": push_reason,
        "telegram_reason": telegram_reason,
    }


def get_alert_event_by_id(alert_id):
    normalized_alert_id = _normalize_alert_id(alert_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    watch_rule_id,
                    analysis_job_id,
                    product_id,
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
                    body_excerpt,
                    body_text,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE id = %s
                LIMIT 1
                """,
                (normalized_alert_id,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            try:
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        NULL AS watch_rule_id,
                        analysis_job_id,
                        product_id,
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
                        body_excerpt,
                        NULL AS body_text,
                        trigger_reason,
                        message,
                        status,
                        send_attempts,
                        error_message,
                        created_at,
                        sent_at,
                        updated_at
                    FROM alert_events
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (normalized_alert_id,),
                )
            except Exception as detail_exc:
                if "unknown column" not in str(detail_exc).lower():
                    raise
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        NULL AS watch_rule_id,
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
                        send_attempts,
                        error_message,
                        created_at,
                        sent_at,
                        updated_at
                    FROM alert_events
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (normalized_alert_id,),
                )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def dispatch_alert_event_immediately(alert_id, *, fallback_alert=None):
    normalized_alert_id = _normalize_alert_id(alert_id)

    claimed = mark_alert_event_sending(normalized_alert_id)
    if not claimed:
        return {
            "ok": True,
            "alert_id": normalized_alert_id,
            "status": "skipped_not_pending",
            "reason": "not_pending",
        }

    fallback_payload = None
    if isinstance(fallback_alert, dict):
        fallback_payload = dict(fallback_alert)
        fallback_payload["id"] = normalized_alert_id

    alert_payload = get_alert_event_by_id(normalized_alert_id)
    if isinstance(alert_payload, dict) and isinstance(fallback_payload, dict):
        for key, value in fallback_payload.items():
            if key not in alert_payload or alert_payload.get(key) is None:
                alert_payload[key] = value

    if not isinstance(alert_payload, dict) and isinstance(fallback_payload, dict):
        alert_payload = fallback_payload

    if not isinstance(alert_payload, dict):
        mark_alert_event_failed(normalized_alert_id, "alert_event_not_found_after_claim")
        return {
            "ok": False,
            "alert_id": normalized_alert_id,
            "status": "failed",
            "reason": "alert_event_not_found_after_claim",
        }

    try:
        return send_alert_event(alert_payload)
    except Exception as exc:
        mark_alert_event_failed(normalized_alert_id, str(exc))
        return {
            "ok": False,
            "alert_id": normalized_alert_id,
            "status": "failed",
            "reason": str(exc),
        }


def process_pending_alert_events(limit=20):
    pending_alerts = get_pending_alert_events(limit=limit)
    stats = {
        "fetched": len(pending_alerts),
        "sent": 0,
        "app_only": 0,
        "failed": 0,
        "results": [],
    }

    for alert in pending_alerts:
        alert_id = _normalize_alert_id(alert.get("id"))

        try:
            claimed = mark_alert_event_sending(alert_id)
            if not claimed:
                stats["results"].append(
                    {
                        "ok": True,
                        "alert_id": alert_id,
                        "status": "skipped_not_pending",
                    }
                )
                continue

            send_result = send_alert_event(alert)
            stats["results"].append(send_result)

            status = send_result.get("status")
            if status == "sent":
                stats["sent"] += 1
            elif status == "app_only":
                stats["app_only"] += 1
            else:
                stats["failed"] += 1
        except Exception as exc:
            try:
                mark_alert_event_failed(alert_id, str(exc))
            except Exception:
                pass
            stats["failed"] += 1
            stats["results"].append(
                {
                    "ok": False,
                    "alert_id": alert_id,
                    "status": "failed",
                    "reason": str(exc),
                }
            )

    return stats


def list_alert_events_for_user(user_id, limit=200, is_read="0", exclude_read_archive_cleared=False):
    normalized_user_id = _normalize_required_text(user_id, "user_id")
    normalized_limit = _normalize_limit(limit)
    normalized_is_read = _normalize_is_read_filter(is_read)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        rows, has_detail_columns = _fetch_alert_rows(
            cursor,
            normalized_user_id=normalized_user_id,
            normalized_limit=normalized_limit,
            normalized_is_read=normalized_is_read,
            exclude_read_archive_cleared=exclude_read_archive_cleared,
        )
        listing_image_url_map = _fetch_listing_image_urls(
            cursor,
            [row.get("product_id") for row in rows],
        )

        items = []
        for row in rows:
            drop_rate_percent = _normalize_optional_float(row.get("drop_rate_percent"))
            alert_drop_rate_percent = _normalize_optional_float(row.get("alert_drop_rate_percent"))
            diff_ratio = drop_rate_percent

            alert_price_direction = normalize_alert_price_direction(row.get("alert_price_direction"))
            risk_keywords = _parse_risk_keywords(row.get("risk_keywords"))
            risk_level = _normalize_optional_text(row.get("risk_level"))
            risk_score = _safe_int(row.get("risk_score"))
            is_exchange_post = _normalize_optional_bool(row.get("is_exchange_post"))
            trade_type = _normalize_optional_text(row.get("trade_type"))
            source = _normalize_optional_text(row.get("source"))
            product_type = _normalize_optional_text(row.get("product_type"))
            chip = _normalize_optional_text(row.get("chip"))
            screen_inch = _safe_int(row.get("screen_inch"))
            ram_gb = _safe_int(row.get("ram_gb"))
            ssd_gb = _safe_int(row.get("ssd_gb"))
            body_text = _normalize_optional_text(row.get("body_text"))
            body_excerpt_source = row.get("body_excerpt")
            if body_excerpt_source is None:
                body_excerpt_source = body_text
            body_excerpt = _build_body_excerpt(body_excerpt_source)
            analyzed_at = row.get("analyzed_at") or row.get("created_at")
            confidence_score = _safe_int(row.get("confidence_score"))
            is_read_value = bool(_safe_int(row.get("is_read")) or 0)
            read_at = row.get("read_at")
            is_read_archive_cleared = bool(_safe_int(row.get("is_read_archive_cleared")) or 0)
            read_archive_cleared_at = row.get("read_archive_cleared_at")
            trigger_reason = _normalize_optional_text(row.get("trigger_reason"))
            is_condition_change_candidate_notice = (
                trigger_reason == CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON
            )

            if not has_detail_columns:
                log_detail = _fetch_latest_log_details(
                    cursor,
                    user_id=row.get("user_id"),
                    url=row.get("url"),
                )
                source = source or _normalize_optional_text(log_detail.get("source"))
                product_type = product_type or _normalize_optional_text(log_detail.get("product_type"))
                chip = chip or _normalize_optional_text(log_detail.get("chip"))
                screen_inch = screen_inch or _safe_int(log_detail.get("screen_inch"))
                ram_gb = ram_gb or _safe_int(log_detail.get("ram_gb"))
                ssd_gb = ssd_gb or _safe_int(log_detail.get("ssd_gb"))
                risk_level = risk_level or _normalize_optional_text(log_detail.get("risk_level"))
                if risk_score is None:
                    risk_score = _safe_int(log_detail.get("risk_score"))
                if not risk_keywords:
                    risk_keywords = _parse_risk_keywords(log_detail.get("risk_keywords"))
                if is_exchange_post is None:
                    is_exchange_post = _normalize_optional_bool(log_detail.get("is_exchange_post"))
                if trade_type is None:
                    trade_type = _normalize_optional_text(log_detail.get("trade_type"))
                if body_text is None:
                    body_text = _normalize_optional_text(log_detail.get("body_text"))
                if body_excerpt is None:
                    body_excerpt = _build_body_excerpt(body_text)
                analyzed_at = analyzed_at or log_detail.get("created_at")
                if confidence_score is None:
                    confidence_score = _safe_int(log_detail.get("confidence_score"))

            trade_type_flags = _build_trade_type_flags(
                is_exchange_post=is_exchange_post,
                trade_type=trade_type,
                risk_level=risk_level,
            )
            risk_keywords_display = risk_keywords if risk_keywords else []
            listing_image_url = _resolve_listing_image_url(
                row.get("product_id"),
                listing_image_url_map,
            )

            items.append(
                {
                    "id": int(row.get("id")),
                    "user_id": row.get("user_id"),
                    "watch_rule_id": row.get("watch_rule_id"),
                    "analysis_job_id": row.get("analysis_job_id"),
                    "product_id": row.get("product_id"),
                    "source": source or "joongna",
                    "url": row.get("url"),
                    "product_url": row.get("url"),
                    "listing_image_url": listing_image_url,
                    "image_url": listing_image_url,
                    "title": row.get("title"),
                    "product_type": product_type,
                    "chip": chip,
                    "screen_inch": screen_inch,
                    "ram_gb": ram_gb,
                    "ssd_gb": ssd_gb,
                    "price_krw": row.get("price_krw"),
                    "listing_price_krw": row.get("price_krw"),
                    "fair_price_krw": row.get("fair_price_krw"),
                    "user_market_price_krw": row.get("fair_price_krw"),
                    "target_price_krw": row.get("target_price_krw"),
                    "alert_target_price_krw": row.get("target_price_krw"),
                    "drop_rate_percent": diff_ratio,
                    "diff_ratio": diff_ratio,
                    "price_gap_percent": diff_ratio,
                    "alert_drop_rate_percent": alert_drop_rate_percent,
                    "alert_price_direction": alert_price_direction,
                    "alert_condition_label": _build_alert_condition_label(alert_price_direction),
                    "trigger_reason": trigger_reason,
                    "message": row.get("message"),
                    "risk_level": risk_level,
                    "formatted_risk_label": _build_formatted_risk_label(risk_level),
                    "risk_score": risk_score,
                    "risk_keywords": risk_keywords_display,
                    "trade_type_flags": trade_type_flags,
                    "is_exchange_post": bool(is_exchange_post) if is_exchange_post is not None else False,
                    "trade_type": trade_type,
                    "body_excerpt": body_excerpt,
                    "body_text": body_text,
                    "analyzed_at": analyzed_at,
                    "confidence_score": confidence_score,
                    "status": row.get("status"),
                    "send_attempts": row.get("send_attempts"),
                    "error_message": row.get("error_message"),
                    "is_read": is_read_value,
                    "read_at": read_at,
                    "is_read_archive_cleared": is_read_archive_cleared,
                    "read_archive_cleared_at": read_archive_cleared_at,
                    "created_at": row.get("created_at"),
                    "sent_at": row.get("sent_at"),
                    "updated_at": row.get("updated_at"),
                    "is_alert_target": not is_condition_change_candidate_notice,
                    "is_condition_change_candidate_notice": is_condition_change_candidate_notice,
                }
            )

        return items
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_alert_event_read_for_user(*, user_id, alert_event_id):
    normalized_user_id = _normalize_required_text(user_id, "user_id")
    normalized_alert_id = _normalize_alert_id(alert_event_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                UPDATE alert_events
                SET is_read = 1,
                    read_at = COALESCE(read_at, NOW())
                WHERE id = %s
                  AND user_id = %s
                """,
                (normalized_alert_id, normalized_user_id),
            )
            updated_rows = cursor.rowcount or 0
        except Exception as exc:
            lowered = str(exc).lower()
            if "unknown column" in lowered:
                return {
                    "ok": False,
                    "reason": "alert_read_columns_missing",
                    "alert_event_id": normalized_alert_id,
                }
            raise

        connection.commit()

        if updated_rows == 0:
            cursor.execute(
                """
                SELECT id, COALESCE(is_read, 0) AS is_read, read_at
                FROM alert_events
                WHERE id = %s
                  AND user_id = %s
                LIMIT 1
                """,
                (normalized_alert_id, normalized_user_id),
            )
            existing = cursor.fetchone()
            if not existing:
                return {
                    "ok": False,
                    "reason": "alert_event_not_found",
                    "alert_event_id": normalized_alert_id,
                }

            return {
                "ok": True,
                "alert_event_id": normalized_alert_id,
                "is_read": bool(_safe_int(existing.get("is_read")) or 0),
                "read_at": existing.get("read_at"),
                "already_read": True,
            }

        cursor.execute(
            """
            SELECT id, COALESCE(is_read, 0) AS is_read, read_at
            FROM alert_events
            WHERE id = %s
              AND user_id = %s
            LIMIT 1
            """,
            (normalized_alert_id, normalized_user_id),
        )
        row = cursor.fetchone() or {}
        return {
            "ok": True,
            "alert_event_id": normalized_alert_id,
            "is_read": bool(_safe_int(row.get("is_read")) or 0),
            "read_at": row.get("read_at"),
            "already_read": False,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_all_alert_events_read_for_user(*, user_id):
    normalized_user_id = _normalize_required_text(user_id, "user_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                UPDATE alert_events
                SET is_read = 1,
                    read_at = COALESCE(read_at, NOW())
                WHERE user_id = %s
                  AND COALESCE(is_read, 0) = 0
                """,
                (normalized_user_id,),
            )
            updated_rows = cursor.rowcount or 0
        except Exception as exc:
            lowered = str(exc).lower()
            if "unknown column" in lowered:
                return {
                    "ok": False,
                    "reason": "alert_read_columns_missing",
                    "updated_count": 0,
                }
            raise

        connection.commit()
        return {
            "ok": True,
            "updated_count": int(updated_rows),
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def clear_all_read_alert_events_for_user(*, user_id):
    normalized_user_id = _normalize_required_text(user_id, "user_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                UPDATE alert_events
                SET
                    is_read_archive_cleared = 1,
                    read_archive_cleared_at = COALESCE(read_archive_cleared_at, NOW())
                WHERE user_id = %s
                  AND COALESCE(is_read, 0) = 1
                  AND COALESCE(is_read_archive_cleared, 0) = 0
                """,
                (normalized_user_id,),
            )
            cleared_rows = cursor.rowcount or 0
        except Exception as exc:
            lowered = str(exc).lower()
            if "unknown column" in lowered:
                return {
                    "ok": False,
                    "reason": "read_archive_clear_columns_missing",
                    "cleared_count": 0,
                }
            raise

        connection.commit()
        return {
            "ok": True,
            "cleared_count": int(cleared_rows),
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def clear_selected_read_alert_events_for_user(*, user_id, alert_event_ids):
    normalized_user_id = _normalize_required_text(user_id, "user_id")
    normalized_ids = _normalize_alert_id_list(alert_event_ids)

    if not normalized_ids:
        return {
            "ok": True,
            "requested_count": 0,
            "cleared_count": 0,
            "skipped_count": 0,
            "not_found_ids": [],
        }

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        placeholders = ", ".join(["%s"] * len(normalized_ids))
        try:
            cursor.execute(
                f"""
                SELECT
                    id,
                    COALESCE(is_read_archive_cleared, 0) AS is_read_archive_cleared
                FROM alert_events
                WHERE user_id = %s
                  AND COALESCE(is_read, 0) = 1
                  AND id IN ({placeholders})
                """,
                tuple([normalized_user_id, *normalized_ids]),
            )
            rows = cursor.fetchall() or []
        except Exception as exc:
            lowered = str(exc).lower()
            if "unknown column" in lowered:
                return {
                    "ok": False,
                    "reason": "read_archive_clear_columns_missing",
                    "requested_count": len(normalized_ids),
                    "cleared_count": 0,
                    "skipped_count": len(normalized_ids),
                    "not_found_ids": normalized_ids,
                }
            raise

        found_by_id = {int(row.get("id")): row for row in rows if row.get("id") is not None}
        found_ids = set(found_by_id.keys())
        not_found_ids = [alert_id for alert_id in normalized_ids if alert_id not in found_ids]
        ids_to_clear = [
            alert_id
            for alert_id in normalized_ids
            if alert_id in found_ids
            and not bool(_safe_int(found_by_id[alert_id].get("is_read_archive_cleared")) or 0)
        ]

        cleared_count = 0
        if ids_to_clear:
            update_placeholders = ", ".join(["%s"] * len(ids_to_clear))
            cursor.execute(
                f"""
                UPDATE alert_events
                SET
                    is_read_archive_cleared = 1,
                    read_archive_cleared_at = COALESCE(read_archive_cleared_at, NOW())
                WHERE user_id = %s
                  AND COALESCE(is_read, 0) = 1
                  AND COALESCE(is_read_archive_cleared, 0) = 0
                  AND id IN ({update_placeholders})
                """,
                tuple([normalized_user_id, *ids_to_clear]),
            )
            cleared_count = int(cursor.rowcount or 0)

        connection.commit()
        requested_count = len(normalized_ids)
        skipped_count = max(0, requested_count - cleared_count - len(not_found_ids))
        return {
            "ok": True,
            "requested_count": requested_count,
            "cleared_count": cleared_count,
            "skipped_count": skipped_count,
            "not_found_ids": not_found_ids,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _chip_group_sort_key(chip_key):
    normalized = (_normalize_optional_text(chip_key) or "").upper()
    preferred_order = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5}
    if normalized in preferred_order:
        return (0, preferred_order[normalized], normalized)
    if normalized == "기타":
        return (2, 999, normalized)
    return (1, 500, normalized)


def _screen_group_sort_key(screen_key):
    normalized = _normalize_optional_text(screen_key)
    if normalized is None:
        return (2, 999)
    if normalized == "기타":
        return (2, 999)
    try:
        return (0, int(normalized))
    except ValueError:
        return (1, 500)


def _group_chip_key(chip):
    normalized_chip = _normalize_optional_text(chip)
    if normalized_chip is None:
        return "기타"
    return normalized_chip.upper()


def _group_screen_key(screen_inch):
    normalized_screen = _safe_int(screen_inch)
    if normalized_screen is None or normalized_screen <= 0:
        return "기타"
    return str(normalized_screen)


def _alert_group_item_sort_key(item):
    read_at = _coerce_datetime_for_sort(item.get("read_at"))
    analyzed_at = _coerce_datetime_for_sort(item.get("analyzed_at"))
    created_at = _coerce_datetime_for_sort(item.get("created_at"))
    return (
        read_at or datetime.min,
        analyzed_at or datetime.min,
        created_at or datetime.min,
        _safe_int(item.get("id")) or 0,
    )


def list_grouped_read_alert_events_for_user(user_id, limit=500):
    items = list_alert_events_for_user(
        user_id=user_id,
        limit=limit,
        is_read="1",
        exclude_read_archive_cleared=True,
    )
    grouped = {}

    for item in items:
        chip_key = _group_chip_key(item.get("chip"))
        screen_key = _group_screen_key(item.get("screen_inch"))
        grouped.setdefault(chip_key, {}).setdefault(screen_key, []).append(item)

    ordered_grouped = {}
    chip_keys = sorted(grouped.keys(), key=_chip_group_sort_key)
    for chip_key in chip_keys:
        screen_groups = grouped.get(chip_key) or {}
        ordered_screen_groups = {}
        for screen_key in sorted(screen_groups.keys(), key=_screen_group_sort_key):
            alerts = screen_groups.get(screen_key) or []
            alerts.sort(key=_alert_group_item_sort_key, reverse=True)
            ordered_screen_groups[screen_key] = alerts
        ordered_grouped[chip_key] = ordered_screen_groups

    return ordered_grouped
