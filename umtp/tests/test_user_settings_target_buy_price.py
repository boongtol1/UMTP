import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import _poll_target_row_to_dict, upsert_user_fair_price_setting  # noqa: E402


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class UserSettingsTargetBuyPriceTest(unittest.TestCase):
    def test_poll_target_row_includes_target_buy_price(self):
        row = {
            "id": 1,
            "user_id": "boongtol",
            "product_type": "MacBook Air",
            "chip": "M2",
            "screen_inch": 13,
            "ram_gb": 8,
            "ssd_gb": 256,
            "search_keyword": "m2맥북에어",
            "enabled": True,
            "force_poll": False,
            "poll_interval_seconds": 60,
            "fair_price_krw": 1000000,
            "alert_drop_rate_percent": 20.50,
            "target_buy_price_krw": 795000,
            "alert_price_direction": "ABOVE_OR_EQUAL",
            "min_price_krw": None,
            "max_price_krw": 900000,
            "last_polled_at": None,
            "last_poll_requested_at": None,
            "created_at": None,
            "updated_at": None,
        }

        item = _poll_target_row_to_dict(row)
        self.assertEqual(item.get("target_buy_price_krw"), 795000)
        self.assertEqual(item.get("alert_price_direction"), "ABOVE_OR_EQUAL")
        self.assertIsNone(item.get("min_price_krw"))
        self.assertEqual(item.get("max_price_krw"), 900000)

    def test_upsert_query_does_not_write_generated_target_column(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_macbook_air_unit", return_value=True):
                with patch(
                    "src.user_settings_service._resolve_setting_search_keyword",
                    return_value="m2맥북에어",
                ):
                    result = upsert_user_fair_price_setting(
                        user_id="boongtol",
                        product_type="MacBook Air",
                        chip="M2",
                        screen_inch=13,
                        ram_gb=8,
                        ssd_gb=256,
                        fair_price_krw=1000000,
                        alert_drop_rate_percent=20.50,
                        enabled=True,
                        search_keyword="m2맥북에어",
                        poll_interval_seconds=60,
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(len(fake_cursor.executed), 1)
        executed_query = fake_cursor.executed[0][0]
        lowered = " ".join(executed_query.lower().split())
        self.assertIn("insert into user_fair_prices", lowered)
        self.assertIn("fair_price_krw", lowered)
        self.assertIn("alert_drop_rate_percent", lowered)
        self.assertIn("alert_price_direction", lowered)
        self.assertNotIn("target_buy_price_krw", lowered)

    def test_upsert_accepts_negative_drop_rate_and_above_direction(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_macbook_air_unit", return_value=True):
                with patch(
                    "src.user_settings_service._resolve_setting_search_keyword",
                    return_value="m2맥북에어",
                ):
                    result = upsert_user_fair_price_setting(
                        user_id="boongtol",
                        product_type="MacBook Air",
                        chip="M2",
                        screen_inch=13,
                        ram_gb=8,
                        ssd_gb=256,
                        fair_price_krw=1000000,
                        alert_drop_rate_percent=-10.00,
                        enabled=True,
                        alert_price_direction="ABOVE_OR_EQUAL",
                        max_price_krw=1100000,
                        search_keyword="m2맥북에어",
                        poll_interval_seconds=60,
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("item", {}).get("target_buy_price_krw"), 1100000)
        self.assertEqual(result.get("item", {}).get("alert_price_direction"), "ABOVE_OR_EQUAL")
        self.assertIsNone(result.get("item", {}).get("min_price_krw"))
        self.assertEqual(result.get("item", {}).get("max_price_krw"), 1100000)

    def test_upsert_normalizes_bounds_by_direction(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_macbook_air_unit", return_value=True):
                with patch(
                    "src.user_settings_service._resolve_setting_search_keyword",
                    return_value="m2맥북에어",
                ):
                    result = upsert_user_fair_price_setting(
                        user_id="boongtol",
                        product_type="MacBook Air",
                        chip="M2",
                        screen_inch=13,
                        ram_gb=8,
                        ssd_gb=256,
                        fair_price_krw=1000000,
                        alert_drop_rate_percent=20.0,
                        enabled=True,
                        alert_price_direction="BELOW_OR_EQUAL",
                        min_price_krw=300000,
                        max_price_krw=900000,
                        search_keyword="m2맥북에어",
                        poll_interval_seconds=60,
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("item", {}).get("min_price_krw"), 300000)
        self.assertIsNone(result.get("item", {}).get("max_price_krw"))

    def test_upsert_rejects_invalid_alert_price_direction(self):
        result = upsert_user_fair_price_setting(
            user_id="boongtol",
            product_type="MacBook Air",
            chip="M2",
            screen_inch=13,
            ram_gb=8,
            ssd_gb=256,
            fair_price_krw=1000000,
            alert_drop_rate_percent=20.50,
            enabled=True,
            alert_price_direction="INVALID_DIRECTION",
            search_keyword="m2맥북에어",
            poll_interval_seconds=60,
        )

        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("reason"), "invalid_alert_price_direction")


if __name__ == "__main__":
    unittest.main()
