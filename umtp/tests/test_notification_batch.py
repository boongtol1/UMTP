import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import notification_worker as worker


def alert(alert_id, user_id):
    return {"id": alert_id, "user_id": user_id, "title": f"listing-{alert_id}"}


class NotificationBatchTest(unittest.TestCase):
    def test_personalized_messages_share_one_send_each_call(self):
        alerts = [alert(1, "u1"), alert(2, "u2")]
        policies = {"u1": {"enabled": True}, "u2": {"enabled": True}}
        tokens = {
            "u1": [{"id": 11, "token": "token-1"}],
            "u2": [{"id": 22, "token": "token-2"}],
        }
        firebase = Mock()
        firebase.Message.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
        firebase.Notification.side_effect = lambda **kwargs: kwargs
        firebase.AndroidConfig.side_effect = lambda **kwargs: kwargs
        firebase.send_each.return_value = SimpleNamespace(responses=[
            SimpleNamespace(success=True), SimpleNamespace(success=True),
        ])
        with patch.object(worker, "messaging", firebase), \
             patch.object(worker, "_fcm_configured", return_value=True), \
             patch.object(worker, "_ensure_firebase_initialized", return_value=(True, None)), \
             patch.object(worker, "_persist_batch_push_token_results") as persist:
            outcomes = worker._send_fcm_batch(alerts, policies, tokens)
        firebase.send_each.assert_called_once()
        messages = firebase.send_each.call_args.args[0]
        self.assertEqual([message.token for message in messages], ["token-1", "token-2"])
        self.assertEqual([message.notification["title"] for message in messages], ["listing-1", "listing-2"])
        self.assertEqual([outcomes[1]["sent"], outcomes[2]["sent"]], [1, 1])
        persist.assert_called_once_with([11, 22], [])

    def test_batches_are_capped_at_500_and_all_submit_before_telegram(self):
        alerts = [alert(index, f"u{index}") for index in range(1, 502)]
        policies = {row["user_id"]: {"enabled": True} for row in alerts}
        tokens = {row["user_id"]: [{"id": row["id"], "token": f"t{row['id']}"}] for row in alerts}
        firebase = Mock()
        firebase.Message.side_effect = lambda **kwargs: kwargs
        firebase.send_each.side_effect = lambda messages: SimpleNamespace(
            responses=[SimpleNamespace(success=True) for _ in messages],
        )
        with patch.object(worker, "messaging", firebase), \
             patch.object(worker, "_fcm_configured", return_value=True), \
             patch.object(worker, "_ensure_firebase_initialized", return_value=(True, None)), \
             patch.object(worker, "_persist_batch_push_token_results"), \
             patch.dict(os.environ, {"UMTP_FCM_BATCH_SIZE": "500"}):
            worker._send_fcm_batch(alerts, policies, tokens)
        self.assertEqual([len(item.args[0]) for item in firebase.send_each.call_args_list], [500, 1])

        order = []
        with patch.object(worker, "_claim_alert_events_for_batch", return_value=alerts[:2]), \
             patch.object(worker, "_fetch_batch_push_context", return_value=(policies, tokens)), \
             patch.object(worker, "_send_fcm_batch", side_effect=lambda *args: (
                 order.append("fcm") or {1: {}, 2: {}}
             )), \
             patch.object(worker, "send_alert_event", side_effect=lambda row, **kwargs: (
                 order.append(f"telegram-{row['id']}") or
                 {"ok": True, "alert_id": row["id"], "status": "sent"}
             )):
            worker.dispatch_alert_events_immediately([1, 2])
        self.assertEqual(order, ["fcm", "telegram-1", "telegram-2"])

    def test_partial_results_map_to_the_correct_users_and_disable_dead_token(self):
        alerts = [alert(1, "u1"), alert(2, "u2")]
        policies = {"u1": {"enabled": True}, "u2": {"enabled": False}}
        tokens = {
            "u1": [{"id": 10, "token": "ok"}, {"id": 11, "token": "dead"}],
            "u2": [{"id": 20, "token": "must-not-send"}],
        }
        firebase = Mock()
        firebase.Message.side_effect = lambda **kwargs: kwargs
        firebase.send_each.return_value = SimpleNamespace(responses=[
            SimpleNamespace(success=True),
            SimpleNamespace(success=False, exception=RuntimeError("unregistered")),
        ])
        with patch.object(worker, "messaging", firebase), \
             patch.object(worker, "_fcm_configured", return_value=True), \
             patch.object(worker, "_ensure_firebase_initialized", return_value=(True, None)), \
             patch.object(worker, "_persist_batch_push_token_results") as persist:
            outcomes = worker._send_fcm_batch(alerts, policies, tokens)
        self.assertEqual([message["token"] for message in firebase.send_each.call_args.args[0]], ["ok", "dead"])
        self.assertEqual(outcomes[1]["sent"], 1)
        self.assertEqual(outcomes[1]["failed"], 1)
        self.assertEqual(outcomes[2]["attempted"], 0)
        self.assertEqual(outcomes[2]["reason"], "alerts_disabled")
        persist.assert_called_once_with([10], [(11, "unregistered")])

    def test_batch_claim_uses_one_transaction_and_only_pending_rows(self):
        cursor = Mock()
        cursor.fetchall.side_effect = [[alert(2, "u2"), alert(1, "u1")]]
        connection = Mock()
        connection.cursor.return_value = cursor
        with patch.object(worker, "get_connection", return_value=connection):
            rows = worker._claim_alert_events_for_batch([1, 2])
        self.assertEqual([row["id"] for row in rows], [1, 2])
        self.assertIn("status = 'pending' FOR UPDATE", cursor.execute.call_args_list[0].args[0])
        self.assertIn("send_attempts", cursor.execute.call_args_list[1].args[0])
        connection.commit.assert_called_once()

    def test_background_worker_uses_batch_dispatch(self):
        rows = [alert(1, "u1"), alert(2, "u2")]
        stats = {"fetched": 2, "sent": 2, "app_only": 0, "failed": 0, "results": []}
        with patch.object(worker, "get_pending_alert_events", return_value=rows), \
             patch.object(worker, "dispatch_alert_events_immediately", return_value=stats) as dispatch:
            result = worker.process_pending_alert_events(limit=20)
        dispatch.assert_called_once_with([1, 2], fallback_alerts={1: rows[0], 2: rows[1]})
        self.assertEqual(result["fetched"], 2)

    def test_one_telegram_exception_does_not_stop_later_alerts(self):
        rows = [alert(1, "u1"), alert(2, "u2")]
        policies = {"u1": {"enabled": True}, "u2": {"enabled": True}}
        success = {"ok": True, "alert_id": 2, "status": "sent"}
        with patch.object(worker, "_claim_alert_events_for_batch", return_value=rows), \
             patch.object(worker, "_fetch_batch_push_context", return_value=(policies, {})), \
             patch.object(worker, "_send_fcm_batch", return_value={1: {}, 2: {}}), \
             patch.object(worker, "send_alert_event", side_effect=[RuntimeError("telegram failed"), success]) as send, \
             patch.object(worker, "mark_alert_event_failed") as failed:
            stats = worker.dispatch_alert_events_immediately([1, 2])
        self.assertEqual(send.call_count, 2)
        failed.assert_called_once_with(1, "telegram failed")
        self.assertEqual([row["status"] for row in stats["results"]], ["failed", "sent"])

    def test_precomputed_push_result_prevents_duplicate_fcm_send(self):
        row = alert(1, "u1")
        policy = {"enabled": True, "telegram_chat_id": None, "allow_global_fallback": False}
        with patch.object(worker, "_send_fcm_to_user") as single_send, \
             patch.object(worker, "_enrich_alert_for_display"), \
             patch.object(worker, "_ensure_alert_fraud_probability_for_delivery"), \
             patch.object(worker, "_telegram_configured", return_value=False), \
             patch.object(worker, "mark_alert_event_sent"):
            result = worker.send_alert_event(
                row,
                push_result={"sent": 1, "failed": 0, "attempted": 1, "reason": "fcm_sent"},
                delivery_policy=policy,
            )
        single_send.assert_not_called()
        self.assertEqual(result["status"], "sent")


if __name__ == "__main__":
    unittest.main()
