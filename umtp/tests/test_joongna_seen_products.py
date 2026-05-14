import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_seen_products import should_analyze_seen_product


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
