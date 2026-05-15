import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import get_due_user_fair_price_polling_targets  # noqa: E402


class _FakeCursor:
    def __init__(self, *, raise_unknown_column=False):
        self.executed = []
        self.raise_unknown_column = raise_unknown_column

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self.raise_unknown_column and "FROM user_fair_prices" in query:
            raise RuntimeError("Unknown column 'search_keyword' in 'where clause'")

    def fetchall(self):
        return []

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor

    def is_connected(self):
        return True

    def close(self):
        return None


class UserSettingsPollTargetsTest(unittest.TestCase):
    def test_due_targets_require_registered_users_with_app_toggle_when_column_exists(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        def _column_exists(_cursor, table_name, column_name):
            if table_name == "users" and column_name in {"user_id", "app_notification_enabled"}:
                return True
            return False

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service._column_exists", side_effect=_column_exists):
                get_due_user_fair_price_polling_targets()

        executed_query = fake_cursor.executed[0][0]
        self.assertIn("last_poll_requested_at IS NOT NULL", executed_query)
        self.assertIn("EXISTS (SELECT 1 FROM users u", executed_query)
        self.assertIn("u.app_notification_enabled = TRUE", executed_query)

    def test_due_targets_skip_when_users_table_not_ready(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service._column_exists", return_value=False):
                rows = get_due_user_fair_price_polling_targets()

        self.assertEqual(rows, [])
        self.assertEqual(len(fake_cursor.executed), 0)

    def test_due_targets_do_not_generate_fallback_keywords_on_missing_columns(self):
        fake_cursor = _FakeCursor(raise_unknown_column=True)
        fake_connection = _FakeConnection(fake_cursor)

        def _column_exists(_cursor, table_name, column_name):
            if table_name == "users" and column_name in {"user_id", "app_notification_enabled"}:
                return True
            return False

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service._column_exists", side_effect=_column_exists):
                rows = get_due_user_fair_price_polling_targets()

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
