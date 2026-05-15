import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import poll_once  # noqa: E402
from src.user_watch_rules import get_due_watch_rules, mark_watch_rule_polled, upsert_user_watch_rule  # noqa: E402


class _FakeCursor:
    def __init__(self, *, rows=None):
        self.rows = rows or []
        self.executed = []
        self.rowcount = 1

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class WatchRuleImmediatePollingTest(unittest.TestCase):
    def test_enabled_true_upsert_requests_immediate_poll(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            response = upsert_user_watch_rule(
                user_id="boongtol",
                search_keyword="m1맥북에어",
                enabled=True,
                poll_interval_seconds=60,
                target_price_krw=650000,
                fair_price_krw=800000,
            )

        self.assertTrue(response.get("ok"))
        self.assertTrue(response.get("immediate_poll_requested"))
        executed_query = fake_cursor.executed[0][0]
        self.assertIn("force_poll", executed_query)
        self.assertIn("VALUES(enabled) = TRUE THEN TRUE", executed_query)

    def test_enabled_false_upsert_disables_immediate_poll(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            response = upsert_user_watch_rule(
                user_id="boongtol",
                search_keyword="m1맥북에어",
                enabled=False,
                poll_interval_seconds=60,
            )

        self.assertTrue(response.get("ok"))
        self.assertFalse(response.get("immediate_poll_requested"))
        executed_query = fake_cursor.executed[0][0]
        self.assertIn("ELSE FALSE", executed_query)

    def test_force_poll_is_in_due_query(self):
        fake_cursor = _FakeCursor(rows=[])
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            get_due_watch_rules(user_id="boongtol")

        executed_query = fake_cursor.executed[0][0]
        self.assertIn("force_poll = TRUE", executed_query)

    def test_mark_watch_rule_polled_clears_force_poll(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            mark_watch_rule_polled(1)

        executed_query = fake_cursor.executed[0][0]
        self.assertIn("force_poll = FALSE", executed_query)

    def test_cli_search_mode_does_not_consume_force_poll(self):
        with patch(
            "src.joongna_polling_service.get_due_watch_rules",
            return_value=[
                {
                    "id": 1,
                    "user_id": "boongtol",
                    "search_keyword": "m2맥북에어",
                }
            ],
        ):
            with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                with patch("src.joongna_polling_service.search_joongna_products", return_value=[]):
                    with patch("src.joongna_polling_service.mark_watch_rule_polled") as mock_mark_polled:
                        poll_once(user_id="boongtol", search_words=["m2맥북에어"])

        self.assertEqual(mock_mark_polled.call_count, 0)


if __name__ == "__main__":
    unittest.main()
