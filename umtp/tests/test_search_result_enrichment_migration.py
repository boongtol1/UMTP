import os
import unittest


class SearchResultEnrichmentMigrationTest(unittest.TestCase):
    def test_migration_adds_body_metadata_and_refresh_index(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(project_root, "sql", "migrate_search_result_enrichment.sql")
        with open(path, "r", encoding="utf-8") as handle:
            sql = handle.read().lower()

        self.assertIn("body_hash", sql)
        self.assertIn("body_fetched_at", sql)
        self.assertIn("self_check_json", sql)
        self.assertIn("joongna_store_profiles", sql)
        self.assertIn("trust_score", sql)
        self.assertIn("idx_seen_content_refresh", sql)


if __name__ == "__main__":
    unittest.main()
