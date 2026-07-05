import os
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import fraud_probability_features  # noqa: E402


SELLER_HISTORY_COLUMNS = [
    "has_seller_history",
    "seller_search_result_count_before",
    "seller_search_result_count_7d",
    "seller_seen_product_count_before",
    "seller_seen_product_count_24h",
    "seller_seen_product_count_7d",
    "seller_history_age_hours",
    "seller_avg_price_7d",
    "seller_min_price_7d",
    "seller_max_price_7d",
    "seller_product_snapshot_count_before",
    "seller_product_snapshot_count_7d",
    "seller_price_change_count_7d",
    "seller_content_change_count_7d",
    "seller_alert_count_before",
    "seller_alert_count_30d",
    "seller_alert_product_count_30d",
    "seller_store_name_change_count_before",
    "seller_store_name_change_count_30d",
]


class FraudProbabilityFeaturesTest(unittest.TestCase):
    def test_training_sql_includes_seller_history_columns(self):
        sql = fraud_probability_features.TRAINING_FEATURE_SQL

        self.assertIn("seller_search_history AS", sql)
        self.assertIn("seller_snapshot_history AS", sql)
        self.assertIn("seller_alert_history AS", sql)
        self.assertIn("seller_store_name_history AS", sql)
        for column in SELLER_HISTORY_COLUMNS:
            self.assertIn(column, sql)

    def test_write_training_features_csv_preserves_seller_history_columns(self):
        row = {
            "label": 1,
            "product_id": "p1",
            "store_id": "s1",
            "title_text": "title",
            "body_text": "body",
        }
        for column in SELLER_HISTORY_COLUMNS:
            row[column] = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "training_features.csv")
            with patch.object(fraud_probability_features, "fetch_training_feature_rows", return_value=[row]):
                result = fraud_probability_features.write_training_features_csv(output_path)

            with open(output_path, "r", encoding="utf-8") as output_file:
                header = output_file.readline().strip().split(",")

        self.assertEqual(result["row_count"], 1)
        for column in SELLER_HISTORY_COLUMNS:
            self.assertIn(column, header)


if __name__ == "__main__":
    unittest.main()
