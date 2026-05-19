import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_watch_rules import (  # noqa: E402
    compute_alert_drop_rate_percent,
    get_due_watch_rules,
    upsert_user_watch_rule,
)


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
        self.committed = False

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def is_connected(self):
        return True

    def close(self):
        return None


class UserWatchRulesTest(unittest.TestCase):
    def test_compute_alert_drop_rate_percent(self):
        self.assertEqual(compute_alert_drop_rate_percent(650000, 800000), 18.75)

    def test_compute_alert_drop_rate_percent_without_fair_price(self):
        self.assertIsNone(compute_alert_drop_rate_percent(650000, None))

    def test_upsert_uses_on_duplicate_key_update(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            response = upsert_user_watch_rule(
                user_id="boongtol",
                product_type="MacBook Air",
                chip="M1",
                screen_inch=13,
                ram_gb=8,
                ssd_gb=256,
                search_keyword="m1맥북에어",
                enabled=True,
                poll_interval_seconds=60,
                target_price_krw=650000,
                fair_price_krw=800000,
            )

        self.assertTrue(response.get("ok"))
        self.assertEqual(len(fake_cursor.executed), 1)
        executed_query = fake_cursor.executed[0][0]
        self.assertIn("ON DUPLICATE KEY UPDATE", executed_query)

    def test_due_query_excludes_disabled_rules(self):
        fake_cursor = _FakeCursor(
            rows=[
                {
                    "id": 1,
                    "user_id": "boongtol",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                    "search_keyword": "m1맥북에어",
                    "enabled": True,
                    "poll_interval_seconds": 60,
                    "target_price_krw": 650000,
                    "fair_price_krw": 800000,
                    "alert_drop_rate_percent": 18.75,
                    "last_polled_at": None,
                    "created_at": None,
                    "updated_at": None,
                }
            ]
        )
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            rules = get_due_watch_rules()

        self.assertEqual(len(rules), 1)
        self.assertTrue(rules[0]["enabled"])
        executed_query = fake_cursor.executed[0][0]
        self.assertIn("enabled = TRUE", executed_query)

    def test_upsert_builds_default_search_keyword_when_empty(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            response = upsert_user_watch_rule(
                user_id="boongtol",
                product_type="MacBook Air",
                chip="M1",
                screen_inch=13,
                ram_gb=8,
                ssd_gb=256,
                search_keyword="",
                enabled=True,
                poll_interval_seconds=60,
                target_price_krw=650000,
                fair_price_krw=800000,
            )

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("search_keyword"), "m1 맥북에어")

    def test_due_query_excludes_empty_search_keyword(self):
        fake_cursor = _FakeCursor(rows=[])
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_watch_rules.get_connection", return_value=fake_connection):
            get_due_watch_rules()

        executed_query = fake_cursor.executed[0][0]
        self.assertIn("COALESCE(TRIM(search_keyword), '') <> ''", executed_query)


if __name__ == "__main__":
    unittest.main()
