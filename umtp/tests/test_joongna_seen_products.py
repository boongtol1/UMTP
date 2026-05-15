import os
import sys
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_seen_products import should_analyze_seen_product, upsert_seen_product_observation


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))


class ShouldAnalyzeSeenProductTest(unittest.TestCase):
    def test_new_product(self):
        should_analyze, reason = should_analyze_seen_product(
            None,
            {
                "title": "M2 맥북에어 16/512",
                "price": 1200000,
                "refresh_key": "2026-05-15T10:00:00+09:00",
            },
        )
        self.assertTrue(should_analyze)
        self.assertEqual(reason, "new_product")

    def test_price_changed(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M2 맥북에어 16/512",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
            },
            {
                "title": "M2 맥북에어 16/512",
                "price": 1150000,
                "refresh_key": "rk-1",
            },
        )
        self.assertTrue(should_analyze)
        self.assertEqual(reason, "price_changed")

    def test_title_changed(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M2 맥북에어 16/512",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
            },
            {
                "title": "M2 맥북에어 24/512",
                "price": 1200000,
                "refresh_key": "rk-1",
            },
        )
        self.assertTrue(should_analyze)
        self.assertEqual(reason, "title_changed")

    def test_refresh_key_changed(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M2 맥북에어 16/512",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
            },
            {
                "title": "M2 맥북에어 16/512",
                "price": 1200000,
                "refresh_key": "rk-2",
            },
        )
        self.assertTrue(should_analyze)
        self.assertEqual(reason, "refresh_key_changed")

    def test_sort_date_changed_detects_reexposure(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M3 맥북에어 8/256",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
                "last_sort_date": "2026-05-15 10:00:00",
            },
            {
                "title": "M3 맥북에어 8/256",
                "price": 1200000,
                "refresh_key": "rk-1",
                "sort_date": "2026-05-15 12:28:52",
            },
        )
        self.assertTrue(should_analyze)
        self.assertEqual(reason, "sort_date_changed")

    def test_sort_date_same_is_unchanged(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M3 맥북에어 8/256",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
                "last_sort_date": "2026-05-15 12:28:52",
            },
            {
                "title": "M3 맥북에어 8/256",
                "price": 1200000,
                "refresh_key": "rk-1",
                "sort_date": "2026-05-15 12:28:52",
            },
        )
        self.assertFalse(should_analyze)
        self.assertEqual(reason, "unchanged")

    def test_sort_date_missing_does_not_create_bump_reason(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M3 맥북에어 8/256",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
                "last_sort_date": "2026-05-15 12:28:52",
            },
            {
                "title": "M3 맥북에어 8/256",
                "price": 1200000,
                "refresh_key": "rk-1",
                "sort_date": None,
            },
        )
        self.assertFalse(should_analyze)
        self.assertEqual(reason, "unchanged")
        self.assertNotIn("bump", reason)

    def test_sort_date_takes_priority_over_title_or_price_if_changed_first(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M3 맥북에어 8/256",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
                "last_sort_date": "2026-05-15 10:00:00",
            },
            {
                "title": "M3 맥북에어 16/512",
                "price": 1100000,
                "refresh_key": "rk-1",
                "sort_date": "2026-05-15 12:28:52",
            },
        )
        self.assertTrue(should_analyze)
        self.assertEqual(reason, "sort_date_changed")

    def test_upsert_seen_product_tracks_sort_date_columns(self):
        cursor = _FakeCursor()

        upsert_seen_product_observation(
            cursor,
            {
                "product_id": 1001,
                "search_word": "m3맥북에어",
                "title": "M3 맥북에어 8/256",
                "price": 1200000,
                "product_url": "https://web.joongna.com/product/1001",
                "image_url": "https://example.com/image.jpg",
                "sort_date": "2026-05-15 12:28:52",
                "refresh_key": "rk-1",
            },
            change_reason="sort_date_changed",
            status="analysis_pending",
        )

        self.assertEqual(len(cursor.executed), 1)
        query, params = cursor.executed[0]
        self.assertIn("last_sort_date", query)
        self.assertIn("previous_sort_date", query)
        self.assertIn("sort_date_changed_count", query)
        self.assertIn("last_sort_date_changed_at", query)
        self.assertIn("sort_date_changed", query)
        self.assertIsInstance(params[11], datetime)

    def test_unchanged(self):
        should_analyze, reason = should_analyze_seen_product(
            {
                "last_title": "M2 맥북에어 16/512",
                "last_price_krw": 1200000,
                "last_refresh_key": "rk-1",
            },
            {
                "title": "M2 맥북에어 16/512",
                "price": 1200000,
                "refresh_key": "rk-1",
            },
        )
        self.assertFalse(should_analyze)
        self.assertEqual(reason, "unchanged")


if __name__ == "__main__":
    unittest.main()
