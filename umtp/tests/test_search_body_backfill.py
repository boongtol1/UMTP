import contextlib
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import search_body_backfill as service


class Database:
    """Execute selection SQL against actual relational data without a live DB."""

    def __init__(self):
        self.database = sqlite3.connect(":memory:")
        self.database.create_function(
            "REGEXP", 2,
            lambda pattern, value: int(bool(re.search(
                pattern.replace("[^[:space:]]", r"\S").replace("[[:space:]]", r"\s"),
                value or "",
            ))),
        )
        self.database.executescript("""
            CREATE TABLE search_queries (id INTEGER PRIMARY KEY, source TEXT);
            INSERT INTO search_queries VALUES (1, 'joongna'), (2, 'other');
            CREATE TABLE search_results (
                id INTEGER PRIMARY KEY, product_id TEXT, search_query_id INTEGER,
                fetched_at TEXT, body_text TEXT, body_fetched_at TEXT, url TEXT,
                body_hash TEXT
            );
        """)
        self.connections = []

    def add(self, row_id, product_id, body=None, *, source_id=1,
            fetched_at="2026-09-18 12:00:00", body_fetched_at=None):
        self.database.execute(
            """INSERT INTO search_results
               (id, product_id, search_query_id, fetched_at, body_text, body_fetched_at, url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (row_id, str(product_id), source_id, fetched_at, body, body_fetched_at,
             f"https://web.joongna.com/product/{product_id}"),
        )
        self.database.commit()

    def connection(self):
        database = self.database

        class Cursor:
            closed = False

            def execute(self, sql, params=()):
                self.result = database.execute(sql.replace("%s", "?"), params)

            def fetchone(self):
                return self.result.fetchone()

            def fetchall(self):
                return self.result.fetchall()

            @property
            def rowcount(self):
                return self.result.rowcount

            def close(self):
                if hasattr(self, "result"):
                    self.result.close()
                self.closed = True

        class Connection:
            closed = False
            commits = 0
            rollbacks = 0

            def __init__(self):
                self.cursor_value = Cursor()

            def cursor(self):
                return self.cursor_value

            def commit(self):
                self.commits += 1
                database.commit()

            def rollback(self):
                self.rollbacks += 1
                database.rollback()

            def close(self):
                self.closed = True

        connection = Connection()
        self.connections.append(connection)
        return connection

    def close(self):
        for connection in self.connections:
            connection.cursor_value.close()
            connection.close()
        self.database.close()


class CandidateSelectionTest(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def tearDown(self):
        self.db.close()

    def test_all_history_whitespace_deduplication_and_source_filter(self):
        self.db.add(1, "old", fetched_at="2023-01-01 00:00:00")
        self.db.add(2, "new", "\t\n  ")
        self.db.add(3, "new")
        self.db.add(4, "filled", "기존 본문")
        self.db.add(5, "other", source_id=2)
        rows = service.find_missing_body_candidates(self.db.connection().cursor())
        self.assertEqual([row["product_id"] for row in rows], ["new", "old"])
        self.assertEqual(rows[0]["missing_rows"], 2)

    def test_keyset_continues_after_prior_batch_is_filled(self):
        for row_id in range(1, 5):
            self.db.add(row_id, row_id)
        cursor = self.db.connection().cursor()
        first = service.find_missing_body_candidates(cursor, limit=2)
        self.db.database.execute("UPDATE search_results SET body_text = 'filled' WHERE id >= 3")
        second = service.find_missing_body_candidates(
            cursor, limit=2,
            after=(first[-1]["latest_fetched_at"], first[-1]["latest_id"]),
        )
        self.assertEqual([row["product_id"] for row in second], ["2", "1"])


class ProductBackfillTest(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.connection_patch = patch.object(service, "get_connection", side_effect=self.db.connection)
        self.connection_patch.start()

    def tearDown(self):
        self.connection_patch.stop()
        for connection in self.db.connections:
            self.assertTrue(connection.closed)
            self.assertTrue(connection.cursor_value.closed)
        self.db.close()

    def test_donor_body_is_reused_with_original_timestamp_without_network(self):
        stamp = "2026-09-17 13:00:00"
        self.db.add(1, 10, "원래 본문", body_fetched_at=stamp)
        self.db.add(2, 10)
        with patch.object(service, "fetch_html") as fetch:
            with patch.object(service, "fill_missing_search_result_bodies", return_value=1) as fill:
                result = service.backfill_product(10)
        fetch.assert_not_called()
        self.assertEqual(fill.call_args.args[1:], (10, "원래 본문"))
        self.assertEqual(fill.call_args.kwargs, {"body_fetched_at": stamp})
        self.assertEqual(result["source"], "stored")
        self.assertEqual(result["updated_rows"], 1)
        self.assertEqual(self.db.connections[0].commits, 1)

    def test_missing_body_fetches_even_without_title_or_price_and_uses_db_timestamp(self):
        self.db.add(1, 10)
        with patch.object(service, "fetch_html", return_value="<html>body only</html>") as fetch:
            with patch.object(service, "extract_listing_body_text", return_value="복원된 본문"):
                with patch.object(service, "fill_missing_search_result_bodies", return_value=1) as fill:
                    result = service.backfill_product(10)
        fetch.assert_called_once_with("https://web.joongna.com/product/10")
        self.assertEqual(result["source"], "detail")
        self.assertRegex(fill.call_args.kwargs["body_fetched_at"], r"^\d{4}-\d{2}-\d{2} ")
        self.assertEqual(self.db.connections[0].rollbacks, 1)

    def test_newer_observation_does_not_replace_newer_actual_body(self):
        self.db.add(1, 10, "최근 수집 원문", fetched_at="2026-09-18 12:00:00",
                    body_fetched_at="2026-09-18 21:00:00")
        self.db.add(2, 10, "다시 관측된 오래된 원문", fetched_at="2026-09-19 12:00:00",
                    body_fetched_at="2026-09-17 21:00:00")
        self.db.add(3, 10, "수집 시각 미상 복사본", fetched_at="2026-09-20 12:00:00")
        self.db.add(4, 10)
        with patch.object(service, "fetch_html") as fetch:
            with patch.object(service, "fill_missing_search_result_bodies", return_value=1) as fill:
                result = service.backfill_product(10)
        self.assertEqual(fill.call_args.args[2], "최근 수집 원문")
        self.assertEqual(fill.call_args.kwargs["body_fetched_at"], "2026-09-18 21:00:00")
        self.assertEqual(result["source"], "stored")
        fetch.assert_not_called()

    def test_real_fill_updates_blank_history_and_preserves_existing_nonempty_text(self):
        stamp = "2026-09-18 09:00:00"
        self.db.add(1, 10, "예전 본문", body_fetched_at="2026-09-17 09:00:00")
        self.db.add(2, 10, "현재 본문", body_fetched_at=stamp)
        self.db.add(3, 10, "\n\t  ")
        self.db.add(4, 10)
        self.db.add(5, 11)
        with patch.object(service, "fetch_html") as fetch:
            result = service.backfill_product(10)
        rows = self.db.database.execute(
            "SELECT body_text, body_fetched_at, body_hash FROM search_results ORDER BY id"
        ).fetchall()
        self.assertEqual(result["updated_rows"], 2)
        self.assertEqual(rows[0][0], "예전 본문")
        self.assertEqual(rows[1][0], "현재 본문")
        self.assertEqual(rows[2][:2], ("현재 본문", stamp))
        self.assertEqual(rows[3][:2], ("현재 본문", stamp))
        self.assertEqual(len(rows[2][2]), 64)
        self.assertIsNone(rows[4][0])
        fetch.assert_not_called()

    def test_empty_extraction_and_fetch_failure_never_write(self):
        self.db.add(1, 10)
        with patch.object(service, "fetch_html", return_value="<html>empty</html>"):
            with patch.object(service, "extract_listing_body_text", return_value=" \n\t"):
                with patch.object(service, "fill_missing_search_result_bodies") as fill:
                    result = service.backfill_product(10)
        self.assertEqual(result["reason"], "empty_body")
        fill.assert_not_called()
        with patch.object(service, "fetch_html", side_effect=RuntimeError("secret body")):
            with patch.object(service, "fill_missing_search_result_bodies") as fill:
                result = service.backfill_product(10)
        self.assertEqual(result["reason"], "RuntimeError")
        self.assertNotIn("secret body", json.dumps(result))
        fill.assert_not_called()

    def test_no_missing_rows_skips_network_and_write(self):
        self.db.add(1, 10, "기존 본문")
        with patch.object(service, "fetch_html") as fetch:
            with patch.object(service, "fill_missing_search_result_bodies") as fill:
                result = service.backfill_product(10)
        self.assertEqual(result["reason"], "already_filled")
        fetch.assert_not_called()
        fill.assert_not_called()


class BackfillSchedulingTest(unittest.TestCase):
    def test_failed_new_products_do_not_hide_older_candidates(self):
        db = Database()
        try:
            for row_id in range(1, 7):
                db.add(row_id, row_id)
            state = service.BodyBackfillState(batch_size=2)
            for product_id in ("6", "5", "4", "3"):
                state.record_result({"product_id": product_id, "failed": 1}, now=100)
            cursor = db.connection().cursor()
            self.assertIsNone(state.next_candidate(cursor, now=101))
            self.assertEqual(state.next_candidate(cursor, now=102)["product_id"], "2")
        finally:
            db.close()

    def test_deleted_and_transient_failures_have_distinct_retry_cooldowns(self):
        state = service.BodyBackfillState()
        state.record_result({"product_id": "deleted", "failed": 1, "http_status": 404}, now=100)
        state.record_result({"product_id": "timeout", "failed": 1}, now=100)
        first_retry = state.retry["timeout"][0]
        state.record_result({"product_id": "timeout", "failed": 1}, now=first_retry)
        self.assertEqual(state.retry["deleted"][0], 100 + 7 * 24 * 60 * 60)
        self.assertEqual(first_retry, 400)
        self.assertEqual(state.retry["timeout"][0], first_retry + 600)

    def test_newest_candidates_are_refreshed_while_old_batch_remains(self):
        db = Database()
        try:
            for row_id in range(1, 5):
                db.add(row_id, row_id)
            state = service.BodyBackfillState(batch_size=2)
            cursor = db.connection().cursor()
            self.assertEqual(state.next_candidate(cursor, now=100)["product_id"], "4")
            db.add(5, 5)
            self.assertEqual(state.next_candidate(cursor, now=161)["product_id"], "5")
        finally:
            db.close()


class BackfillCommandTest(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.add(1, "old")
        self.db.add(2, "new")
        self.patcher = patch.object(service, "get_connection", side_effect=self.db.connection)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()

    def test_dry_run_reports_candidates_without_fetching_or_writing(self):
        with patch.object(service, "backfill_product") as fill:
            with contextlib.redirect_stdout(io.StringIO()):
                report = service.run_backfill(dry_run=True)
        self.assertEqual(report["candidate_products"], 2)
        self.assertEqual(report["candidate_missing_rows"], 2)
        self.assertEqual(report["processed_products"], 0)
        fill.assert_not_called()

    def test_one_pass_continues_after_failure_and_writes_safe_json_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "report.json")
            with patch.object(service, "backfill_product", side_effect=[
                {"product_id": "new", "processed": 1, "failed": 1, "reason": "empty_body"},
                {"product_id": "old", "processed": 1, "source": "detail", "updated_rows": 2},
            ]) as fill:
                with contextlib.redirect_stdout(io.StringIO()):
                    report = service.run_backfill(report_path=path)
            self.assertEqual(fill.call_count, 2)
            self.assertEqual(report["updated_rows"], 2)
            self.assertEqual(report["detail_products"], 1)
            self.assertEqual(len(report["failures"]), 1)
            self.assertTrue(report["completed"])
            with open(path, encoding="utf-8") as saved:
                self.assertEqual(json.load(saved), report)

    def test_product_scope_and_limit_are_applied(self):
        with contextlib.redirect_stdout(io.StringIO()):
            report = service.run_backfill(product_id="old", dry_run=True, limit=1)
        self.assertEqual(report["candidate_products"], 1)


if __name__ == "__main__":
    unittest.main()
