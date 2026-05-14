import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.notification_worker import process_pending_alert_events, send_alert_event  # noqa: E402


class NotificationWorkerTest(unittest.TestCase):
    def test_send_alert_event_app_only_when_telegram_not_configured(self):
        with patch("src.notification_worker._telegram_configured", return_value=False):
            with patch("src.notification_worker.mark_alert_event_app_only") as mock_mark_app_only:
                result = send_alert_event(
                    {
                        "id": 1,
                        "title": "테스트",
                        "message": "테스트 메시지",
                    }
                )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "app_only")
        self.assertEqual(mock_mark_app_only.call_count, 1)

    def test_send_alert_event_sent_when_telegram_success(self):
        with patch("src.notification_worker._telegram_configured", return_value=True):
            with patch("src.notification_worker.send_telegram_alert", return_value=True):
                with patch("src.notification_worker.mark_alert_event_sent") as mock_mark_sent:
                    result = send_alert_event(
                        {
                            "id": 2,
                            "title": "테스트",
                            "message": "테스트 메시지",
                        }
                    )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(mock_mark_sent.call_count, 1)

    def test_process_pending_alert_events_continues_after_failure(self):
        pending_alerts = [
            {"id": 11, "message": "A"},
            {"id": 12, "message": "B"},
        ]

        def _send_side_effect(alert):
            if alert.get("id") == 11:
                raise RuntimeError("send failed")
            return {"ok": True, "alert_id": 12, "status": "sent"}

        with patch("src.notification_worker.get_pending_alert_events", return_value=pending_alerts):
            with patch("src.notification_worker.mark_alert_event_sending"):
                with patch("src.notification_worker.send_alert_event", side_effect=_send_side_effect):
                    with patch("src.notification_worker.mark_alert_event_failed") as mock_mark_failed:
                        stats = process_pending_alert_events(limit=20)

        self.assertEqual(stats.get("fetched"), 2)
        self.assertEqual(stats.get("failed"), 1)
        self.assertEqual(stats.get("sent"), 1)
        self.assertEqual(mock_mark_failed.call_count, 1)


if __name__ == "__main__":
    unittest.main()
