import csv
import os
import sys
import tempfile
import unittest

import joblib


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.train_fraud_probability_model import (  # noqa: E402
    MODEL_VERSION,
    TEXT_FEATURES,
    _load_rows,
    train_model,
)


FIELDNAMES = [
    "label",
    "product_id",
    "store_id",
    "title_text",
    "body_text",
    "price_krw",
    "risk_level",
    "trade_type",
    "has_seller_history",
    "seller_seen_product_count_7d",
]


def _write_training_csv(path):
    rows = []
    for index in range(20):
        label = 1 if index % 2 else 0
        if label:
            title_text = "급매 선입금 택배 거래"
            body_text = "택배만 가능하고 선입금 먼저 부탁드립니다"
            risk_level = "high"
        else:
            title_text = "직거래 안전거래 정상 매물"
            body_text = "직거래 가능하고 구성품 확인 가능합니다"
            risk_level = "none"
        rows.append(
            {
                "label": label,
                "product_id": f"p{index}",
                "store_id": f"s{index % 3}",
                "title_text": title_text,
                "body_text": body_text,
                "price_krw": 1000000 + index,
                "risk_level": risk_level,
                "trade_type": "sale",
                "has_seller_history": 1 if index > 5 else 0,
                "seller_seen_product_count_7d": index % 4,
            }
        )

    with open(path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class TrainFraudProbabilityModelTest(unittest.TestCase):
    def test_load_rows_preserves_text_features(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "features.csv")
            _write_training_csv(input_path)

            rows = _load_rows(input_path)

        features, label, product_id = rows[0]
        self.assertEqual(label, 0)
        self.assertEqual(product_id, "p0")
        self.assertEqual(features["title_text"], "직거래 안전거래 정상 매물")
        self.assertEqual(features["body_text"], "직거래 가능하고 구성품 확인 가능합니다")
        self.assertTrue(TEXT_FEATURES.issubset(features.keys()))

    def test_train_model_saves_tfidf_pipeline_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "features.csv")
            model_path = os.path.join(temp_dir, "model.joblib")
            metrics_path = os.path.join(temp_dir, "metrics.json")
            _write_training_csv(input_path)

            metrics = train_model(
                input_path=input_path,
                model_path=model_path,
                metrics_path=metrics_path,
            )
            artifact = joblib.load(model_path)
            probability = artifact["model"].predict_proba(
                [
                    {
                        "title_text": "급매 선입금 택배 거래",
                        "body_text": "택배만 가능하고 선입금 먼저 부탁드립니다",
                        "price_krw": 1000000,
                        "risk_level": "high",
                        "trade_type": "sale",
                        "has_seller_history": 1,
                        "seller_seen_product_count_7d": 3,
                    }
                ]
            )[0][1]

        self.assertEqual(metrics["model_version"], MODEL_VERSION)
        self.assertEqual(artifact["model_version"], MODEL_VERSION)
        self.assertEqual(artifact["text_features"], sorted(TEXT_FEATURES))
        self.assertIn("feature_schema", metrics)
        self.assertIn("title_tfidf", metrics["feature_schema"])
        self.assertTrue(0.0 <= float(probability) <= 1.0)


if __name__ == "__main__":
    unittest.main()
