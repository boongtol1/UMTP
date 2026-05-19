import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.notification_worker import (  # noqa: E402
    _build_telegram_message,
    dispatch_alert_event_immediately,
    process_pending_alert_events,
    send_alert_event,
)


class NotificationWorkerTest(unittest.TestCase):
    def test_build_telegram_message_uses_alert_feed_wording(self):
        message = _build_telegram_message(
            {
                "source": "joongna",
                "url": "https://web.joongna.com/product/1001",
                "listing_image_url": "https://img.joongna.com/1001.jpg",
                "product_type": "MacBook Air",
                "chip": "M2",
                "screen_inch": 13,
                "ram_gb": 16,
                "ssd_gb": 512,
                "price_krw": 650000,
                "fair_price_krw": 800000,
                "target_price_krw": 795000,
                "drop_rate_percent": 18.75,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_keywords": "[]",
                "body_text": "m2 기본형",
                "analyzed_at": "2026-05-19T10:46:58",
                "trade_type_flags": {
                    "is_exchange": False,
                    "is_free": False,
                    "is_suspicious": False,
                },
            }
        )

        self.assertIn("거래 알림 피드", message)
        self.assertIn("출처\njoongna", message)
        self.assertIn("URL\nhttps://web.joongna.com/product/1001", message)
        self.assertIn("대표 이미지\nhttps://img.joongna.com/1001.jpg", message)
        self.assertIn("제품 분류\nMacBook Air", message)
        self.assertIn("칩\nM2", message)
        self.assertIn("화면 크기\n13인치", message)
        self.assertIn("RAM\n16GB", message)
        self.assertIn("SSD\n512GB", message)
        self.assertIn("등록 가격\n650,000원", message)
        self.assertIn("내가 생각한 시장가\n800,000원", message)
        self.assertIn("알림 기준 가격\n795,000원", message)
        self.assertIn("시장가와의 차이\n18.75%", message)
        self.assertIn("차이율 계산식\n(내가 생각한 시장가 - 등록 가격) / 내가 생각한 시장가 × 100", message)
        self.assertIn("알림 조건\n이 가격 이하이면 알림", message)
        self.assertIn("위험도\n낮음", message)
        self.assertIn("위험 점수\n0", message)
        self.assertIn("위험 키워드\n특이사항 없음", message)
        self.assertIn("본문 내용\nm2 기본형", message)
        self.assertIn("분석 시각\n2026-05-19T10:46:58", message)
        self.assertIn("교환/나눔/의심\n특이사항 없음", message)
        self.assertIn("특이사항\n특이사항 없음", message)
        self.assertIn("https://web.joongna.com/product/1001", message)

        expected_order_tokens = [
            "거래 알림 피드",
            "출처\n",
            "URL\n",
            "대표 이미지\n",
            "제품 분류\n",
            "칩\n",
            "화면 크기\n",
            "RAM\n",
            "SSD\n",
            "등록 가격\n",
            "내가 생각한 시장가\n",
            "알림 기준 가격\n",
            "시장가와의 차이\n",
            "차이율 계산식\n",
            "알림 조건\n",
            "위험도\n",
            "위험 점수\n",
            "위험 키워드\n",
            "본문 내용\n",
            "분석 시각\n",
            "교환/나눔/의심\n",
            "\n\n특이사항\n",
        ]
        last_index = -1
        for token in expected_order_tokens:
            current_index = message.find(token)
            self.assertNotEqual(current_index, -1, msg=f"missing token: {token}")
            self.assertGreater(current_index, last_index, msg=f"order mismatch at: {token}")
            last_index = current_index

    def test_send_alert_event_app_only_when_alerts_disabled(self):
        with patch(
            "src.notification_worker.resolve_user_alert_delivery_policy",
            return_value={
                "enabled": False,
                "telegram_chat_id": None,
                "allow_global_fallback": False,
            },
        ):
            with patch("src.notification_worker.mark_alert_event_app_only") as mock_mark_app_only:
                with patch("src.notification_worker.send_telegram_alert") as mock_send_telegram:
                    result = send_alert_event(
                        {
                            "id": 1,
                            "user_id": "boongtol",
                            "title": "테스트",
                            "message": "테스트 메시지",
                        }
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "app_only")
        self.assertEqual(result.get("reason"), "alerts_disabled")
        self.assertEqual(mock_mark_app_only.call_count, 1)
        self.assertEqual(mock_send_telegram.call_count, 0)

    def test_send_alert_event_skips_when_missing_user_chat_id(self):
        with patch(
            "src.notification_worker.resolve_user_alert_delivery_policy",
            return_value={
                "enabled": True,
                "telegram_chat_id": None,
                "allow_global_fallback": False,
            },
        ):
            with patch("src.notification_worker._send_fcm_to_user", return_value={"sent": 0, "failed": 0, "attempted": 0, "reason": "no_active_push_tokens"}):
                with patch("src.notification_worker._telegram_configured", return_value=True):
                    with patch("src.notification_worker.mark_alert_event_app_only") as mock_mark_app_only:
                        with patch("src.notification_worker.send_telegram_alert") as mock_send_telegram:
                            result = send_alert_event(
                                {
                                    "id": 2,
                                    "user_id": "boongtol",
                                    "title": "테스트",
                                    "message": "테스트 메시지",
                                }
                            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "app_only")
        self.assertEqual(result.get("reason"), "missing_telegram_chat_id")
        self.assertEqual(mock_mark_app_only.call_count, 1)
        self.assertEqual(mock_send_telegram.call_count, 0)

    def test_send_alert_event_sent_when_telegram_success(self):
        with patch(
            "src.notification_worker.resolve_user_alert_delivery_policy",
            return_value={
                "enabled": True,
                "telegram_chat_id": "123456",
                "allow_global_fallback": False,
            },
        ):
            with patch("src.notification_worker._send_fcm_to_user", return_value={"sent": 0, "failed": 0, "attempted": 0, "reason": "no_active_push_tokens"}):
                with patch("src.notification_worker._telegram_configured", return_value=True):
                    with patch("src.notification_worker.send_telegram_alert", return_value=True) as mock_send_telegram:
                        with patch("src.notification_worker.mark_alert_event_sent") as mock_mark_sent:
                            result = send_alert_event(
                                {
                                    "id": 3,
                                    "user_id": "boongtol",
                                    "title": "테스트",
                                    "message": "테스트 메시지",
                                }
                            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(result.get("reason"), "telegram_sent")
        self.assertEqual(mock_mark_sent.call_count, 1)
        self.assertEqual(mock_send_telegram.call_args.kwargs.get("chat_id"), "123456")

    def test_send_alert_event_passes_listing_image_url_to_telegram(self):
        with patch(
            "src.notification_worker.resolve_user_alert_delivery_policy",
            return_value={
                "enabled": True,
                "telegram_chat_id": "123456",
                "allow_global_fallback": False,
            },
        ):
            with patch("src.notification_worker._send_fcm_to_user", return_value={"sent": 0, "failed": 0, "attempted": 0, "reason": "no_active_push_tokens"}):
                with patch("src.notification_worker._telegram_configured", return_value=True):
                    with patch("src.notification_worker._fetch_listing_image_url_by_product_id", return_value="https://img.joongna.com/p/1001.jpg"):
                        with patch("src.notification_worker.send_telegram_alert", return_value=True) as mock_send_telegram:
                            with patch("src.notification_worker.mark_alert_event_sent"):
                                result = send_alert_event(
                                    {
                                        "id": 301,
                                        "user_id": "boongtol",
                                        "product_id": "1001",
                                        "title": "이미지 테스트",
                                    }
                                )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(
            mock_send_telegram.call_args.kwargs.get("image_url"),
            "https://img.joongna.com/p/1001.jpg",
        )

    def test_send_alert_event_sent_when_push_success_without_telegram(self):
        with patch(
            "src.notification_worker.resolve_user_alert_delivery_policy",
            return_value={
                "enabled": True,
                "telegram_chat_id": None,
                "allow_global_fallback": False,
            },
        ):
            with patch("src.notification_worker._send_fcm_to_user", return_value={"sent": 1, "failed": 0, "attempted": 1, "reason": "fcm_sent"}):
                with patch("src.notification_worker._telegram_configured", return_value=True):
                    with patch("src.notification_worker.mark_alert_event_sent") as mock_mark_sent:
                        with patch("src.notification_worker.send_telegram_alert") as mock_send_telegram:
                            result = send_alert_event(
                                {
                                    "id": 4,
                                    "user_id": "boongtol",
                                    "title": "푸시 테스트",
                                    "message": "푸시 테스트 메시지",
                                }
                            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(result.get("reason"), "push_sent")
        self.assertEqual(mock_mark_sent.call_count, 1)
        self.assertEqual(mock_send_telegram.call_count, 0)

    def test_process_pending_alert_events_continues_after_failure(self):
        pending_alerts = [
            {"id": 11, "user_id": "u1", "message": "A"},
            {"id": 12, "user_id": "u2", "message": "B"},
        ]

        def _send_side_effect(alert):
            if alert.get("id") == 11:
                raise RuntimeError("send failed")
            return {"ok": True, "alert_id": 12, "status": "sent", "reason": "telegram_sent"}

        with patch("src.notification_worker.get_pending_alert_events", return_value=pending_alerts):
            with patch("src.notification_worker.mark_alert_event_sending"):
                with patch("src.notification_worker.send_alert_event", side_effect=_send_side_effect):
                    with patch("src.notification_worker.mark_alert_event_failed") as mock_mark_failed:
                        stats = process_pending_alert_events(limit=20)

        self.assertEqual(stats.get("fetched"), 2)
        self.assertEqual(stats.get("failed"), 1)
        self.assertEqual(stats.get("sent"), 1)
        self.assertEqual(mock_mark_failed.call_count, 1)

    def test_process_pending_alert_events_skips_when_not_claimed(self):
        pending_alerts = [{"id": 11, "user_id": "u1", "message": "A"}]

        with patch("src.notification_worker.get_pending_alert_events", return_value=pending_alerts):
            with patch("src.notification_worker.mark_alert_event_sending", return_value=False):
                with patch("src.notification_worker.send_alert_event") as mock_send_alert:
                    stats = process_pending_alert_events(limit=20)

        self.assertEqual(stats.get("fetched"), 1)
        self.assertEqual(stats.get("sent"), 0)
        self.assertEqual(stats.get("failed"), 0)
        self.assertEqual(mock_send_alert.call_count, 0)
        self.assertEqual(stats.get("results")[0].get("status"), "skipped_not_pending")

    def test_dispatch_alert_event_immediately_skips_when_not_pending(self):
        with patch("src.notification_worker.mark_alert_event_sending", return_value=False):
            with patch("src.notification_worker.send_alert_event") as mock_send_alert:
                result = dispatch_alert_event_immediately(
                    101,
                    fallback_alert={
                        "user_id": "boongtol",
                        "message": "테스트 메시지",
                    },
                )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "skipped_not_pending")
        self.assertEqual(mock_send_alert.call_count, 0)

    def test_dispatch_alert_event_immediately_sends_with_fallback_payload(self):
        with patch("src.notification_worker.mark_alert_event_sending", return_value=True):
            with patch(
                "src.notification_worker.send_alert_event",
                return_value={
                    "ok": True,
                    "alert_id": 102,
                    "status": "sent",
                    "reason": "telegram_sent",
                },
            ) as mock_send_alert:
                with patch("src.notification_worker.get_alert_event_by_id") as mock_get_alert:
                    result = dispatch_alert_event_immediately(
                        102,
                        fallback_alert={
                            "user_id": "boongtol",
                            "title": "테스트",
                            "message": "테스트 메시지",
                        },
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(mock_get_alert.call_count, 0)
        self.assertEqual(mock_send_alert.call_count, 1)
        sent_payload = mock_send_alert.call_args.args[0]
        self.assertEqual(sent_payload.get("id"), 102)
        self.assertEqual(sent_payload.get("user_id"), "boongtol")


if __name__ == "__main__":
    unittest.main()
