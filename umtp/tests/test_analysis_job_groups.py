import unittest
from unittest.mock import patch

from src.analysis_jobs import claim_pending_analysis_group, create_analysis_jobs_for_rules


class Cursor:
    def __init__(self, candidates=(), jobs=(), acquired=1):
        self.candidates = list(candidates)
        self.jobs = list(jobs)
        self.acquired = acquired
        self.query = ""
        self.calls = []
        self.inserted = []

    def execute(self, query, params=None):
        self.query = query
        self.calls.append((query, params))

    def executemany(self, query, values):
        self.calls.append((query, values))
        for value in values:
            self.inserted.append({"id": len(self.inserted) + 1, "user_id": value[6],
                                  "watch_rule_id": value[7], "status": "pending"})

    def fetchall(self):
        if "candidates ON" in self.query:
            return self.candidates
        if "SELECT id, user_id" in self.query:
            return self.inserted
        return self.jobs

    def fetchone(self):
        return {"acquired": self.acquired}

    def close(self):
        pass


class Connection:
    def __init__(self, cursor):
        self.cur = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self, **kwargs):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class AnalysisJobGroupsTest(unittest.TestCase):
    def test_all_recipients_are_published_at_one_commit(self):
        cur = Cursor()
        conn = Connection(cur)
        product = {"product_id": "101", "product_url": "https://example.test/101", "price": 100}
        targets = [{"user_id": f"user{i}", "setting_id": i + 1} for i in range(501)]
        with patch("src.analysis_jobs.get_connection", return_value=conn):
            result = create_analysis_jobs_for_rules(product, targets, "new")
        self.assertEqual(len(result["created_jobs"]), 501)
        self.assertEqual(conn.commits, 1)
        inserts = [values for sql, values in cur.calls if "INSERT INTO" in sql]
        self.assertEqual([len(values) for values in inserts], [500, 1])
        self.assertEqual(len({row[10] for values in inserts for row in values}), 1)

    def test_group_is_not_cut_at_twenty_jobs_and_lock_lives_until_exit(self):
        candidate = {"source": "joongna", "product_id": "101", "change_fingerprint": "revision"}
        cur = Cursor([candidate], [{"id": i} for i in range(1, 49)])
        conn = Connection(cur)
        with patch("src.analysis_jobs.get_connection", return_value=conn):
            with claim_pending_analysis_group() as jobs:
                self.assertEqual(len(jobs), 48)
                self.assertFalse(any("RELEASE_LOCK" in sql for sql, _ in cur.calls))
                self.assertFalse(conn.closed)
        self.assertTrue(any("RELEASE_LOCK" in sql for sql, _ in cur.calls))
        self.assertTrue(conn.closed)
        group_query = next(sql for sql, _ in cur.calls if "ORDER BY id FOR UPDATE" in sql)
        self.assertNotIn("LIMIT", group_query)

    def test_busy_product_is_not_claimed_by_second_worker(self):
        candidate = {"source": "joongna", "product_id": "101", "change_fingerprint": "revision"}
        cur = Cursor([candidate], [{"id": 1}], acquired=0)
        conn = Connection(cur)
        with patch("src.analysis_jobs.get_connection", return_value=conn):
            with claim_pending_analysis_group() as jobs:
                self.assertEqual(jobs, [])
        self.assertFalse(any("UPDATE analysis_jobs" in sql for sql, _ in cur.calls))

    def test_uncaught_failure_requeues_only_still_running_and_releases_lock(self):
        candidate = {"source": "joongna", "product_id": "101", "change_fingerprint": "revision"}
        cur = Cursor([candidate], [{"id": 8}])
        conn = Connection(cur)
        with patch("src.analysis_jobs.get_connection", return_value=conn):
            with self.assertRaisesRegex(RuntimeError, "failure"):
                with claim_pending_analysis_group():
                    raise RuntimeError("failure")
        requeue = [sql for sql, _ in cur.calls if "status = 'pending'" in sql and "UPDATE" in sql]
        self.assertEqual(len(requeue), 1)
        self.assertIn("AND status = 'running'", requeue[0])
        self.assertTrue(any("RELEASE_LOCK" in sql for sql, _ in cur.calls))


if __name__ == "__main__":
    unittest.main()
