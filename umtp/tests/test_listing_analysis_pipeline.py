import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.listing_analysis_pipeline import analyze_product_for_watch_rule  # noqa: E402


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return None

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class ListingAnalysisPipelineTest(unittest.TestCase):
    def test_unmatched_watch_rule_does_not_create_alert(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.listing_analysis_pipeline.fetch_html", return_value="<html></html>"):
            with patch(
                "src.listing_analysis_pipeline.parse_joongna_listing_page",
                return_value={
                    "title": "맥북에어 M2 16GB 512GB",
                    "description": "테스트",
                    "listing_price_krw": 600000,
                    "self_check_fields": {},
                },
            ):
                with patch(
                    "src.listing_analysis_pipeline.parse_listing_title",
                    return_value={
                        "parse_success": True,
                        "product_type": "MacBook Air",
                        "chip": "M2",
                        "screen_inch": 13,
                        "ram_gb": 16,
                        "ssd_gb": 512,
                        "confidence_score": 100,
                        "screen_inch_defaulted": False,
                        "unit_valid": True,
                        "unit_validation_reason": None,
                    },
                ):
                    with patch(
                        "src.listing_analysis_pipeline._get_watch_rule_by_id",
                        return_value={
                            "id": 1,
                            "user_id": "boongtol",
                            "product_type": "MacBook Air",
                            "chip": "M1",
                            "screen_inch": 13,
                            "ram_gb": 8,
                            "ssd_gb": 256,
                            "fair_price_krw": 800000,
                            "target_price_krw": 650000,
                            "alert_drop_rate_percent": 18.75,
                        },
                    ):
                        with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                            with patch(
                                "src.listing_analysis_pipeline.save_listing_analysis_result",
                                return_value={"analysis_result_id": 1, "diff_ratio": 25.0},
                            ):
                                with patch(
                                    "src.listing_analysis_pipeline.maybe_create_alert_event"
                                ) as mock_create_alert:
                                    result = analyze_product_for_watch_rule(
                                        {
                                            "id": 1,
                                            "product_id": "1001",
                                            "url": "https://web.joongna.com/product/1001",
                                            "user_id": "boongtol",
                                            "watch_rule_id": 1,
                                            "trigger_reason": "price_changed",
                                            "search_keyword": "맥북",
                                        }
                                    )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("matched_watch_rule"))
        self.assertFalse(result.get("alert_created"))
        self.assertEqual(mock_create_alert.call_count, 0)

    def test_matched_watch_rule_and_price_condition_creates_alert(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.listing_analysis_pipeline.fetch_html", return_value="<html></html>"):
            with patch(
                "src.listing_analysis_pipeline.parse_joongna_listing_page",
                return_value={
                    "title": "맥북에어 M1 8GB 256GB",
                    "description": "테스트",
                    "listing_price_krw": 600000,
                    "self_check_fields": {},
                },
            ):
                with patch(
                    "src.listing_analysis_pipeline.parse_listing_title",
                    return_value={
                        "parse_success": True,
                        "product_type": "MacBook Air",
                        "chip": "M1",
                        "screen_inch": 13,
                        "ram_gb": 8,
                        "ssd_gb": 256,
                        "confidence_score": 100,
                        "screen_inch_defaulted": False,
                        "unit_valid": True,
                        "unit_validation_reason": None,
                    },
                ):
                    with patch(
                        "src.listing_analysis_pipeline._get_watch_rule_by_id",
                        return_value={
                            "id": 1,
                            "user_id": "boongtol",
                            "product_type": "MacBook Air",
                            "chip": "M1",
                            "screen_inch": 13,
                            "ram_gb": 8,
                            "ssd_gb": 256,
                            "fair_price_krw": 800000,
                            "target_price_krw": 650000,
                            "alert_drop_rate_percent": 18.75,
                        },
                    ):
                        with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                            with patch(
                                "src.listing_analysis_pipeline.save_listing_analysis_result",
                                return_value={"analysis_result_id": 2, "diff_ratio": 25.0},
                            ):
                                with patch(
                                    "src.listing_analysis_pipeline.maybe_create_alert_event",
                                    return_value={"created": True, "alert_id": 9},
                                ) as mock_create_alert:
                                    result = analyze_product_for_watch_rule(
                                        {
                                            "id": 2,
                                            "product_id": "1002",
                                            "url": "https://web.joongna.com/product/1002",
                                            "user_id": "boongtol",
                                            "watch_rule_id": 1,
                                            "trigger_reason": "price_changed",
                                            "search_keyword": "맥북",
                                        }
                                    )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("matched_watch_rule"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertTrue(result.get("alert_created"))
        self.assertEqual(result.get("alert_event_id"), 9)
        self.assertEqual(mock_create_alert.call_count, 1)


if __name__ == "__main__":
    unittest.main()
