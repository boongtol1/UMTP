import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.notification_worker import (  # noqa: E402
    _build_push_notification_payload,
    _build_telegram_message,
    dispatch_alert_event_immediately,
    list_alert_events_for_user,
    list_grouped_read_alert_events_for_user,
    process_pending_alert_events,
    send_alert_event,
)


class NotificationWorkerTest(unittest.TestCase):
    def test_build_telegram_message_defaults_source_to_joongna(self):
        message = _build_telegram_message(
            {
                "url": "https://web.joongna.com/product/999",
                "price_krw": 500000,
                "fair_price_krw": 550000,
                "target_price_krw": 600000,
            }
        )

        self.assertIn("출처\njoongna", message)
        self.assertNotIn("출처\n정보 없음", message)

    def test_list_alert_events_rejects_invalid_is_read_filter(self):
        with self.assertRaises(ValueError):
            list_alert_events_for_user("boongtol", is_read="invalid-filter")

    @patch(
        "src.notification_worker.list_alert_events_for_user",
        return_value=[
            {
                "id": 11,
                "chip": "M2",
                "screen_inch": 13,
                "read_at": "2026-05-19T10:50:00",
                "analyzed_at": "2026-05-19T10:45:00",
                "created_at": "2026-05-19T10:40:00",
            },
            {
                "id": 12,
                "chip": "",
                "screen_inch": 0,
                "read_at": "2026-05-19T10:52:00",
                "analyzed_at": "2026-05-19T10:46:00",
                "created_at": "2026-05-19T10:41:00",
            },
            {
                "id": 13,
                "chip": "M1",
                "screen_inch": 13,
                "read_at": "2026-05-19T10:53:00",
                "analyzed_at": "2026-05-19T10:47:00",
                "created_at": "2026-05-19T10:42:00",
            },
        ],
    )
    def test_grouped_read_alerts_are_grouped_by_chip_then_screen(self, mock_list_alerts):
        grouped = list_grouped_read_alert_events_for_user("boongtol")

        self.assertEqual(list(grouped.keys()), ["M1", "M2", "기타"])
        self.assertIn("13", grouped["M1"])
        self.assertEqual(grouped["M1"]["13"][0]["id"], 13)
        self.assertEqual(grouped["M2"]["13"][0]["id"], 11)
        self.assertEqual(grouped["기타"]["기타"][0]["id"], 12)
        mock_list_alerts.assert_called_once_with(
            user_id="boongtol",
            limit=500,
            is_read="1",
            exclude_read_archive_cleared=True,
        )

    def test_build_telegram_message_uses_alert_feed_wording(self):
        message = _build_telegram_message(
            {
                "source": "joongna",
                "title": "M2 맥북에어 16/512",
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
        self.assertIn("게시글 제목\nM2 맥북에어 16/512", message)
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
        self.assertIn("알림 유형\n정식 알림", message)
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
            "알림 유형\n",
            "게시글 제목\n",
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

    def test_build_telegram_message_displays_fraud_probability(self):
        message = _build_telegram_message(
            {
                "source": "joongna",
                "title": "사기 확률 표시 테스트",
                "url": "https://web.joongna.com/product/1002",
                "fraud_probability": 0.755,
                "fraud_probability_label": "HIGH",
            }
        )

        self.assertIn("사기 가능성\n높음 (76%)", message)

    def test_build_telegram_message_marks_refresh_based_alerts(self):
        message = _build_telegram_message(
            {
                "source": "joongna",
                "title": "끌올된 매물",
                "url": "https://web.joongna.com/product/2001",
                "trigger_reason": "sort_date_changed",
                "risk_level": "LOW",
                "risk_keywords": "[]",
                "trade_type_flags": {
                    "is_exchange": False,
                    "is_free": False,
                    "is_suspicious": False,
                },
            }
        )

        self.assertIn("특이사항\n끌올된 정보를 사용한 알림입니다", message)

    def test_build_telegram_message_keeps_refresh_notice_for_condition_change_notice(self):
        message = _build_telegram_message(
            {
                "source": "umtp_notice",
                "title": "조건 변경 사이 후보",
                "url": "https://web.joongna.com/product/2002",
                "trigger_reason": "condition_change_candidate_notice",
                "message": "조건 변경 후보\n끌올된 정보를 사용한 알림입니다",
                "risk_level": "LOW",
                "risk_keywords": "[]",
            }
        )

        self.assertIn("특이사항\n끌올된 정보를 사용한 알림입니다", message)

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

    def test_send_alert_event_scores_missing_fraud_probability_before_telegram(self):
        class FakeCursor:
            def close(self):
                pass

        class FakeConnection:
            def cursor(self, dictionary=False):
                return FakeCursor()

            def is_connected(self):
                return True

            def close(self):
                pass

        score = {
            "fraud_probability": 0.755,
            "fraud_probability_label": "HIGH",
            "fraud_model_version": "fraud-logreg-tfidf-v2",
            "fraud_scored_at": "2026-07-04 08:30:00",
            "fraud_probability_v1": 0.455,
            "fraud_probability_label_v1": "MEDIUM",
            "fraud_model_version_v1": "fraud-logreg-v1",
            "fraud_scored_at_v1": "2026-07-04 08:30:00",
            "fraud_probability_v2": 0.755,
            "fraud_probability_label_v2": "HIGH",
            "fraud_model_version_v2": "fraud-logreg-tfidf-v2",
            "fraud_scored_at_v2": "2026-07-04 08:30:00",
        }

        with patch(
            "src.notification_worker.resolve_user_alert_delivery_policy",
            return_value={
                "enabled": True,
                "telegram_chat_id": "123456",
                "allow_global_fallback": False,
            },
        ):
            with patch("src.notification_worker.get_connection", return_value=FakeConnection()):
                with patch("src.notification_worker.score_alert_fraud_probability_comparison", return_value=score) as mock_score:
                    with patch("src.notification_worker._update_alert_event_fraud_probability", return_value=True) as mock_update_score:
                        with patch("src.notification_worker._send_fcm_to_user", return_value={"sent": 0, "failed": 0, "attempted": 0, "reason": "no_active_push_tokens"}) as mock_send_fcm:
                            with patch("src.notification_worker._telegram_configured", return_value=True):
                                with patch("src.notification_worker._fetch_listing_image_url_by_product_id", return_value=None):
                                    with patch("src.notification_worker.send_telegram_alert", return_value=True) as mock_send_telegram:
                                        with patch("src.notification_worker.mark_alert_event_sent"):
                                            result = send_alert_event(
                                                {
                                                    "id": 31,
                                                    "user_id": "boongtol",
                                                    "product_id": "1002",
                                                    "title": "사기 확률 표시 테스트",
                                                    "fraud_probability": None,
                                                }
                                            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        mock_score.assert_called_once()
        mock_update_score.assert_called_once_with(31, score)
        self.assertEqual(mock_send_fcm.call_args.args[1].get("fraud_probability_label"), "HIGH")
        self.assertEqual(mock_send_fcm.call_args.args[1].get("fraud_probability_label_v1"), "MEDIUM")
        self.assertEqual(mock_send_fcm.call_args.args[1].get("fraud_probability_label_v2"), "HIGH")
        self.assertIn("사기 가능성\n높음 (76%)", mock_send_telegram.call_args.args[0])

    def test_push_payload_uses_comparison_text_for_existing_app_field(self):
        _title, body, data = _build_push_notification_payload(
            {
                "id": 41,
                "title": "사기 확률 비교 테스트",
                "body_excerpt": "본문",
                "fraud_probability": 0.755,
                "fraud_probability_label": "HIGH",
                "fraud_probability_v1": 0.455,
                "fraud_probability_label_v1": "MEDIUM",
                "fraud_probability_v2": 0.755,
                "fraud_probability_label_v2": "HIGH",
            }
        )

        self.assertEqual(
            data.get("fraud_probability_text"),
            "v1 주의 (46%) · v2 높음 (76%) · 차이 +30%p",
        )
        self.assertIn("사기 가능성 v1 주의 (46%) · v2 높음 (76%) · 차이 +30%p", body)

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

    def test_send_alert_event_resolves_product_id_from_url_for_image_lookup(self):
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
                    with patch("src.notification_worker._fetch_listing_image_url_by_product_id", return_value="https://img.joongna.com/p/228752931.jpg") as mock_fetch_image:
                        with patch("src.notification_worker.send_telegram_alert", return_value=True) as mock_send_telegram:
                            with patch("src.notification_worker.mark_alert_event_sent"):
                                result = send_alert_event(
                                    {
                                        "id": 401,
                                        "user_id": "boongtol",
                                        "url": "https://web.joongna.com/product/228752931",
                                        "title": "URL 이미지 추출 테스트",
                                    }
                                )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        mock_fetch_image.assert_called_once_with("228752931")
        self.assertEqual(
            mock_send_telegram.call_args.kwargs.get("image_url"),
            "https://img.joongna.com/p/228752931.jpg",
        )

    def test_send_alert_event_prefers_seen_product_image_over_existing_alert_image(self):
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
                    with patch("src.notification_worker._fetch_listing_image_url_by_product_id", return_value="https://img.joongna.com/p/2002-seen.jpg"):
                        with patch("src.notification_worker.send_telegram_alert", return_value=True) as mock_send_telegram:
                            with patch("src.notification_worker.mark_alert_event_sent"):
                                result = send_alert_event(
                                    {
                                        "id": 302,
                                        "user_id": "boongtol",
                                        "product_id": "2002",
                                        "title": "이미지 우선순위 테스트",
                                        "listing_image_url": "https://old.example.com/old.jpg",
                                    }
                                )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(
            mock_send_telegram.call_args.kwargs.get("image_url"),
            "https://img.joongna.com/p/2002-seen.jpg",
        )

    def test_send_alert_event_uses_seen_product_title_when_alert_title_missing(self):
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
                    with patch("src.notification_worker._fetch_listing_image_url_by_product_id", return_value=None):
                        with patch("src.notification_worker._fetch_listing_title_by_product_id", return_value="DB 저장 제목") as mock_fetch_title:
                            with patch("src.notification_worker.send_telegram_alert", return_value=True) as mock_send_telegram:
                                with patch("src.notification_worker.mark_alert_event_sent"):
                                    result = send_alert_event(
                                        {
                                            "id": 303,
                                            "user_id": "boongtol",
                                            "product_id": "303",
                                        }
                                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        mock_fetch_title.assert_called_once_with("303")
        self.assertIn("게시글 제목\nDB 저장 제목", mock_send_telegram.call_args.args[0])

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

    def test_dispatch_alert_event_immediately_prefers_db_payload_and_merges_fallback(self):
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
                with patch(
                    "src.notification_worker.get_alert_event_by_id",
                    return_value={
                        "id": 102,
                        "user_id": "boongtol",
                        "product_id": "228752931",
                    },
                ) as mock_get_alert:
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
        self.assertEqual(mock_get_alert.call_count, 1)
        self.assertEqual(mock_send_alert.call_count, 1)
        sent_payload = mock_send_alert.call_args.args[0]
        self.assertEqual(sent_payload.get("id"), 102)
        self.assertEqual(sent_payload.get("user_id"), "boongtol")
        self.assertEqual(sent_payload.get("product_id"), "228752931")
        self.assertEqual(sent_payload.get("title"), "테스트")


if __name__ == "__main__":
    unittest.main()
