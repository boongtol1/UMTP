from decimal import Decimal

from src.db import get_connection
from src.search_keyword_utils import (
    build_default_keyword_for_watch_rule,
    build_recommended_keywords_for_spec,
    normalize_search_keyword,
    validate_search_keyword,
)


UNKNOWN_COLUMN_ERRNO = 1054


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


def _is_unknown_column_error(exc):
    if getattr(exc, "errno", None) == UNKNOWN_COLUMN_ERRNO:
        return True
    return "Unknown column" in str(exc)


def _normalize_user_id(user_id):
    if not isinstance(user_id, str):
        raise ValueError("invalid_user_id")
    normalized = user_id.strip()
    if not normalized:
        raise ValueError("invalid_user_id")
    return normalized


def _normalize_required_search_keyword(search_keyword):
    return validate_search_keyword(search_keyword)


def _normalize_optional_search_keyword(search_keyword):
    if search_keyword is None:
        return None
    normalized = normalize_search_keyword(search_keyword)
    if not normalized:
        return None
    return validate_search_keyword(normalized)


def _normalize_optional_int(value, field_name):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field_name}") from exc


def _normalize_poll_interval_seconds(value):
    if value is None:
        return 60
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_poll_interval_seconds") from exc
    if normalized <= 0:
        raise ValueError("invalid_poll_interval_seconds")
    return normalized


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def compute_alert_drop_rate_percent(target_price_krw, fair_price_krw):
    normalized_target_price_krw = _normalize_optional_int(target_price_krw, "target_price_krw")
    normalized_fair_price_krw = _normalize_optional_int(fair_price_krw, "fair_price_krw")
    if normalized_target_price_krw is None or normalized_fair_price_krw is None:
        return None
    if normalized_fair_price_krw <= 0:
        return None
    return round(
        ((normalized_fair_price_krw - normalized_target_price_krw) / normalized_fair_price_krw) * 100,
        2,
    )


def get_recommended_watch_keywords(product_type, chip, ram_gb=None, ssd_gb=None):
    normalized_product_type = _normalize_optional_text(product_type)
    normalized_chip = _normalize_optional_text(chip)
    if normalized_chip is not None:
        normalized_chip = normalized_chip.upper()

    normalized_ram_gb = _normalize_optional_int(ram_gb, "ram_gb")
    normalized_ssd_gb = _normalize_optional_int(ssd_gb, "ssd_gb")

    return build_recommended_keywords_for_spec(
        normalized_product_type,
        normalized_chip,
        ram_gb=normalized_ram_gb,
        ssd_gb=normalized_ssd_gb,
    )


def _resolve_watch_rule_search_keyword(
    *,
    explicit_search_keyword,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb,
):
    normalized_explicit_search_keyword = _normalize_optional_search_keyword(explicit_search_keyword)
    if normalized_explicit_search_keyword is not None:
        return normalized_explicit_search_keyword

    default_keyword = build_default_keyword_for_watch_rule(
        {
            "product_type": product_type,
            "chip": chip,
            "screen_inch": screen_inch,
            "ram_gb": ram_gb,
            "ssd_gb": ssd_gb,
        }
    )
    if default_keyword is None:
        raise ValueError("unable_to_build_search_keyword")

    return _normalize_required_search_keyword(default_keyword)


def _rule_row_to_dict(row):
    return {
        "id": _safe_int(row.get("id")),
        "user_id": row.get("user_id"),
        "product_type": row.get("product_type"),
        "chip": row.get("chip"),
        "screen_inch": _safe_int(row.get("screen_inch")),
        "ram_gb": _safe_int(row.get("ram_gb")),
        "ssd_gb": _safe_int(row.get("ssd_gb")),
        "search_keyword": _normalize_optional_search_keyword(row.get("search_keyword")),
        "enabled": _safe_bool(row.get("enabled"), default=True),
        "force_poll": _safe_bool(row.get("force_poll"), default=False),
        "poll_interval_seconds": _safe_int(row.get("poll_interval_seconds")),
        "target_price_krw": _safe_int(row.get("target_price_krw")),
        "fair_price_krw": _safe_int(row.get("fair_price_krw")),
        "alert_drop_rate_percent": _safe_float(row.get("alert_drop_rate_percent")),
        "last_polled_at": row.get("last_polled_at"),
        "last_poll_requested_at": row.get("last_poll_requested_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _fetch_watch_rules(*, user_id=None, enabled_only=False, due_only=False):
    filters = ["COALESCE(TRIM(search_keyword), '') <> ''"]
    params = []

    if enabled_only:
        filters.append("enabled = TRUE")

    if due_only:
        filters.append(
            """
            (
                force_poll = TRUE
                OR
                last_polled_at IS NULL
                OR TIMESTAMPDIFF(
                    SECOND,
                    last_polled_at,
                    CURRENT_TIMESTAMP
                ) >= GREATEST(COALESCE(poll_interval_seconds, 60), 1)
            )
            """
        )

    if user_id is not None:
        normalized_user_id = _normalize_user_id(user_id)
        filters.append("user_id = %s")
        params.append(normalized_user_id)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
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
                    target_price_krw,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    last_polled_at,
                    last_poll_requested_at,
                    created_at,
                    updated_at
                FROM user_watch_rules
                {where_clause}
                ORDER BY id ASC
                """,
                tuple(params),
            )
        except Exception as exc:
            if not _is_unknown_column_error(exc):
                raise

            legacy_filters = ["COALESCE(TRIM(search_keyword), '') <> ''"]
            if enabled_only:
                legacy_filters.append("enabled = TRUE")
            if due_only:
                legacy_filters.append(
                    """
                    (
                        last_polled_at IS NULL
                        OR TIMESTAMPDIFF(
                            SECOND,
                            last_polled_at,
                            CURRENT_TIMESTAMP
                        ) >= GREATEST(COALESCE(poll_interval_seconds, 60), 1)
                    )
                    """
                )
            if user_id is not None:
                legacy_filters.append("user_id = %s")

            legacy_where_clause = ""
            if legacy_filters:
                legacy_where_clause = "WHERE " + " AND ".join(legacy_filters)

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
                    poll_interval_seconds,
                    target_price_krw,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    last_polled_at,
                    created_at,
                    updated_at
                FROM user_watch_rules
                {legacy_where_clause}
                ORDER BY id ASC
                """,
                tuple(params),
            )
        rows = cursor.fetchall() or []
        return [_rule_row_to_dict(row) for row in rows]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def list_user_watch_rules(user_id):
    return _fetch_watch_rules(user_id=user_id, enabled_only=False, due_only=False)


def get_enabled_watch_rules(user_id=None):
    return _fetch_watch_rules(user_id=user_id, enabled_only=True, due_only=False)


def get_due_watch_rules(user_id=None):
    return _fetch_watch_rules(user_id=user_id, enabled_only=True, due_only=True)


def upsert_user_watch_rule(
    *,
    user_id,
    search_keyword,
    product_type=None,
    chip=None,
    screen_inch=None,
    ram_gb=None,
    ssd_gb=None,
    enabled=True,
    poll_interval_seconds=60,
    target_price_krw=None,
    fair_price_krw=None,
):
    normalized_user_id = _normalize_user_id(user_id)

    if not isinstance(enabled, bool):
        raise ValueError("invalid_enabled")

    normalized_product_type = _normalize_optional_text(product_type)
    normalized_chip = _normalize_optional_text(chip)
    if normalized_chip is not None:
        normalized_chip = normalized_chip.upper()

    normalized_screen_inch = _normalize_optional_int(screen_inch, "screen_inch")
    normalized_ram_gb = _normalize_optional_int(ram_gb, "ram_gb")
    normalized_ssd_gb = _normalize_optional_int(ssd_gb, "ssd_gb")
    normalized_poll_interval_seconds = _normalize_poll_interval_seconds(poll_interval_seconds)
    normalized_target_price_krw = _normalize_optional_int(target_price_krw, "target_price_krw")
    normalized_fair_price_krw = _normalize_optional_int(fair_price_krw, "fair_price_krw")

    normalized_search_keyword = _resolve_watch_rule_search_keyword(
        explicit_search_keyword=search_keyword,
        product_type=normalized_product_type,
        chip=normalized_chip,
        screen_inch=normalized_screen_inch,
        ram_gb=normalized_ram_gb,
        ssd_gb=normalized_ssd_gb,
    )

    alert_drop_rate_percent = compute_alert_drop_rate_percent(
        normalized_target_price_krw,
        normalized_fair_price_krw,
    )
    immediate_poll_requested = bool(enabled)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_watch_rules (
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    search_keyword,
                    enabled,
                    force_poll,
                    last_poll_requested_at,
                    poll_interval_seconds,
                    target_price_krw,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    last_polled_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    IF(%s = TRUE, TRUE, FALSE),
                    IF(%s = TRUE, CURRENT_TIMESTAMP, NULL),
                    %s, %s, %s, %s, NULL
                )
                ON DUPLICATE KEY UPDATE
                    product_type = VALUES(product_type),
                    chip = VALUES(chip),
                    screen_inch = VALUES(screen_inch),
                    ram_gb = VALUES(ram_gb),
                    ssd_gb = VALUES(ssd_gb),
                    enabled = VALUES(enabled),
                    force_poll = CASE
                        WHEN VALUES(enabled) = TRUE THEN TRUE
                        ELSE FALSE
                    END,
                    last_poll_requested_at = CASE
                        WHEN VALUES(enabled) = TRUE THEN CURRENT_TIMESTAMP
                        ELSE last_poll_requested_at
                    END,
                    poll_interval_seconds = VALUES(poll_interval_seconds),
                    target_price_krw = VALUES(target_price_krw),
                    fair_price_krw = VALUES(fair_price_krw),
                    alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    normalized_user_id,
                    normalized_product_type,
                    normalized_chip,
                    normalized_screen_inch,
                    normalized_ram_gb,
                    normalized_ssd_gb,
                    normalized_search_keyword,
                    enabled,
                    enabled,
                    enabled,
                    normalized_poll_interval_seconds,
                    normalized_target_price_krw,
                    normalized_fair_price_krw,
                    alert_drop_rate_percent,
                ),
            )
        except Exception as exc:
            if not _is_unknown_column_error(exc):
                raise
            cursor.execute(
                """
                INSERT INTO user_watch_rules (
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    search_keyword,
                    enabled,
                    poll_interval_seconds,
                    target_price_krw,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    last_polled_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                ON DUPLICATE KEY UPDATE
                    product_type = VALUES(product_type),
                    chip = VALUES(chip),
                    screen_inch = VALUES(screen_inch),
                    ram_gb = VALUES(ram_gb),
                    ssd_gb = VALUES(ssd_gb),
                    enabled = VALUES(enabled),
                    poll_interval_seconds = VALUES(poll_interval_seconds),
                    target_price_krw = VALUES(target_price_krw),
                    fair_price_krw = VALUES(fair_price_krw),
                    alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
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
                    normalized_search_keyword,
                    enabled,
                    normalized_poll_interval_seconds,
                    normalized_target_price_krw,
                    normalized_fair_price_krw,
                    alert_drop_rate_percent,
                ),
            )
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return {
        "ok": True,
        "message": "감시 조건 저장 완료",
        "search_keyword": normalized_search_keyword,
        "immediate_poll_requested": immediate_poll_requested,
        "alert_drop_rate_percent": alert_drop_rate_percent,
    }


def set_watch_rule_enabled(user_id, search_keyword, enabled):
    normalized_user_id = _normalize_user_id(user_id)
    normalized_search_keyword = _normalize_required_search_keyword(search_keyword)
    if not isinstance(enabled, bool):
        raise ValueError("invalid_enabled")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE user_watch_rules
                SET
                    enabled = %s,
                    force_poll = CASE
                        WHEN %s = TRUE THEN TRUE
                        ELSE FALSE
                    END,
                    last_poll_requested_at = CASE
                        WHEN %s = TRUE THEN CURRENT_TIMESTAMP
                        ELSE last_poll_requested_at
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND search_keyword = %s
                """,
                (
                    enabled,
                    enabled,
                    enabled,
                    normalized_user_id,
                    normalized_search_keyword,
                ),
            )
        except Exception as exc:
            if not _is_unknown_column_error(exc):
                raise
            cursor.execute(
                """
                UPDATE user_watch_rules
                SET
                    enabled = %s,
                    last_polled_at = CASE
                        WHEN %s = TRUE THEN NULL
                        ELSE last_polled_at
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND search_keyword = %s
                """,
                (
                    enabled,
                    enabled,
                    normalized_user_id,
                    normalized_search_keyword,
                ),
            )
        affected_rows = cursor.rowcount
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if affected_rows <= 0:
        return {"ok": False, "reason": "watch_rule_not_found"}
    return {"ok": True, "message": "감시 조건 상태 변경 완료"}


def delete_user_watch_rule(user_id, search_keyword):
    normalized_user_id = _normalize_user_id(user_id)
    normalized_search_keyword = _normalize_required_search_keyword(search_keyword)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM user_watch_rules
            WHERE user_id = %s
              AND search_keyword = %s
            """,
            (normalized_user_id, normalized_search_keyword),
        )
        affected_rows = cursor.rowcount
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if affected_rows <= 0:
        return {"ok": False, "reason": "watch_rule_not_found"}
    return {"ok": True, "message": "감시 조건 삭제 완료"}


def mark_watch_rule_polled(rule_id):
    normalized_rule_id = _normalize_optional_int(rule_id, "rule_id")
    if normalized_rule_id is None or normalized_rule_id <= 0:
        raise ValueError("invalid_rule_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE user_watch_rules
                SET
                    last_polled_at = CURRENT_TIMESTAMP,
                    force_poll = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_rule_id,),
            )
        except Exception as exc:
            if not _is_unknown_column_error(exc):
                raise
            cursor.execute(
                """
                UPDATE user_watch_rules
                SET
                    last_polled_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_rule_id,),
            )
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def request_immediate_poll(user_id, search_keyword):
    normalized_user_id = _normalize_user_id(user_id)
    normalized_search_keyword = _normalize_required_search_keyword(search_keyword)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE user_watch_rules
                SET
                    force_poll = TRUE,
                    last_poll_requested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND search_keyword = %s
                  AND enabled = TRUE
                """,
                (normalized_user_id, normalized_search_keyword),
            )
        except Exception as exc:
            if not _is_unknown_column_error(exc):
                raise
            cursor.execute(
                """
                UPDATE user_watch_rules
                SET
                    last_polled_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND search_keyword = %s
                  AND enabled = TRUE
                """,
                (normalized_user_id, normalized_search_keyword),
            )
        affected_rows = cursor.rowcount
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if affected_rows <= 0:
        return {"ok": False, "reason": "watch_rule_not_found_or_disabled"}

    return {
        "ok": True,
        "message": "즉시 검색 요청 완료",
        "immediate_poll_requested": True,
    }
