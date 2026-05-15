import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.listing_analysis_pipeline import (  # noqa: E402
    analyze_product_for_watch_rule,
    process_analysis_job,
    process_pending_analysis_jobs,
)


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
    def _build_job(self):
        return {
            "id": 1,
            "product_id": "1001",
            "url": "https://web.joongna.com/product/1001",
            "user_id": "boongtol",
            "watch_rule_id": 1,
            "trigger_reason": "price_changed",
            "search_keyword": "맥북",
        }

    def _mock_parsing(self):
        return patch(
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
        )

    def test_fair_price_missing_does_not_create_alert(self):
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
                with self._mock_parsing():
                    with patch(
                        "src.listing_analysis_pipeline.is_user_fair_price_target_enabled",
                        return_value=True,
                    ):
                        with patch(
                            "src.listing_analysis_pipeline.resolve_fair_price_for_user",
                            return_value=None,
                        ):
                            with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                                with patch(
                                    "src.listing_analysis_pipeline.save_listing_analysis_result",
                                    return_value={"analysis_result_id": 1, "diff_ratio": 0.0},
                                ):
                                    with patch("src.listing_analysis_pipeline.save_success_log"):
                                        with patch(
                                            "src.listing_analysis_pipeline.maybe_create_alert_event"
                                        ) as mock_create_alert:
                                            result = analyze_product_for_watch_rule(self._build_job())

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertFalse(result.get("alert_created"))
        self.assertEqual(result.get("alert_skip_reason"), "fair_price_missing")
        self.assertEqual(mock_create_alert.call_count, 0)

    def test_user_override_price_can_create_alert(self):
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
                with self._mock_parsing():
                    with patch(
                        "src.listing_analysis_pipeline.is_user_fair_price_target_enabled",
                        return_value=True,
                    ):
                        with patch(
                            "src.listing_analysis_pipeline.resolve_fair_price_for_user",
                            return_value={
                                "fair_price_krw": 800000,
                                "alert_drop_rate_percent": 20.0,
                                "source": "user_fair_prices",
                            },
                        ):
                            with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                                with patch(
                                    "src.listing_analysis_pipeline.save_listing_analysis_result",
                                    return_value={"analysis_result_id": 2, "diff_ratio": 25.0},
                                ):
                                    with patch("src.listing_analysis_pipeline.save_success_log"):
                                        with patch(
                                            "src.listing_analysis_pipeline.maybe_create_alert_event",
                                            return_value={"created": True, "alert_id": 9},
                                        ) as mock_create_alert:
                                            result = analyze_product_for_watch_rule(self._build_job())

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertTrue(result.get("alert_created"))
        self.assertEqual(result.get("alert_event_id"), 9)
        self.assertEqual(result.get("fair_price_source"), "user_fair_prices")
        self.assertEqual(mock_create_alert.call_count, 1)

    def test_system_fallback_price_source_is_mac_fair_prices(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.listing_analysis_pipeline.fetch_html", return_value="<html></html>"):
            with patch(
                "src.listing_analysis_pipeline.parse_joongna_listing_page",
                return_value={
                    "title": "맥북에어 M1 8GB 256GB",
                    "description": "테스트",
                    "listing_price_krw": 700000,
                    "self_check_fields": {},
                },
            ):
                with self._mock_parsing():
                    with patch(
                        "src.listing_analysis_pipeline.is_user_fair_price_target_enabled",
                        return_value=True,
                    ):
                        with patch(
                            "src.listing_analysis_pipeline.resolve_fair_price_for_user",
                            return_value={
                                "fair_price_krw": 800000,
                                "alert_drop_rate_percent": 20.0,
                                "source": "mac_fair_prices",
                            },
                        ):
                            with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                                with patch(
                                    "src.listing_analysis_pipeline.save_listing_analysis_result",
                                    return_value={"analysis_result_id": 2, "diff_ratio": 12.5},
                                ):
                                    with patch("src.listing_analysis_pipeline.save_success_log"):
                                        with patch(
                                            "src.listing_analysis_pipeline.maybe_create_alert_event"
                                        ) as mock_create_alert:
                                            result = analyze_product_for_watch_rule(self._build_job())

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertEqual(result.get("fair_price_source"), "mac_fair_prices")
        self.assertEqual(result.get("alert_skip_reason"), "drop_rate_below_threshold")
        self.assertEqual(mock_create_alert.call_count, 0)

    def test_disabled_toggle_never_creates_alert(self):
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
                with self._mock_parsing():
                    with patch(
                        "src.listing_analysis_pipeline.is_user_fair_price_target_enabled",
                        return_value=False,
                    ):
                        with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                            with patch(
                                "src.listing_analysis_pipeline.save_listing_analysis_result",
                                return_value={"analysis_result_id": 3, "diff_ratio": 0.0},
                            ):
                                with patch("src.listing_analysis_pipeline.save_success_log"):
                                    with patch(
                                        "src.listing_analysis_pipeline.maybe_create_alert_event"
                                    ) as mock_create_alert:
                                        result = analyze_product_for_watch_rule(self._build_job())

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertFalse(result.get("alert_created"))
        self.assertEqual(result.get("alert_skip_reason"), "user_target_disabled")
        self.assertEqual(mock_create_alert.call_count, 0)

    def test_process_analysis_job_skips_when_not_pending(self):
        job = {"id": 10, "product_id": "1001"}

        with patch("src.listing_analysis_pipeline.mark_analysis_job_started", return_value=False):
            with patch("src.listing_analysis_pipeline.analyze_product_for_watch_rule") as mock_analyze:
                result = process_analysis_job(job)

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("skipped"))
        self.assertEqual(result.get("reason"), "job_not_pending")
        self.assertEqual(mock_analyze.call_count, 0)

    def test_analyze_job_without_user_id_fails(self):
        job = self._build_job()
        job["user_id"] = None

        with self.assertRaises(ValueError):
            analyze_product_for_watch_rule(job)

    def test_process_pending_analysis_jobs_counts_skipped(self):
        jobs = [{"id": 11, "product_id": "1002"}]

        with patch("src.listing_analysis_pipeline.get_pending_analysis_jobs", return_value=jobs):
            with patch(
                "src.listing_analysis_pipeline.process_analysis_job",
                return_value={"ok": True, "skipped": True, "job_id": 11, "reason": "job_not_pending"},
            ):
                stats = process_pending_analysis_jobs(limit=20)

        self.assertEqual(stats.get("fetched"), 1)
        self.assertEqual(stats.get("skipped"), 1)
        self.assertEqual(stats.get("done"), 0)
        self.assertEqual(stats.get("failed"), 0)


if __name__ == "__main__":
    unittest.main()
