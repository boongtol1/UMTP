import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import fraud_probability_service as service  # noqa: E402


class _CapturingModel:
    def __init__(self, positive_probability=0.92):
        self.features = None
        self.positive_probability = positive_probability

    def predict_proba(self, rows):
        self.features = rows[0]
        return [[1 - self.positive_probability, self.positive_probability]]


class FraudProbabilityServiceTest(unittest.TestCase):
    def test_build_features_includes_v2_text_and_seller_history(self):
        features = service._build_features(
            search_result={
                "title": "검색 제목",
                "body_text": "검색 본문",
                "price": 700000,
                "sort_date": datetime(2026, 7, 5, 13, 30),
                "seller_store_name": "상점",
                "seller_profile_image_url": "https://example.test/profile.png",
                "seller_review_count": 3,
            },
            activity={},
            profile={},
            seller_history={
                "has_seller_history": 1,
                "seller_seen_product_count_7d": 4,
                "seller_content_change_count_7d": 2,
            },
            alert_context={
                "title": "알림 제목",
                "body_text": "알림 본문",
                "risk_level": "high",
                "trade_type": "sale",
            },
        )

        self.assertEqual(features["title_text"], "알림 제목")
        self.assertEqual(features["body_text"], "알림 본문")
        self.assertEqual(features["has_seller_history"], 1.0)
        self.assertEqual(features["seller_seen_product_count_7d"], 4.0)
        self.assertEqual(features["seller_content_change_count_7d"], 2.0)
        self.assertIn("seller_alert_count_30d", features)
        self.assertEqual(features["risk_level"], "high")

    def test_score_alert_passes_v2_features_to_model(self):
        model = _CapturingModel()
        artifact = {
            "model": model,
            "model_version": "fraud-logreg-tfidf-v2",
        }
        feature_time = datetime(2026, 7, 5, 13, 30)

        with patch.object(service, "_load_model_artifact", return_value=artifact):
            with patch.object(
                service,
                "_fetch_first_search_result",
                return_value={
                    "title": "검색 제목",
                    "body_text": "검색 본문",
                    "price": 700000,
                    "sort_date": feature_time,
                    "seller_store_seq": "s1",
                    "seller_store_name": "상점",
                    "seller_profile_image_url": "",
                    "seller_review_count": 0,
                    "fetched_at": feature_time,
                },
            ):
                with patch.object(service, "_fetch_latest_activity", return_value={}):
                    with patch.object(service, "_fetch_latest_profile", return_value={}):
                        with patch.object(
                            service,
                            "_fetch_seller_history",
                            return_value={
                                "has_seller_history": 1,
                                "seller_seen_product_count_7d": 4,
                            },
                        ) as mock_history:
                            result = service.score_alert_fraud_probability(
                                object(),
                                product_id="p1",
                                store_id="s1",
                                alert_context={
                                    "title": "알림 제목",
                                    "body_text": "알림 본문",
                                    "price_krw": 700000,
                                    "risk_level": "high",
                                    "trade_type": "sale",
                                },
                            )

        self.assertEqual(result["fraud_probability"], 0.92)
        self.assertEqual(result["fraud_probability_label"], "HIGH")
        self.assertEqual(result["fraud_model_version"], "fraud-logreg-tfidf-v2")
        self.assertEqual(model.features["title_text"], "알림 제목")
        self.assertEqual(model.features["body_text"], "알림 본문")
        self.assertEqual(model.features["seller_seen_product_count_7d"], 4.0)
        mock_history.assert_called_once()

    def test_score_alert_comparison_scores_v1_and_v2_models(self):
        v1_model = _CapturingModel(0.31)
        v2_model = _CapturingModel(0.82)
        feature_time = datetime(2026, 7, 5, 13, 30)

        with patch.object(service, "_load_v1_model_artifact", return_value={
            "model": v1_model,
            "model_version": "fraud-logreg-v1",
        }):
            with patch.object(service, "_load_v2_model_artifact", return_value={
                "model": v2_model,
                "model_version": "fraud-logreg-tfidf-v2",
            }):
                with patch.object(
                    service,
                    "_fetch_first_search_result",
                    return_value={
                        "title": "검색 제목",
                        "body_text": "검색 본문",
                        "price": 700000,
                        "sort_date": feature_time,
                        "seller_store_seq": "s1",
                        "seller_store_name": "상점",
                        "seller_profile_image_url": "",
                        "seller_review_count": 0,
                        "fetched_at": feature_time,
                    },
                ):
                    with patch.object(service, "_fetch_latest_activity", return_value={}):
                        with patch.object(service, "_fetch_latest_profile", return_value={}):
                            with patch.object(service, "_fetch_seller_history", return_value={}):
                                result = service.score_alert_fraud_probability_comparison(
                                    object(),
                                    product_id="p1",
                                    store_id="s1",
                                    alert_context={
                                        "title": "알림 제목",
                                        "body_text": "알림 본문",
                                        "price_krw": 700000,
                                        "risk_level": "high",
                                        "trade_type": "sale",
                                    },
                                )

        self.assertEqual(result["fraud_probability"], 0.82)
        self.assertEqual(result["fraud_probability_label"], "HIGH")
        self.assertEqual(result["fraud_model_version"], "fraud-logreg-tfidf-v2")
        self.assertEqual(result["fraud_probability_v1"], 0.31)
        self.assertEqual(result["fraud_probability_label_v1"], "MEDIUM")
        self.assertEqual(result["fraud_model_version_v1"], "fraud-logreg-v1")
        self.assertEqual(result["fraud_probability_v2"], 0.82)
        self.assertEqual(result["fraud_probability_label_v2"], "HIGH")
        self.assertEqual(result["fraud_model_version_v2"], "fraud-logreg-tfidf-v2")
        self.assertEqual(v1_model.features["title_text"], "알림 제목")
        self.assertEqual(v2_model.features["body_text"], "알림 본문")


if __name__ == "__main__":
    unittest.main()
