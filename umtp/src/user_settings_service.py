from decimal import Decimal

from src.db import get_connection
from src.macbook_air_units import PRODUCT_TYPE, generate_macbook_air_units, is_valid_macbook_air_unit


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


def register_user(user_id, device_id=None):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id_empty")

    normalized_user_id = user_id.strip()
    normalized_device_id = device_id.strip() if isinstance(device_id, str) and device_id.strip() else None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _create_users_table_if_needed(cursor)
        _ensure_users_device_id_column(cursor)

        if normalized_device_id is not None:
            cursor.execute(
                """
                SELECT id, user_id
                FROM users
                WHERE device_id = %s
                LIMIT 1
                """,
                (normalized_device_id,),
            )
            existing_device_user = cursor.fetchone()
            if existing_device_user is not None:
                cursor.execute(
                    """
                    UPDATE users
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (existing_device_user["id"],),
                )
                connection.commit()
                mapped_user_id = existing_device_user["user_id"]
                return {
                    "ok": True,
                    "user_id": mapped_user_id,
                    "message": "기존 사용자로 로그인",
                }

        cursor.execute(
            """
            SELECT id, user_id, device_id
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (normalized_user_id,),
        )
        existing_user = cursor.fetchone()
        if existing_user is not None:
            existing_user_device_id = existing_user.get("device_id")
            if normalized_device_id is not None and not existing_user_device_id:
                cursor.execute(
                    """
                    UPDATE users
                    SET device_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (normalized_device_id, existing_user["id"]),
                )
            else:
                cursor.execute(
                    """
                    UPDATE users
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (existing_user["id"],),
                )
            connection.commit()
            return {
                "ok": True,
                "user_id": existing_user["user_id"],
                "message": "기존 사용자로 로그인",
            }

        try:
            cursor.execute(
                """
                INSERT INTO users (user_id, device_id)
                VALUES (%s, %s)
                """,
                (normalized_user_id, normalized_device_id),
            )
        except Exception as exc:
            # 동시 등록 등으로 duplicate key가 발생해도 실패로 보지 않고 기존 사용자로 처리
            if "duplicate entry" in str(exc).lower():
                connection.rollback()
                if normalized_device_id is not None:
                    cursor.execute(
                        """
                        SELECT user_id
                        FROM users
                        WHERE device_id = %s
                        LIMIT 1
                        """,
                        (normalized_device_id,),
                    )
                    by_device_user = cursor.fetchone()
                    if by_device_user is not None:
                        mapped_user_id = by_device_user["user_id"]
                        return {
                            "ok": True,
                            "user_id": mapped_user_id,
                            "message": "기존 사용자로 로그인",
                        }
                cursor.execute(
                    """
                    SELECT user_id
                    FROM users
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (normalized_user_id,),
                )
                by_user_id = cursor.fetchone()
                mapped_user_id = by_user_id["user_id"] if by_user_id else normalized_user_id
                return {
                    "ok": True,
                    "user_id": mapped_user_id,
                    "message": "기존 사용자로 로그인",
                }
            raise
        connection.commit()
        return {
            "ok": True,
            "user_id": normalized_user_id,
            "message": "사용자 등록 완료",
        }
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

    connection = None
    cursor = None
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
                    enabled
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    fair_price_krw = VALUES(fair_price_krw),
                    alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
                    enabled = VALUES(enabled),
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
                ),
            )
        except Exception as exc:
            if "unknown column" in str(exc).lower() and "enabled" in str(exc).lower():
                return {"ok": False, "reason": "missing_enabled_column"}
            raise

        connection.commit()
        return {
            "ok": True,
            "message": "사용자 공정가 설정 저장 완료",
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
            },
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
