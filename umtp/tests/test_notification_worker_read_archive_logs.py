import os
import sys
import json
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
                if isinstance(exc, list):
                    if not exc:
                        continue
                    next_exc = exc.pop(0)
                    if next_exc is None:
                        continue
                    raise next_exc
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
        self.rollback_count = 0

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

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

    def test_mark_single_read_recovers_when_read_columns_missing(self):
        cursor = _ReadArchiveCursor(
            fetchone_rows=[{"id": 101, "is_read": 1, "read_at": "2026-05-20 18:00:00"}],
            rowcount_map={"update alert_events set is_read = 1": 1},
            raise_on_tokens={
                "update alert_events set is_read = 1": [RuntimeError("Unknown column 'read_at' in 'field list'")],
            },
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_alert_event_read_for_user(user_id="boongtol", alert_event_id=101)

        self.assertTrue(result.get("ok"))
        executed_queries = [query for query, _ in cursor.executed]
        self.assertTrue(any("alter table alert_events add column is_read" in query for query in executed_queries))
        self.assertTrue(any("alter table alert_events add column read_at" in query for query in executed_queries))

    def test_clear_selected_read_archive_inserts_action_log_row(self):
        cursor = _ReadArchiveCursor(
            fetchall_rows=[
                [{"id": 11, "is_read_archive_cleared": 0}],
                [
                    {
                        "id": 11,
                        "user_id": "boongtol",
                        "watch_rule_id": 7,
                        "analysis_job_id": 51,
                        "trigger_reason": "new_product",
                        "source": "joongna",
                        "url": "https://web.joongna.com/product/11",
                        "title": "맥북에어 m2",
                        "product_id": "11",
                        "sort_date": "2026-05-20 17:00:00",
                        "product_type": "MacBook Air",
                        "chip": "M2",
                        "screen_inch": 13,
                        "ram_gb": 8,
                        "ssd_gb": 256,
                        "price_krw": 900000,
                        "fair_price_krw": 1050000,
                        "target_price_krw": 980000,
                        "drop_rate_percent": 14.29,
                        "alert_drop_rate_percent": 6.67,
                        "alert_price_direction": "BELOW_OR_EQUAL",
                        "risk_level": "LOW",
                        "risk_score": 10,
                        "risk_keywords": "[]",
                        "is_exchange_post": 0,
                        "trade_type": "sale",
                        "body_excerpt": "본문",
                        "body_text": "본문",
                        "analyzed_at": "2026-05-20 17:01:00",
                        "message": "조건 만족",
                        "status": "sent",
                        "read_at": "2026-05-20 17:03:00",
                        "created_at": "2026-05-20 17:01:10",
                        "sent_at": "2026-05-20 17:01:20",
                        "updated_at": "2026-05-20 17:03:00",
                    }
                ],
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
        self.assertEqual(item_params[3], 2)
        self.assertEqual(item_params[4], 1)
        self.assertEqual(item_params[5], 0)
        self.assertEqual(item_params[6], "[12]")
        self.assertEqual(item_params[7], "clear_selected_item")

    def test_mark_all_read_rolls_back_when_log_insert_fails(self):
        cursor = _ReadArchiveCursor(
            rowcount_map={"update alert_events set is_read = 1": 3},
            raise_on_tokens={
                "insert into alert_read_archive_events": RuntimeError("temporary insert failure"),
            },
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_all_alert_events_read_for_user(user_id="boongtol")

        self.assertFalse(result.get("ok"))
        self.assertIn("mark_read_all_failed", result.get("reason") or "")
        self.assertEqual(connection.commit_count, 0)
        self.assertEqual(connection.rollback_count, 1)

    def test_mark_all_read_recovers_when_read_columns_missing(self):
        cursor = _ReadArchiveCursor(
            fetchall_rows=[
                [{"id": 11}, {"id": 12}],
                [],
            ],
            rowcount_map={"update alert_events set is_read = 1": 2},
            raise_on_tokens={
                "update alert_events set is_read = 1": [RuntimeError("Unknown column 'is_read' in 'field list'")],
            },
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_all_alert_events_read_for_user(user_id="boongtol")

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("updated_count"), 2)
        executed_queries = [query for query, _ in cursor.executed]
        self.assertTrue(any("alter table alert_events add column is_read" in query for query in executed_queries))
        self.assertTrue(any("alter table alert_events add column read_at" in query for query in executed_queries))

    def test_mark_single_read_logs_alert_detail_fields(self):
        cursor = _ReadArchiveCursor(
            fetchone_rows=[{"id": 101, "is_read": 1, "read_at": "2026-05-20 18:00:00"}],
            fetchall_rows=[
                [
                    {
                        "id": 101,
                        "user_id": "boongtol",
                        "watch_rule_id": 7,
                        "analysis_job_id": 99,
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
        self.assertEqual(params[31], '["교환"]')
        self.assertEqual(params[33], True)
        self.assertEqual(params[34], "교환, 허위/의심")
        self.assertIn("위험도 위험", params[35])
        payload = json.loads(params[45])
        self.assertEqual(payload["alert_event"]["watch_rule_id"], 7)
        self.assertEqual(payload["alert_event"]["analysis_job_id"], 99)
        self.assertEqual(payload["display_fields"]["alert_condition_label"], "이 가격 이하이면 알림")
        self.assertEqual(payload["display_fields"]["alert_type_label"], "정식 알림")
        self.assertEqual(payload["display_fields"]["alert_risk_label"], "위험")
        self.assertEqual(payload["action_metadata"]["action_type"], "mark_read_single")
        self.assertEqual(payload["action_metadata"]["requested_count"], 1)
        self.assertEqual(payload["action_metadata"]["affected_count"], 1)

    def test_condition_change_candidate_label_is_saved(self):
        cursor = _ReadArchiveCursor(
            fetchone_rows=[{"id": 102, "is_read": 1, "read_at": "2026-05-20 18:10:00"}],
            fetchall_rows=[
                [
                    {
                        "id": 102,
                        "user_id": "boongtol",
                        "watch_rule_id": 1,
                        "analysis_job_id": None,
                        "trigger_reason": "condition_change_candidate_notice",
                        "source": "joongna",
                        "url": "https://web.joongna.com/product/102",
                        "title": "조건 변경 후보",
                        "product_id": "102",
                        "sort_date": "2026-05-20 18:00:00",
                        "product_type": "Mac mini",
                        "chip": "M4",
                        "screen_inch": 0,
                        "ram_gb": 16,
                        "ssd_gb": 256,
                        "price_krw": 1200000,
                        "fair_price_krw": 1300000,
                        "target_price_krw": 1250000,
                        "drop_rate_percent": 7.69,
                        "alert_drop_rate_percent": 3.85,
                        "alert_price_direction": "BELOW_OR_EQUAL",
                        "risk_level": "LOW",
                        "risk_score": 5,
                        "risk_keywords": "[]",
                        "is_exchange_post": 0,
                        "trade_type": "sale",
                        "body_excerpt": "본문",
                        "body_text": "본문",
                        "analyzed_at": "2026-05-20 18:01:00",
                        "message": "참고 후보",
                        "status": "pending",
                        "read_at": "2026-05-20 18:10:00",
                        "created_at": "2026-05-20 18:01:10",
                        "sent_at": None,
                        "updated_at": "2026-05-20 18:10:00",
                    }
                ]
            ],
            rowcount_map={"update alert_events set is_read = 1": 1},
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_alert_event_read_for_user(user_id="boongtol", alert_event_id=102)

        self.assertTrue(result.get("ok"))
        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_read_archive_events" in query
        ]
        self.assertEqual(len(insert_params), 1)
        params = insert_params[0]
        self.assertEqual(params[10], "조건 변경 사이 후보")

    def test_risk_level_medium_maps_to_notice_label(self):
        cursor = _ReadArchiveCursor(
            fetchone_rows=[{"id": 103, "is_read": 1, "read_at": "2026-05-20 18:20:00"}],
            fetchall_rows=[
                [
                    {
                        "id": 103,
                        "user_id": "boongtol",
                        "watch_rule_id": 3,
                        "analysis_job_id": 77,
                        "trigger_reason": "new_product",
                        "source": "joongna",
                        "url": "https://web.joongna.com/product/103",
                        "title": "m2",
                        "product_id": "103",
                        "sort_date": "2026-05-20 18:15:00",
                        "product_type": "MacBook Air",
                        "chip": "M2",
                        "screen_inch": 13,
                        "ram_gb": 8,
                        "ssd_gb": 256,
                        "price_krw": 999000,
                        "fair_price_krw": 1100000,
                        "target_price_krw": 1000000,
                        "drop_rate_percent": 9.18,
                        "alert_drop_rate_percent": 9.09,
                        "alert_price_direction": "BELOW_OR_EQUAL",
                        "risk_level": "MEDIUM",
                        "risk_score": 50,
                        "risk_keywords": '["주의"]',
                        "is_exchange_post": 0,
                        "trade_type": "sale",
                        "body_excerpt": None,
                        "body_text": None,
                        "analyzed_at": "2026-05-20 18:16:00",
                        "message": "ok",
                        "status": "pending",
                        "read_at": "2026-05-20 18:20:00",
                        "created_at": "2026-05-20 18:16:10",
                        "sent_at": None,
                        "updated_at": "2026-05-20 18:20:00",
                    }
                ]
            ],
            rowcount_map={"update alert_events set is_read = 1": 1},
        )
        connection = _ReadArchiveConnection(cursor)

        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_alert_event_read_for_user(user_id="boongtol", alert_event_id=103)

        self.assertTrue(result.get("ok"))
        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_read_archive_events" in query
        ]
        params = insert_params[0]
        self.assertEqual(params[29], "주의")

    def test_bulk_mark_all_writes_per_alert_snapshot_rows(self):
        cursor = _ReadArchiveCursor(
            fetchall_rows=[
                [{"id": 201}, {"id": 202}],
                [
                    {
                        "id": 201,
                        "user_id": "boongtol",
                        "watch_rule_id": 1,
                        "analysis_job_id": 1,
                        "trigger_reason": "new_product",
                        "source": "joongna",
                        "url": "https://web.joongna.com/product/201",
                        "title": "201",
                        "product_id": "201",
                        "sort_date": "2026-05-20 18:00:00",
                        "product_type": "MacBook Air",
                        "chip": "M2",
                        "screen_inch": 13,
                        "ram_gb": 8,
                        "ssd_gb": 256,
                        "price_krw": 900000,
                        "fair_price_krw": 1100000,
                        "target_price_krw": 1000000,
                        "drop_rate_percent": 18.18,
                        "alert_drop_rate_percent": 9.09,
                        "alert_price_direction": "BELOW_OR_EQUAL",
                        "risk_level": "LOW",
                        "risk_score": 10,
                        "risk_keywords": "[]",
                        "is_exchange_post": 0,
                        "trade_type": "sale",
                        "body_excerpt": "a",
                        "body_text": "a",
                        "analyzed_at": "2026-05-20 18:01:00",
                        "message": "a",
                        "status": "pending",
                        "read_at": "2026-05-20 18:10:00",
                        "created_at": "2026-05-20 18:01:10",
                        "sent_at": None,
                        "updated_at": "2026-05-20 18:10:00",
                    },
                    {
                        "id": 202,
                        "user_id": "boongtol",
                        "watch_rule_id": 2,
                        "analysis_job_id": 2,
                        "trigger_reason": "new_product",
                        "source": "joongna",
                        "url": "https://web.joongna.com/product/202",
                        "title": "202",
                        "product_id": "202",
                        "sort_date": "2026-05-20 18:02:00",
                        "product_type": "MacBook Air",
                        "chip": "M2",
                        "screen_inch": 13,
                        "ram_gb": 8,
                        "ssd_gb": 256,
                        "price_krw": 910000,
                        "fair_price_krw": 1110000,
                        "target_price_krw": 1010000,
                        "drop_rate_percent": 18.02,
                        "alert_drop_rate_percent": 9.01,
                        "alert_price_direction": "BELOW_OR_EQUAL",
                        "risk_level": "LOW",
                        "risk_score": 12,
                        "risk_keywords": "[]",
                        "is_exchange_post": 0,
                        "trade_type": "sale",
                        "body_excerpt": "b",
                        "body_text": "b",
                        "analyzed_at": "2026-05-20 18:03:00",
                        "message": "b",
                        "status": "pending",
                        "read_at": "2026-05-20 18:10:00",
                        "created_at": "2026-05-20 18:03:10",
                        "sent_at": None,
                        "updated_at": "2026-05-20 18:10:00",
                    },
                ],
            ],
            rowcount_map={"update alert_events set is_read = 1": 2},
        )
        connection = _ReadArchiveConnection(cursor)
        with patch("src.notification_worker.get_connection", return_value=connection):
            result = mark_all_alert_events_read_for_user(user_id="boongtol")

        self.assertTrue(result.get("ok"))
        insert_params = [
            params
            for query, params in cursor.executed
            if "insert into alert_read_archive_events" in query
        ]
        item_params = [p for p in insert_params if p[2] == "mark_read_all_item"]
        self.assertEqual(len(item_params), 2)


if __name__ == "__main__":
    unittest.main()
