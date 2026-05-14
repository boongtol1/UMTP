from decimal import Decimal

from src.db import get_connection
from src.macbook_air_units import PRODUCT_TYPE, generate_macbook_air_units


CHIP_SORT_ORDER = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
}
DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT = 20.0


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


def _unit_key(product_type, chip, screen_inch, ram_gb, ssd_gb):
    return (product_type, chip, int(screen_inch), int(ram_gb), int(ssd_gb))


def _create_users_table_if_needed(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            nickname VARCHAR(100) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_users_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
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
                   fair_price_krw, alert_drop_rate_percent, enabled
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
            """,
            (user_id, PRODUCT_TYPE),
        )
        rows = cursor.fetchall() or []
    except Exception as exc:
        if "unknown column" not in str(exc).lower() or "enabled" not in str(exc).lower():
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
            row["enabled"] = True

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
                "has_user_override": has_user_override,
            }
        )

    return items


def register_user(user_id, nickname=None):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id_empty")

    normalized_user_id = user_id.strip()
    normalized_nickname = nickname.strip() if isinstance(nickname, str) and nickname.strip() else None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        _create_users_table_if_needed(cursor)
        cursor.execute(
            """
            INSERT INTO users (user_id, nickname)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                nickname = COALESCE(VALUES(nickname), nickname),
                updated_at = CURRENT_TIMESTAMP
            """,
            (normalized_user_id, normalized_nickname),
        )
        connection.commit()
        return {"ok": True, "user_id": normalized_user_id, "message": "사용자 등록 완료"}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
