import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import (  # noqa: E402
    WATCH_PRIORITY_FAST,
    WATCH_PRIORITY_LOW,
    WATCH_PRIORITY_NORMAL,
    apply_polling_jitter,
    normalize_watch_priority,
    polling_interval_for_priority,
    upsert_user_fair_price_setting,
)


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self._last_query = ""

    def execute(self, query, params=None):
        self.executed.append((query, params))
        self._last_query = (query or "").lower()

    def fetchone(self):
        if "select current_timestamp" in self._last_query:
            return (datetime(2026, 5, 19, 10, 0, 0),)
        return None

    def fetchall(self):
        return []

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


class WatchPriorityPollingTest(unittest.TestCase):
    def test_priority_defaults_to_normal_when_missing(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch(
                    "src.user_settings_service._resolve_setting_search_keyword",
                    return_value="m2 맥북에어",
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
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("item", {}).get("priority"), WATCH_PRIORITY_NORMAL)

    def test_fast_priority_interval_is_calculated(self):
        interval = polling_interval_for_priority(
            WATCH_PRIORITY_FAST,
            random_fn=lambda _low, _high: 0.0,
        )
        self.assertEqual(interval, 45)

    def test_normal_and_low_priority_interval_range(self):
        normal_min = polling_interval_for_priority(
            WATCH_PRIORITY_NORMAL,
            random_fn=lambda low, _high: low,
        )
        normal_max = polling_interval_for_priority(
            WATCH_PRIORITY_NORMAL,
            random_fn=lambda _low, high: high,
        )
        low_min = polling_interval_for_priority(
            WATCH_PRIORITY_LOW,
            random_fn=lambda low, _high: low,
        )
        low_max = polling_interval_for_priority(
            WATCH_PRIORITY_LOW,
            random_fn=lambda _low, high: high,
        )

        self.assertEqual(normal_min, 144)
        self.assertEqual(normal_max, 216)
        self.assertEqual(low_min, 480)
        self.assertEqual(low_max, 720)

    def test_invalid_priority_is_normalized_to_normal(self):
        self.assertEqual(normalize_watch_priority("weird"), WATCH_PRIORITY_NORMAL)
        self.assertEqual(normalize_watch_priority(None), WATCH_PRIORITY_NORMAL)
        self.assertEqual(normalize_watch_priority("low"), WATCH_PRIORITY_LOW)

    def test_invalid_priority_value_is_corrected_to_normal_on_upsert(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch(
                    "src.user_settings_service._resolve_setting_search_keyword",
                    return_value="m2 맥북에어",
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
                        priority="TOO_FAST",
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("item", {}).get("priority"), WATCH_PRIORITY_NORMAL)

    def test_jitter_never_goes_below_minimum_30_seconds(self):
        interval = apply_polling_jitter(
            10,
            random_fn=lambda low, _high: low,
        )
        self.assertGreaterEqual(interval, 30)


if __name__ == "__main__":
    unittest.main()
