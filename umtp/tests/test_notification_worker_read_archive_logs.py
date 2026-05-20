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
            fetchall_rows=[[{"id": 11, "is_read_archive_cleared": 0}]],
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
        self.assertEqual(len(insert_params), 1)
        params = insert_params[0]
        self.assertEqual(params[0], "boongtol")
        self.assertEqual(params[2], "clear_read_archive_selected")
        self.assertEqual(params[3], 2)
        self.assertEqual(params[4], 1)
        self.assertEqual(params[5], 0)
        self.assertEqual(params[6], "[12]")
        self.assertEqual(params[7], "clear_selected_completed")

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


if __name__ == "__main__":
    unittest.main()
