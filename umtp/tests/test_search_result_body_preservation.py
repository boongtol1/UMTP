import json
import os
import re
import sqlite3
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import _insert_search_result_row, save_group_search_results
from src.joongna_search_client import _normalize_item
from src.search_result_enrichment import (
    build_body_hash,
    fill_missing_search_result_bodies,
    load_latest_search_result_bodies,
)


class SqliteCursor:
    """Run the body-cache SQL against real rows without requiring a live MySQL DB."""

    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.create_function(
            "regexp", 2,
            lambda pattern, value: bool(re.search(pattern.replace("[[:space:]]", r"\s"), value or "")),
        )
        self.cursor = self.connection.cursor()
        self.cursor.execute("""
            CREATE TABLE search_results (
                id INTEGER PRIMARY KEY, product_id TEXT, body_text TEXT,
                body_hash TEXT, body_fetched_at TEXT, fetched_at TEXT
            )
        """)

    def execute(self, query, params=()):
        query = query.replace("ON DUPLICATE KEY UPDATE", "ON CONFLICT DO UPDATE SET")
        query = re.sub(r"VALUES\((\w+)\)", r"excluded.\1", query, flags=re.IGNORECASE)
        query = query.replace("GREATEST(", "MAX(")
        self.cursor.execute(query.replace("%s", "?"), params)

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount


class SearchCacheCursor:
    def __init__(self, rows=None, db_timestamp=None):
        self.rows = rows or []
        self.rowcount = 0
        self.result = []
        self.body_cache_reads = 0
        self.body_fill_writes = 0
        self.timestamp_reads = 0
        self.db_timestamp = db_timestamp

    def execute(self, query, params=()):
        sql = " ".join(query.split()).lower()
        self.rowcount = 0
        self.result = []
        if sql.startswith("select id from search_queries"):
            self.result = [(1,)]
        elif sql.startswith("select current_timestamp as body_fetched_at"):
            self.timestamp_reads += 1
            self.result = [(self.db_timestamp,)]
        elif sql.startswith("select sr.product_id, sr.body_text"):
            self.body_cache_reads += 1
            for product_id in params:
                candidates = [
                    row for row in self.rows
                    if row["product_id"] == product_id and (row.get("body_text") or "").strip()
                ]
                if candidates:
                    cached = dict(max(candidates, key=lambda row: (
                        row.get("body_fetched_at") or datetime.min, row["fetched_at"], row["id"],
                    )))
                    cached["has_missing"] = any(
                        row["product_id"] == product_id and not (row.get("body_text") or "").strip()
                        for row in self.rows
                    )
                    self.result.append(cached)
        elif sql.startswith("select content_signature"):
            candidates = [
                row for row in self.rows
                if row["search_query_id"] == params[0] and row["product_id"] == params[1]
            ]
            if candidates:
                self.result = [max(candidates, key=lambda row: (row["fetched_at"], row["id"]))]
        elif sql.startswith("update search_results set body_text"):
            self.body_fill_writes += 1
            body_text, body_hash, body_fetched_at, product_id = params
            for row in self.rows:
                if row["product_id"] == product_id and not (row.get("body_text") or "").strip():
                    row.update(body_text=body_text, body_hash=body_hash, body_fetched_at=body_fetched_at)
                    self.rowcount += 1
        elif sql.startswith("insert into search_results"):
            columns = [value.strip() for value in sql.split("(", 1)[1].split(")", 1)[0].split(",")]
            row = dict(zip(columns, params))
            row["id"] = len(self.rows) + 1
            self.rows.append(row)
            self.rowcount = 1

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result


class SearchResultBodyPreservationTest(unittest.TestCase):
    def test_repeated_search_signature_preserves_original_body_and_metadata(self):
        cursor = SqliteCursor()
        self.addCleanup(cursor.connection.close)
        extra_columns = (
            "search_query_id", "title", "price", "sort_date", "url", "refresh_key",
            "seller_store_seq", "seller_store_name", "seller_profile_image_url",
            "seller_store_level", "seller_trust_score", "seller_review_count",
            "raw_json", "content_signature",
        )
        for column in extra_columns:
            cursor.execute(f"ALTER TABLE search_results ADD COLUMN {column}")
        cursor.execute("""
            CREATE UNIQUE INDEX unique_signature ON search_results
            (search_query_id, product_id, content_signature)
        """)
        values = dict.fromkeys(extra_columns)
        values.update(
            search_query_id=1, product_id="p1", title="listing", raw_json='{"wish_count":1}',
            body_text="body A", body_fetched_at="2026-09-01", fetched_at="2026-09-01",
            content_signature="signature A",
        )
        _insert_search_result_row(cursor, **values)
        values.update(
            raw_json='{"wish_count":2}', content_signature="signature B", body_text="body B",
            body_fetched_at="2026-09-02", fetched_at="2026-09-02",
        )
        _insert_search_result_row(cursor, **values)
        # Wish count returns to 1: cache contains B but signature A still owns body A.
        values.update(raw_json='{"wish_count":1}', content_signature="signature A", fetched_at="2026-09-03")
        _insert_search_result_row(cursor, **values)
        cursor.execute("SELECT body_text, body_hash, body_fetched_at FROM search_results ORDER BY id")
        self.assertEqual(cursor.fetchall(), [
            ("body A", build_body_hash("body A"), "2026-09-01"),
            ("body B", build_body_hash("body B"), "2026-09-02"),
        ])
        # A duplicate may still fill an actually empty historical snapshot.
        cursor.execute("UPDATE search_results SET body_text = ' \t ', body_hash = NULL, body_fetched_at = NULL WHERE id = 1")
        _insert_search_result_row(cursor, **values)
        cursor.execute("SELECT body_text, body_hash, body_fetched_at FROM search_results WHERE id = 1")
        self.assertEqual(cursor.fetchall(), [("body B", build_body_hash("body B"), "2026-09-02")])

    def test_fill_blanks_preserves_existing_text_and_source_timestamp(self):
        cursor = SqliteCursor()
        self.addCleanup(cursor.connection.close)
        cursor.cursor.executemany(
            "INSERT INTO search_results VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, "p1", "old description", "old hash", "2026-09-01", "2026-09-01"),
                (2, "p1", None, None, None, "2026-09-02"),
                (3, "p1", " \n\t ", None, None, "2026-09-03"),
                (4, "other", None, None, None, "2026-09-04"),
            ],
        )

        self.assertEqual(fill_missing_search_result_bodies(cursor, "p1", " recovered "), 2)
        cursor.execute("SELECT body_text, body_hash, body_fetched_at FROM search_results ORDER BY id")
        self.assertEqual(cursor.fetchall(), [
            ("old description", "old hash", "2026-09-01"),
            ("recovered", build_body_hash("recovered"), None),
            ("recovered", build_body_hash("recovered"), None),
            (None, None, None),
        ])
        self.assertEqual(fill_missing_search_result_bodies(cursor, "p1", "changed"), 0)
        self.assertEqual(fill_missing_search_result_bodies(cursor, "other", "  "), 0)
        self.assertEqual(fill_missing_search_result_bodies(
            cursor, "other", "other body", body_fetched_at="2026-09-05",
        ), 1)
        cursor.execute("SELECT body_fetched_at FROM search_results WHERE product_id = 'other'")
        self.assertEqual(cursor.fetchall(), [("2026-09-05",)])

    def test_batch_cache_uses_latest_nonblank_snapshot(self):
        cursor = SqliteCursor()
        self.addCleanup(cursor.connection.close)
        cursor.cursor.executemany(
            "INSERT INTO search_results VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, "p1", "older", None, None, "2026-09-01"),
                (2, "p1", "newer", None, "2026-09-02", "2026-09-02"),
                (3, "p1", None, None, None, "2026-09-03"),
                (4, "p2", " \t\n", None, None, "2026-09-04"),
                (5, "p3", "revived old body", None, "2026-09-01", "2026-09-04"),
                (6, "p3", "freshly fetched body", None, "2026-09-02", "2026-09-02"),
                (7, "p3", "unknown age body", None, None, "2026-09-05"),
            ],
        )
        self.assertEqual(load_latest_search_result_bodies(cursor, ["p1", "p2", "p1", "p3"]), {
            "p1": {
                "body_text": "newer", "body_hash": build_body_hash("newer"),
                "body_fetched_at": "2026-09-02",
                "has_missing": True,
            },
            "p3": {
                "body_text": "freshly fetched body", "body_hash": build_body_hash("freshly fetched body"),
                "body_fetched_at": "2026-09-02", "has_missing": False,
            },
        })

    def test_wish_count_change_reuses_body_without_changing_search_fingerprint(self):
        cursor = SearchCacheCursor()
        now = datetime(2026, 9, 18, 12)
        item = {"seq": 1001, "product_id": 1001, "title": "MacBook", "wish_count": 2}

        def save(value, at):
            return save_group_search_results(
                cursor, source="joongna", search_keyword="MacBook", items=[value],
                fetched_at=at, enrich_details=False,
            )

        self.assertEqual(save(dict(item), now)["inserted_count"], 1)
        original_signature = cursor.rows[0]["content_signature"]
        cursor.rows[0].update(
            body_text="Detailed listing text", body_hash=build_body_hash("Detailed listing text"),
            body_fetched_at=now,
        )
        # Acquiring a body after search must not manufacture a changed search result.
        self.assertEqual(save(dict(item), now + timedelta(minutes=1))["skipped_unchanged_count"], 1)
        self.assertEqual(cursor.rows[0]["content_signature"], original_signature)

        item["wish_count"] = 3
        with patch("src.joongna_polling_service.fetch_html") as fetch_html:
            self.assertEqual(save(item, now + timedelta(minutes=2))["inserted_count"], 1)
            self.assertEqual(save(item, now + timedelta(minutes=3))["skipped_unchanged_count"], 1)
        fetch_html.assert_not_called()
        self.assertEqual(len(cursor.rows), 2)
        latest = cursor.rows[-1]
        self.assertEqual(latest["body_text"], "Detailed listing text")
        self.assertEqual(latest["body_hash"], build_body_hash("Detailed listing text"))
        self.assertEqual(latest["body_fetched_at"], now)
        self.assertNotIn("body_text", item)
        self.assertNotIn("body_text", json.loads(latest["raw_json"]))
        self.assertEqual(cursor.body_cache_reads, 4)
        self.assertEqual(cursor.body_fill_writes, 0)
        self.assertEqual(cursor.timestamp_reads, 0)

        # Legacy rows without a stored signature must reconstruct it from raw search data.
        latest["content_signature"] = None
        self.assertEqual(save(item, now + timedelta(minutes=4))["skipped_unchanged_count"], 1)
        self.assertEqual(len(cursor.rows), 2)

    def test_unchanged_snapshot_fills_historical_gaps_only_once(self):
        cursor = SearchCacheCursor()
        now = datetime(2026, 9, 18, 12)
        item = {"seq": 1001, "title": "MacBook", "wish_count": 2}

        def save():
            return save_group_search_results(
                cursor, source="joongna", search_keyword="MacBook", items=[dict(item)],
                fetched_at=now, enrich_details=False,
            )

        save()
        item["wish_count"] = 3
        save()
        cursor.rows[0].update(body_text="older recovered text", body_fetched_at=now)
        self.assertEqual(save()["skipped_unchanged_count"], 1)
        self.assertEqual(cursor.rows[1]["body_text"], "older recovered text")
        self.assertEqual(cursor.rows[1]["body_fetched_at"], now)
        self.assertEqual(cursor.body_fill_writes, 1)
        self.assertEqual(save()["skipped_unchanged_count"], 1)
        self.assertEqual(cursor.body_fill_writes, 1)

    def test_api_body_takes_precedence_over_cached_body(self):
        now = datetime(2026, 9, 18, 12)
        db_timestamp = now + timedelta(hours=9)
        cursor = SearchCacheCursor([{
            "id": 1, "search_query_id": 1, "product_id": "1001", "fetched_at": now,
            "body_text": "old body", "content_signature": "old signature",
        }], db_timestamp=db_timestamp)
        save_group_search_results(
            cursor, source="joongna", search_keyword="MacBook",
            items=[{"seq": 1001, "body_text": "fresh API body"}],
            fetched_at=now + timedelta(minutes=1), enrich_details=False,
        )
        self.assertEqual(cursor.rows[0]["body_text"], "old body")
        self.assertEqual(cursor.rows[-1]["body_text"], "fresh API body")
        self.assertEqual(cursor.rows[-1]["body_fetched_at"], db_timestamp)
        self.assertEqual(cursor.body_cache_reads, 0)
        self.assertEqual(cursor.timestamp_reads, 1)

    def test_search_normalization_retains_descriptions_and_omits_missing_body(self):
        for key in ("body_text", "body", "content", "description", "productDescription", "productDesc"):
            with self.subTest(key=key):
                self.assertEqual(_normalize_item({"seq": 1, key: " description "})["body_text"], "description")
        self.assertEqual(_normalize_item({"seq": 1, "data": {"description": "nested"}})["body_text"], "nested")
        self.assertNotIn("body_text", _normalize_item({"seq": 1}))
        self.assertNotIn("body_text", _normalize_item({"seq": 1, "content": {"irrelevant": "value"}}))


if __name__ == "__main__":
    unittest.main()
