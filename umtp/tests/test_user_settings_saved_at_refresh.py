import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import (  # noqa: E402
    refresh_user_fair_price_saved_at_for_active_rules,
    refresh_user_fair_price_saved_at_for_single_rule,
)


class _FakeCursor:
    def __init__(self, *, rowcount=0):
        self.executed = []
        self.rowcount = rowcount

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def is_connected(self):
        return True

    def close(self):
        return None


class UserSettingsSavedAtRefreshTest(unittest.TestCase):
    def test_refresh_active_rules_updates_enabled_rows_only(self):
        fake_cursor = _FakeCursor(rowcount=3)
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            result = refresh_user_fair_price_saved_at_for_active_rules("boongtol")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("refreshed_rule_count"), 3)
        executed_query, executed_params = fake_cursor.executed[0]
        self.assertIn("enabled = TRUE", executed_query)
        self.assertIn("WHERE user_id = %s", executed_query)
        self.assertEqual(executed_params, ("boongtol",))

    def test_refresh_single_rule_scopes_user_id_and_rule_id(self):
        fake_cursor = _FakeCursor(rowcount=1)
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            result = refresh_user_fair_price_saved_at_for_single_rule("boongtol", 77)

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("rule_id"), 77)
        executed_query, executed_params = fake_cursor.executed[0]
        self.assertIn("WHERE user_id = %s", executed_query)
        self.assertIn("AND id = %s", executed_query)
        self.assertIn("AND enabled = TRUE", executed_query)
        self.assertEqual(executed_params, ("boongtol", 77))

    def test_refresh_single_rule_returns_not_found_when_no_active_row(self):
        fake_cursor = _FakeCursor(rowcount=0)
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            result = refresh_user_fair_price_saved_at_for_single_rule("boongtol", 77)

        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("reason"), "active_rule_not_found")

    def test_refresh_single_rule_rejects_invalid_rule_id(self):
        result = refresh_user_fair_price_saved_at_for_single_rule("boongtol", "abc")

        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("reason"), "invalid_rule_id")


if __name__ == "__main__":
    unittest.main()
