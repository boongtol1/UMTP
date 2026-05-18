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
    from src.joongna_seen_products import mark_seen_product_analyzed
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
    from joongna_seen_products import mark_seen_product_analyzed
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
    }


def enqueue_analysis_for_product(product, watch_rules, trigger_reason):
    return create_analysis_jobs_for_rules(product, watch_rules, trigger_reason)


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
):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_product_id = _normalize_optional_text(product_id)

    if normalized_user_id is None or normalized_product_id is None:
        return None

    try:
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
):
    parsed_spec = parsed_spec or {}
    risk_result = risk_result or {}

    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_product_id = _normalize_optional_text(product_id)
    normalized_sort_date = _coerce_datetime(sort_date)

    duplicate = _find_alert_event_by_identity(
        cursor,
        user_id=normalized_user_id,
        watch_rule_id=normalized_watch_rule_id,
        product_id=normalized_product_id,
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
                message,
                status,
                send_attempts
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, 'pending', 0
            )
            """,
            (
                normalized_user_id,
                normalized_watch_rule_id,
                _normalize_optional_int(analysis_job_id),
                normalized_product_id,
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
                        message,
                        status,
                        send_attempts
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, 'pending', 0
                    )
                    """,
                    (
                        normalized_user_id,
                        normalized_watch_rule_id,
                        _normalize_optional_int(analysis_job_id),
                        normalized_product_id,
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

    html = fetch_html(url)
    parsed_page = parse_joongna_listing_page(html)

    title = parsed_page.get("title")
    description = parsed_page.get("description")
    listing_price_krw = _normalize_optional_int(parsed_page.get("listing_price_krw"))
    self_check_fields = parsed_page.get("self_check_fields") or {}

    parsing_source_text = f"{title or ''} {description or ''}".strip()
    parsed_spec = parse_listing_title(parsing_source_text, self_check_fields=self_check_fields)
    risk_result = analyze_risk(parsing_source_text, self_check_fields=self_check_fields)

    matched_watch_rule = bool(parsed_spec.get("parse_success"))

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        saved_window_allowed, saved_window_reason = _evaluate_watch_rule_saved_window(
            cursor,
            user_id=user_id,
            watch_rule_id=watch_rule_id,
            sort_date=sort_date,
        )

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

        drop_rate_percent = None
        if fair_price_krw is not None and fair_price_krw > 0 and listing_price_krw is not None:
            drop_rate_percent = ((fair_price_krw - listing_price_krw) / fair_price_krw) * 100

        is_alert_target = False
        alert_skip_reason = price_error_reason
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

        alert_create_result = {
            "created": False,
            "alert_id": None,
        }
        alert_message = None
        if is_alert_target:
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
                    import json

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
                        "user_id": user_id,
                        "title": title,
                        "url": url,
                        "price_krw": listing_price_krw,
                        "fair_price_krw": fair_price_krw,
                        "target_price_krw": target_price_krw,
                        "drop_rate_percent": drop_rate_percent,
                        "trigger_reason": trigger_reason,
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
        "done": 0,
        "skipped": 0,
        "failed": 0,
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
