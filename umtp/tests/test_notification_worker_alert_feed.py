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
        "src.notification_worker._fetch_alert_rows",
        return_value=(
            [
                {
                    "id": 11,
                    "user_id": "boongtol",
                    "watch_rule_id": None,
                    "analysis_job_id": 100,
                    "product_id": "p1",
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
    def test_alert_feed_includes_detailed_fields(self, _mock_rows, _mock_conn):
        items = list_alert_events_for_user("boongtol", limit=20)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.get("source"), "joongna")
        self.assertEqual(item.get("product_type"), "MacBook Air")
        self.assertEqual(item.get("alert_target_price_krw"), 795000)
        self.assertEqual(item.get("price_gap_percent"), 20.5)
        self.assertEqual(item.get("alert_price_direction"), "BELOW_OR_EQUAL")
        self.assertEqual(item.get("alert_condition_label"), "이 가격 이하이면 알림")
        self.assertEqual(item.get("formatted_risk_label"), "낮음")
        self.assertEqual(item.get("risk_keywords"), [])
        self.assertEqual(item.get("body_excerpt"), "상태 좋고 배터리 정상")

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
        self.assertEqual(item.get("risk_level"), "HIGH")
        self.assertEqual(item.get("formatted_risk_label"), "위험")
        self.assertEqual(item.get("risk_keywords"), ["교환"])
        self.assertTrue(item.get("trade_type_flags", {}).get("is_exchange"))
        self.assertTrue(item.get("trade_type_flags", {}).get("is_suspicious"))
        self.assertEqual(item.get("body_excerpt"), None)


if __name__ == "__main__":
    unittest.main()
