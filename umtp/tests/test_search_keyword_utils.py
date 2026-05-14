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
        self.assertEqual(keyword, "m1맥북에어")

    def test_build_recommended_keywords_for_spec(self):
        keywords = build_recommended_keywords_for_spec("MacBook Air", "M1", ram_gb=8, ssd_gb=256)
        self.assertGreaterEqual(len(keywords), 4)
        self.assertEqual(keywords[0], "m1맥북에어")
        self.assertIn("맥북에어 M1", keywords)
        self.assertIn("맥북 M1", keywords)


if __name__ == "__main__":
    unittest.main()
