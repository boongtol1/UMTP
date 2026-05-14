import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.analysis_jobs import (  # noqa: E402
    create_analysis_job,
    get_pending_analysis_jobs,
    mark_analysis_job_done,
    mark_analysis_job_failed,
    mark_analysis_job_started,
)


class _FakeCursor:
    def __init__(self, *, rows=None, row=None, rowcount=1, lastrowid=1):
        self.rows = rows or []
        self.row = row
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.row

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class AnalysisJobsTest(unittest.TestCase):
    def test_create_analysis_job_dedup(self):
        with patch(
            "src.analysis_jobs.find_recent_duplicate_job",
            return_value={"id": 7, "status": "pending"},
        ):
            result = create_analysis_job(
                product_id="1001",
                url="https://web.joongna.com/product/1001",
                watch_rule_id=1,
                trigger_reason="price_changed",
            )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("created"))
        self.assertEqual(result.get("job_id"), 7)

    def test_create_analysis_job_insert(self):
        fake_cursor = _FakeCursor(lastrowid=11)
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.analysis_jobs.find_recent_duplicate_job", return_value=None):
            with patch("src.analysis_jobs.get_connection", return_value=fake_connection):
                result = create_analysis_job(
                    product_id="1002",
                    url="https://web.joongna.com/product/1002",
                    user_id="boongtol",
                    watch_rule_id=2,
                    trigger_reason="new_product",
                )

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("job_id"), 11)
        self.assertIn("INSERT INTO analysis_jobs", fake_cursor.executed[0][0])

    def test_get_pending_analysis_jobs(self):
        fake_cursor = _FakeCursor(rows=[{"id": 1}, {"id": 2}])
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.analysis_jobs.get_connection", return_value=fake_connection):
            rows = get_pending_analysis_jobs(limit=10)

        self.assertEqual(len(rows), 2)
        self.assertIn("status = 'pending'", fake_cursor.executed[0][0])
        self.assertIn("ORDER BY created_at ASC", fake_cursor.executed[0][0])

    def test_mark_analysis_job_status_updates(self):
        fake_cursor = _FakeCursor(rowcount=1)
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.analysis_jobs.get_connection", return_value=fake_connection):
            self.assertTrue(mark_analysis_job_started(3))
            self.assertTrue(mark_analysis_job_done(3))
            self.assertTrue(mark_analysis_job_failed(3, "boom"))

        self.assertIn("status = 'processing'", fake_cursor.executed[0][0])
        self.assertIn("status = 'done'", fake_cursor.executed[1][0])
        self.assertIn("status = 'failed'", fake_cursor.executed[2][0])


if __name__ == "__main__":
    unittest.main()
