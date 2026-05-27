import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.notification_worker import list_alert_events_for_user  # noqa: E402


class _FakeCursor:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self):
        self._cursor = _FakeCursor()

    def cursor(self, dictionary=False):
        return self._cursor

    def is_connected(self):
        return True

    def close(self):
        return None


class NotificationWorkerAlertFeedTest(unittest.TestCase):
    @patch("src.notification_worker.get_connection", return_value=_FakeConnection())
    @patch(
        "src.notification_worker._fetch_listing_image_urls",
        return_value={"1": "https://img.joongna.com/p/1.jpg"},
    )
    @patch(
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 11,
                    "user_id": "boongtol",
                    "watch_rule_id": None,
                    "analysis_job_id": 100,
                    "product_id": "1",
                    "source": "joongna",
                    "url": "https://web.joongna.com/product/1",
                    "title": "맥북에어 m1 8 256",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                    "price_krw": 790000,
                    "fair_price_krw": 1000000,
                    "target_price_krw": 795000,
                    "drop_rate_percent": 20.5,
                    "alert_drop_rate_percent": 20.5,
                    "alert_price_direction": "BELOW_OR_EQUAL",
                    "risk_level": "LOW",
                    "risk_score": 0,
                    "risk_keywords": "[]",
                    "is_exchange_post": False,
                    "trade_type": "sale",
                    "body_excerpt": "상태 좋고 배터리 정상",
                    "body_text": "상태 좋고 배터리 정상. 사용감 적음.",
                    "analyzed_at": "2026-05-16T12:00:00",
                    "trigger_reason": "new_product",
                    "message": "msg",
                    "status": "pending",
                    "send_attempts": 0,
                    "error_message": None,
                    "created_at": "2026-05-16T12:00:01",
                    "sent_at": None,
                    "updated_at": "2026-05-16T12:00:01",
                }
            ],
            True,
        ),
    )
    def test_alert_feed_includes_detailed_fields(self, _mock_rows, _mock_images, _mock_conn):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.get("source"), "joongna")
        self.assertEqual(item.get("product_type"), "MacBook Air")
        self.assertEqual(item.get("alert_target_price_krw"), 795000)
        self.assertEqual(item.get("price_gap_percent"), 20.5)
        self.assertEqual(item.get("alert_price_direction"), "BELOW_OR_EQUAL")
        self.assertEqual(item.get("alert_condition_label"), "이 가격 이하이면 알림")
        self.assertEqual(item.get("alert_type_label"), "정식 알림")
        self.assertEqual(item.get("formatted_risk_label"), "낮음")
        self.assertEqual(item.get("risk_keywords"), [])
        self.assertEqual(item.get("body_excerpt"), "상태 좋고 배터리 정상")
        self.assertEqual(item.get("body_text"), "상태 좋고 배터리 정상. 사용감 적음.")
        self.assertEqual(item.get("listing_image_url"), "https://img.joongna.com/p/1.jpg")
        self.assertTrue(item.get("is_alert_target"))
        self.assertFalse(item.get("is_condition_change_candidate_notice"))
        self.assertFalse(item.get("is_read"))
        self.assertIsNone(item.get("read_at"))

    @patch("src.notification_worker.get_connection", return_value=_FakeConnection())
    @patch(
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 12,
                    "user_id": "boongtol",
                    "watch_rule_id": None,
                    "analysis_job_id": 101,
                    "product_id": "p2",
                    "url": "https://web.joongna.com/product/2",
                    "title": "맥북에어 m2",
                    "price_krw": 1150000,
                    "fair_price_krw": 1000000,
                    "target_price_krw": 1100000,
                    "drop_rate_percent": -10.0,
                    "trigger_reason": "new_product",
                    "message": "msg",
                    "status": "pending",
                    "send_attempts": 0,
                    "error_message": None,
                    "created_at": "2026-05-16T12:10:01",
                    "sent_at": None,
                    "updated_at": "2026-05-16T12:10:01",
                }
            ],
            False,
        ),
    )
    @patch(
        "src.notification_worker._fetch_latest_log_details",
        return_value={
            "source": "joongna",
            "product_type": "MacBook Air",
            "chip": "M2",
            "screen_inch": 13,
            "ram_gb": 16,
            "ssd_gb": 256,
            "risk_level": "HIGH",
            "risk_score": 88,
            "risk_keywords": '["교환"]',
            "is_exchange_post": True,
            "trade_type": "exchange",
            "body_text": "교환 원합니다. 본문 테스트",
            "created_at": "2026-05-16T12:10:00",
        },
    )
    def test_alert_feed_falls_back_to_analysis_log_when_detail_columns_missing(
        self,
        _mock_log_detail,
        _mock_rows,
        _mock_conn,
    ):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.get("alert_price_direction"), "BELOW_OR_EQUAL")
        self.assertEqual(item.get("alert_condition_label"), "이 가격 이하이면 알림")
        self.assertEqual(item.get("alert_type_label"), "정식 알림")
        self.assertEqual(item.get("risk_level"), "HIGH")
        self.assertEqual(item.get("formatted_risk_label"), "위험")
        self.assertEqual(item.get("risk_keywords"), ["교환"])
        self.assertTrue(item.get("trade_type_flags", {}).get("is_exchange"))
        self.assertTrue(item.get("trade_type_flags", {}).get("is_suspicious"))
        self.assertEqual(item.get("body_text"), "교환 원합니다. 본문 테스트")
        self.assertEqual(item.get("body_excerpt"), "교환 원합니다. 본문 테스트")
        self.assertTrue(item.get("is_alert_target"))
        self.assertFalse(item.get("is_condition_change_candidate_notice"))
        self.assertFalse(item.get("is_read"))
        self.assertIsNone(item.get("read_at"))

    @patch("src.notification_worker.get_connection", return_value=_FakeConnection())
    @patch(
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 13,
                    "user_id": "boongtol",
                    "watch_rule_id": 9,
                    "analysis_job_id": None,
                    "product_id": "cccn-9-abcdef",
                    "url": "",
                    "title": "조건 변경 사이 후보 · M2 / 13인치 / 8GB / 256GB SSD",
                    "price_krw": None,
                    "fair_price_krw": 1000000,
                    "target_price_krw": 950000,
                    "drop_rate_percent": None,
                    "alert_drop_rate_percent": 5.0,
                    "alert_price_direction": "BELOW_OR_EQUAL",
                    "trigger_reason": "condition_change_candidate_notice",
                    "message": "조건 변경 후보: 새 기준에 맞는 매물이 1개 있었어요.",
                    "status": "app_only",
                    "send_attempts": 0,
                    "error_message": None,
                    "created_at": "2026-05-19T13:30:00",
                    "sent_at": None,
                    "updated_at": "2026-05-19T13:30:00",
                }
            ],
            True,
        ),
    )
    def test_condition_change_candidate_notice_is_not_alert_target(
        self,
        _mock_rows,
        _mock_conn,
    ):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.get("trigger_reason"), "condition_change_candidate_notice")
        self.assertEqual(item.get("alert_type_label"), "참고 알림 (조건 변경 사이 후보)")
        self.assertEqual(item.get("alert_condition_label"), "조건 변경 사이 후보")
        self.assertFalse(item.get("is_alert_target"))
        self.assertTrue(item.get("is_condition_change_candidate_notice"))

    @patch("src.notification_worker.get_connection", return_value=_FakeConnection())
    @patch(
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 14,
                    "user_id": "boongtol",
                    "watch_rule_id": 4,
                    "analysis_job_id": 102,
                    "product_id": "p14",
                    "url": "https://web.joongna.com/product/14",
                    "title": "제목 수정된 매물",
                    "price_krw": 1200000,
                    "fair_price_krw": 1300000,
                    "target_price_krw": 1250000,
                    "drop_rate_percent": 7.69,
                    "alert_drop_rate_percent": 3.85,
                    "alert_price_direction": "ABOVE_OR_EQUAL",
                    "trigger_reason": "title_changed",
                    "message": "내용 변경",
                    "status": "pending",
                    "send_attempts": 0,
                    "error_message": None,
                    "created_at": "2026-05-20T11:00:00",
                    "sent_at": None,
                    "updated_at": "2026-05-20T11:00:00",
                }
            ],
            True,
        ),
    )
    def test_content_change_type_keeps_price_condition_label(self, _mock_rows, _mock_conn):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.get("trigger_reason"), "title_changed")
        self.assertEqual(item.get("alert_type_label"), "내용 변경 알림")
        self.assertEqual(item.get("alert_condition_label"), "이 가격 이상이면 알림")
        self.assertTrue(item.get("is_alert_target"))

    @patch("src.notification_worker.get_connection", return_value=_FakeConnection())
    @patch(
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 15,
                    "user_id": "boongtol",
                    "watch_rule_id": 5,
                    "analysis_job_id": 103,
                    "product_id": "p15",
                    "url": "https://web.joongna.com/product/15",
                    "title": "끌올된 매물",
                    "price_krw": 780000,
                    "fair_price_krw": 900000,
                    "target_price_krw": 820000,
                    "drop_rate_percent": 13.33,
                    "alert_drop_rate_percent": 10.0,
                    "alert_price_direction": "BELOW_OR_EQUAL",
                    "trigger_reason": "sort_date_changed",
                    "message": "정식 알림 메시지",
                    "body_excerpt": "본문 요약",
                    "status": "pending",
                    "send_attempts": 0,
                    "error_message": None,
                    "created_at": "2026-05-21T11:00:00",
                    "sent_at": None,
                    "updated_at": "2026-05-21T11:00:00",
                }
            ],
            True,
        ),
    )
    def test_refresh_based_alert_includes_refresh_notice_fields(self, _mock_rows, _mock_conn):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertTrue(item.get("used_refresh_info"))
        self.assertEqual(item.get("refresh_notice_text"), "끌올된 정보를 사용한 알림입니다")
        self.assertIn("끌올된 정보를 사용한 알림입니다", item.get("body_excerpt"))
        self.assertIn("끌올된 정보를 사용한 알림입니다", item.get("special_notes_text"))

    @patch("src.notification_worker.get_connection", return_value=_FakeConnection())
    @patch(
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 16,
                    "user_id": "boongtol",
                    "watch_rule_id": 6,
                    "analysis_job_id": None,
                    "product_id": "p16",
                    "url": "https://web.joongna.com/product/16",
                    "title": "조건 변경 사이 후보",
                    "price_krw": 980000,
                    "fair_price_krw": 1050000,
                    "target_price_krw": 990000,
                    "drop_rate_percent": 6.67,
                    "alert_drop_rate_percent": 5.0,
                    "alert_price_direction": "BELOW_OR_EQUAL",
                    "trigger_reason": "condition_change_candidate_notice",
                    "message": "조건 변경 후보\n끌올된 정보를 사용한 알림입니다",
                    "body_excerpt": "조건 변경 후보 안내",
                    "status": "pending",
                    "send_attempts": 0,
                    "error_message": None,
                    "created_at": "2026-05-21T12:00:00",
                    "sent_at": None,
                    "updated_at": "2026-05-21T12:00:00",
                }
            ],
            True,
        ),
    )
    def test_condition_change_notice_can_carry_refresh_notice(self, _mock_rows, _mock_conn):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertTrue(item.get("used_refresh_info"))
        self.assertEqual(item.get("refresh_notice_text"), "끌올된 정보를 사용한 알림입니다")
        self.assertIn("끌올된 정보를 사용한 알림입니다", item.get("special_notes_text"))


if __name__ == "__main__":
    unittest.main()
