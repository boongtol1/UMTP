import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import (  # noqa: E402
    bulk_set_user_watch_rules_enabled,
    bulk_update_user_fair_price_drop_rate,
    reset_user_fair_prices_to_system_market_prices,
)


class _BulkFakeCursor:
    def __init__(self, *, watch_rowcount=0, fair_rowcount=0):
        self.watch_rowcount = watch_rowcount
        self.fair_rowcount = fair_rowcount
        self.executed = []
        self.rowcount = 0
        self._last_query = ""

    def execute(self, query, params=None):
        normalized_query = " ".join((query or "").lower().split())
        self.executed.append((query, params))
        self._last_query = normalized_query
        if normalized_query.startswith("update user_watch_rules"):
            self.rowcount = self.watch_rowcount
        elif normalized_query.startswith("update user_fair_prices"):
            self.rowcount = self.fair_rowcount
        elif normalized_query.startswith("insert into user_fair_prices"):
            self.rowcount = 1
        else:
            self.rowcount = 0

    def fetchone(self):
        if self._last_query.startswith("select current_timestamp"):
            return (datetime(2026, 5, 21, 15, 0, 0),)
        return None

    def fetchall(self):
        return []

    def close(self):
        return None


class _BulkFakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def is_connected(self):
        return True

    def close(self):
        return None


class UserSettingsBulkControlsTest(unittest.TestCase):
    def _find_query(self, cursor, keyword):
        lowered_keyword = keyword.lower()
        for query, params in cursor.executed:
            normalized_query = " ".join((query or "").lower().split())
            if lowered_keyword in normalized_query:
                return query, params
        self.fail(f"query not found: {keyword}")

    def test_bulk_enabled_updates_all_rows_for_true_and_false(self):
        for enabled_value in (True, False):
            fake_cursor = _BulkFakeCursor(watch_rowcount=3, fair_rowcount=3)
            fake_connection = _BulkFakeConnection(fake_cursor)
            with patch("src.user_settings_service.get_connection", return_value=fake_connection):
                result = bulk_set_user_watch_rules_enabled("boongtol", enabled_value)

            self.assertTrue(result.get("ok"))
            self.assertEqual(result.get("enabled"), enabled_value)
            self.assertEqual(result.get("affected_count"), 3)
            watch_query, watch_params = self._find_query(fake_cursor, "update user_watch_rules")
            fair_query, fair_params = self._find_query(fake_cursor, "update user_fair_prices")
            self.assertIn("where user_id = %s", watch_query.lower())
            self.assertIn("where user_id = %s", fair_query.lower())
            self.assertIn("boongtol", watch_params)
            self.assertIn("boongtol", fair_params)

    def test_bulk_enabled_applies_product_type_filter(self):
        fake_cursor = _BulkFakeCursor(watch_rowcount=2, fair_rowcount=2)
        fake_connection = _BulkFakeConnection(fake_cursor)
        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            result = bulk_set_user_watch_rules_enabled("boongtol", True, product_type="MacBook Air")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("affected_count"), 2)
        watch_query, watch_params = self._find_query(fake_cursor, "update user_watch_rules")
        fair_query, fair_params = self._find_query(fake_cursor, "update user_fair_prices")
        self.assertIn("and product_type = %s", watch_query.lower())
        self.assertIn("and product_type = %s", fair_query.lower())
        self.assertIn("MacBook Air", watch_params)
        self.assertIn("MacBook Air", fair_params)

    def test_bulk_drop_rate_updates_fair_prices_and_watch_rules(self):
        fake_cursor = _BulkFakeCursor(watch_rowcount=4, fair_rowcount=4)
        fake_connection = _BulkFakeConnection(fake_cursor)
        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            result = bulk_update_user_fair_price_drop_rate("boongtol", 20.0)

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("affected_count"), 4)
        fair_query, fair_params = self._find_query(fake_cursor, "update user_fair_prices")
        watch_query, watch_params = self._find_query(fake_cursor, "update user_watch_rules")
        self.assertIn("alert_drop_rate_percent", fair_query.lower())
        self.assertIn("target_price_krw", watch_query.lower())
        self.assertEqual(fair_params[0], 20.0)
        self.assertEqual(watch_params[0], 20.0)

    def test_reset_to_system_market_prices_preserves_existing_user_settings(self):
        unit = {
            "product_type": "MacBook Air",
            "chip": "M4",
            "screen_inch": 13,
            "ram_gb": 16,
            "ssd_gb": 512,
        }
        key = ("MacBook Air", "M4", 13, 16, 512)
        system_map = {key: {"fair_price_krw": 1500000}}
        user_map = {
            key: {
                "fair_price_krw": 1300000,
                "alert_drop_rate_percent": 18.5,
                "alert_price_direction": "ABOVE_OR_EQUAL",
                "min_price_krw": None,
                "max_price_krw": 1700000,
                "enabled": True,
                "condition_change_candidate_notice_enabled": True,
                "search_keyword": "m4 맥북에어",
                "poll_interval_seconds": 45,
                "priority": "FAST",
                "force_poll": True,
                "last_poll_requested_at": datetime(2026, 5, 21, 11, 30, 0),
                "last_polled_at": datetime(2026, 5, 21, 11, 0, 0),
                "saved_at": datetime(2026, 5, 20, 9, 0, 0),
            }
        }
        fake_cursor = _BulkFakeCursor()
        fake_connection = _BulkFakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service._fetch_system_defaults_map", return_value=system_map):
                with patch("src.user_settings_service._fetch_user_overrides_map", return_value=user_map):
                    with patch("src.user_settings_service.get_all_macbook_air_units_sorted", return_value=[unit]):
                        result = reset_user_fair_prices_to_system_market_prices("boongtol")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("inserted_count"), 0)
        self.assertEqual(result.get("updated_count"), 1)
        upsert_query, upsert_params = self._find_query(fake_cursor, "insert into user_fair_prices")
        self.assertIn("on duplicate key update", upsert_query.lower())
        self.assertEqual(upsert_params[6], 1500000)
        self.assertEqual(upsert_params[7], 18.5)
        self.assertEqual(upsert_params[8], "ABOVE_OR_EQUAL")
        self.assertEqual(upsert_params[10], 1700000)
        self.assertTrue(upsert_params[11])
        self.assertTrue(upsert_params[12])
        self.assertEqual(upsert_params[13], "m4 맥북에어")
        self.assertEqual(upsert_params[14], 45)
        self.assertEqual(upsert_params[15], "FAST")

    def test_reset_to_system_market_prices_inserts_new_and_updates_existing(self):
        unit_existing = {
            "product_type": "MacBook Air",
            "chip": "M4",
            "screen_inch": 13,
            "ram_gb": 16,
            "ssd_gb": 512,
        }
        unit_new = {
            "product_type": "MacBook Air",
            "chip": "M4",
            "screen_inch": 13,
            "ram_gb": 24,
            "ssd_gb": 1024,
        }
        key_existing = ("MacBook Air", "M4", 13, 16, 512)
        key_new = ("MacBook Air", "M4", 13, 24, 1024)
        system_map = {
            key_existing: {"fair_price_krw": 1500000},
            key_new: {"fair_price_krw": 1900000},
        }
        user_map = {
            key_existing: {
                "alert_drop_rate_percent": 20.0,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "enabled": True,
                "condition_change_candidate_notice_enabled": False,
                "search_keyword": "m4 맥북에어",
                "poll_interval_seconds": 60,
                "priority": "NORMAL",
                "force_poll": False,
                "last_poll_requested_at": None,
                "last_polled_at": None,
                "saved_at": datetime(2026, 5, 20, 9, 0, 0),
            }
        }
        fake_cursor = _BulkFakeCursor()
        fake_connection = _BulkFakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service._fetch_system_defaults_map", return_value=system_map):
                with patch("src.user_settings_service._fetch_user_overrides_map", return_value=user_map):
                    with patch(
                        "src.user_settings_service.get_all_macbook_air_units_sorted",
                        return_value=[unit_existing, unit_new],
                    ):
                        result = reset_user_fair_prices_to_system_market_prices("boongtol")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("inserted_count"), 1)
        self.assertEqual(result.get("updated_count"), 1)
        self.assertEqual(result.get("affected_count"), 2)


if __name__ == "__main__":
    unittest.main()
