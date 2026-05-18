from src.db import get_connection


DEFAULT_PLATFORM = "android"


def _safe_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    normalized = str(value).strip()
    return normalized or None


def _table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (table_name,),
    )
    row = cursor.fetchone() or {}
    return int(row.get("table_count", 0)) > 0


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


def _create_user_push_tokens_table_if_needed(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_push_tokens (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            device_id VARCHAR(200) NULL,
            platform VARCHAR(30) NOT NULL DEFAULT 'android',
            fcm_token VARCHAR(512) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_error VARCHAR(255) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_sent_at TIMESTAMP NULL,
            UNIQUE KEY uq_user_push_tokens_fcm_token (fcm_token),
            KEY idx_user_push_tokens_user_active (user_id, is_active),
            KEY idx_user_push_tokens_device (device_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    if not _column_exists(cursor, "user_push_tokens", "device_id"):
        cursor.execute(
            """
            ALTER TABLE user_push_tokens
            ADD COLUMN device_id VARCHAR(200) NULL AFTER user_id
            """
        )

    if not _column_exists(cursor, "user_push_tokens", "platform"):
        cursor.execute(
            """
            ALTER TABLE user_push_tokens
            ADD COLUMN platform VARCHAR(30) NOT NULL DEFAULT 'android' AFTER device_id
            """
        )

    if not _column_exists(cursor, "user_push_tokens", "last_error"):
        cursor.execute(
            """
            ALTER TABLE user_push_tokens
            ADD COLUMN last_error VARCHAR(255) NULL AFTER is_active
            """
        )

    if not _column_exists(cursor, "user_push_tokens", "last_sent_at"):
        cursor.execute(
            """
            ALTER TABLE user_push_tokens
            ADD COLUMN last_sent_at TIMESTAMP NULL AFTER updated_at
            """
        )

    if not _index_exists(cursor, "user_push_tokens", "idx_user_push_tokens_user_active"):
        cursor.execute(
            """
            ALTER TABLE user_push_tokens
            ADD INDEX idx_user_push_tokens_user_active (user_id, is_active)
            """
        )


def upsert_user_push_token(user_id, token, platform=DEFAULT_PLATFORM, device_id=None):
    normalized_user_id = _safe_text(user_id)
    normalized_token = _safe_text(token)
    normalized_platform = (_safe_text(platform) or DEFAULT_PLATFORM).lower()
    normalized_device_id = _safe_text(device_id)

    if normalized_user_id is None:
        return {"ok": False, "reason": "invalid_user_id", "message": "유효하지 않은 user_id입니다."}
    if normalized_token is None:
        return {"ok": False, "reason": "invalid_token", "message": "유효하지 않은 토큰입니다."}

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _create_user_push_tokens_table_if_needed(cursor)

        cursor.execute(
            """
            INSERT INTO user_push_tokens (
                user_id,
                device_id,
                platform,
                fcm_token,
                is_active,
                last_error
            )
            VALUES (%s, %s, %s, %s, TRUE, NULL)
            ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                device_id = COALESCE(VALUES(device_id), user_push_tokens.device_id),
                platform = VALUES(platform),
                is_active = TRUE,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            """,
            (normalized_user_id, normalized_device_id, normalized_platform, normalized_token),
        )
        connection.commit()
        return {
            "ok": True,
            "message": "푸시 토큰 저장 완료",
            "user_id": normalized_user_id,
            "platform": normalized_platform,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def list_active_user_push_tokens(user_id, *, platform=None):
    normalized_user_id = _safe_text(user_id)
    if normalized_user_id is None:
        return []

    normalized_platform = _safe_text(platform)
    if normalized_platform is not None:
        normalized_platform = normalized_platform.lower()

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        if not _table_exists(cursor, "user_push_tokens"):
            return []

        if normalized_platform is None:
            cursor.execute(
                """
                SELECT id, fcm_token
                FROM user_push_tokens
                WHERE user_id = %s
                  AND is_active = TRUE
                ORDER BY updated_at DESC
                """,
                (normalized_user_id,),
            )
        else:
            cursor.execute(
                """
                SELECT id, fcm_token
                FROM user_push_tokens
                WHERE user_id = %s
                  AND platform = %s
                  AND is_active = TRUE
                ORDER BY updated_at DESC
                """,
                (normalized_user_id, normalized_platform),
            )

        rows = cursor.fetchall() or []
        result = []
        for row in rows:
            token_id = row.get("id")
            token = _safe_text(row.get("fcm_token"))
            if token_id is None or token is None:
                continue
            result.append({"id": int(token_id), "token": token})
        return result
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_user_push_token_sent(token_id):
    try:
        normalized_token_id = int(token_id)
    except (TypeError, ValueError):
        return False

    if normalized_token_id <= 0:
        return False

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE user_push_tokens
            SET
                last_sent_at = CURRENT_TIMESTAMP,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (normalized_token_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def deactivate_user_push_token(token_id, error_message=None):
    try:
        normalized_token_id = int(token_id)
    except (TypeError, ValueError):
        return False

    if normalized_token_id <= 0:
        return False

    normalized_error = _safe_text(error_message)
    if normalized_error is not None and len(normalized_error) > 255:
        normalized_error = normalized_error[:255]

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE user_push_tokens
            SET
                is_active = FALSE,
                last_error = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (normalized_error, normalized_token_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
