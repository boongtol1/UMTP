import logging
from decimal import Decimal

from src.db import get_connection
from src.macbook_air_units import PRODUCT_TYPE, generate_macbook_air_units, is_valid_macbook_air_unit
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
DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT = 20.0
DEFAULT_POLL_INTERVAL_SECONDS = 60
logger = logging.getLogger("umtp.user_settings")


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
    units = generate_macbook_air_units()
    return sorted(
        units,
        key=lambda unit: (
            CHIP_SORT_ORDER.get(unit.get("chip"), 999),
            unit.get("screen_inch"),
            unit.get("ram_gb"),
            unit.get("ssd_gb"),
        ),
    )


def _fetch_system_defaults_map(cursor):
    cursor.execute(
        """
        SELECT product_type, chip, screen_inch, ram_gb, ssd_gb, fair_price_krw
        FROM mac_fair_prices
        WHERE product_type = %s
        """,
        (PRODUCT_TYPE,),
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
    try:
        cursor.execute(
            """
            SELECT product_type, chip, screen_inch, ram_gb, ssd_gb,
                   fair_price_krw, alert_drop_rate_percent, enabled,
                   search_keyword, force_poll, poll_interval_seconds,
                   last_polled_at, last_poll_requested_at
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
            """,
            (user_id, PRODUCT_TYPE),
        )
        rows = cursor.fetchall() or []
    except Exception as exc:
        if "unknown column" not in str(exc).lower():
            raise
        try:
            cursor.execute(
                """
                SELECT product_type, chip, screen_inch, ram_gb, ssd_gb,
                       fair_price_krw, alert_drop_rate_percent, enabled
                FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type = %s
                """,
                (user_id, PRODUCT_TYPE),
            )
            rows = cursor.fetchall() or []
        except Exception as second_exc:
            if "unknown column" not in str(second_exc).lower() or "enabled" not in str(second_exc).lower():
                raise
            cursor.execute(
                """
                SELECT product_type, chip, screen_inch, ram_gb, ssd_gb,
                       fair_price_krw, alert_drop_rate_percent
                FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type = %s
                """,
                (user_id, PRODUCT_TYPE),
            )
            rows = cursor.fetchall() or []
        for row in rows:
            row.setdefault("enabled", True)
            row["search_keyword"] = None
            row["force_poll"] = False
            row["poll_interval_seconds"] = DEFAULT_POLL_INTERVAL_SECONDS
            row["last_polled_at"] = None
            row["last_poll_requested_at"] = None

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
            "fair_price_krw": _safe_int(row.get("fair_price_krw")),
            "alert_drop_rate_percent": _safe_float(row.get("alert_drop_rate_percent")),
            "enabled": _safe_bool(row.get("enabled"), default=True),
            "search_keyword": _normalize_optional_search_keyword(row.get("search_keyword")),
            "force_poll": _safe_bool(row.get("force_poll"), default=False),
            "poll_interval_seconds": _safe_int(row.get("poll_interval_seconds")) or DEFAULT_POLL_INTERVAL_SECONDS,
            "last_polled_at": row.get("last_polled_at"),
            "last_poll_requested_at": row.get("last_poll_requested_at"),
        }
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

        has_user_override = user_item is not None
        user_fair_price_krw = user_item.get("fair_price_krw") if has_user_override else None
        user_alert_drop_rate_percent = (
            user_item.get("alert_drop_rate_percent") if has_user_override else None
        )
        enabled = user_item.get("enabled", True) if has_user_override else False
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
        last_polled_at = user_item.get("last_polled_at") if has_user_override else None
        last_poll_requested_at = user_item.get("last_poll_requested_at") if has_user_override else None

        if has_user_override:
            effective_fair_price_krw = user_fair_price_krw
            effective_alert_drop_rate_percent = user_alert_drop_rate_percent
        else:
            effective_fair_price_krw = system_fair_price_krw
            effective_alert_drop_rate_percent = system_alert_drop_rate_percent

        items.append(
            {
                "product_type": unit["product_type"],
                "chip": unit["chip"],
                "screen_inch": unit["screen_inch"],
                "ram_gb": unit["ram_gb"],
                "ssd_gb": unit["ssd_gb"],
                "system_fair_price_krw": system_fair_price_krw,
                "system_alert_drop_rate_percent": system_alert_drop_rate_percent,
                "user_fair_price_krw": user_fair_price_krw,
                "user_alert_drop_rate_percent": user_alert_drop_rate_percent,
                "enabled": bool(enabled),
                "effective_fair_price_krw": effective_fair_price_krw,
                "effective_alert_drop_rate_percent": effective_alert_drop_rate_percent,
                "custom_search_keyword": custom_search_keyword,
                "recommended_search_keyword": recommended_search_keyword,
                "effective_search_keyword": effective_search_keyword,
                "poll_interval_seconds": poll_interval_seconds,
                "force_poll": bool(force_poll),
                "last_polled_at": last_polled_at,
                "last_poll_requested_at": last_poll_requested_at,
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
    search_keyword=None,
    poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
):
    if not isinstance(user_id, str) or not user_id.strip():
        return {"ok": False, "reason": "invalid_user_id"}

    normalized_user_id = user_id.strip()
    normalized_product_type = product_type.strip() if isinstance(product_type, str) else ""
    normalized_chip = chip.strip().upper() if isinstance(chip, str) else ""

    if normalized_product_type != PRODUCT_TYPE:
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

    if normalized_alert_drop_rate_percent < 0 or normalized_alert_drop_rate_percent > 100:
        return {"ok": False, "reason": "invalid_alert_drop_rate_percent"}

    if not isinstance(enabled, bool):
        return {"ok": False, "reason": "invalid_enabled"}

    if not is_valid_macbook_air_unit(
        normalized_chip, normalized_screen_inch, normalized_ram_gb, normalized_ssd_gb
    ):
        return {"ok": False, "reason": "invalid_macbook_air_unit"}

    try:
        normalized_poll_interval_seconds = _normalize_poll_interval_seconds(poll_interval_seconds)
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}

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

    connection = None
    cursor = None
    immediate_poll_requested = bool(enabled)
    try:
        connection = get_connection()
        cursor = connection.cursor()
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
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            if "enabled" in str(exc).lower():
                return {"ok": False, "reason": "missing_enabled_column"}
            if (
                "search_keyword" in str(exc).lower()
                or "poll_interval_seconds" in str(exc).lower()
                or "force_poll" in str(exc).lower()
            ):
                return {"ok": False, "reason": "missing_polling_columns"}
            raise

        connection.commit()
        return {
            "ok": True,
            "message": "사용자 공정가 설정 저장 완료",
            "immediate_poll_requested": immediate_poll_requested,
            "item": {
                "user_id": normalized_user_id,
                "product_type": normalized_product_type,
                "chip": normalized_chip,
                "screen_inch": normalized_screen_inch,
                "ram_gb": normalized_ram_gb,
                "ssd_gb": normalized_ssd_gb,
                "fair_price_krw": normalized_fair_price_krw,
                "alert_drop_rate_percent": normalized_alert_drop_rate_percent,
                "enabled": enabled,
                "custom_search_keyword": resolved_search_keyword,
                "recommended_search_keyword": _build_recommended_search_keyword(
                    normalized_product_type,
                    normalized_chip,
                    screen_inch=normalized_screen_inch,
                    ram_gb=normalized_ram_gb,
                    ssd_gb=normalized_ssd_gb,
                ),
                "poll_interval_seconds": normalized_poll_interval_seconds,
            },
        }
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
        "fair_price_krw": _safe_int(row.get("fair_price_krw")),
        "alert_drop_rate_percent": _safe_float(row.get("alert_drop_rate_percent")),
        "last_polled_at": row.get("last_polled_at"),
        "last_poll_requested_at": row.get("last_poll_requested_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def get_due_user_fair_price_polling_targets(user_id=None):
    filters = [
        "enabled = TRUE",
        "COALESCE(TRIM(search_keyword), '') <> ''",
        """
        (
            force_poll = TRUE
            OR
            last_polled_at IS NULL
            OR TIMESTAMPDIFF(
                SECOND,
                last_polled_at,
                CURRENT_TIMESTAMP
            ) >= GREATEST(COALESCE(poll_interval_seconds, %s), 1)
        )
        """,
    ]
    params = [DEFAULT_POLL_INTERVAL_SECONDS]
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
                    fair_price_krw,
                    alert_drop_rate_percent,
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
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    enabled,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    created_at,
                    updated_at
                FROM user_fair_prices
                WHERE enabled = TRUE
                """
                + (" AND user_id = %s" if normalized_user_id else "")
                + """
                ORDER BY id ASC
                """,
                ((normalized_user_id,) if normalized_user_id else ()),
            )
            legacy_rows = cursor.fetchall() or []
            rows = []
            for row in legacy_rows:
                try:
                    row["search_keyword"] = _resolve_setting_search_keyword(
                        explicit_search_keyword=None,
                        product_type=row.get("product_type"),
                        chip=row.get("chip"),
                        screen_inch=row.get("screen_inch"),
                        ram_gb=row.get("ram_gb"),
                        ssd_gb=row.get("ssd_gb"),
                    )
                except ValueError:
                    row["search_keyword"] = None
                row["force_poll"] = False
                row["poll_interval_seconds"] = DEFAULT_POLL_INTERVAL_SECONDS
                row["last_polled_at"] = None
                row["last_poll_requested_at"] = None
                if row["search_keyword"] is not None:
                    rows.append(row)
        return [_poll_target_row_to_dict(row) for row in rows]
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
