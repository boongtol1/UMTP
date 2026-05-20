import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import upsert_user_fair_price_setting  # noqa: E402


class _HistoryFakeCursor:
    def __init__(self, existing_row):
        self.existing_row = existing_row
        self.executed = []
        self._last_query = ""
        self._existing_fetched = False

    def execute(self, query, params=None):
        self.executed.append((query, params))
        self._last_query = query or ""

    def fetchone(self):
        lowered = " ".join((self._last_query or "").lower().split())
        if lowered.startswith("select current_timestamp"):
            return (datetime(2026, 5, 20, 17, 0, 0),)
        if "from user_fair_prices" in lowered and "limit 1" in lowered and not self._existing_fetched:
            self._existing_fetched = True
            return self.existing_row
        return None

    def fetchall(self):
        return []

    def close(self):
        return None


class _HistoryFakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class UserFairPriceHistoryTest(unittest.TestCase):
    def _call_upsert(self, cursor, *, fair_price_krw, alert_drop_rate_percent):
        connection = _HistoryFakeConnection(cursor)
        with patch("src.user_settings_service.get_connection", return_value=connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch(
                    "src.user_settings_service._resolve_setting_search_keyword",
                    return_value="m4 맥미니",
                ):
                    return upsert_user_fair_price_setting(
                        user_id="boongtol",
                        product_type="Mac mini",
                        chip="M4",
                        screen_inch=0,
                        ram_gb=16,
                        ssd_gb=512,
                        fair_price_krw=fair_price_krw,
                        alert_drop_rate_percent=alert_drop_rate_percent,
                        enabled=True,
                        search_keyword="m4 맥미니",
                        poll_interval_seconds=60,
                    )

    def test_creates_history_on_meaningful_price_change_same_spec(self):
        existing_row = (
            14,
            datetime(2026, 5, 20, 15, 0, 0),
            datetime(2026, 5, 20, 15, 0, 0),
            1_000_000,
            20.0,
            800_000,
            "BELOW_OR_EQUAL",
            None,
            None,
            1,
            1,
        )
        cursor = _HistoryFakeCursor(existing_row)

        result = self._call_upsert(
            cursor,
            fair_price_krw=1_100_000,
            alert_drop_rate_percent=20.0,
        )

        self.assertTrue(result.get("ok"))
        history_inserts = [
            params
            for query, params in cursor.executed
            if "insert into user_fair_price_history" in " ".join((query or "").lower().split())
        ]
        self.assertEqual(len(history_inserts), 1)
        inserted_params = history_inserts[0]
        self.assertEqual(inserted_params[0], 14)
        self.assertEqual(inserted_params[7], 1_000_000)
        self.assertEqual(inserted_params[8], 1_100_000)

    def test_does_not_create_history_when_values_unchanged(self):
        existing_row = (
            14,
            datetime(2026, 5, 20, 15, 0, 0),
            datetime(2026, 5, 20, 15, 0, 0),
            1_000_000,
            20.0,
            800_000,
            "BELOW_OR_EQUAL",
            None,
            None,
            1,
            1,
        )
        cursor = _HistoryFakeCursor(existing_row)

        result = self._call_upsert(
            cursor,
            fair_price_krw=1_000_000,
            alert_drop_rate_percent=20.0,
        )

        self.assertTrue(result.get("ok"))
        history_inserts = [
            query
            for query, _params in cursor.executed
            if "insert into user_fair_price_history" in " ".join((query or "").lower().split())
        ]
        self.assertEqual(len(history_inserts), 0)


if __name__ == "__main__":
    unittest.main()
