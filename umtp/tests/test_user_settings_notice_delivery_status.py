import os
import sys
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import _insert_condition_change_candidate_notice_alert_event  # noqa: E402


class _NoticeInsertCursor:
    def __init__(
        self,
        *,
        fail_primary=False,
        fail_fallback=False,
        existing_alert_id=None,
        alert_detail_row=None,
        url_log_row=None,
    ):
        self.fail_primary = fail_primary
        self.fail_fallback = fail_fallback
        self.existing_alert_id = existing_alert_id
        self.alert_detail_row = alert_detail_row
        self.url_log_row = url_log_row
        self.executed = []
        self._insert_attempt_count = 0
        self._last_query = ""

    def execute(self, query, params=None):
        normalized_query = " ".join((query or "").lower().split())
        self.executed.append((normalized_query, params))
        self._last_query = normalized_query

        if "insert into alert_events" in normalized_query:
            expected_placeholder_count = normalized_query.count("%s")
            actual_param_count = len(params or ())
            if expected_placeholder_count != actual_param_count:
                raise AssertionError(
                    f"placeholder_mismatch expected={expected_placeholder_count} actual={actual_param_count}"
                )

            self._insert_attempt_count += 1
            if self._insert_attempt_count == 1 and self.fail_primary:
                raise RuntimeError("unknown column detail_col")
            if self._insert_attempt_count == 2 and self.fail_fallback:
                raise RuntimeError("unknown column fallback_col")

    def fetchone(self):
        if (
            "from alert_events" in self._last_query
            and "watch_rule_id = %s" in self._last_query
            and "product_id = %s" in self._last_query
            and "select id" in self._last_query
        ):
            if self.existing_alert_id is not None:
                return (self.existing_alert_id,)
            return None
        if (
            "from alert_events" in self._last_query
            and "coalesce(trigger_reason, '') <> %s" in self._last_query
            and self.alert_detail_row is not None
        ):
            row = self.alert_detail_row
            self.alert_detail_row = None
            return row
        if "from url_analysis_logs" in self._last_query and self.url_log_row is not None:
            row = self.url_log_row
            self.url_log_row = None
            return row
        return None


class UserSettingsNoticeDeliveryStatusTest(unittest.TestCase):
    def _call_insert_notice(self, cursor, *, listing_trigger_reason=None):
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
            listing_trigger_reason=listing_trigger_reason,
        )

    def test_primary_insert_uses_pending_status(self):
        cursor = _NoticeInsertCursor()

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("reason"), "created")
        primary_query = [
            query for query, _params in cursor.executed if "insert into alert_events" in query
        ][0]
        self.assertIn("'pending'", primary_query)
        self.assertNotIn("'app_only'", primary_query)

    def test_fallback_insert_uses_pending_status(self):
        cursor = _NoticeInsertCursor(fail_primary=True)

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("reason"), "created_fallback")
        fallback_query = [
            query for query, _params in cursor.executed if "insert into alert_events" in query
        ][1]
        self.assertIn("'pending'", fallback_query)
        self.assertNotIn("'app_only'", fallback_query)

    def test_minimal_insert_uses_pending_status(self):
        cursor = _NoticeInsertCursor(fail_primary=True, fail_fallback=True)

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("reason"), "created_minimal")
        minimal_query = [
            query for query, _params in cursor.executed if "insert into alert_events" in query
        ][2]
        self.assertIn("'pending'", minimal_query)
        self.assertNotIn("'app_only'", minimal_query)

    def test_primary_insert_prefills_risk_trade_body_from_db(self):
        cursor = _NoticeInsertCursor(
            alert_detail_row=(
                "joongna",
                "https://web.joongna.com/product/228796648",
                "맥미니 m4 기본형",
                1380000,
                datetime(2026, 5, 20, 19, 40, 0),
                "HIGH",
                88,
                '["교환"]',
                1,
                "exchange",
                "교환 제안 포함",
                "교환 제안 포함 본문",
                datetime(2026, 5, 20, 19, 41, 0),
                datetime(2026, 5, 20, 19, 41, 0),
            )
        )

        result = self._call_insert_notice(cursor)

        self.assertTrue(result.get("created"))
        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_events" in query
        ][0]
        self.assertIn("HIGH", insert_params)
        self.assertIn(88, insert_params)
        self.assertIn('["교환"]', insert_params)
        self.assertIn("exchange", insert_params)
        self.assertIn("교환 제안 포함", insert_params)
        self.assertTrue(any("[참고 알림]" in str(value) for value in insert_params))

    def test_skips_when_same_user_rule_product_already_has_alert_event(self):
        cursor = _NoticeInsertCursor(existing_alert_id=321)

        result = self._call_insert_notice(cursor)

        self.assertFalse(result.get("created"))
        self.assertEqual(result.get("reason"), "existing_alert_event_for_user_rule_product")
        self.assertEqual(result.get("alert_id"), 321)
        insert_queries = [query for query, _params in cursor.executed if "insert into alert_events" in query]
        self.assertEqual(insert_queries, [])

    def test_refresh_based_notice_includes_refresh_notice_text(self):
        cursor = _NoticeInsertCursor()

        result = self._call_insert_notice(cursor, listing_trigger_reason="sort_date_changed")

        self.assertTrue(result.get("created"))
        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_events" in query
        ][0]
        self.assertTrue(
            any("끌올된 정보를 사용한 알림입니다" in str(value) for value in insert_params)
        )


if __name__ == "__main__":
    unittest.main()
