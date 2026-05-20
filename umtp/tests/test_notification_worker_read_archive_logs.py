import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.notification_worker import (  # noqa: E402
    clear_selected_read_alert_events_for_user,
    mark_alert_event_read_for_user,
    mark_all_alert_events_read_for_user,
)


class _ReadArchiveCursor:
    def __init__(
        self,
        *,
        fetchone_rows=None,
        fetchall_rows=None,
        rowcount_map=None,
        raise_on_tokens=None,
    ):
        self._fetchone_rows = list(fetchone_rows or [])
        self._fetchall_rows = list(fetchall_rows or [])
        self._rowcount_map = dict(rowcount_map or {})
        self._raise_on_tokens = dict(raise_on_tokens or {})
        self.executed = []
        self.rowcount = 0
        self.closed = False

    def execute(self, query, params=None):
        normalized = " ".join((query or "").lower().split())
        self.executed.append((normalized, params))

        for token, exc in self._raise_on_tokens.items():
            if token in normalized:
                raise exc

        self.rowcount = 0
        for token, value in self._rowcount_map.items():
            if token in normalized:
                self.rowcount = int(value)
                break

    def fetchone(self):
        if self._fetchone_rows:
            return self._fetchone_rows.pop(0)
        return None

    def fetchall(self):
        if self._fetchall_rows:
            return self._fetchall_rows.pop(0)
        return []

    def close(self):
        self.closed = True


class _ReadArchiveConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commit_count = 0

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.commit_count += 1

    def is_connected(self):
        return True

    def close(self):
        return None


class NotificationWorkerReadArchiveLogsTest(unittest.TestCase):
    def test_mark_single_read_inserts_action_log_row(self):
        cursor = _ReadArchiveCursor(
            fetchone_rows=[{"id": 101, "is_read": 1, "read_at": "2026-05-20 18:00:00"}],
            rowcount_map={"update alert_events set is_read = 1": 1},
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_alert_event_read_for_user(user_id="boongtol", alert_event_id=101)

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("already_read"))
        self.assertEqual(connection.commit_count, 1)

        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_read_archive_events" in query
        ]
        self.assertEqual(len(insert_params), 1)
        params = insert_params[0]
        self.assertEqual(params[0], "boongtol")
        self.assertEqual(params[1], 101)
        self.assertEqual(params[2], "mark_read_single")
        self.assertEqual(params[3], 1)
        self.assertEqual(params[4], 1)
        self.assertEqual(params[7], "marked_read")

    def test_clear_selected_read_archive_inserts_action_log_row(self):
        cursor = _ReadArchiveCursor(
            fetchall_rows=[
                [{"id": 11, "is_read_archive_cleared": 0}],
                [],
            ],
            rowcount_map={"update alert_events set is_read_archive_cleared = 1": 1},
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = clear_selected_read_alert_events_for_user(
                user_id="boongtol",
                alert_event_ids=[11, 12],
            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("requested_count"), 2)
        self.assertEqual(result.get("cleared_count"), 1)
        self.assertEqual(result.get("not_found_ids"), [12])
        self.assertEqual(connection.commit_count, 1)

        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_read_archive_events" in query
        ]
        self.assertGreaterEqual(len(insert_params), 2)

        summary_params = next((p for p in insert_params if p[2] == "clear_read_archive_selected"), None)
        item_params = next((p for p in insert_params if p[2] == "clear_read_archive_selected_item"), None)

        self.assertIsNotNone(summary_params)
        self.assertIsNotNone(item_params)

        self.assertEqual(summary_params[0], "boongtol")
        self.assertEqual(summary_params[3], 2)
        self.assertEqual(summary_params[4], 1)
        self.assertEqual(summary_params[5], 0)
        self.assertEqual(summary_params[6], "[12]")
        self.assertEqual(summary_params[7], "clear_selected_completed")

        self.assertEqual(item_params[0], "boongtol")
        self.assertEqual(item_params[1], 11)
        self.assertEqual(item_params[3], 1)
        self.assertEqual(item_params[4], 1)
        self.assertEqual(item_params[7], "clear_selected_item")

    def test_mark_all_read_succeeds_even_when_log_insert_fails(self):
        cursor = _ReadArchiveCursor(
            rowcount_map={"update alert_events set is_read = 1": 3},
            raise_on_tokens={
                "insert into alert_read_archive_events": RuntimeError("temporary insert failure"),
            },
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_all_alert_events_read_for_user(user_id="boongtol")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("updated_count"), 3)
        self.assertEqual(connection.commit_count, 1)

    def test_mark_single_read_logs_alert_detail_fields(self):
        cursor = _ReadArchiveCursor(
            fetchone_rows=[{"id": 101, "is_read": 1, "read_at": "2026-05-20 18:00:00"}],
            fetchall_rows=[
                [
                    {
                        "id": 101,
                        "trigger_reason": "new_product",
                        "source": "joongna",
                        "url": "https://web.joongna.com/product/101",
                        "title": "맥북에어 m2 16/512",
                        "product_id": "101",
                        "sort_date": "2026-05-20 17:58:00",
                        "product_type": "MacBook Air",
                        "chip": "M2",
                        "screen_inch": 13,
                        "ram_gb": 16,
                        "ssd_gb": 512,
                        "price_krw": 980000,
                        "fair_price_krw": 1200000,
                        "target_price_krw": 1100000,
                        "drop_rate_percent": 18.33,
                        "alert_drop_rate_percent": 8.33,
                        "alert_price_direction": "BELOW_OR_EQUAL",
                        "risk_level": "HIGH",
                        "risk_score": 82,
                        "risk_keywords": '["교환"]',
                        "is_exchange_post": 1,
                        "trade_type": "exchange",
                        "body_excerpt": "교환 제안 있음",
                        "body_text": "교환 제안 있음 본문",
                        "analyzed_at": "2026-05-20 17:59:00",
                        "message": "테스트 메시지",
                        "status": "pending",
                        "read_at": "2026-05-20 18:00:00",
                        "created_at": "2026-05-20 17:59:10",
                        "sent_at": None,
                        "updated_at": "2026-05-20 18:00:00",
                    }
                ]
            ],
            rowcount_map={"update alert_events set is_read = 1": 1},
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            with patch(
                "src.notification_worker._fetch_listing_image_url_by_product_id",
                return_value="https://img.joongna.com/p/101.jpg",
            ):
                result = mark_alert_event_read_for_user(user_id="boongtol", alert_event_id=101)

        self.assertTrue(result.get("ok"))
        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_read_archive_events" in query
        ]
        self.assertEqual(len(insert_params), 1)
        params = insert_params[0]
        self.assertEqual(params[9], "new_product")
        self.assertEqual(params[11], "joongna")
        self.assertEqual(params[14], "맥북에어 m2 16/512")
        self.assertEqual(params[22], 980000)
        self.assertEqual(params[28], "HIGH")
        self.assertEqual(params[29], "위험")
        self.assertEqual(params[31], "교환")
        self.assertEqual(params[33], True)
        self.assertEqual(params[34], "교환, 허위/의심")
        self.assertIn("위험도 위험", params[35])


if __name__ == "__main__":
    unittest.main()
