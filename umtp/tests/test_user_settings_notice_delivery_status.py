import os
import sys
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import _insert_condition_change_candidate_notice_alert_event  # noqa: E402


class _NoticeInsertCursor:
    def __init__(self, *, fail_primary=False, fail_fallback=False):
        self.fail_primary = fail_primary
        self.fail_fallback = fail_fallback
        self.executed = []
        self._execute_count = 0

    def execute(self, query, params=None):
        self._execute_count += 1
        normalized_query = " ".join((query or "").lower().split())
        self.executed.append((normalized_query, params))

        if self._execute_count == 1 and self.fail_primary:
            raise RuntimeError("unknown column detail_col")
        if self._execute_count == 2 and self.fail_fallback:
            raise RuntimeError("unknown column fallback_col")


class UserSettingsNoticeDeliveryStatusTest(unittest.TestCase):
    def _call_insert_notice(self, cursor):
        return _insert_condition_change_candidate_notice_alert_event(
            cursor,
            user_id="boongtol",
            watch_rule_id=14,
            product_type="Mac mini",
            chip="M4",
            screen_inch=0,
            ram_gb=16,
            ssd_gb=256,
            fair_price_krw=1_400_000,
            target_price_krw=1_380_000,
            alert_drop_rate_percent=1.5,
            alert_price_direction="BELOW_OR_EQUAL",
            missed_candidate_count=1,
            sort_date=datetime(2026, 5, 20, 20, 0, 0),
            listing_product_id="228796648",
            listing_title="맥미니 m4 기본형",
            listing_url="https://web.joongna.com/product/228796648",
            listing_source="joongna",
            listing_price_krw=1_380_000,
            listing_sort_date=datetime(2026, 5, 20, 19, 40, 0),
        )

    def test_primary_insert_uses_pending_status(self):
        cursor = _NoticeInsertCursor()

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("reason"), "created")
        primary_query = cursor.executed[0][0]
        self.assertIn("'pending'", primary_query)
        self.assertNotIn("'app_only'", primary_query)

    def test_fallback_insert_uses_pending_status(self):
        cursor = _NoticeInsertCursor(fail_primary=True)

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("reason"), "created_fallback")
        fallback_query = cursor.executed[1][0]
        self.assertIn("'pending'", fallback_query)
        self.assertNotIn("'app_only'", fallback_query)

    def test_minimal_insert_uses_pending_status(self):
        cursor = _NoticeInsertCursor(fail_primary=True, fail_fallback=True)

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("reason"), "created_minimal")
        minimal_query = cursor.executed[2][0]
        self.assertIn("'pending'", minimal_query)
        self.assertNotIn("'app_only'", minimal_query)


if __name__ == "__main__":
    unittest.main()
