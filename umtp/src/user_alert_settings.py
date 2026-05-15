import os

from dotenv import load_dotenv

try:
    from src.db import get_connection
except ModuleNotFoundError:
    from db import get_connection


def _normalize_user_id(user_id):
    if not isinstance(user_id, str):
        return None
    normalized = user_id.strip()
    return normalized or None


def _table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    if not row:
        return False
    return int(row[0]) > 0 if isinstance(row, (tuple, list)) else int(next(iter(row.values()))) > 0


def _column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    row = cursor.fetchone()
    if not row:
        return False
    return int(row[0]) > 0 if isinstance(row, (tuple, list)) else int(next(iter(row.values()))) > 0


def _safe_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "y", "yes"}:
            return True
        if normalized in {"false", "0", "n", "no"}:
            return False
    return bool(value)


def _safe_text(value):
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _resolve_enabled_from_users(cursor, user_id):
    if not _table_exists(cursor, "users"):
        return None
    if not _column_exists(cursor, "users", "app_notification_enabled"):
        return None

    cursor.execute(
        """
        SELECT app_notification_enabled
        FROM users
        WHERE user_id = %s
        LIMIT 1
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    value = row[0] if isinstance(row, (tuple, list)) else row.get("app_notification_enabled")
    normalized = _safe_bool(value)
    if normalized is None:
        return None
    return {
        "enabled": normalized,
        "source": "users.app_notification_enabled",
    }


def _resolve_enabled_from_user_fair_prices(cursor, user_id):
    if not _table_exists(cursor, "user_fair_prices"):
        return None

    has_enabled_column = _column_exists(cursor, "user_fair_prices", "enabled")
    if has_enabled_column:
        cursor.execute(
            """
            SELECT 1
            FROM user_fair_prices
            WHERE user_id = %s
              AND enabled = TRUE
            LIMIT 1
            """,
            (user_id,),
        )
        enabled_row = cursor.fetchone()
        return {
            "enabled": enabled_row is not None,
            "source": "user_fair_prices.enabled",
        }

    cursor.execute(
        """
        SELECT 1
        FROM user_fair_prices
        WHERE user_id = %s
        LIMIT 1
        """,
        (user_id,),
    )
    legacy_row = cursor.fetchone()
    return {
        "enabled": legacy_row is not None,
        "source": "user_fair_prices.legacy",
    }


def _resolve_enabled_from_user_watch_rules(cursor, user_id):
    if not _table_exists(cursor, "user_watch_rules"):
        return None

    has_enabled_column = _column_exists(cursor, "user_watch_rules", "enabled")
    if has_enabled_column:
        cursor.execute(
            """
            SELECT 1
            FROM user_watch_rules
            WHERE user_id = %s
              AND enabled = TRUE
            LIMIT 1
            """,
            (user_id,),
        )
        enabled_row = cursor.fetchone()
        return {
            "enabled": enabled_row is not None,
            "source": "user_watch_rules.enabled",
        }

    cursor.execute(
        """
        SELECT 1
        FROM user_watch_rules
        WHERE user_id = %s
        LIMIT 1
        """,
        (user_id,),
    )
    legacy_row = cursor.fetchone()
    return {
        "enabled": legacy_row is not None,
        "source": "user_watch_rules.legacy",
    }


def is_user_alert_enabled(user_id):
    resolved_user_id = _normalize_user_id(user_id)
    if resolved_user_id is None:
        return False

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        for resolver in (
            _resolve_enabled_from_users,
            _resolve_enabled_from_user_fair_prices,
            _resolve_enabled_from_user_watch_rules,
        ):
            resolved = resolver(cursor, resolved_user_id)
            if resolved is None:
                continue
            return bool(resolved.get("enabled"))

        return False
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def resolve_user_telegram_chat_id(user_id):
    resolved_user_id = _normalize_user_id(user_id)
    if resolved_user_id is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        if not _table_exists(cursor, "users"):
            return None
        if not _column_exists(cursor, "users", "telegram_chat_id"):
            return None

        cursor.execute(
            """
            SELECT telegram_chat_id
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (resolved_user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        raw_value = row[0] if isinstance(row, (tuple, list)) else row.get("telegram_chat_id")
        return _safe_text(raw_value)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def is_global_telegram_fallback_enabled():
    load_dotenv()
    value = (os.getenv("UMTP_ALLOW_GLOBAL_TELEGRAM_FALLBACK") or "").strip().lower()
    return value in {"1", "true", "y", "yes"}


def resolve_user_alert_delivery_policy(user_id):
    resolved_user_id = _normalize_user_id(user_id)
    if resolved_user_id is None:
        return {
            "enabled": False,
            "enabled_source": "invalid_user_id",
            "telegram_chat_id": None,
            "telegram_chat_source": None,
            "allow_global_fallback": False,
        }

    enabled = is_user_alert_enabled(resolved_user_id)
    chat_id = resolve_user_telegram_chat_id(resolved_user_id)

    if chat_id:
        return {
            "enabled": enabled,
            "enabled_source": "resolved",
            "telegram_chat_id": chat_id,
            "telegram_chat_source": "users.telegram_chat_id",
            "allow_global_fallback": False,
        }

    fallback_enabled = is_global_telegram_fallback_enabled()
    return {
        "enabled": enabled,
        "enabled_source": "resolved",
        "telegram_chat_id": None,
        "telegram_chat_source": None,
        "allow_global_fallback": fallback_enabled,
    }
