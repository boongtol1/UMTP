import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.search_keyword_utils import (  # noqa: E402
    build_default_keyword_for_watch_rule,
    build_recommended_keywords_for_spec,
    dedupe_keywords_keep_order,
    normalize_search_keyword,
)


class SearchKeywordUtilsTest(unittest.TestCase):
    def test_normalize_search_keyword(self):
        self.assertEqual(normalize_search_keyword("  맥북   m1  "), "맥북 m1")

    def test_dedupe_keywords_keep_order(self):
        keywords = dedupe_keywords_keep_order([" 맥북 m1", "맥북 m1 ", "m1맥북에어"])
        self.assertEqual(keywords, ["맥북 m1", "m1맥북에어"])

    def test_build_default_keyword_for_watch_rule(self):
        keyword = build_default_keyword_for_watch_rule(
            {
                "product_type": "MacBook Air",
                "chip": "M1",
                "ram_gb": 8,
                "ssd_gb": 256,
            }
        )
        self.assertEqual(keyword, "m1 맥북에어")

    def test_build_recommended_keywords_for_spec(self):
        keywords = build_recommended_keywords_for_spec("MacBook Air", "M1", ram_gb=8, ssd_gb=256)
        self.assertGreaterEqual(len(keywords), 4)
        self.assertEqual(keywords[0], "m1 맥북에어")
        self.assertIn("맥북에어 M1", keywords)
        self.assertIn("맥북 M1", keywords)

    def test_build_recommended_keywords_for_mac_mini(self):
        keywords = build_recommended_keywords_for_spec("Mac mini", "m2pro", ram_gb=16, ssd_gb=1024)
        self.assertGreaterEqual(len(keywords), 5)
        self.assertEqual(keywords[0], "m2pro 맥미니")
        self.assertIn("맥미니 M2 Pro", keywords)
        self.assertIn("mac mini m2pro", keywords)

    def test_macbook_pro_default_keywords_keep_chip_tier(self):
        for chip, expected in (("M1", "m1"), ("m3pro", "m3pro"), ("M5 Max", "m5max")):
            with self.subTest(chip=chip):
                self.assertEqual(
                    build_default_keyword_for_watch_rule({"product_type": "MacBook Pro", "chip": chip}),
                    f"{expected} 맥북프로",
                )
        self.assertEqual(build_default_keyword_for_watch_rule({"product_type": "MacBook Pro"}), "맥북프로")

    def test_macbook_pro_recommendations_match_air_format(self):
        keywords = build_recommended_keywords_for_spec("MacBook Pro", "m3max", ram_gb=96, ssd_gb=8192)
        self.assertEqual(keywords[0], "m3max 맥북프로")
        self.assertIn("맥북프로 M3 Max", keywords)
        self.assertIn("m3max 맥북프로 96 8192", keywords)
        self.assertIn("MacBook Pro M3 Max", keywords)
        self.assertEqual(len(keywords), len(set(keyword.lower() for keyword in keywords)))


if __name__ == "__main__":
    unittest.main()
