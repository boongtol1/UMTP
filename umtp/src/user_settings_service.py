import json
import logging
import random
from datetime import datetime
from decimal import Decimal

from src.alert_price_direction import (
    DEFAULT_ALERT_PRICE_DIRECTION,
    compute_target_buy_price_krw,
    is_listing_alert_match,
    passes_price_bounds,
    is_valid_alert_drop_rate_percent,
    is_valid_alert_price_direction,
    normalize_alert_price_direction,
)
from src.db import get_connection
from src.macbook_air_units import (
    SUPPORTED_PRODUCT_TYPES,
    generate_supported_units,
    is_valid_macbook_air_unit,
    is_supported_product_type,
    is_valid_silicon_unit,
)
from src.search_keyword_utils import (
    build_default_keyword_for_watch_rule,
    build_recommended_keywords_for_spec,
    normalize_search_keyword,
    validate_search_keyword,
)


CHIP_SORT_ORDER = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
}
PRODUCT_TYPE_SORT_ORDER = {name: index for index, name in enumerate(SUPPORTED_PRODUCT_TYPES, start=1)}
DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT = 20.0
DEFAULT_POLL_INTERVAL_SECONDS = 60
DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED = False
CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON = "condition_change_candidate_notice"
CONDITION_CHANGE_CANDIDATE_NOTICE_SOURCE = "umtp_notice"
WATCH_PRIORITY_FAST = "FAST"
WATCH_PRIORITY_NORMAL = "NORMAL"
WATCH_PRIORITY_LOW = "LOW"
WATCH_PRIORITY_VALUES = (WATCH_PRIORITY_FAST, WATCH_PRIORITY_NORMAL, WATCH_PRIORITY_LOW)
DEFAULT_WATCH_PRIORITY = WATCH_PRIORITY_NORMAL
WATCH_PRIORITY_BASE_INTERVAL_SECONDS = {
    WATCH_PRIORITY_FAST: 45,
    WATCH_PRIORITY_NORMAL: 180,
    WATCH_PRIORITY_LOW: 600,
}
POLLING_JITTER_RATIO = 0.2
MIN_POLLING_INTERVAL_SECONDS = 30
logger = logging.getLogger("umtp.user_settings")

USER_SETTINGS_SAVE_LOG_ERROR_CONDITION_CHANGE_NOTICE_INSERT_FAILED = (
    "CONDITION_CHANGE_NOTICE_INSERT_FAILED"
)
USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED = "USER_SETTINGS_SAVE_FAILED"
USER_SETTINGS_SAVE_LOG_SENSITIVE_KEYWORDS = (
    "token",
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "push_token",
    "fcm_token",
)


def _is_sensitive_log_key(key):
    normalized = _safe_text(key)
    if normalized is None:
        return False
    lowered = normalized.lower()
    return any(keyword in lowered for keyword in USER_SETTINGS_SAVE_LOG_SENSITIVE_KEYWORDS)


def _mask_sensitive_log_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        if len(value) <= 8:
            return "***"
        return f"{value[:2]}***{value[-2:]}"
    return "***"


def _sanitize_payload_for_log(payload):
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if _is_sensitive_log_key(key):
                sanitized[key] = _mask_sensitive_log_value(value)
            else:
                sanitized[key] = _sanitize_payload_for_log(value)
        return sanitized

    if isinstance(payload, list):
        return [_sanitize_payload_for_log(item) for item in payload]

    if isinstance(payload, tuple):
        return [_sanitize_payload_for_log(item) for item in payload]

    return payload


def _json_default_serializer(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _to_json_text_or_none(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=_json_default_serializer)


def _insert_user_settings_save_log(
    *,
    user_id,
    watch_rule_id,
    action_type,
    request_payload,
    response_payload,
    success,
    error_code=None,
    error_message=None,
    metadata=None,
    connection=None,
    cursor=None,
    commit=False,
):
    normalized_user_id = _safe_text(user_id)
    normalized_action_type = _safe_text(action_type)
    if normalized_user_id is None or normalized_action_type is None:
        return None

    normalized_watch_rule_id = _safe_int_or_none(watch_rule_id)
    normalized_error_code = _safe_text(error_code)
    normalized_error_message = _safe_text(error_message)
    normalized_request_payload = _sanitize_payload_for_log(request_payload)
    normalized_response_payload = _sanitize_payload_for_log(response_payload)
    normalized_metadata = _sanitize_payload_for_log(metadata)
    normalized_success = 1 if bool(success) else 0

    local_connection = None
    local_cursor = None
    target_connection = connection
    target_cursor = cursor

    try:
        if target_connection is None or target_cursor is None:
            local_connection = get_connection()
            target_connection = local_connection
            target_cursor = target_connection.cursor()
            commit = True

        target_cursor.execute(
            """
            INSERT INTO user_settings_save_logs (
                user_id,
                watch_rule_id,
                action_type,
                request_json,
                response_json,
                success,
                error_code,
                error_message,
                metadata_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                normalized_user_id,
                normalized_watch_rule_id,
                normalized_action_type,
                _to_json_text_or_none(normalized_request_payload),
                _to_json_text_or_none(normalized_response_payload),
                normalized_success,
                normalized_error_code,
                normalized_error_message,
                _to_json_text_or_none(normalized_metadata),
            ),
        )
        inserted_id = _safe_int_or_none(getattr(target_cursor, "lastrowid", None))
        if commit and target_connection is not None:
            target_connection.commit()
        return inserted_id
    except Exception:
        logger.warning(
            "user-settings save log insert failed user_id=%s watch_rule_id=%s action_type=%s",
            normalized_user_id,
            normalized_watch_rule_id,
            normalized_action_type,
            exc_info=True,
        )
        return None
    finally:
        if local_cursor is not None:
            local_cursor.close()
        if local_connection is not None and local_connection.is_connected():
            local_connection.close()


def _mask_device_id(device_id):
    if device_id is None:
        return None
    text = str(device_id)
    if len(text) <= 8:
        return text
    return f"{text[:4]}...{text[-4:]}"


def _safe_int(value):
    if value is None:
        return None
    return int(value)


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _safe_bool(value, default=False):
    if value is None:
        return default
    return bool(value)


def _safe_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_optional_search_keyword(search_keyword):
    if search_keyword is None:
        return None
    normalized = normalize_search_keyword(search_keyword)
    if not normalized:
        return None
    return validate_search_keyword(normalized)


def _normalize_chip_for_setting(chip):
    normalized = _safe_text(chip)
    if normalized is None:
        return ""

    compact_lower = normalized.lower().replace(" ", "")
    if compact_lower == "m2pro":
        return "M2 Pro"
    if compact_lower == "m4pro":
        return "M4 Pro"

    return normalized.upper()


def _normalize_poll_interval_seconds(value):
    if value is None:
        return DEFAULT_POLL_INTERVAL_SECONDS
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_poll_interval_seconds") from exc
    if normalized <= 0:
        raise ValueError("invalid_poll_interval_seconds")
    return normalized


def normalize_watch_priority(value):
    normalized = _safe_text(value)
    if normalized is None:
        return DEFAULT_WATCH_PRIORITY
    candidate = normalized.upper()
    if candidate not in WATCH_PRIORITY_VALUES:
        return DEFAULT_WATCH_PRIORITY
    return candidate


def apply_polling_jitter(base_seconds, *, random_fn=None, jitter_ratio=POLLING_JITTER_RATIO):
    normalized_base = _safe_int(base_seconds) or 0
    normalized_base = max(normalized_base, MIN_POLLING_INTERVAL_SECONDS)
    ratio = _safe_float(jitter_ratio)
    if ratio is None or ratio < 0:
        ratio = POLLING_JITTER_RATIO
    sampler = random_fn or random.uniform
    jitter_delta = normalized_base * ratio
    sampled_offset = sampler(-jitter_delta, jitter_delta)
    jittered_seconds = int(round(normalized_base + sampled_offset))
    return max(jittered_seconds, MIN_POLLING_INTERVAL_SECONDS)


def polling_interval_for_priority(priority, *, random_fn=None):
    normalized_priority = normalize_watch_priority(priority)
    base_seconds = WATCH_PRIORITY_BASE_INTERVAL_SECONDS.get(
        normalized_priority,
        WATCH_PRIORITY_BASE_INTERVAL_SECONDS[DEFAULT_WATCH_PRIORITY],
    )
    return apply_polling_jitter(base_seconds, random_fn=random_fn)


def _normalize_rule_id(rule_id):
    try:
        normalized = int(rule_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_rule_id") from exc
    if normalized <= 0:
        raise ValueError("invalid_rule_id")
    return normalized


def _normalize_optional_price_bound(value, *, field_name):
    if value is None:
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(field_name) from exc
    if normalized < 0:
        raise ValueError(field_name)
    return normalized


def _normalize_alert_bounds(
    *,
    alert_price_direction,
    min_price_krw=None,
    max_price_krw=None,
):
    normalized_min = _normalize_optional_price_bound(
        min_price_krw,
        field_name="invalid_min_price_krw",
    )
    normalized_max = _normalize_optional_price_bound(
        max_price_krw,
        field_name="invalid_max_price_krw",
    )

    if alert_price_direction == DEFAULT_ALERT_PRICE_DIRECTION:
        return normalized_min, None

    return None, normalized_max


def _is_unknown_column_error(exc, *column_names):
    lowered_exc = str(exc).lower()
    if "unknown column" not in lowered_exc:
        return False
    if not column_names:
        return True
    return any(column_name.lower() in lowered_exc for column_name in column_names)


def _coerce_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        normalized = normalized.replace("T", " ")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            parsed = None
            for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    parsed = datetime.strptime(normalized, date_format)
                    break
                except ValueError:
                    continue
            if parsed is None:
                return None
        if parsed.tzinfo is not None:
            return parsed.replace(tzinfo=None)
        return parsed
    return None


def _resolve_db_current_timestamp(cursor):
    if cursor is None or not hasattr(cursor, "execute") or not hasattr(cursor, "fetchone"):
        return None

    try:
        cursor.execute("SELECT CURRENT_TIMESTAMP")
        row = cursor.fetchone()
    except Exception:
        return None

    if row is None:
        return None

    if isinstance(row, dict):
        for key in ("CURRENT_TIMESTAMP", "current_timestamp", "current_ts", "now", "evaluated_at"):
            parsed = _coerce_datetime(row.get(key))
            if parsed is not None:
                return parsed
        return None

    if isinstance(row, (tuple, list)) and row:
        return _coerce_datetime(row[0])

    return _coerce_datetime(row)


def _format_saved_at_notice_message(missed_candidate_count):
    normalized_count = _safe_int(missed_candidate_count) or 0
    return f"조건 변경 사이에 새 기준에 맞는 매물이 {normalized_count}개 있었어요."


def _build_condition_change_candidate_notice_title(*, chip, screen_inch, ram_gb, ssd_gb):
    normalized_chip = _safe_text(chip) or "기타"
    normalized_screen_inch = _safe_int(screen_inch)
    normalized_ram_gb = _safe_int(ram_gb)
    normalized_ssd_gb = _safe_int(ssd_gb)

    segments = [normalized_chip]
    if normalized_screen_inch is not None and normalized_screen_inch > 0:
        segments.append(f"{normalized_screen_inch}인치")
    if normalized_ram_gb is not None and normalized_ram_gb > 0:
        segments.append(f"{normalized_ram_gb}GB")
    if normalized_ssd_gb is not None and normalized_ssd_gb > 0:
        segments.append(f"{normalized_ssd_gb}GB SSD")
    return "조건 변경 사이 후보 · " + " / ".join(segments)


def _safe_int_or_none(value):
    try:
        return _safe_int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool_or_none(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))

    normalized = _safe_text(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered in {"1", "true", "y", "yes"}:
        return True
    if lowered in {"0", "false", "n", "no"}:
        return False
    return None


def _build_body_excerpt_from_text(value, *, max_len=280):
    normalized = _safe_text(value)
    if normalized is None:
        return None
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len].rstrip()}..."


def _row_to_column_map(row, columns):
    if row is None:
        return {}
    if isinstance(row, dict):
        return {column: row.get(column) for column in columns}
    if isinstance(row, (tuple, list)):
        mapped = {}
        for index, column in enumerate(columns):
            mapped[column] = row[index] if index < len(row) else None
        return mapped
    return {}


def _fetch_condition_change_notice_enrichment_from_alert_events(
    cursor,
    *,
    user_id,
    product_id,
    source=None,
):
    normalized_user_id = _safe_text(user_id)
    normalized_product_id = _safe_text(product_id)
    normalized_source = _safe_text(source)
    if normalized_user_id is None or normalized_product_id is None:
        return {}

    source_filter_sql = ""
    query_params = [normalized_user_id, normalized_product_id, CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON]
    if normalized_source is not None:
        source_filter_sql = "AND source = %s"
        query_params.append(normalized_source)

    columns = (
        "source",
        "url",
        "title",
        "price_krw",
        "sort_date",
        "risk_level",
        "risk_score",
        "risk_keywords",
        "is_exchange_post",
        "trade_type",
        "body_excerpt",
        "body_text",
        "analyzed_at",
        "created_at",
    )
    try:
        cursor.execute(
            f"""
            SELECT
                source,
                url,
                title,
                price_krw,
                sort_date,
                risk_level,
                risk_score,
                risk_keywords,
                is_exchange_post,
                trade_type,
                body_excerpt,
                body_text,
                analyzed_at,
                created_at
            FROM alert_events
            WHERE user_id = %s
              AND product_id = %s
              AND COALESCE(trigger_reason, '') <> %s
              {source_filter_sql}
            ORDER BY COALESCE(analyzed_at, created_at) DESC, id DESC
            LIMIT 1
            """,
            tuple(query_params),
        )
        return _row_to_column_map(cursor.fetchone(), columns)
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    # Legacy fallback where detail columns may not exist.
    fallback_columns = ("source", "url", "title", "price_krw", "sort_date", "created_at")
    try:
        cursor.execute(
            f"""
            SELECT
                source,
                url,
                title,
                price_krw,
                sort_date,
                created_at
            FROM alert_events
            WHERE user_id = %s
              AND product_id = %s
              {source_filter_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            tuple(([normalized_user_id, normalized_product_id] + ([normalized_source] if normalized_source is not None else []))),
        )
        return _row_to_column_map(cursor.fetchone(), fallback_columns)
    except Exception as fallback_exc:
        if _is_unknown_column_error(fallback_exc):
            return {}
        raise


def _fetch_condition_change_notice_enrichment_from_url_logs(
    cursor,
    *,
    user_id,
    url,
):
    normalized_user_id = _safe_text(user_id)
    normalized_url = _safe_text(url)
    if normalized_user_id is None or normalized_url is None:
        return {}

    columns = (
        "source",
        "title",
        "body_text",
        "risk_level",
        "risk_score",
        "risk_keywords",
        "is_exchange_post",
        "trade_type",
        "created_at",
    )
    try:
        cursor.execute(
            """
            SELECT
                source,
                title,
                body_text,
                risk_level,
                risk_score,
                risk_keywords,
                is_exchange_post,
                trade_type,
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
        return _row_to_column_map(cursor.fetchone(), columns)
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    fallback_columns = ("source", "title", "body_text", "created_at")
    try:
        cursor.execute(
            """
            SELECT
                source,
                title,
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
        return _row_to_column_map(cursor.fetchone(), fallback_columns)
    except Exception as fallback_exc:
        if _is_unknown_column_error(fallback_exc):
            return {}
        raise


def _resolve_condition_change_candidate_notice_enrichment(
    cursor,
    *,
    user_id,
    product_id,
    source,
    url,
):
    alert_detail = _fetch_condition_change_notice_enrichment_from_alert_events(
        cursor,
        user_id=user_id,
        product_id=product_id,
        source=source,
    )

    lookup_url = _safe_text(url) or _safe_text(alert_detail.get("url"))
    log_detail = _fetch_condition_change_notice_enrichment_from_url_logs(
        cursor,
        user_id=user_id,
        url=lookup_url,
    )

    risk_level = (
        _safe_text(alert_detail.get("risk_level"))
        or _safe_text(log_detail.get("risk_level"))
        or "NONE"
    )
    risk_score = (
        _safe_int_or_none(alert_detail.get("risk_score"))
        if _safe_int_or_none(alert_detail.get("risk_score")) is not None
        else _safe_int_or_none(log_detail.get("risk_score"))
    )
    if risk_score is None:
        risk_score = 0

    risk_keywords = (
        _safe_text(alert_detail.get("risk_keywords"))
        or _safe_text(log_detail.get("risk_keywords"))
        or "[]"
    )

    is_exchange_post = _coerce_bool_or_none(alert_detail.get("is_exchange_post"))
    if is_exchange_post is None:
        is_exchange_post = _coerce_bool_or_none(log_detail.get("is_exchange_post"))
    if is_exchange_post is None:
        is_exchange_post = False

    trade_type = _safe_text(alert_detail.get("trade_type")) or _safe_text(log_detail.get("trade_type"))
    if trade_type is None:
        trade_type = "exchange" if is_exchange_post else "sale"

    body_text = (
        _safe_text(alert_detail.get("body_text"))
        or _safe_text(log_detail.get("body_text"))
    )
    body_excerpt = (
        _safe_text(alert_detail.get("body_excerpt"))
        or _build_body_excerpt_from_text(body_text)
    )
    analyzed_at = (
        _coerce_datetime(alert_detail.get("analyzed_at"))
        or _coerce_datetime(log_detail.get("created_at"))
        or _coerce_datetime(alert_detail.get("created_at"))
    )

    return {
        "source": _safe_text(alert_detail.get("source")) or _safe_text(log_detail.get("source")),
        "url": _safe_text(alert_detail.get("url")) or lookup_url,
        "title": _safe_text(alert_detail.get("title")) or _safe_text(log_detail.get("title")),
        "price_krw": _safe_int_or_none(alert_detail.get("price_krw")),
        "sort_date": _coerce_datetime(alert_detail.get("sort_date")),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_keywords": risk_keywords,
        "is_exchange_post": bool(is_exchange_post),
        "trade_type": trade_type,
        "body_excerpt": body_excerpt,
        "body_text": body_text,
        "analyzed_at": analyzed_at,
    }


def _insert_condition_change_candidate_notice_alert_event(
    cursor,
    *,
    user_id,
    watch_rule_id,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb,
    fair_price_krw,
    target_price_krw,
    alert_drop_rate_percent,
    alert_price_direction,
    missed_candidate_count,
    sort_date,
    listing_product_id=None,
    listing_title=None,
    listing_url=None,
    listing_source=None,
    listing_price_krw=None,
    listing_sort_date=None,
):
    normalized_user_id = _safe_text(user_id)
    normalized_rule_id = _safe_int(watch_rule_id)
    normalized_notice_sort_date = _coerce_datetime(sort_date) or datetime.now()
    normalized_sort_date = _coerce_datetime(listing_sort_date) or normalized_notice_sort_date
    normalized_message = _format_saved_at_notice_message(missed_candidate_count)

    if normalized_user_id is None or normalized_rule_id is None or normalized_rule_id <= 0:
        return {"created": False, "reason": "invalid_reference_notice_context"}

    product_id = _safe_text(listing_product_id)
    if product_id is None:
        product_id = f"cccn-{normalized_rule_id}-{int(normalized_notice_sort_date.timestamp())}"

    normalized_listing_source = _safe_text(listing_source)
    normalized_listing_url = _safe_text(listing_url)
    detail_enrichment = _resolve_condition_change_candidate_notice_enrichment(
        cursor,
        user_id=normalized_user_id,
        product_id=product_id,
        source=normalized_listing_source,
        url=normalized_listing_url,
    )

    title = _safe_text(listing_title) or _safe_text(detail_enrichment.get("title")) or _build_condition_change_candidate_notice_title(
        chip=chip,
        screen_inch=screen_inch,
        ram_gb=ram_gb,
        ssd_gb=ssd_gb,
    )
    normalized_listing_source = (
        normalized_listing_source
        or _safe_text(detail_enrichment.get("source"))
        or CONDITION_CHANGE_CANDIDATE_NOTICE_SOURCE
    )
    normalized_listing_url = (
        normalized_listing_url
        or _safe_text(detail_enrichment.get("url"))
        or ""
    )
    normalized_listing_price_krw = _safe_int_or_none(listing_price_krw)
    if normalized_listing_price_krw is None:
        normalized_listing_price_krw = _safe_int_or_none(detail_enrichment.get("price_krw"))
    normalized_sort_date = (
        _coerce_datetime(listing_sort_date)
        or _coerce_datetime(detail_enrichment.get("sort_date"))
        or normalized_notice_sort_date
    )

    detail_body_text = _safe_text(detail_enrichment.get("body_text"))
    policy_notice = "정식 알림 기준은 저장 이후 매물이며, 이 항목은 참고용 후보입니다."
    if detail_body_text is None:
        body_text = f"{normalized_message}\n{policy_notice}"
    else:
        body_text = f"{detail_body_text}\n\n[참고 알림] {normalized_message}\n{policy_notice}"

    body_excerpt = (
        _safe_text(detail_enrichment.get("body_excerpt"))
        or _build_body_excerpt_from_text(detail_body_text)
        or normalized_message
    )
    analyzed_at = _coerce_datetime(detail_enrichment.get("analyzed_at")) or normalized_notice_sort_date
    risk_level = _safe_text(detail_enrichment.get("risk_level")) or "NONE"
    risk_score = _safe_int_or_none(detail_enrichment.get("risk_score"))
    if risk_score is None:
        risk_score = 0
    risk_keywords = _safe_text(detail_enrichment.get("risk_keywords")) or "[]"
    is_exchange_post = _coerce_bool_or_none(detail_enrichment.get("is_exchange_post"))
    if is_exchange_post is None:
        is_exchange_post = False
    trade_type = _safe_text(detail_enrichment.get("trade_type"))
    if trade_type is None:
        trade_type = "exchange" if is_exchange_post else "sale"

    try:
        cursor.execute(
            """
            INSERT INTO alert_events (
                user_id,
                watch_rule_id,
                analysis_job_id,
                product_id,
                sort_date,
                source,
                url,
                title,
                price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
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
                is_read,
                read_at
            )
            VALUES (
                %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 0, 0, NULL
            )
            """,
            (
                normalized_user_id,
                normalized_rule_id,
                product_id,
                normalized_sort_date,
                normalized_listing_source,
                normalized_listing_url,
                title,
                normalized_listing_price_krw,
                _safe_text(product_type),
                _safe_text(chip),
                _safe_int(screen_inch),
                _safe_int(ram_gb),
                _safe_int(ssd_gb),
                _safe_int(fair_price_krw),
                _safe_int(target_price_krw),
                _safe_float(alert_drop_rate_percent),
                _safe_text(alert_price_direction),
                risk_level,
                risk_score,
                risk_keywords,
                bool(is_exchange_post),
                trade_type,
                body_excerpt,
                body_text,
                analyzed_at,
                CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON,
                normalized_message,
            ),
        )
        return {"created": True, "reason": "created", "product_id": product_id}
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" not in lowered_exc:
            raise

    try:
        cursor.execute(
            """
            INSERT INTO alert_events (
                user_id,
                watch_rule_id,
                product_id,
                sort_date,
                source,
                url,
                title,
                price_krw,
                fair_price_krw,
                target_price_krw,
                alert_drop_rate_percent,
                alert_price_direction,
                trigger_reason,
                message,
                status,
                send_attempts
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 0)
            """,
            (
                normalized_user_id,
                normalized_rule_id,
                product_id,
                normalized_sort_date,
                normalized_listing_source,
                normalized_listing_url,
                title,
                normalized_listing_price_krw,
                _safe_int(fair_price_krw),
                _safe_int(target_price_krw),
                _safe_float(alert_drop_rate_percent),
                _safe_text(alert_price_direction),
                CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON,
                normalized_message,
            ),
        )
        return {"created": True, "reason": "created_fallback", "product_id": product_id}
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" not in lowered_exc:
            raise

    cursor.execute(
        """
        INSERT INTO alert_events (
            user_id,
            product_id,
            url,
            title,
            price_krw,
            fair_price_krw,
            target_price_krw,
            trigger_reason,
            message,
            status,
            send_attempts
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 0)
        """,
        (
            normalized_user_id,
            product_id,
            normalized_listing_url,
            title,
            normalized_listing_price_krw,
            _safe_int(fair_price_krw),
            _safe_int(target_price_krw),
            CONDITION_CHANGE_CANDIDATE_NOTICE_TRIGGER_REASON,
            normalized_message,
        ),
    )
    return {"created": True, "reason": "created_minimal", "product_id": product_id}


def _build_rule_snapshot(
    *,
    fair_price_krw,
    alert_drop_rate_percent,
    target_buy_price_krw=None,
    alert_price_direction=DEFAULT_ALERT_PRICE_DIRECTION,
    min_price_krw=None,
    max_price_krw=None,
    enabled=True,
):
    normalized_fair_price_krw = _safe_int(fair_price_krw)
    normalized_alert_drop_rate_percent = _safe_float(alert_drop_rate_percent)
    normalized_target_buy_price_krw = _safe_int(target_buy_price_krw)
    normalized_alert_price_direction = normalize_alert_price_direction(alert_price_direction)
    normalized_min_price_krw = _safe_int(min_price_krw)
    normalized_max_price_krw = _safe_int(max_price_krw)
    normalized_enabled = _safe_bool(enabled, default=True)

    if normalized_target_buy_price_krw is None:
        normalized_target_buy_price_krw = compute_target_buy_price_krw(
            normalized_fair_price_krw,
            normalized_alert_drop_rate_percent,
        )

    return {
        "fair_price_krw": normalized_fair_price_krw,
        "alert_drop_rate_percent": normalized_alert_drop_rate_percent,
        "target_buy_price_krw": normalized_target_buy_price_krw,
        "alert_price_direction": normalized_alert_price_direction,
        "min_price_krw": normalized_min_price_krw,
        "max_price_krw": normalized_max_price_krw,
        "enabled": normalized_enabled,
    }


def _is_price_match_for_rule(listing_price_krw, rule_snapshot):
    if not isinstance(rule_snapshot, dict):
        return False
    if not _safe_bool(rule_snapshot.get("enabled"), default=True):
        return False

    normalized_listing_price_krw = _safe_int(listing_price_krw)
    if normalized_listing_price_krw is None:
        return False

    target_buy_price_krw = _safe_int(rule_snapshot.get("target_buy_price_krw"))
    if target_buy_price_krw is None:
        target_buy_price_krw = compute_target_buy_price_krw(
            rule_snapshot.get("fair_price_krw"),
            rule_snapshot.get("alert_drop_rate_percent"),
        )
    if target_buy_price_krw is None:
        return False

    alert_price_direction = normalize_alert_price_direction(rule_snapshot.get("alert_price_direction"))
    if not is_listing_alert_match(
        normalized_listing_price_krw,
        target_buy_price_krw,
        alert_price_direction,
    ):
        return False

    return passes_price_bounds(
        normalized_listing_price_krw,
        alert_price_direction,
        min_price_krw=rule_snapshot.get("min_price_krw"),
        max_price_krw=rule_snapshot.get("max_price_krw"),
    )


def _normalize_drop_percent_for_compare(value):
    normalized = _safe_float(value)
    if normalized is None:
        return None
    return round(normalized, 4)


def _insert_user_fair_price_history_if_changed(
    cursor,
    *,
    user_fair_price_id,
    user_id,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb,
    old_rule_snapshot,
    new_rule_snapshot,
    changed_at,
):
    normalized_rule_id = _safe_int(user_fair_price_id)
    if normalized_rule_id is None or normalized_rule_id <= 0:
        return {"created": False, "reason": "invalid_user_fair_price_id"}
    if not isinstance(old_rule_snapshot, dict) or not isinstance(new_rule_snapshot, dict):
        return {"created": False, "reason": "missing_rule_snapshot"}

    old_fair_price_krw = _safe_int(old_rule_snapshot.get("fair_price_krw"))
    new_fair_price_krw = _safe_int(new_rule_snapshot.get("fair_price_krw"))

    old_drop_percent = _safe_float(old_rule_snapshot.get("alert_drop_rate_percent"))
    new_drop_percent = _safe_float(new_rule_snapshot.get("alert_drop_rate_percent"))

    old_desired_price_krw = _safe_int(old_rule_snapshot.get("target_buy_price_krw"))
    if old_desired_price_krw is None:
        old_desired_price_krw = compute_target_buy_price_krw(old_fair_price_krw, old_drop_percent)
    new_desired_price_krw = _safe_int(new_rule_snapshot.get("target_buy_price_krw"))
    if new_desired_price_krw is None:
        new_desired_price_krw = compute_target_buy_price_krw(new_fair_price_krw, new_drop_percent)

    fair_changed = old_fair_price_krw != new_fair_price_krw
    desired_changed = old_desired_price_krw != new_desired_price_krw
    drop_changed = (
        _normalize_drop_percent_for_compare(old_drop_percent)
        != _normalize_drop_percent_for_compare(new_drop_percent)
    )
    if not (fair_changed or desired_changed or drop_changed):
        return {"created": False, "reason": "no_meaningful_change"}

    normalized_changed_at = _coerce_datetime(changed_at) or datetime.now()
    cursor.execute(
        """
        INSERT INTO user_fair_price_history (
            user_fair_price_id,
            user_id,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            old_fair_price_krw,
            new_fair_price_krw,
            old_desired_price_krw,
            new_desired_price_krw,
            old_drop_percent,
            new_drop_percent,
            change_type,
            changed_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, 'updated', %s
        )
        """,
        (
            normalized_rule_id,
            _safe_text(user_id),
            _safe_text(product_type),
            _safe_text(chip),
            _safe_int(screen_inch),
            _safe_int(ram_gb),
            _safe_int(ssd_gb),
            old_fair_price_krw,
            new_fair_price_krw,
            old_desired_price_krw,
            new_desired_price_krw,
            old_drop_percent,
            new_drop_percent,
            normalized_changed_at,
        ),
    )
    return {"created": True, "reason": "created"}


def _fetch_existing_user_fair_price_rule_state(
    cursor,
    *,
    user_id,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb,
):
    params = (
        user_id,
        product_type,
        chip,
        screen_inch,
        ram_gb,
        ssd_gb,
    )
    queries = (
        (
            """
            SELECT
                id,
                saved_at,
                last_poll_requested_at,
                fair_price_krw,
                alert_drop_rate_percent,
                target_buy_price_krw,
                alert_price_direction,
                min_price_krw,
                max_price_krw,
                condition_change_candidate_notice_enabled,
                enabled
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
            LIMIT 1
            """,
            (
                "id",
                "saved_at",
                "last_poll_requested_at",
                "fair_price_krw",
                "alert_drop_rate_percent",
                "target_buy_price_krw",
                "alert_price_direction",
                "min_price_krw",
                "max_price_krw",
                "condition_change_candidate_notice_enabled",
                "enabled",
            ),
        ),
        (
            """
            SELECT
                id,
                saved_at,
                last_poll_requested_at,
                fair_price_krw,
                alert_drop_rate_percent,
                target_buy_price_krw,
                alert_price_direction,
                enabled
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
            LIMIT 1
            """,
            (
                "id",
                "saved_at",
                "last_poll_requested_at",
                "fair_price_krw",
                "alert_drop_rate_percent",
                "target_buy_price_krw",
                "alert_price_direction",
                "enabled",
            ),
        ),
        (
            """
            SELECT
                id,
                saved_at,
                last_poll_requested_at,
                fair_price_krw,
                alert_drop_rate_percent,
                enabled
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
            LIMIT 1
            """,
            (
                "id",
                "saved_at",
                "last_poll_requested_at",
                "fair_price_krw",
                "alert_drop_rate_percent",
                "enabled",
            ),
        ),
        (
            """
            SELECT
                id,
                last_poll_requested_at,
                fair_price_krw,
                alert_drop_rate_percent
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
            LIMIT 1
            """,
            (
                "id",
                "last_poll_requested_at",
                "fair_price_krw",
                "alert_drop_rate_percent",
            ),
        ),
    )

    for query, columns in queries:
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            row_data = {}
            for index, column_name in enumerate(columns):
                if index < len(row):
                    row_data[column_name] = row[index]
            previous_saved_at = _coerce_datetime(row_data.get("saved_at")) or _coerce_datetime(
                row_data.get("last_poll_requested_at")
            )
            return {
                "rule_id": _safe_int(row_data.get("id")),
                "previous_saved_at": previous_saved_at,
                "rule_snapshot": _build_rule_snapshot(
                    fair_price_krw=row_data.get("fair_price_krw"),
                    alert_drop_rate_percent=row_data.get("alert_drop_rate_percent"),
                    target_buy_price_krw=row_data.get("target_buy_price_krw"),
                    alert_price_direction=row_data.get("alert_price_direction"),
                    min_price_krw=row_data.get("min_price_krw"),
                    max_price_krw=row_data.get("max_price_krw"),
                    enabled=row_data.get("enabled"),
                ),
                "condition_change_candidate_notice_enabled": _safe_bool(
                    row_data.get("condition_change_candidate_notice_enabled"),
                    default=DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED,
                ),
            }
        except Exception as exc:
            if not _is_unknown_column_error(exc):
                raise
            continue

    return None


def _collect_missed_candidates_between_saved_windows(
    cursor,
    *,
    user_id,
    rule_id,
    source,
    search_keyword,
    previous_saved_at,
    current_saved_at,
    old_rule_snapshot,
    new_rule_snapshot,
):
    normalized_rule_id = _safe_int(rule_id)
    normalized_source = (_safe_text(source) or "joongna").lower()
    normalized_search_keyword = _normalize_optional_search_keyword(search_keyword)
    if normalized_search_keyword is None:
        return {
            "candidate_rows": 0,
            "missed_count": 0,
            "representative_candidate": None,
            "missed_candidates": [],
        }

    previous_saved_at_dt = _coerce_datetime(previous_saved_at)
    current_saved_at_dt = _coerce_datetime(current_saved_at)
    if previous_saved_at_dt is None or current_saved_at_dt is None:
        return {
            "candidate_rows": 0,
            "missed_count": 0,
            "representative_candidate": None,
            "missed_candidates": [],
        }
    if previous_saved_at_dt >= current_saved_at_dt:
        return {
            "candidate_rows": 0,
            "missed_count": 0,
            "representative_candidate": None,
            "missed_candidates": [],
        }
    if not _safe_bool(new_rule_snapshot.get("enabled"), default=True):
        return {
            "candidate_rows": 0,
            "missed_count": 0,
            "representative_candidate": None,
            "missed_candidates": [],
        }

    try:
        cursor.execute(
            """
            SELECT product_id, sort_date, price_krw, title, url, source
            FROM analysis_jobs
            WHERE user_id = %s
              AND source = %s
              AND LOWER(TRIM(search_keyword)) = LOWER(TRIM(%s))
              AND sort_date IS NOT NULL
              AND sort_date >= %s
              AND sort_date < %s
              AND price_krw IS NOT NULL
            ORDER BY sort_date ASC
            """,
            (
                user_id,
                normalized_source,
                normalized_search_keyword,
                previous_saved_at_dt,
                current_saved_at_dt,
            ),
        )
    except Exception as exc:
        if _is_unknown_column_error(exc):
            return {
                "candidate_rows": 0,
                "missed_count": 0,
                "representative_candidate": None,
                "missed_candidates": [],
            }
        raise

    rows = cursor.fetchall() or []
    if not rows:
        return {
            "candidate_rows": 0,
            "missed_count": 0,
            "representative_candidate": None,
            "missed_candidates": [],
        }

    def _row_to_candidate(raw_row):
        if isinstance(raw_row, dict):
            return {
                "product_id": _safe_text(raw_row.get("product_id")),
                "sort_date": _coerce_datetime(raw_row.get("sort_date")),
                "price_krw": _safe_int(raw_row.get("price_krw")),
                "title": _safe_text(raw_row.get("title")),
                "url": _safe_text(raw_row.get("url")),
                "source": _safe_text(raw_row.get("source")),
            }
        if isinstance(raw_row, (tuple, list)):
            return {
                "product_id": _safe_text(raw_row[0]) if len(raw_row) > 0 else None,
                "sort_date": _coerce_datetime(raw_row[1]) if len(raw_row) > 1 else None,
                "price_krw": _safe_int(raw_row[2]) if len(raw_row) > 2 else None,
                "title": _safe_text(raw_row[3]) if len(raw_row) > 3 else None,
                "url": _safe_text(raw_row[4]) if len(raw_row) > 4 else None,
                "source": _safe_text(raw_row[5]) if len(raw_row) > 5 else None,
            }
        return None

    missed_count = 0
    grouped_rows = {}
    representative_candidate = None
    missed_candidates = []
    for row in rows:
        candidate = _row_to_candidate(row)
        if candidate is None:
            continue
        product_id = candidate.get("product_id")
        listing_sort_date = candidate.get("sort_date")
        listing_price_krw = candidate.get("price_krw")
        if listing_sort_date is None or listing_price_krw is None:
            continue
        if listing_sort_date < previous_saved_at_dt or listing_sort_date >= current_saved_at_dt:
            continue

        if product_id is not None:
            dedupe_key = product_id
        else:
            dedupe_key = f"anon:{listing_sort_date.isoformat()}:{listing_price_krw}"

        grouped_rows.setdefault(dedupe_key, []).append(candidate)

    for dedupe_key_rows in grouped_rows.values():
        has_missed_candidate = False
        group_representative = None
        for candidate in dedupe_key_rows:
            listing_price_krw = candidate.get("price_krw")
            old_rule_match = _is_price_match_for_rule(listing_price_krw, old_rule_snapshot)
            new_rule_match = _is_price_match_for_rule(listing_price_krw, new_rule_snapshot)
            if new_rule_match and not old_rule_match:
                has_missed_candidate = True
                if (
                    group_representative is None
                    or (candidate.get("sort_date") or datetime.min) > (group_representative.get("sort_date") or datetime.min)
                ):
                    group_representative = candidate

        if has_missed_candidate:
            missed_count += 1
            if group_representative is not None:
                missed_candidates.append(group_representative)
                if (
                    representative_candidate is None
                    or (group_representative.get("sort_date") or datetime.min) > (representative_candidate.get("sort_date") or datetime.min)
                ):
                    representative_candidate = group_representative

    missed_candidates.sort(
        key=lambda candidate: (
            candidate.get("sort_date") or datetime.min,
            _safe_text(candidate.get("product_id")) or "",
        )
    )

    return {
        "candidate_rows": len(rows),
        "missed_count": missed_count,
        "representative_candidate": representative_candidate,
        "missed_candidates": missed_candidates,
        "user_id": user_id,
        "source": normalized_source,
        "search_keyword": normalized_search_keyword,
        "rule_id": normalized_rule_id,
    }


def _count_missed_candidates_between_saved_windows(
    cursor,
    *,
    user_id,
    rule_id,
    source,
    search_keyword,
    previous_saved_at,
    current_saved_at,
    old_rule_snapshot,
    new_rule_snapshot,
):
    normalized_rule_id = _safe_int(rule_id)
    stats = _collect_missed_candidates_between_saved_windows(
        cursor,
        user_id=user_id,
        rule_id=rule_id,
        source=source,
        search_keyword=search_keyword,
        previous_saved_at=previous_saved_at,
        current_saved_at=current_saved_at,
        old_rule_snapshot=old_rule_snapshot,
        new_rule_snapshot=new_rule_snapshot,
    )
    missed_count = _safe_int(stats.get("missed_count")) or 0
    candidate_rows = _safe_int(stats.get("candidate_rows")) or 0
    normalized_source = (_safe_text(source) or "joongna").lower()
    normalized_search_keyword = _normalize_optional_search_keyword(search_keyword)

    if missed_count == 0:
        logger.info(
            "[condition_change_candidate] count_scope=keyword user_id=%s source=%s search_keyword=%s candidate_rows=%s missed_candidate_count=%s rule_id=%s",
            user_id,
            normalized_source,
            normalized_search_keyword,
            candidate_rows,
            0,
            normalized_rule_id,
        )
        return 0

    logger.info(
        "[condition_change_candidate] count_scope=keyword user_id=%s source=%s search_keyword=%s candidate_rows=%s missed_candidate_count=%s rule_id=%s",
        user_id,
        normalized_source,
        normalized_search_keyword,
        candidate_rows,
        missed_count,
        normalized_rule_id,
    )
    return missed_count


def _build_recommended_search_keyword(product_type, chip, screen_inch=None, ram_gb=None, ssd_gb=None):
    keywords = build_recommended_keywords_for_spec(
        product_type,
        chip,
        ram_gb=ram_gb,
        ssd_gb=ssd_gb,
    )
    if keywords:
        return keywords[0]

    fallback = build_default_keyword_for_watch_rule(
        {
            "product_type": product_type,
            "chip": chip,
            "screen_inch": screen_inch,
            "ram_gb": ram_gb,
            "ssd_gb": ssd_gb,
        }
    )
    return _normalize_optional_search_keyword(fallback)


def _resolve_setting_search_keyword(
    *,
    explicit_search_keyword,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb,
):
    normalized_explicit = _normalize_optional_search_keyword(explicit_search_keyword)
    if normalized_explicit is not None:
        return normalized_explicit

    recommended = _build_recommended_search_keyword(
        product_type,
        chip,
        screen_inch=screen_inch,
        ram_gb=ram_gb,
        ssd_gb=ssd_gb,
    )
    if recommended is None:
        raise ValueError("unable_to_build_search_keyword")
    return recommended


def _unit_key(product_type, chip, screen_inch, ram_gb, ssd_gb):
    return (product_type, chip, int(screen_inch), int(ram_gb), int(ssd_gb))


def _create_users_table_if_needed(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            device_id VARCHAR(200) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_users_user_id (user_id),
            UNIQUE KEY uq_users_device_id (device_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def _column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS column_count
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    row = cursor.fetchone() or {}
    return int(row.get("column_count", 0)) > 0


def _index_exists(cursor, table_name, index_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS index_count
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        """,
        (table_name, index_name),
    )
    row = cursor.fetchone() or {}
    return int(row.get("index_count", 0)) > 0


def _ensure_users_device_id_column(cursor):
    if not _column_exists(cursor, "users", "device_id"):
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN device_id VARCHAR(200) NULL AFTER user_id
            """
        )
    if not _index_exists(cursor, "users", "uq_users_device_id"):
        cursor.execute(
            """
            ALTER TABLE users
            ADD UNIQUE KEY uq_users_device_id (device_id)
            """
        )


def get_all_macbook_air_units_sorted():
    units = generate_supported_units()
    return sorted(
        units,
        key=lambda unit: (
            PRODUCT_TYPE_SORT_ORDER.get(unit.get("product_type"), 999),
            CHIP_SORT_ORDER.get(unit.get("chip"), 999),
            unit.get("screen_inch"),
            unit.get("ram_gb"),
            unit.get("ssd_gb"),
        ),
    )


def _fetch_system_defaults_map(cursor):
    product_type_placeholders = ", ".join(["%s"] * len(SUPPORTED_PRODUCT_TYPES))
    cursor.execute(
        f"""
        SELECT product_type, chip, screen_inch, ram_gb, ssd_gb, fair_price_krw
        FROM mac_fair_prices
        WHERE product_type IN ({product_type_placeholders})
        """,
        tuple(SUPPORTED_PRODUCT_TYPES),
    )
    rows = cursor.fetchall() or []
    system_map = {}
    for row in rows:
        key = _unit_key(
            row["product_type"],
            row["chip"],
            row["screen_inch"],
            row["ram_gb"],
            row["ssd_gb"],
        )
        system_map[key] = {"fair_price_krw": _safe_int(row.get("fair_price_krw"))}
    return system_map


def _fetch_user_overrides_map(cursor, user_id):
    product_type_placeholders = ", ".join(["%s"] * len(SUPPORTED_PRODUCT_TYPES))
    query_params = (user_id, *SUPPORTED_PRODUCT_TYPES)

    try:
        cursor.execute(
            f"""
            SELECT id, product_type, chip, screen_inch, ram_gb, ssd_gb,
               fair_price_krw, alert_drop_rate_percent, target_buy_price_krw, alert_price_direction,
               min_price_krw, max_price_krw,
               enabled, condition_change_candidate_notice_enabled,
               search_keyword, force_poll, poll_interval_seconds, priority,
               last_polled_at, last_poll_requested_at, saved_at
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type IN ({product_type_placeholders})
            """,
            query_params,
        )
        rows = cursor.fetchall() or []
    except Exception as exc:
        if "unknown column" not in str(exc).lower():
            raise
        try:
            cursor.execute(
                f"""
                SELECT id, product_type, chip, screen_inch, ram_gb, ssd_gb,
                   fair_price_krw, alert_drop_rate_percent, target_buy_price_krw, alert_price_direction, enabled,
                   search_keyword, force_poll, poll_interval_seconds,
                   last_polled_at, last_poll_requested_at
                FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type IN ({product_type_placeholders})
                """,
                query_params,
            )
            rows = cursor.fetchall() or []
            for row in rows:
                row["min_price_krw"] = None
                row["max_price_krw"] = None
                row["saved_at"] = row.get("saved_at") or row.get("last_poll_requested_at")
                row.setdefault(
                    "condition_change_candidate_notice_enabled",
                    DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED,
                )
                row["priority"] = DEFAULT_WATCH_PRIORITY
        except Exception as first_fallback_exc:
            if "unknown column" not in str(first_fallback_exc).lower():
                raise
            try:
                cursor.execute(
                    f"""
                    SELECT id, product_type, chip, screen_inch, ram_gb, ssd_gb,
                           fair_price_krw, alert_drop_rate_percent, enabled
                    FROM user_fair_prices
                    WHERE user_id = %s
                      AND product_type IN ({product_type_placeholders})
                    """,
                    query_params,
                )
                rows = cursor.fetchall() or []
            except Exception as second_exc:
                if "unknown column" not in str(second_exc).lower() or "enabled" not in str(second_exc).lower():
                    raise
                cursor.execute(
                    f"""
                    SELECT id, product_type, chip, screen_inch, ram_gb, ssd_gb,
                           fair_price_krw, alert_drop_rate_percent
                    FROM user_fair_prices
                    WHERE user_id = %s
                      AND product_type IN ({product_type_placeholders})
                    """,
                    query_params,
                )
                rows = cursor.fetchall() or []

            for row in rows:
                row.setdefault("enabled", True)
                row.setdefault(
                    "condition_change_candidate_notice_enabled",
                    DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED,
                )
                row["alert_price_direction"] = DEFAULT_ALERT_PRICE_DIRECTION
                row["search_keyword"] = None
                row["force_poll"] = False
                row["poll_interval_seconds"] = DEFAULT_POLL_INTERVAL_SECONDS
                row["last_polled_at"] = None
                row["last_poll_requested_at"] = None
                row["saved_at"] = None
                row["min_price_krw"] = None
                row["max_price_krw"] = None
                row["target_buy_price_krw"] = None
                row["priority"] = DEFAULT_WATCH_PRIORITY

    user_map = {}
    for row in rows:
        key = _unit_key(
            row["product_type"],
            row["chip"],
            row["screen_inch"],
            row["ram_gb"],
            row["ssd_gb"],
        )
        user_map[key] = {
            "id": _safe_int(row.get("id")),
            "fair_price_krw": _safe_int(row.get("fair_price_krw")),
            "alert_drop_rate_percent": _safe_float(row.get("alert_drop_rate_percent")),
            "target_buy_price_krw": _safe_int(row.get("target_buy_price_krw")),
            "alert_price_direction": normalize_alert_price_direction(row.get("alert_price_direction")),
            "min_price_krw": _safe_int(row.get("min_price_krw")),
            "max_price_krw": _safe_int(row.get("max_price_krw")),
            "enabled": _safe_bool(row.get("enabled"), default=True),
            "condition_change_candidate_notice_enabled": _safe_bool(
                row.get("condition_change_candidate_notice_enabled"),
                default=DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED,
            ),
            "search_keyword": _normalize_optional_search_keyword(row.get("search_keyword")),
            "force_poll": _safe_bool(row.get("force_poll"), default=False),
            "poll_interval_seconds": _safe_int(row.get("poll_interval_seconds")) or DEFAULT_POLL_INTERVAL_SECONDS,
            "priority": normalize_watch_priority(row.get("priority")),
            "last_polled_at": row.get("last_polled_at"),
            "last_poll_requested_at": row.get("last_poll_requested_at"),
            "saved_at": row.get("saved_at") or row.get("last_poll_requested_at"),
        }
        if user_map[key]["target_buy_price_krw"] is None:
            user_map[key]["target_buy_price_krw"] = compute_target_buy_price_krw(
                user_map[key].get("fair_price_krw"),
                user_map[key].get("alert_drop_rate_percent"),
            )
    return user_map


def get_user_fair_price_settings(user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id_empty")

    normalized_user_id = user_id.strip()
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        system_map = _fetch_system_defaults_map(cursor)
        user_map = _fetch_user_overrides_map(cursor, normalized_user_id)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    items = []
    for unit in get_all_macbook_air_units_sorted():
        key = _unit_key(
            unit["product_type"],
            unit["chip"],
            unit["screen_inch"],
            unit["ram_gb"],
            unit["ssd_gb"],
        )
        system_item = system_map.get(key) or {}
        user_item = user_map.get(key)

        system_fair_price_krw = system_item.get("fair_price_krw")
        system_alert_drop_rate_percent = (
            DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT if system_fair_price_krw is not None else None
        )
        system_alert_price_direction = (
            DEFAULT_ALERT_PRICE_DIRECTION if system_fair_price_krw is not None else None
        )
        system_min_price_krw = None
        system_max_price_krw = None

        has_user_override = user_item is not None
        user_fair_price_krw = user_item.get("fair_price_krw") if has_user_override else None
        user_alert_drop_rate_percent = (
            user_item.get("alert_drop_rate_percent") if has_user_override else None
        )
        user_alert_price_direction = (
            user_item.get("alert_price_direction") if has_user_override else None
        )
        user_target_buy_price_krw = user_item.get("target_buy_price_krw") if has_user_override else None
        user_min_price_krw = user_item.get("min_price_krw") if has_user_override else None
        user_max_price_krw = user_item.get("max_price_krw") if has_user_override else None
        enabled = user_item.get("enabled", True) if has_user_override else False
        condition_change_candidate_notice_enabled = (
            user_item.get(
                "condition_change_candidate_notice_enabled",
                DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED,
            )
            if has_user_override
            else DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED
        )
        custom_search_keyword = user_item.get("search_keyword") if has_user_override else None
        recommended_search_keyword = _build_recommended_search_keyword(
            unit["product_type"],
            unit["chip"],
            screen_inch=unit["screen_inch"],
            ram_gb=unit["ram_gb"],
            ssd_gb=unit["ssd_gb"],
        )
        effective_search_keyword = custom_search_keyword or recommended_search_keyword
        force_poll = user_item.get("force_poll", False) if has_user_override else False
        poll_interval_seconds = (
            user_item.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
            if has_user_override
            else DEFAULT_POLL_INTERVAL_SECONDS
        )
        priority = (
            normalize_watch_priority(user_item.get("priority"))
            if has_user_override
            else DEFAULT_WATCH_PRIORITY
        )
        last_polled_at = user_item.get("last_polled_at") if has_user_override else None
        last_poll_requested_at = user_item.get("last_poll_requested_at") if has_user_override else None
        saved_at = user_item.get("saved_at") if has_user_override else None
        user_rule_id = user_item.get("id") if has_user_override else None

        if has_user_override:
            effective_fair_price_krw = user_fair_price_krw
            effective_alert_drop_rate_percent = user_alert_drop_rate_percent
            effective_alert_price_direction = user_alert_price_direction
            effective_target_buy_price_krw = user_target_buy_price_krw
            effective_min_price_krw = user_min_price_krw
            effective_max_price_krw = user_max_price_krw
        else:
            effective_fair_price_krw = system_fair_price_krw
            effective_alert_drop_rate_percent = system_alert_drop_rate_percent
            effective_alert_price_direction = system_alert_price_direction
            effective_target_buy_price_krw = None
            effective_min_price_krw = system_min_price_krw
            effective_max_price_krw = system_max_price_krw
        if effective_target_buy_price_krw is None:
            effective_target_buy_price_krw = compute_target_buy_price_krw(
                effective_fair_price_krw,
                effective_alert_drop_rate_percent,
            )

        items.append(
            {
                "id": user_rule_id,
                "product_type": unit["product_type"],
                "chip": unit["chip"],
                "screen_inch": unit["screen_inch"],
                "ram_gb": unit["ram_gb"],
                "ssd_gb": unit["ssd_gb"],
                "system_fair_price_krw": system_fair_price_krw,
                "system_alert_drop_rate_percent": system_alert_drop_rate_percent,
                "system_alert_price_direction": system_alert_price_direction,
                "system_min_price_krw": system_min_price_krw,
                "system_max_price_krw": system_max_price_krw,
                "user_fair_price_krw": user_fair_price_krw,
                "user_alert_drop_rate_percent": user_alert_drop_rate_percent,
                "user_alert_price_direction": user_alert_price_direction,
                "user_target_buy_price_krw": user_target_buy_price_krw,
                "user_min_price_krw": user_min_price_krw,
                "user_max_price_krw": user_max_price_krw,
                "enabled": bool(enabled),
                "condition_change_candidate_notice_enabled": bool(condition_change_candidate_notice_enabled),
                "effective_fair_price_krw": effective_fair_price_krw,
                "effective_alert_drop_rate_percent": effective_alert_drop_rate_percent,
                "effective_alert_price_direction": effective_alert_price_direction,
                "effective_target_buy_price_krw": effective_target_buy_price_krw,
                "effective_min_price_krw": effective_min_price_krw,
                "effective_max_price_krw": effective_max_price_krw,
                "custom_search_keyword": custom_search_keyword,
                "recommended_search_keyword": recommended_search_keyword,
                "effective_search_keyword": effective_search_keyword,
                "poll_interval_seconds": poll_interval_seconds,
                "priority": priority,
                "force_poll": bool(force_poll),
                "last_polled_at": last_polled_at,
                "last_poll_requested_at": last_poll_requested_at,
                "saved_at": saved_at,
                "has_user_override": has_user_override,
            }
        )

    return items


def register_user(user_id, device_id=None):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id_empty")

    normalized_user_id = user_id.strip()
    normalized_device_id = device_id.strip() if isinstance(device_id, str) and device_id.strip() else None
    masked_device_id = _mask_device_id(normalized_device_id)

    logger.info(
        "[users/register] start requested_user_id=%s device_id=%s",
        normalized_user_id,
        masked_device_id,
    )

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _create_users_table_if_needed(cursor)
        _ensure_users_device_id_column(cursor)

        cursor.execute(
            """
            SELECT id, user_id, device_id
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (normalized_user_id,),
        )
        existing_by_user = cursor.fetchone()

        # device_id 없이 호출되는 경로는 "등록된 사용자 확인"만 허용한다.
        if normalized_device_id is None:
            if existing_by_user is None:
                return {
                    "ok": False,
                    "reason": "user_not_registered",
                    "message": "등록된 사용자가 없습니다. 먼저 로그인해주세요.",
                }
            cursor.execute(
                """
                UPDATE users
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (existing_by_user["id"],),
            )
            connection.commit()
            return {
                "ok": True,
                "user_id": existing_by_user["user_id"],
                "message": "기존 사용자 확인 완료",
                "action": "existing_user_check",
                "requested_user_id": normalized_user_id,
                "saved_user_id": existing_by_user["user_id"],
            }

        cursor.execute(
            """
            SELECT id, user_id, device_id
            FROM users
            WHERE device_id = %s
            LIMIT 1
            """,
            (normalized_device_id,),
        )
        existing_by_device = cursor.fetchone()

        if existing_by_user is None and existing_by_device is None:
            cursor.execute(
                """
                INSERT INTO users (user_id, device_id)
                VALUES (%s, %s)
                """,
                (normalized_user_id, normalized_device_id),
            )
            connection.commit()
            return {
                "ok": True,
                "user_id": normalized_user_id,
                "message": "사용자 등록 완료",
                "action": "created",
                "requested_user_id": normalized_user_id,
                "saved_user_id": normalized_user_id,
                "commit_called": True,
            }

        if existing_by_user is not None and existing_by_device is not None:
            if existing_by_user["id"] != existing_by_device["id"]:
                return {
                    "ok": False,
                    "reason": "user_device_mismatch",
                    "message": "user_id와 device_id가 서로 일치하지 않습니다.",
                    "requested_user_id": normalized_user_id,
                }
            cursor.execute(
                """
                UPDATE users
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (existing_by_user["id"],),
            )
            connection.commit()
            return {
                "ok": True,
                "user_id": existing_by_user["user_id"],
                "message": "기존 사용자로 로그인",
                "action": "existing_user_login",
                "requested_user_id": normalized_user_id,
                "saved_user_id": existing_by_user["user_id"],
                "commit_called": True,
            }

        if existing_by_user is not None and existing_by_device is None:
            existing_user_device_id = _safe_text(existing_by_user.get("device_id"))
            if existing_user_device_id is None:
                cursor.execute(
                    """
                    UPDATE users
                    SET device_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (normalized_device_id, existing_by_user["id"]),
                )
                connection.commit()
                return {
                    "ok": True,
                    "user_id": existing_by_user["user_id"],
                    "message": "기존 사용자 기기에 로그인",
                    "action": "existing_user_bind_device",
                    "requested_user_id": normalized_user_id,
                    "saved_user_id": existing_by_user["user_id"],
                    "commit_called": True,
                }
            return {
                "ok": False,
                "reason": "user_device_mismatch",
                "message": "해당 user_id는 다른 device_id에 연결되어 있습니다.",
                "requested_user_id": normalized_user_id,
                "saved_user_id": existing_by_user["user_id"],
            }

        if existing_by_user is None and existing_by_device is not None:
            return {
                "ok": False,
                "reason": "device_user_mismatch",
                "message": "해당 device_id는 다른 user_id에 연결되어 있습니다.",
                "requested_user_id": normalized_user_id,
                "saved_user_id": existing_by_device["user_id"],
            }

        return {
            "ok": False,
            "reason": "unknown_register_state",
            "message": "등록 상태를 확인할 수 없습니다.",
        }
    except Exception:
        if connection is not None and connection.is_connected():
            try:
                connection.rollback()
                logger.info("[users/register] rollback called due to exception")
            except Exception as rollback_exc:
                logger.warning("[users/register] rollback failed: %s", rollback_exc)
        logger.exception(
            "[users/register] failed requested_user_id=%s device_id=%s",
            normalized_user_id,
            masked_device_id,
        )
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def upsert_user_fair_price_setting(
    user_id,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb,
    fair_price_krw,
    alert_drop_rate_percent,
    enabled,
    alert_price_direction=DEFAULT_ALERT_PRICE_DIRECTION,
    min_price_krw=None,
    max_price_krw=None,
    search_keyword=None,
    poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
    priority=DEFAULT_WATCH_PRIORITY,
    condition_change_candidate_notice_enabled=DEFAULT_CONDITION_CHANGE_CANDIDATE_NOTICE_ENABLED,
):
    if not isinstance(user_id, str) or not user_id.strip():
        return {"ok": False, "reason": "invalid_user_id"}

    normalized_user_id = user_id.strip()
    normalized_product_type = product_type.strip() if isinstance(product_type, str) else ""
    normalized_chip = _normalize_chip_for_setting(chip)

    if not is_supported_product_type(normalized_product_type):
        return {"ok": False, "reason": "invalid_product_type"}

    try:
        normalized_screen_inch = int(screen_inch)
        normalized_ram_gb = int(ram_gb)
        normalized_ssd_gb = int(ssd_gb)
        normalized_fair_price_krw = int(fair_price_krw)
        normalized_alert_drop_rate_percent = float(alert_drop_rate_percent)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "invalid_numeric_value"}

    if normalized_fair_price_krw <= 0:
        return {"ok": False, "reason": "invalid_fair_price_krw"}

    if not is_valid_alert_drop_rate_percent(normalized_alert_drop_rate_percent):
        return {"ok": False, "reason": "invalid_alert_drop_rate_percent"}

    if alert_price_direction is None:
        normalized_alert_price_direction = DEFAULT_ALERT_PRICE_DIRECTION
    elif not is_valid_alert_price_direction(alert_price_direction):
        return {"ok": False, "reason": "invalid_alert_price_direction"}
    else:
        normalized_alert_price_direction = normalize_alert_price_direction(alert_price_direction)

    try:
        normalized_min_price_krw, normalized_max_price_krw = _normalize_alert_bounds(
            alert_price_direction=normalized_alert_price_direction,
            min_price_krw=min_price_krw,
            max_price_krw=max_price_krw,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}

    if not isinstance(enabled, bool):
        return {"ok": False, "reason": "invalid_enabled"}
    if not isinstance(condition_change_candidate_notice_enabled, bool):
        return {"ok": False, "reason": "invalid_condition_change_candidate_notice_enabled"}

    if not is_valid_silicon_unit(
        normalized_product_type,
        normalized_chip,
        normalized_screen_inch,
        normalized_ram_gb,
        normalized_ssd_gb,
    ):
        return {"ok": False, "reason": "invalid_silicon_unit"}

    try:
        normalized_poll_interval_seconds = _normalize_poll_interval_seconds(poll_interval_seconds)
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    normalized_priority = normalize_watch_priority(priority)

    try:
        resolved_search_keyword = _resolve_setting_search_keyword(
            explicit_search_keyword=search_keyword,
            product_type=normalized_product_type,
            chip=normalized_chip,
            screen_inch=normalized_screen_inch,
            ram_gb=normalized_ram_gb,
            ssd_gb=normalized_ssd_gb,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}

    request_payload = {
        "user_id": normalized_user_id,
        "product_type": normalized_product_type,
        "chip": normalized_chip,
        "screen_inch": normalized_screen_inch,
        "ram_gb": normalized_ram_gb,
        "ssd_gb": normalized_ssd_gb,
        "fair_price_krw": normalized_fair_price_krw,
        "alert_drop_rate_percent": normalized_alert_drop_rate_percent,
        "enabled": enabled,
        "alert_price_direction": normalized_alert_price_direction,
        "min_price_krw": normalized_min_price_krw,
        "max_price_krw": normalized_max_price_krw,
        "search_keyword": resolved_search_keyword,
        "poll_interval_seconds": normalized_poll_interval_seconds,
        "priority": normalized_priority,
        "condition_change_candidate_notice_enabled": condition_change_candidate_notice_enabled,
    }

    connection = None
    cursor = None
    save_action_type = "save_user_fair_price"
    immediate_poll_requested = bool(enabled)
    previous_saved_at = None
    current_saved_at = None
    missed_candidate_count = 0
    representative_missed_candidate = None
    missed_candidates = []
    condition_change_notice_created = False
    condition_change_notice_error = None
    rule_id = None
    old_rule_snapshot = None
    new_rule_snapshot = _build_rule_snapshot(
        fair_price_krw=normalized_fair_price_krw,
        alert_drop_rate_percent=normalized_alert_drop_rate_percent,
        target_buy_price_krw=compute_target_buy_price_krw(
            normalized_fair_price_krw,
            normalized_alert_drop_rate_percent,
        ),
        alert_price_direction=normalized_alert_price_direction,
        min_price_krw=normalized_min_price_krw,
        max_price_krw=normalized_max_price_krw,
        enabled=enabled,
    )

    def _build_save_log_metadata():
        return {
            "missed_candidate_count": missed_candidate_count,
            "condition_change_notice_created": condition_change_notice_created,
            "condition_change_notice_error": condition_change_notice_error,
            "previous_saved_at": previous_saved_at,
            "current_saved_at": current_saved_at,
        }

    def _log_failed_save_result(reason, *, error_code=None, error_message=None):
        save_log_id = _insert_user_settings_save_log(
            user_id=normalized_user_id,
            watch_rule_id=rule_id,
            action_type=save_action_type,
            request_payload=request_payload,
            response_payload=None,
            success=False,
            error_code=error_code or USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED,
            error_message=error_message or reason,
            metadata=_build_save_log_metadata(),
        )
        result = {"ok": False, "reason": reason}
        if save_log_id is not None:
            result["save_log_id"] = save_log_id
        return result

    try:
        connection = get_connection()
        cursor = connection.cursor()
        existing_rule_state = _fetch_existing_user_fair_price_rule_state(
            cursor,
            user_id=normalized_user_id,
            product_type=normalized_product_type,
            chip=normalized_chip,
            screen_inch=normalized_screen_inch,
            ram_gb=normalized_ram_gb,
            ssd_gb=normalized_ssd_gb,
        )
        if isinstance(existing_rule_state, dict):
            previous_saved_at = _coerce_datetime(existing_rule_state.get("previous_saved_at"))
            old_rule_snapshot = existing_rule_state.get("rule_snapshot")
            rule_id = _safe_int(existing_rule_state.get("rule_id"))
        save_action_type = "update_watch_rule" if rule_id is not None else "create_watch_rule"

        try:
            cursor.execute("SELECT CURRENT_TIMESTAMP")
            now_row = cursor.fetchone()
            if now_row is not None and len(now_row) > 0:
                current_saved_at = _coerce_datetime(now_row[0])
        except Exception:
            current_saved_at = None
        if current_saved_at is None:
            current_saved_at = datetime.now()

        try:
            cursor.execute(
                """
                INSERT INTO user_fair_prices (
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    alert_price_direction,
                    min_price_krw,
                    max_price_krw,
                    enabled,
                    condition_change_candidate_notice_enabled,
                    search_keyword,
                    poll_interval_seconds,
                    force_poll,
                    last_poll_requested_at,
                    last_polled_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    IF(%s = TRUE, TRUE, FALSE),
                    IF(%s = TRUE, CURRENT_TIMESTAMP, NULL),
                    NULL
                )
                ON DUPLICATE KEY UPDATE
                    fair_price_krw = VALUES(fair_price_krw),
                    alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                    alert_price_direction = VALUES(alert_price_direction),
                    min_price_krw = VALUES(min_price_krw),
                    max_price_krw = VALUES(max_price_krw),
                    enabled = VALUES(enabled),
                    condition_change_candidate_notice_enabled = VALUES(condition_change_candidate_notice_enabled),
                    search_keyword = VALUES(search_keyword),
                    poll_interval_seconds = VALUES(poll_interval_seconds),
                    force_poll = CASE
                        WHEN VALUES(enabled) = TRUE THEN TRUE
                        ELSE FALSE
                    END,
                    last_poll_requested_at = CASE
                        WHEN VALUES(enabled) = TRUE THEN CURRENT_TIMESTAMP
                        ELSE last_poll_requested_at
                    END,
                    last_polled_at = CASE
                        WHEN VALUES(enabled) = TRUE THEN NULL
                        ELSE last_polled_at
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    normalized_user_id,
                    normalized_product_type,
                    normalized_chip,
                    normalized_screen_inch,
                    normalized_ram_gb,
                    normalized_ssd_gb,
                    normalized_fair_price_krw,
                    normalized_alert_drop_rate_percent,
                    normalized_alert_price_direction,
                    normalized_min_price_krw,
                    normalized_max_price_krw,
                    enabled,
                    condition_change_candidate_notice_enabled,
                    resolved_search_keyword,
                    normalized_poll_interval_seconds,
                    enabled,
                    enabled,
                ),
            )
        except Exception as exc:
            lowered_exc = str(exc).lower()
            if "unknown column" not in lowered_exc:
                raise
            handled_unknown_column = False
            if "condition_change_candidate_notice_enabled" in lowered_exc:
                cursor.execute(
                    """
                    INSERT INTO user_fair_prices (
                        user_id,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        fair_price_krw,
                        alert_drop_rate_percent,
                        alert_price_direction,
                        min_price_krw,
                        max_price_krw,
                        enabled,
                        search_keyword,
                        poll_interval_seconds,
                        force_poll,
                        last_poll_requested_at,
                        last_polled_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s,
                        %s,
                        %s,
                        IF(%s = TRUE, TRUE, FALSE),
                        IF(%s = TRUE, CURRENT_TIMESTAMP, NULL),
                        NULL
                    )
                    ON DUPLICATE KEY UPDATE
                        fair_price_krw = VALUES(fair_price_krw),
                        alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                        alert_price_direction = VALUES(alert_price_direction),
                        min_price_krw = VALUES(min_price_krw),
                        max_price_krw = VALUES(max_price_krw),
                        enabled = VALUES(enabled),
                        search_keyword = VALUES(search_keyword),
                        poll_interval_seconds = VALUES(poll_interval_seconds),
                        force_poll = CASE
                            WHEN VALUES(enabled) = TRUE THEN TRUE
                            ELSE FALSE
                        END,
                        last_poll_requested_at = CASE
                            WHEN VALUES(enabled) = TRUE THEN CURRENT_TIMESTAMP
                            ELSE last_poll_requested_at
                        END,
                        last_polled_at = CASE
                            WHEN VALUES(enabled) = TRUE THEN NULL
                            ELSE last_polled_at
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        normalized_user_id,
                        normalized_product_type,
                        normalized_chip,
                        normalized_screen_inch,
                        normalized_ram_gb,
                        normalized_ssd_gb,
                        normalized_fair_price_krw,
                        normalized_alert_drop_rate_percent,
                        normalized_alert_price_direction,
                        normalized_min_price_krw,
                        normalized_max_price_krw,
                        enabled,
                        resolved_search_keyword,
                        normalized_poll_interval_seconds,
                        enabled,
                        enabled,
                    ),
                )
                handled_unknown_column = True
            elif "min_price_krw" in lowered_exc or "max_price_krw" in lowered_exc:
                try:
                    cursor.execute(
                        """
                        INSERT INTO user_fair_prices (
                            user_id,
                            product_type,
                            chip,
                            screen_inch,
                            ram_gb,
                            ssd_gb,
                            fair_price_krw,
                            alert_drop_rate_percent,
                            alert_price_direction,
                            enabled,
                            search_keyword,
                            poll_interval_seconds,
                            force_poll,
                            last_poll_requested_at,
                            last_polled_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s,
                            %s,
                            %s,
                            IF(%s = TRUE, TRUE, FALSE),
                            IF(%s = TRUE, CURRENT_TIMESTAMP, NULL),
                            NULL
                        )
                        ON DUPLICATE KEY UPDATE
                            fair_price_krw = VALUES(fair_price_krw),
                            alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                            alert_price_direction = VALUES(alert_price_direction),
                            enabled = VALUES(enabled),
                            search_keyword = VALUES(search_keyword),
                            poll_interval_seconds = VALUES(poll_interval_seconds),
                            force_poll = CASE
                                WHEN VALUES(enabled) = TRUE THEN TRUE
                                ELSE FALSE
                            END,
                            last_poll_requested_at = CASE
                                WHEN VALUES(enabled) = TRUE THEN CURRENT_TIMESTAMP
                                ELSE last_poll_requested_at
                            END,
                            last_polled_at = CASE
                                WHEN VALUES(enabled) = TRUE THEN NULL
                                ELSE last_polled_at
                            END,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            normalized_user_id,
                            normalized_product_type,
                            normalized_chip,
                            normalized_screen_inch,
                            normalized_ram_gb,
                            normalized_ssd_gb,
                            normalized_fair_price_krw,
                            normalized_alert_drop_rate_percent,
                            normalized_alert_price_direction,
                            enabled,
                            resolved_search_keyword,
                            normalized_poll_interval_seconds,
                            enabled,
                            enabled,
                        ),
                    )
                    handled_unknown_column = True
                except Exception as second_exc:
                    lowered_second_exc = str(second_exc).lower()
                    if "unknown column" not in lowered_second_exc or "alert_price_direction" not in lowered_second_exc:
                        raise
                    cursor.execute(
                        """
                        INSERT INTO user_fair_prices (
                            user_id,
                            product_type,
                            chip,
                            screen_inch,
                            ram_gb,
                            ssd_gb,
                            fair_price_krw,
                            alert_drop_rate_percent,
                            enabled,
                            search_keyword,
                            poll_interval_seconds,
                            force_poll,
                            last_poll_requested_at,
                            last_polled_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s,
                            %s,
                            IF(%s = TRUE, TRUE, FALSE),
                            IF(%s = TRUE, CURRENT_TIMESTAMP, NULL),
                            NULL
                        )
                        ON DUPLICATE KEY UPDATE
                            fair_price_krw = VALUES(fair_price_krw),
                            alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                            enabled = VALUES(enabled),
                            search_keyword = VALUES(search_keyword),
                            poll_interval_seconds = VALUES(poll_interval_seconds),
                            force_poll = CASE
                                WHEN VALUES(enabled) = TRUE THEN TRUE
                                ELSE FALSE
                            END,
                            last_poll_requested_at = CASE
                                WHEN VALUES(enabled) = TRUE THEN CURRENT_TIMESTAMP
                                ELSE last_poll_requested_at
                            END,
                            last_polled_at = CASE
                                WHEN VALUES(enabled) = TRUE THEN NULL
                                ELSE last_polled_at
                            END,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            normalized_user_id,
                            normalized_product_type,
                            normalized_chip,
                            normalized_screen_inch,
                            normalized_ram_gb,
                            normalized_ssd_gb,
                            normalized_fair_price_krw,
                            normalized_alert_drop_rate_percent,
                            enabled,
                            resolved_search_keyword,
                            normalized_poll_interval_seconds,
                            enabled,
                            enabled,
                        ),
                    )
                    handled_unknown_column = True
            elif "alert_price_direction" in lowered_exc:
                cursor.execute(
                    """
                    INSERT INTO user_fair_prices (
                        user_id,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        fair_price_krw,
                        alert_drop_rate_percent,
                        enabled,
                        search_keyword,
                        poll_interval_seconds,
                        force_poll,
                        last_poll_requested_at,
                        last_polled_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s,
                        %s,
                        IF(%s = TRUE, TRUE, FALSE),
                        IF(%s = TRUE, CURRENT_TIMESTAMP, NULL),
                        NULL
                    )
                    ON DUPLICATE KEY UPDATE
                        fair_price_krw = VALUES(fair_price_krw),
                        alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                        enabled = VALUES(enabled),
                        search_keyword = VALUES(search_keyword),
                        poll_interval_seconds = VALUES(poll_interval_seconds),
                        force_poll = CASE
                            WHEN VALUES(enabled) = TRUE THEN TRUE
                            ELSE FALSE
                        END,
                        last_poll_requested_at = CASE
                            WHEN VALUES(enabled) = TRUE THEN CURRENT_TIMESTAMP
                            ELSE last_poll_requested_at
                        END,
                        last_polled_at = CASE
                            WHEN VALUES(enabled) = TRUE THEN NULL
                            ELSE last_polled_at
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        normalized_user_id,
                        normalized_product_type,
                        normalized_chip,
                        normalized_screen_inch,
                        normalized_ram_gb,
                        normalized_ssd_gb,
                        normalized_fair_price_krw,
                        normalized_alert_drop_rate_percent,
                        enabled,
                        resolved_search_keyword,
                        normalized_poll_interval_seconds,
                        enabled,
                        enabled,
                    ),
                )
                handled_unknown_column = True
            elif "enabled" in lowered_exc:
                return _log_failed_save_result(
                    "missing_enabled_column",
                    error_code=USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED,
                    error_message=str(exc),
                )
            if (
                "search_keyword" in lowered_exc
                or "poll_interval_seconds" in lowered_exc
                or "force_poll" in lowered_exc
                or "priority" in lowered_exc
            ):
                return _log_failed_save_result(
                    "missing_polling_columns",
                    error_code=USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED,
                    error_message=str(exc),
                )
            if not handled_unknown_column and "alert_price_direction" not in lowered_exc:
                raise

        try:
            cursor.execute(
                """
                UPDATE user_fair_prices
                SET priority = %s
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    normalized_priority,
                    normalized_user_id,
                    normalized_product_type,
                    normalized_chip,
                    normalized_screen_inch,
                    normalized_ram_gb,
                    normalized_ssd_gb,
                ),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower() or "priority" not in str(exc).lower():
                raise

        try:
            cursor.execute(
                """
                UPDATE user_fair_prices
                SET
                    saved_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    current_saved_at,
                    normalized_user_id,
                    normalized_product_type,
                    normalized_chip,
                    normalized_screen_inch,
                    normalized_ram_gb,
                    normalized_ssd_gb,
                ),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower() or "saved_at" not in str(exc).lower():
                raise

        if rule_id is not None and old_rule_snapshot is not None:
            try:
                _insert_user_fair_price_history_if_changed(
                    cursor,
                    user_fair_price_id=rule_id,
                    user_id=normalized_user_id,
                    product_type=normalized_product_type,
                    chip=normalized_chip,
                    screen_inch=normalized_screen_inch,
                    ram_gb=normalized_ram_gb,
                    ssd_gb=normalized_ssd_gb,
                    old_rule_snapshot=old_rule_snapshot,
                    new_rule_snapshot=new_rule_snapshot,
                    changed_at=current_saved_at,
                )
            except Exception as history_exc:
                lowered_history_exc = str(history_exc).lower()
                if "doesn't exist" in lowered_history_exc and "user_fair_price_history" in lowered_history_exc:
                    logger.warning(
                        "user_fair_price_history table missing; skip history insert user_id=%s rule_id=%s",
                        normalized_user_id,
                        rule_id,
                    )
                else:
                    raise

        if (
            previous_saved_at is not None
            and current_saved_at is not None
            and old_rule_snapshot is not None
            and rule_id is not None
        ):
            missed_candidate_stats = _collect_missed_candidates_between_saved_windows(
                cursor,
                user_id=normalized_user_id,
                rule_id=rule_id,
                source="joongna",
                search_keyword=resolved_search_keyword,
                previous_saved_at=previous_saved_at,
                current_saved_at=current_saved_at,
                old_rule_snapshot=old_rule_snapshot,
                new_rule_snapshot=new_rule_snapshot,
            )
            missed_candidate_count = _safe_int(missed_candidate_stats.get("missed_count")) or 0
            representative_missed_candidate = missed_candidate_stats.get("representative_candidate")
            missed_candidates = (
                missed_candidate_stats.get("missed_candidates")
                if isinstance(missed_candidate_stats.get("missed_candidates"), list)
                else []
            )
            logger.info(
                "[condition_change_candidate] count_scope=keyword user_id=%s source=%s search_keyword=%s candidate_rows=%s missed_candidate_count=%s rule_id=%s",
                normalized_user_id,
                "joongna",
                resolved_search_keyword,
                _safe_int(missed_candidate_stats.get("candidate_rows")) or 0,
                missed_candidate_count,
                rule_id,
            )

        if (
            missed_candidate_count > 0
            and condition_change_candidate_notice_enabled
            and rule_id is not None
        ):
            candidate_notice_targets = []
            for candidate in missed_candidates:
                if isinstance(candidate, dict):
                    candidate_notice_targets.append(candidate)

            if not candidate_notice_targets and isinstance(representative_missed_candidate, dict):
                candidate_notice_targets.append(representative_missed_candidate)

            if not candidate_notice_targets:
                candidate_notice_targets.append({})

            created_notice_count = 0
            failed_notice_count = 0
            first_notice_error = None

            try:
                for candidate in candidate_notice_targets:
                    notice_insert_result = _insert_condition_change_candidate_notice_alert_event(
                        cursor,
                        user_id=normalized_user_id,
                        watch_rule_id=rule_id,
                        product_type=normalized_product_type,
                        chip=normalized_chip,
                        screen_inch=normalized_screen_inch,
                        ram_gb=normalized_ram_gb,
                        ssd_gb=normalized_ssd_gb,
                        fair_price_krw=normalized_fair_price_krw,
                        target_price_krw=compute_target_buy_price_krw(
                            normalized_fair_price_krw,
                            normalized_alert_drop_rate_percent,
                        ),
                        alert_drop_rate_percent=normalized_alert_drop_rate_percent,
                        alert_price_direction=normalized_alert_price_direction,
                        missed_candidate_count=missed_candidate_count,
                        sort_date=current_saved_at,
                        listing_product_id=candidate.get("product_id") if isinstance(candidate, dict) else None,
                        listing_title=candidate.get("title") if isinstance(candidate, dict) else None,
                        listing_url=candidate.get("url") if isinstance(candidate, dict) else None,
                        listing_source=candidate.get("source") if isinstance(candidate, dict) else None,
                        listing_price_krw=candidate.get("price_krw") if isinstance(candidate, dict) else None,
                        listing_sort_date=candidate.get("sort_date") if isinstance(candidate, dict) else None,
                    )

                    if isinstance(notice_insert_result, dict) and notice_insert_result.get("created") is True:
                        created_notice_count += 1
                        continue

                    failed_notice_count += 1
                    notice_reason = _safe_text(
                        notice_insert_result.get("reason") if isinstance(notice_insert_result, dict) else None
                    )
                    if first_notice_error is None:
                        first_notice_error = notice_reason or "notice_not_created"
                    logger.warning(
                        "condition-change candidate notice not created user_id=%s rule_id=%s product_id=%s result=%s",
                        normalized_user_id,
                        rule_id,
                        candidate.get("product_id") if isinstance(candidate, dict) else None,
                        notice_insert_result,
                    )

                condition_change_notice_created = (
                    created_notice_count > 0 and failed_notice_count == 0
                )

                if failed_notice_count > 0:
                    condition_change_notice_error = first_notice_error or "notice_not_created"
                    logger.warning(
                        "condition-change candidate notice partial failure user_id=%s rule_id=%s created=%s failed=%s total=%s",
                        normalized_user_id,
                        rule_id,
                        created_notice_count,
                        failed_notice_count,
                        len(candidate_notice_targets),
                    )

                if created_notice_count == 0 and condition_change_notice_error is None:
                    condition_change_notice_error = "notice_not_created"
            except Exception as notice_exc:
                condition_change_notice_created = False
                condition_change_notice_error = _safe_text(str(notice_exc)) or "notice_insert_failed"
                logger.warning(
                    "condition-change candidate notice insert skipped user_id=%s rule_id=%s reason=%s",
                    normalized_user_id,
                    rule_id,
                    notice_exc,
                    exc_info=True,
                )

        response_message = "사용자 공정가 설정 저장 완료"
        if missed_candidate_count > 0 and condition_change_candidate_notice_enabled:
            if condition_change_notice_created:
                response_message = _format_saved_at_notice_message(missed_candidate_count)
            else:
                response_message = (
                    "조건 변경 사이 후보는 찾았지만 참고 알림 생성에 실패했어요. 서버 로그를 확인해 주세요."
                )

        response_payload = {
            "ok": True,
            "message": response_message,
            "immediate_poll_requested": immediate_poll_requested,
            "saved_at": current_saved_at,
            "previous_saved_at": previous_saved_at,
            "missed_candidate_count": missed_candidate_count,
            "condition_change_notice_created": condition_change_notice_created,
            "condition_change_notice_error": condition_change_notice_error,
            "item": {
                "id": rule_id,
                "user_id": normalized_user_id,
                "product_type": normalized_product_type,
                "chip": normalized_chip,
                "screen_inch": normalized_screen_inch,
                "ram_gb": normalized_ram_gb,
                "ssd_gb": normalized_ssd_gb,
                "fair_price_krw": normalized_fair_price_krw,
                "alert_drop_rate_percent": normalized_alert_drop_rate_percent,
                "target_buy_price_krw": compute_target_buy_price_krw(
                    normalized_fair_price_krw,
                    normalized_alert_drop_rate_percent,
                ),
                "alert_price_direction": normalized_alert_price_direction,
                "min_price_krw": normalized_min_price_krw,
                "max_price_krw": normalized_max_price_krw,
                "enabled": enabled,
                "condition_change_candidate_notice_enabled": condition_change_candidate_notice_enabled,
                "custom_search_keyword": resolved_search_keyword,
                "recommended_search_keyword": _build_recommended_search_keyword(
                    normalized_product_type,
                    normalized_chip,
                    screen_inch=normalized_screen_inch,
                    ram_gb=normalized_ram_gb,
                    ssd_gb=normalized_ssd_gb,
                ),
                "poll_interval_seconds": normalized_poll_interval_seconds,
                "priority": normalized_priority,
            },
        }
        condition_change_notice_attempted = bool(
            missed_candidate_count > 0 and condition_change_candidate_notice_enabled
        )
        condition_change_notice_failed = bool(
            condition_change_notice_attempted and not condition_change_notice_created
        )
        save_log_id = _insert_user_settings_save_log(
            user_id=normalized_user_id,
            watch_rule_id=rule_id,
            action_type=save_action_type,
            request_payload=request_payload,
            response_payload=response_payload,
            success=True,
            error_code=(
                USER_SETTINGS_SAVE_LOG_ERROR_CONDITION_CHANGE_NOTICE_INSERT_FAILED
                if condition_change_notice_failed
                else None
            ),
            error_message=condition_change_notice_error if condition_change_notice_failed else None,
            metadata=_build_save_log_metadata(),
            connection=connection,
            cursor=cursor,
            commit=False,
        )
        if save_log_id is not None:
            response_payload["save_log_id"] = save_log_id

        connection.commit()
        return response_payload
    except Exception as exc:
        if connection is not None and connection.is_connected():
            try:
                connection.rollback()
            except Exception:
                logger.warning(
                    "user-fair-price upsert rollback failed user_id=%s rule_id=%s",
                    normalized_user_id,
                    rule_id,
                    exc_info=True,
                )

        _insert_user_settings_save_log(
            user_id=normalized_user_id,
            watch_rule_id=rule_id,
            action_type=save_action_type,
            request_payload=request_payload,
            response_payload=None,
            success=False,
            error_code=USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED,
            error_message=str(exc),
            metadata=_build_save_log_metadata(),
        )
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def get_recommended_setting_keywords(product_type, chip, ram_gb=None, ssd_gb=None):
    normalized_product_type = _safe_text(product_type)
    normalized_chip = _safe_text(chip)
    if normalized_chip is not None:
        normalized_chip = normalized_chip.upper()
    return build_recommended_keywords_for_spec(
        normalized_product_type,
        normalized_chip,
        ram_gb=_safe_int(ram_gb),
        ssd_gb=_safe_int(ssd_gb),
    )


def _poll_target_row_to_dict(row):
    fair_price_krw = _safe_int(row.get("fair_price_krw"))
    alert_drop_rate_percent = _safe_float(row.get("alert_drop_rate_percent"))
    target_buy_price_krw = _safe_int(row.get("target_buy_price_krw"))
    if target_buy_price_krw is None:
        target_buy_price_krw = compute_target_buy_price_krw(fair_price_krw, alert_drop_rate_percent)

    return {
        "id": _safe_int(row.get("id")),
        "user_id": _safe_text(row.get("user_id")),
        "product_type": _safe_text(row.get("product_type")),
        "chip": _safe_text(row.get("chip")),
        "screen_inch": _safe_int(row.get("screen_inch")),
        "ram_gb": _safe_int(row.get("ram_gb")),
        "ssd_gb": _safe_int(row.get("ssd_gb")),
        "search_keyword": _normalize_optional_search_keyword(row.get("search_keyword")),
        "enabled": _safe_bool(row.get("enabled"), default=True),
        "force_poll": _safe_bool(row.get("force_poll"), default=False),
        "poll_interval_seconds": _safe_int(row.get("poll_interval_seconds")) or DEFAULT_POLL_INTERVAL_SECONDS,
        "priority": normalize_watch_priority(row.get("priority")),
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "target_buy_price_krw": target_buy_price_krw,
        "alert_price_direction": normalize_alert_price_direction(row.get("alert_price_direction")),
        "min_price_krw": _safe_int(row.get("min_price_krw")),
        "max_price_krw": _safe_int(row.get("max_price_krw")),
        "last_polled_at": row.get("last_polled_at"),
        "last_poll_requested_at": row.get("last_poll_requested_at"),
        "saved_at": row.get("saved_at") or row.get("last_poll_requested_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def get_due_user_fair_price_polling_targets(user_id=None):
    user_scope_exists_clause = None
    filters = [
        "enabled = TRUE",
        "COALESCE(TRIM(search_keyword), '') <> ''",
        "last_poll_requested_at IS NOT NULL",
        """
        (
            force_poll = TRUE
            OR
            last_polled_at IS NULL
            OR TIMESTAMPDIFF(
                SECOND,
                last_polled_at,
                CURRENT_TIMESTAMP
            ) >= %s
        )
        """,
    ]
    params = [MIN_POLLING_INTERVAL_SECONDS]
    normalized_user_id = _safe_text(user_id)
    if normalized_user_id:
        filters.append("user_id = %s")
        params.append(normalized_user_id)

    where_clause = " AND ".join(filters)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        has_users_user_id = _column_exists(cursor, "users", "user_id")
        if not has_users_user_id:
            logger.warning(
                "[polling_targets] users.user_id column missing; skip due targets to prevent unintended polling"
            )
            return []

        has_app_notification_enabled = _column_exists(cursor, "users", "app_notification_enabled")
        if has_app_notification_enabled:
            user_scope_exists_clause = (
                "EXISTS ("
                "SELECT 1 FROM users u "
                "WHERE u.user_id = user_fair_prices.user_id "
                "AND u.app_notification_enabled = TRUE"
                ")"
            )
        else:
            user_scope_exists_clause = (
                "EXISTS ("
                "SELECT 1 FROM users u "
                "WHERE u.user_id = user_fair_prices.user_id"
                ")"
            )

        filters.append(user_scope_exists_clause)
        where_clause = " AND ".join(filters)

        try:
            cursor.execute(
                f"""
                SELECT
                    id,
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    search_keyword,
                    enabled,
                    force_poll,
                    poll_interval_seconds,
                    priority,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    target_buy_price_krw,
                    alert_price_direction,
                    min_price_krw,
                    max_price_krw,
                    last_polled_at,
                    last_poll_requested_at,
                    saved_at,
                    created_at,
                    updated_at
                FROM user_fair_prices
                WHERE {where_clause}
                ORDER BY id ASC
                """,
                tuple(params),
            )
            rows = cursor.fetchall() or []
        except Exception as exc:
            lowered_exc = str(exc).lower()
            if "unknown column" not in lowered_exc:
                raise
            handled_unknown_column = False
            if "min_price_krw" in lowered_exc or "max_price_krw" in lowered_exc:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        user_id,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        search_keyword,
                        enabled,
                        force_poll,
                        poll_interval_seconds,
                        fair_price_krw,
                        alert_drop_rate_percent,
                        target_buy_price_krw,
                        alert_price_direction,
                        last_polled_at,
                        last_poll_requested_at,
                        created_at,
                        updated_at
                    FROM user_fair_prices
                    WHERE {where_clause}
                    ORDER BY id ASC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall() or []
                for row in rows:
                    row["min_price_krw"] = None
                    row["max_price_krw"] = None
                    row["saved_at"] = row.get("saved_at") or row.get("last_poll_requested_at")
                    row["priority"] = DEFAULT_WATCH_PRIORITY
                handled_unknown_column = True
            elif "saved_at" in lowered_exc:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        user_id,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        search_keyword,
                        enabled,
                        force_poll,
                        poll_interval_seconds,
                        fair_price_krw,
                        alert_drop_rate_percent,
                        target_buy_price_krw,
                        alert_price_direction,
                        min_price_krw,
                        max_price_krw,
                        last_polled_at,
                        last_poll_requested_at,
                        created_at,
                        updated_at
                    FROM user_fair_prices
                    WHERE {where_clause}
                    ORDER BY id ASC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall() or []
                for row in rows:
                    row["saved_at"] = row.get("last_poll_requested_at")
                    row["priority"] = DEFAULT_WATCH_PRIORITY
                handled_unknown_column = True
            elif "priority" in lowered_exc:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        user_id,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        search_keyword,
                        enabled,
                        force_poll,
                        poll_interval_seconds,
                        fair_price_krw,
                        alert_drop_rate_percent,
                        target_buy_price_krw,
                        alert_price_direction,
                        min_price_krw,
                        max_price_krw,
                        last_polled_at,
                        last_poll_requested_at,
                        saved_at,
                        created_at,
                        updated_at
                    FROM user_fair_prices
                    WHERE {where_clause}
                    ORDER BY id ASC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall() or []
                for row in rows:
                    row["priority"] = DEFAULT_WATCH_PRIORITY
                handled_unknown_column = True
            elif "alert_price_direction" in lowered_exc:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        user_id,
                        product_type,
                        chip,
                        screen_inch,
                        ram_gb,
                        ssd_gb,
                        search_keyword,
                        enabled,
                        force_poll,
                        poll_interval_seconds,
                        fair_price_krw,
                        alert_drop_rate_percent,
                        target_buy_price_krw,
                        last_polled_at,
                        last_poll_requested_at,
                        created_at,
                        updated_at
                    FROM user_fair_prices
                    WHERE {where_clause}
                    ORDER BY id ASC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall() or []
                for row in rows:
                    row["alert_price_direction"] = DEFAULT_ALERT_PRICE_DIRECTION
                    row["min_price_krw"] = None
                    row["max_price_krw"] = None
                    row["saved_at"] = row.get("saved_at") or row.get("last_poll_requested_at")
                    row["priority"] = DEFAULT_WATCH_PRIORITY
                handled_unknown_column = True
            if not handled_unknown_column:
                logger.warning(
                    "[polling_targets] required polling columns missing (%s); skip polling targets",
                    lowered_exc,
                )
                rows = []

        evaluated_at = _resolve_db_current_timestamp(cursor) or datetime.now()
        due_rows = []
        for row in rows:
            target = _poll_target_row_to_dict(row)
            watch_rule_id = target.get("id")
            priority = normalize_watch_priority(target.get("priority"))
            calculated_interval_seconds = polling_interval_for_priority(priority)
            target["priority"] = priority
            target["calculated_polling_interval_seconds"] = calculated_interval_seconds

            force_poll = bool(target.get("force_poll"))
            last_polled_at = _coerce_datetime(target.get("last_polled_at"))
            if force_poll or last_polled_at is None:
                print(
                    f"[polling_priority] watch_rule_id={watch_rule_id} "
                    f"priority={priority} "
                    f"calculated_polling_interval_seconds={calculated_interval_seconds} "
                    "due=true"
                )
                logger.info(
                    "[polling_priority] watch_rule_id=%s priority=%s calculated_polling_interval_seconds=%s due=true",
                    watch_rule_id,
                    priority,
                    calculated_interval_seconds,
                )
                due_rows.append(target)
                continue

            elapsed_seconds = int((evaluated_at - last_polled_at).total_seconds())
            if elapsed_seconds < 0:
                print(
                    f"[polling_priority] watch_rule_id={watch_rule_id} "
                    f"priority={priority} "
                    f"calculated_polling_interval_seconds={calculated_interval_seconds} "
                    f"elapsed_seconds={elapsed_seconds} due=true skew_detected=true"
                )
                logger.warning(
                    "[polling_priority] watch_rule_id=%s priority=%s calculated_polling_interval_seconds=%s "
                    "elapsed_seconds=%s due=true skew_detected=true",
                    watch_rule_id,
                    priority,
                    calculated_interval_seconds,
                    elapsed_seconds,
                )
                due_rows.append(target)
                continue

            is_due = elapsed_seconds >= calculated_interval_seconds
            print(
                f"[polling_priority] watch_rule_id={watch_rule_id} "
                f"priority={priority} "
                f"calculated_polling_interval_seconds={calculated_interval_seconds} "
                f"elapsed_seconds={elapsed_seconds} due={'true' if is_due else 'false'}"
            )
            logger.info(
                "[polling_priority] watch_rule_id=%s priority=%s calculated_polling_interval_seconds=%s elapsed_seconds=%s due=%s",
                watch_rule_id,
                priority,
                calculated_interval_seconds,
                elapsed_seconds,
                str(is_due).lower(),
            )
            if is_due:
                due_rows.append(target)

        return due_rows
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_user_fair_price_polled(setting_id):
    normalized_setting_id = _safe_int(setting_id)
    if normalized_setting_id is None or normalized_setting_id <= 0:
        raise ValueError("invalid_setting_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE user_fair_prices
                SET
                    last_polled_at = CURRENT_TIMESTAMP,
                    force_poll = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_setting_id,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                UPDATE user_fair_prices
                SET
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_setting_id,),
            )
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def refresh_user_fair_price_saved_at_for_active_rules(user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        return {"ok": False, "reason": "invalid_user_id"}

    normalized_user_id = user_id.strip()
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE user_fair_prices
            SET
                saved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
              AND enabled = TRUE
            """,
            (normalized_user_id,),
        )
        refreshed_rule_count = cursor.rowcount
        connection.commit()
        return {
            "ok": True,
            "user_id": normalized_user_id,
            "refreshed_rule_count": refreshed_rule_count,
            "message": "활성 저장 조건 saved_at 갱신 완료",
        }
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" in lowered_exc and "saved_at" in lowered_exc:
            return {"ok": False, "reason": "missing_saved_at_column"}
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def refresh_user_fair_price_saved_at_for_single_rule(user_id, rule_id):
    if not isinstance(user_id, str) or not user_id.strip():
        return {"ok": False, "reason": "invalid_user_id"}

    normalized_user_id = user_id.strip()
    try:
        normalized_rule_id = _normalize_rule_id(rule_id)
    except ValueError:
        return {"ok": False, "reason": "invalid_rule_id"}

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE user_fair_prices
            SET
                saved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
              AND id = %s
              AND enabled = TRUE
            """,
            (normalized_user_id, normalized_rule_id),
        )
        affected_rows = cursor.rowcount
        connection.commit()
        if affected_rows <= 0:
            return {"ok": False, "reason": "active_rule_not_found"}
        return {
            "ok": True,
            "user_id": normalized_user_id,
            "rule_id": normalized_rule_id,
            "message": "저장 조건 saved_at 갱신 완료",
        }
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" in lowered_exc and "saved_at" in lowered_exc:
            return {"ok": False, "reason": "missing_saved_at_column"}
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
