import hashlib
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.search_result_enrichment import (  # noqa: E402
    build_body_hash,
    persist_latest_search_result_enrichment,
)


class Cursor:
    def __init__(self):
        self.executed = []
        self.rowcount = 1

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()).lower(), params))


class SearchResultEnrichmentTest(unittest.TestCase):
    def test_body_hash_is_stable_for_trimmed_text(self):
        expected = hashlib.sha256("본문".encode("utf-8")).hexdigest()
        self.assertEqual(build_body_hash("  본문  "), expected)

    def test_persists_body_and_seller_on_latest_search_result(self):
        cursor = Cursor()
        result = persist_latest_search_result_enrichment(
            cursor,
            "1001",
            body_text="상세 본문",
            self_check_fields={"battery": "normal"},
            seller_profile={
                "store_seq": 77,
                "store_name": "판매자",
                "trust_score": 90,
            },
        )

        self.assertTrue(result["updated"])
        query, params = cursor.executed[0]
        self.assertIn("body_fetched_at", query)
        self.assertIn("seller_store_name", query)
        self.assertEqual(params[0], "1001")
        self.assertEqual(params[1], "상세 본문")
        self.assertEqual(params[5], 77)
        self.assertEqual(params[6], "판매자")


if __name__ == "__main__":
    unittest.main()
