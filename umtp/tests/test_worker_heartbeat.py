import json
import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import src.worker_heartbeat as worker_heartbeat  # noqa: E402


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self):
        self._cursor = _FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True

    def is_connected(self):
        return True


class WorkerHeartbeatTest(unittest.TestCase):
    def setUp(self):
        worker_heartbeat._LAST_HEARTBEAT_AT.clear()

    def test_first_write_sends_upsert(self):
        fake_connection = _FakeConnection()
        with patch("src.worker_heartbeat.get_connection", return_value=fake_connection):
            result = worker_heartbeat.write_worker_heartbeat(
                "umtp-polling",
                status="ok",
                detail="groups=1 calls=1 fetched=0 alerts=0",
                stats={"fetched_count": 0},
                min_interval_seconds=60,
            )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("skipped"))
        self.assertTrue(fake_connection.committed)
        self.assertEqual(len(fake_connection._cursor.executed), 1)
        query, params = fake_connection._cursor.executed[0]
        self.assertIn("worker_heartbeats", query)
        self.assertEqual(params[0], "umtp-polling")

    def test_within_interval_skips_write(self):
        fake_connection = _FakeConnection()
        with patch("src.worker_heartbeat.get_connection", return_value=fake_connection):
            worker_heartbeat.write_worker_heartbeat(
                "umtp-analysis-worker",
                status="ok",
                stats={"done": 1},
                min_interval_seconds=60,
            )

            result = worker_heartbeat.write_worker_heartbeat(
                "umtp-analysis-worker",
                status="ok",
                stats={"done": 2},
                min_interval_seconds=60,
            )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("skipped"))
        self.assertEqual(len(fake_connection._cursor.executed), 1)

    def test_force_writes_even_within_interval(self):
        fake_connection = _FakeConnection()
        with patch("src.worker_heartbeat.get_connection", return_value=fake_connection):
            worker_heartbeat.write_worker_heartbeat(
                "umtp-polling",
                status="ok",
                stats={"fetched_count": 1},
                min_interval_seconds=60,
            )
            result = worker_heartbeat.write_worker_heartbeat(
                "umtp-polling",
                status="ok",
                stats={"fetched_count": 2},
                min_interval_seconds=60,
                force=True,
            )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("skipped"))
        self.assertEqual(len(fake_connection._cursor.executed), 2)

    def test_stats_payload_excludes_results_field(self):
        fake_connection = _FakeConnection()
        with patch("src.worker_heartbeat.get_connection", return_value=fake_connection):
            worker_heartbeat.write_worker_heartbeat(
                "umtp-analysis-worker",
                status="degraded",
                stats={
                    "fetched": 5,
                    "results": [{"ok": True}, {"ok": False}],
                },
                min_interval_seconds=60,
            )

        _, params = fake_connection._cursor.executed[0]
        stats_payload = params[3]
        parsed = json.loads(stats_payload)
        self.assertEqual(parsed.get("fetched"), 5)
        self.assertNotIn("results", parsed)


if __name__ == "__main__":
    unittest.main()
