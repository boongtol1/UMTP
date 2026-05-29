import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import (  # noqa: E402
    STORE_PROFILE_SUCCESS_TTL_HOURS,
    resolve_store_profile_for_store_seq,
    save_group_search_results,
)


class _StoreProfileCacheCursor:
    def __init__(self, cache_rows=None):
        self.executed = []
        self._fetchone_result = None
        self._search_query_id = 1
        self.cache_rows = cache_rows or {}
        self.inserted_search_results = 0
        self.rowcount = 0

    def execute(self, query, params=None):
        self.executed.append((query, params))
        normalized = " ".join((query or "").split()).lower()

        if normalized.startswith("insert into search_queries"):
            self._fetchone_result = None
            self.rowcount = 1
            return

        if normalized.startswith("select id from search_queries"):
            self._fetchone_result = (self._search_query_id,)
            self.rowcount = 1
            return

        if "from joongna_store_profiles" in normalized:
            store_seq = int(params[0]) if params and params[0] is not None else None
            self._fetchone_result = self.cache_rows.get(store_seq)
            self.rowcount = 1 if self._fetchone_result is not None else 0
            return

        if normalized.startswith("insert into joongna_store_profiles"):
            if params and len(params) == 2:
                store_seq, store_name = params
                self.cache_rows[int(store_seq)] = {
                    "store_seq": int(store_seq),
                    "store_name": store_name,
                    "fetch_status": "success",
                    "error_message": None,
                    "last_fetched_at": datetime.now(),
                    "next_retry_at": None,
                }
            elif params and len(params) == 3:
                store_seq, error_message, retry_at = params
                existing = self.cache_rows.get(int(store_seq), {})
                self.cache_rows[int(store_seq)] = {
                    "store_seq": int(store_seq),
                    "store_name": existing.get("store_name"),
                    "fetch_status": "failed",
                    "error_message": error_message,
                    "last_fetched_at": datetime.now(),
                    "next_retry_at": retry_at,
                }
            self._fetchone_result = None
            self.rowcount = 1
            return

        if normalized.startswith("insert into search_results"):
            self.inserted_search_results += 1
            self._fetchone_result = None
            self.rowcount = 1
            return

        self._fetchone_result = None
        self.rowcount = 0

    def fetchone(self):
        return self._fetchone_result


class JoongnaStoreProfileCacheTest(unittest.TestCase):
    def test_uses_cached_store_name_without_external_api_call(self):
        cursor = _StoreProfileCacheCursor(
            cache_rows={
                703755: {
                    "store_seq": 703755,
                    "store_name": "벨텁수동",
                    "fetch_status": "success",
                    "error_message": None,
                    "last_fetched_at": datetime.now(),
                    "next_retry_at": None,
                }
            }
        )

        with patch("src.joongna_polling_service.fetch_joongna_store_profile") as mock_fetch:
            result = resolve_store_profile_for_store_seq(cursor, 703755, store_profile_cache={})

        self.assertEqual(result.get("store_name"), "벨텁수동")
        self.assertEqual(mock_fetch.call_count, 0)

    def test_refetches_when_cached_store_name_is_stale(self):
        cursor = _StoreProfileCacheCursor(
            cache_rows={
                703755: {
                    "store_seq": 703755,
                    "store_name": "예전상호",
                    "fetch_status": "success",
                    "error_message": None,
                    "last_fetched_at": datetime.now()
                    - timedelta(hours=STORE_PROFILE_SUCCESS_TTL_HOURS + 1),
                    "next_retry_at": None,
                }
            }
        )

        with patch(
            "src.joongna_polling_service.fetch_joongna_store_profile",
            return_value={
                "store_seq": 703755,
                "store_name": "변경상호",
            },
        ) as mock_fetch:
            result = resolve_store_profile_for_store_seq(cursor, 703755, store_profile_cache={})

        self.assertEqual(mock_fetch.call_count, 1)
        self.assertEqual(result.get("store_name"), "변경상호")
        self.assertEqual((cursor.cache_rows.get(703755) or {}).get("store_name"), "변경상호")

    def test_returns_stale_store_name_during_retry_backoff(self):
        cursor = _StoreProfileCacheCursor(
            cache_rows={
                703755: {
                    "store_seq": 703755,
                    "store_name": "기존상호",
                    "fetch_status": "failed",
                    "error_message": "upstream 503",
                    "last_fetched_at": datetime.now()
                    - timedelta(hours=STORE_PROFILE_SUCCESS_TTL_HOURS + 1),
                    "next_retry_at": datetime.now() + timedelta(minutes=10),
                }
            }
        )

        with patch("src.joongna_polling_service.fetch_joongna_store_profile") as mock_fetch:
            result = resolve_store_profile_for_store_seq(cursor, 703755, store_profile_cache={})

        self.assertEqual(mock_fetch.call_count, 0)
        self.assertEqual(result.get("store_name"), "기존상호")

    def test_fetches_and_persists_when_cache_missing(self):
        cursor = _StoreProfileCacheCursor()

        with patch(
            "src.joongna_polling_service.fetch_joongna_store_profile",
            return_value={
                "store_seq": 703755,
                "store_name": "벨텁수동",
            },
        ) as mock_fetch:
            result = resolve_store_profile_for_store_seq(cursor, 703755, store_profile_cache={})

        self.assertEqual(mock_fetch.call_count, 1)
        self.assertEqual(result.get("store_name"), "벨텁수동")

        cached_row = cursor.cache_rows.get(703755) or {}
        self.assertEqual(cached_row.get("store_name"), "벨텁수동")
        self.assertEqual(cached_row.get("fetch_status"), "success")
        self.assertIsNone(cached_row.get("next_retry_at"))

    def test_api_failure_does_not_break_save_group_search_results(self):
        cursor = _StoreProfileCacheCursor()
        items = [
            {
                "seq": 1001,
                "product_id": 1001,
                "title": "맥북에어 M2",
                "price": 1200000,
                "sort_date": "2026-05-21 12:00:00",
                "product_url": "https://web.joongna.com/product/1001",
                "storeSeq": 703755,
            }
        ]

        with patch(
            "src.joongna_polling_service.fetch_joongna_store_profile",
            side_effect=RuntimeError("upstream 503"),
        ):
            result = save_group_search_results(
                cursor,
                source="joongna",
                search_keyword="맥북",
                items=items,
                fetched_at=datetime.now(),
                status="ok",
                store_profile_cache={},
            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(int(result.get("inserted_count") or 0), 1)
        self.assertEqual(cursor.inserted_search_results, 1)

        cached_row = cursor.cache_rows.get(703755) or {}
        self.assertEqual(cached_row.get("fetch_status"), "failed")
        self.assertIsNotNone(cached_row.get("next_retry_at"))
        self.assertGreater(cached_row.get("next_retry_at"), datetime.now() - timedelta(minutes=1))


if __name__ == "__main__":
    unittest.main()
