import os
import sqlite3
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import MagicMock, call, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import content_refresh_service as service  # noqa: E402


class Cursor:
    def close(self):
        return None


class Connection:
    def __init__(self):
        self.cursor_value = Cursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self, dictionary=False):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def is_connected(self):
        return not self.closed

    def close(self):
        self.closed = True


class ContentRefreshServiceTest(unittest.TestCase):
    def _candidate(self):
        return {
            "product_id": 1001,
            "search_word": "m2 맥북에어",
            "title": "맥북에어 M2 8GB 256GB",
            "price": 700000,
            "product_url": "https://web.joongna.com/product/1001",
            "sort_date": "2026-09-17 10:00:00",
        }

    def test_defers_while_analysis_queue_has_work(self):
        connection = Connection()
        with patch.object(service, "get_connection", return_value=connection):
            with patch.object(service, "has_pending_analysis_jobs", return_value=True):
                with patch.object(service, "find_due_content_candidate") as find_candidate:
                    result = service.process_next_content_refresh()

        self.assertEqual(result["reason"], "analysis_backlog")
        find_candidate.assert_not_called()

    def test_body_change_is_persisted_and_enqueued_once(self):
        first_connection = Connection()
        second_connection = Connection()
        previous = {
            "last_body_hash": service.build_listing_content_snapshot(
                body_text="이전 본문"
            )["body_hash"],
            "last_self_check_hash": None,
        }
        targets = [{"setting_id": 1, "rule_id": 1, "user_id": "u1"}]
        page = {
            "title": "맥북에어 M2 8GB 256GB",
            "description": "변경된 본문",
            "listing_price_krw": 700000,
            "self_check_fields": {},
        }

        with patch.object(
            service,
            "get_connection",
            side_effect=[first_connection, second_connection],
        ):
            with patch.object(service, "has_pending_analysis_jobs", return_value=False):
                with patch.object(service, "find_due_content_candidate", return_value=self._candidate()):
                    with patch.object(service, "fetch_html", return_value="<html>"):
                        with patch.object(service, "parse_joongna_listing_page", return_value=page):
                            with patch.object(service, "get_seen_product", return_value=previous):
                                with patch.object(service, "load_latest_search_result", return_value={}):
                                    with patch.object(service, "persist_latest_search_result_enrichment") as persist:
                                        with patch.object(service, "update_seen_product_content_snapshot") as update:
                                            with patch.object(
                                                service,
                                                "load_active_targets_for_product",
                                                return_value=targets,
                                            ):
                                                with patch.object(
                                                    service,
                                                    "create_analysis_jobs_for_rules",
                                                    return_value={"created_jobs": [{"job_id": 9}]},
                                                ) as enqueue:
                                                    result = service.process_next_content_refresh()

        self.assertEqual(result["change_reason"], "body_changed")
        self.assertEqual(result["analysis_jobs_created"], 1)
        persist.assert_called_once()
        update.assert_called_once()
        enqueue.assert_called_once()
        product = enqueue.call_args.args[0]
        self.assertEqual(product["body_text"], "변경된 본문")
        self.assertEqual(enqueue.call_args.args[2], "body_changed")
        self.assertEqual(second_connection.commits, 1)

    def test_first_body_snapshot_does_not_send_change_alert(self):
        first_connection = Connection()
        second_connection = Connection()
        with patch.object(
            service,
            "get_connection",
            side_effect=[first_connection, second_connection],
        ):
            with patch.object(service, "has_pending_analysis_jobs", return_value=False):
                with patch.object(service, "find_due_content_candidate", return_value=self._candidate()):
                    with patch.object(service, "fetch_html", return_value="<html>"):
                        with patch.object(
                            service,
                            "parse_joongna_listing_page",
                            return_value={
                                "title": "맥북에어",
                                "description": "최초 본문",
                                "listing_price_krw": 700000,
                                "self_check_fields": {},
                            },
                        ):
                            with patch.object(service, "get_seen_product", return_value={}):
                                with patch.object(service, "load_latest_search_result", return_value={}):
                                    with patch.object(service, "persist_latest_search_result_enrichment"):
                                        with patch.object(service, "update_seen_product_content_snapshot"):
                                            with patch.object(service, "create_analysis_jobs_for_rules") as enqueue:
                                                result = service.process_next_content_refresh()

        self.assertIsNone(result["change_reason"])
        enqueue.assert_not_called()


class ContentRefreshKeywordMappingTest(unittest.TestCase):
    """Exercise the real joins against isolated, in-memory relational data."""

    def setUp(self):
        self.database = sqlite3.connect(":memory:")
        self.database.row_factory = sqlite3.Row
        self.database.executescript("""
            CREATE TABLE user_fair_prices (
                id INTEGER PRIMARY KEY, user_id TEXT, product_type TEXT, chip TEXT,
                search_keyword TEXT, enabled INTEGER, last_poll_requested_at TEXT, saved_at TEXT
            );
            CREATE TABLE search_queries (id INTEGER PRIMARY KEY, source TEXT, normalized_keyword TEXT);
            CREATE TABLE search_results (product_id TEXT, search_query_id INTEGER);
            CREATE TABLE joongna_seen_products (
                seq TEXT PRIMARY KEY, search_word TEXT, last_title TEXT, last_price_krw INTEGER,
                product_url TEXT, last_sort_date TEXT, first_seen_at TEXT, last_seen_at TEXT,
                last_content_checked_at TEXT, last_body_hash TEXT, last_self_check_hash TEXT
            );
        """)
        self.now = datetime(2026, 9, 18, 12)
        self.sort_date = "2026-09-18 11:00:00"

    def tearDown(self):
        self.database.close()

    def _cursor(self, *, dictionary=False):
        database = self.database

        class QueryCursor:
            def execute(self, sql, params=()):
                # SQLite supplies the relational checks without connecting to
                # MySQL; only placeholders and the two date functions differ.
                sql = sql.replace("%s", "?")
                sql = sql.replace("DATE_SUB(?, INTERVAL 1 HOUR)", "datetime(?, '-1 hour')")
                sql = sql.replace("DATE_SUB(?, INTERVAL 1 DAY)", "datetime(?, '-1 day')")
                self.result = database.execute(sql, params)

            def fetchone(self):
                row = self.result.fetchone()
                return (dict(row) if dictionary else tuple(row)) if row is not None else None

            def fetchall(self):
                return [dict(row) if dictionary else tuple(row) for row in self.result.fetchall()]

            def close(self):
                pass

        return QueryCursor()

    def _rule(self, setting_id=14, *, product_type="iMac", chip="M1", keyword="m1 아이맥",
              enabled=True, requested=True, saved_at="2026-09-18 10:00:00", user_id="u1"):
        self.database.execute(
            "INSERT INTO user_fair_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (setting_id, user_id, product_type, chip, keyword, enabled,
             "2026-09-18 10:00:00" if requested else None, saved_at),
        )

    def _listing(self, keyword, *, product_id="1001", source="joongna"):
        result = self.database.execute(
            "INSERT INTO search_queries (source, normalized_keyword) VALUES (?, ?)",
            (source, keyword),
        )
        self.database.execute("INSERT INTO search_results VALUES (?, ?)", (product_id, result.lastrowid))
        self.database.execute(
            "INSERT OR IGNORE INTO joongna_seen_products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (product_id, keyword, "iMac M1 8GB 256GB", 600000,
             f"https://web.joongna.com/product/{product_id}", self.sort_date,
             self.sort_date, "2026-09-18 11:50:00", None, "old-body", None),
        )

    def test_english_only_imac_result_is_due_and_targets_its_korean_setting(self):
        self._rule()
        self._listing("imac m1")
        for dictionary in (False, True):
            with self.subTest(dictionary=dictionary):
                cursor = self._cursor(dictionary=dictionary)
                candidate = service.find_due_content_candidate(cursor, now=self.now)
                self.assertEqual(candidate["product_id"], "1001")
                targets = service.load_active_targets_for_product(cursor, "1001", self.sort_date)
                self.assertEqual([target["setting_id"] for target in targets], [14])
                self.assertEqual(targets[0]["search_keyword"], "m1 아이맥")

    def test_bilingual_results_deduplicate_each_setting_and_preserve_other_recipients(self):
        self._rule()
        self._rule(15, user_id="u2")
        self._rule(16, user_id="u1")
        self._listing("m1 아이맥")
        self._listing("IMAC M1")
        targets = service.load_active_targets_for_product(self._cursor(), "1001", self.sort_date)
        self.assertEqual([target["setting_id"] for target in targets], [14, 15, 16])

    def test_custom_imac_search_does_not_acquire_default_alias(self):
        self._rule(keyword="아이맥 작업용")
        self._listing("imac m1")
        cursor = self._cursor()
        self.assertIsNone(service.find_due_content_candidate(cursor, now=self.now))
        self.assertEqual(service.load_active_targets_for_product(cursor, "1001", self.sort_date), [])
        self._listing("아이맥 작업용")
        self.assertIsNotNone(service.find_due_content_candidate(cursor, now=self.now))
        self.assertEqual(len(service.load_active_targets_for_product(cursor, "1001", self.sort_date)), 1)

    def test_disabled_unrequested_and_newer_settings_do_not_receive_old_listing(self):
        self._rule(enabled=False)
        self._rule(15, requested=False)
        self._rule(16, saved_at="2026-09-18 11:30:00")
        self._rule(17, saved_at=None)
        self._listing("imac m1")
        targets = service.load_active_targets_for_product(self._cursor(), "1001", self.sort_date)
        self.assertEqual([target["setting_id"] for target in targets], [17])
        targets_without_date = service.load_active_targets_for_product(self._cursor(), "1001", None)
        self.assertEqual([target["setting_id"] for target in targets_without_date], [16, 17])

    def test_all_supported_products_keep_direct_keyword_refresh(self):
        cases = (
            ("MacBook Air", "M2", "m2 맥북에어"),
            ("Mac mini", "M4", "m4 맥미니"),
            ("MacBook Pro", "M3 Max", "m3max 맥북프로"),
            ("MacBook Neo", "A18 Pro", "맥북 네오"),
            ("iMac", "M4", "m4 아이맥"),
            ("Mac Studio", "M3 Ultra", "m3ultra 맥스튜디오"),
        )
        for index, (product_type, chip, keyword) in enumerate(cases, start=1):
            self._rule(index, product_type=product_type, chip=chip, keyword=keyword)
            self._listing(keyword, product_id=str(index))
            with self.subTest(product_type=product_type, stage="candidate"):
                candidate = service.find_due_content_candidate(self._cursor(), now=self.now)
                self.assertEqual(candidate["product_id"], str(index))
            self.database.execute(
                "UPDATE joongna_seen_products SET last_content_checked_at = ? WHERE seq = ?",
                (self.now, str(index)),
            )
        for index, (product_type, _, _) in enumerate(cases, start=1):
            with self.subTest(product_type=product_type):
                targets = service.load_active_targets_for_product(self._cursor(), str(index), self.sort_date)
                self.assertEqual([target["setting_id"] for target in targets], [index])

    def test_no_active_keywords_or_only_other_source_results_are_not_due(self):
        self._listing("imac m1", source="other")
        self.assertIsNone(service.find_due_content_candidate(self._cursor(), now=self.now))
        self._rule()
        self.assertIsNone(service.find_due_content_candidate(self._cursor(), now=self.now))
        self.assertEqual(service.load_active_targets_for_product(self._cursor(), "1001", self.sort_date), [])

    def test_english_only_body_change_reaches_analysis_queue_once(self):
        self._rule()
        self._listing("imac m1")
        connections = [Connection(), Connection()]
        for connection in connections:
            connection.cursor_value = self._cursor()
        actual_find_candidate = service.find_due_content_candidate
        with ExitStack() as stack:
            stack.enter_context(patch.object(service, "get_connection", side_effect=connections))
            stack.enter_context(patch.object(service, "has_pending_analysis_jobs", return_value=False))
            stack.enter_context(patch.object(service, "find_due_content_candidate",
                                            side_effect=lambda cursor: actual_find_candidate(cursor, now=self.now)))
            stack.enter_context(patch.object(service, "fetch_html", return_value="<html>"))
            stack.enter_context(patch.object(service, "parse_joongna_listing_page", return_value={
                "title": "iMac M1 8GB 256GB", "description": "Changed body", "listing_price_krw": 600000,
                "self_check_fields": {},
            }))
            stack.enter_context(patch.object(service, "get_seen_product", return_value={"last_body_hash": "old-body"}))
            stack.enter_context(patch.object(service, "load_latest_search_result", return_value={}))
            stack.enter_context(patch.object(service, "persist_latest_search_result_enrichment"))
            stack.enter_context(patch.object(service, "update_seen_product_content_snapshot"))
            enqueue = stack.enter_context(patch.object(service, "create_analysis_jobs_for_rules",
                                                      return_value={"created_jobs": [{"job_id": 9}]}))
            result = service.process_next_content_refresh()
        self.assertEqual(result["change_reason"], "body_changed")
        self.assertEqual(result["target_count"], 1)
        self.assertEqual(result["analysis_jobs_created"], 1)
        enqueue.assert_called_once()
        self.assertEqual(enqueue.call_args.args[1][0]["setting_id"], 14)
        self.assertEqual(enqueue.call_args.args[0]["search_keyword"], "imac m1")


if __name__ == "__main__":
    unittest.main()
