from src.db import get_connection
from src.macbook_air_units import generate_macbook_air_units


CHIP_SORT_ORDER = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
}


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
