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
    should_fetch_detail,
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
            "watch_rule_id": None,
            "sort_date": "2026-05-16 12:00:00",
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

    def _run_pipeline_for_price_rule(self, *, listing_price_krw, resolved_fair_price):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.listing_analysis_pipeline.fetch_html", return_value="<html></html>"):
            with patch(
                "src.listing_analysis_pipeline.parse_joongna_listing_page",
                return_value={
                    "title": "맥북에어 M2 8GB 256GB",
                    "description": "테스트",
                    "listing_price_krw": listing_price_krw,
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
                            return_value=resolved_fair_price,
                        ):
                            with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                                with patch(
                                    "src.listing_analysis_pipeline.save_listing_analysis_result",
                                    return_value={"analysis_result_id": 5, "diff_ratio": 0.0},
                                ):
                                    with patch("src.listing_analysis_pipeline.save_success_log"):
                                        with patch(
                                            "src.listing_analysis_pipeline.maybe_create_alert_event",
                                            return_value={"created": True, "alert_id": 71},
                                        ) as mock_create_alert:
                                            result = analyze_product_for_watch_rule(self._build_job())
        return result, mock_create_alert.call_count

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

    def test_watch_rule_id_keeps_rule_scoped_price_resolution(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)
        job = self._build_job()
        job["watch_rule_id"] = 3

        with patch("src.listing_analysis_pipeline.fetch_html", return_value="<html></html>"):
            with patch(
                "src.listing_analysis_pipeline.parse_joongna_listing_page",
                return_value={
                    "title": "맥북에어 m5",
                    "description": "m5 맥북에어 15인치 기본형입니다",
                    "listing_price_krw": 1700000,
                    "self_check_fields": {},
                },
            ):
                with patch(
                    "src.listing_analysis_pipeline.parse_listing_title",
                    return_value={
                        "parse_success": True,
                        "product_type": "MacBook Air",
                        "chip": "M5",
                        "screen_inch": 15,
                        "ram_gb": 16,
                        "ssd_gb": 512,
                        "confidence_score": 100,
                        "screen_inch_defaulted": False,
                        "unit_valid": True,
                        "unit_validation_reason": None,
                    },
                ):
                    with patch(
                        "src.listing_analysis_pipeline.resolve_fair_price_for_watch_rule",
                        return_value=None,
                    ) as mock_rule_resolve:
                        with patch(
                            "src.listing_analysis_pipeline.resolve_fair_price_for_user"
                        ) as mock_user_resolve:
                            with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
                                with patch(
                                    "src.listing_analysis_pipeline.save_listing_analysis_result",
                                    return_value={"analysis_result_id": 11, "diff_ratio": 0.0},
                                ):
                                    with patch("src.listing_analysis_pipeline.save_success_log"):
                                        with patch(
                                            "src.listing_analysis_pipeline._evaluate_watch_rule_saved_window",
                                            return_value=(True, None),
                                        ):
                                            with patch(
                                                "src.listing_analysis_pipeline.maybe_create_alert_event"
                                            ) as mock_create_alert:
                                                result = analyze_product_for_watch_rule(job)

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertFalse(result.get("alert_created"))
        self.assertEqual(result.get("alert_skip_reason"), "watch_rule_spec_mismatch")
        self.assertEqual(mock_create_alert.call_count, 0)
        self.assertEqual(mock_rule_resolve.call_count, 1)
        self.assertEqual(mock_user_resolve.call_count, 0)

    def test_base_model_keyword_parsed_listing_creates_alert(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)

        with patch("src.listing_analysis_pipeline.fetch_html", return_value="<html></html>"):
            with patch(
                "src.listing_analysis_pipeline.parse_joongna_listing_page",
                return_value={
                    "title": "맥북에어 m2 기본형",
                    "description": "테스트",
                    "listing_price_krw": 600000,
                    "self_check_fields": {},
                },
            ):
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
                                return_value={"analysis_result_id": 4, "diff_ratio": 25.0},
                            ) as mock_save_result:
                                with patch("src.listing_analysis_pipeline.save_success_log"):
                                    with patch(
                                        "src.listing_analysis_pipeline.maybe_create_alert_event",
                                        return_value={"created": True, "alert_id": 31},
                                    ) as mock_create_alert:
                                        result = analyze_product_for_watch_rule(self._build_job())

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertTrue(result.get("alert_created"))
        self.assertEqual(result.get("alert_event_id"), 31)
        self.assertEqual(mock_create_alert.call_count, 1)

        parsed_spec = mock_save_result.call_args.kwargs.get("parsed_spec")
        self.assertTrue(parsed_spec.get("parse_success"))
        self.assertEqual(parsed_spec.get("product_type"), "MacBook Air")
        self.assertEqual(parsed_spec.get("chip"), "M2")
        self.assertEqual(parsed_spec.get("ram_gb"), 8)
        self.assertEqual(parsed_spec.get("ssd_gb"), 256)

    def test_below_or_equal_alert_when_listing_is_lower_than_target(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=790000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": 20.50,
                "target_buy_price_krw": 795000,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertEqual(result.get("alert_price_direction"), "BELOW_OR_EQUAL")
        self.assertEqual(result.get("target_price_krw"), 795000)
        self.assertEqual(create_alert_call_count, 1)

    def test_above_or_equal_alert_with_negative_drop_rate_when_listing_is_higher(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=1150000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": -10.00,
                "target_buy_price_krw": 1100000,
                "alert_price_direction": "ABOVE_OR_EQUAL",
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertEqual(result.get("alert_price_direction"), "ABOVE_OR_EQUAL")
        self.assertEqual(result.get("target_price_krw"), 1100000)
        self.assertEqual(create_alert_call_count, 1)

    def test_above_or_equal_alert_skips_when_listing_is_below_target(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=1050000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": -10.00,
                "target_buy_price_krw": 1100000,
                "alert_price_direction": "ABOVE_OR_EQUAL",
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertEqual(result.get("alert_skip_reason"), "price_below_threshold")
        self.assertEqual(create_alert_call_count, 0)

    def test_below_or_equal_alert_with_negative_drop_rate_matches_lower_listing(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=1050000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": -10.00,
                "target_buy_price_krw": 1100000,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertEqual(result.get("alert_price_direction"), "BELOW_OR_EQUAL")
        self.assertEqual(create_alert_call_count, 1)

    def test_below_or_equal_with_min_price_bound_excludes_too_low_listing(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=290000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": 20.00,
                "target_buy_price_krw": 800000,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "min_price_krw": 300000,
                "max_price_krw": None,
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertEqual(result.get("alert_skip_reason"), "below_min_price_bound")
        self.assertEqual(create_alert_call_count, 0)

    def test_above_or_equal_with_max_price_bound_excludes_too_high_listing(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=910000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": -10.00,
                "target_buy_price_krw": 900000,
                "alert_price_direction": "ABOVE_OR_EQUAL",
                "min_price_krw": None,
                "max_price_krw": 900000,
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("is_alert_target"))
        self.assertEqual(result.get("alert_skip_reason"), "above_max_price_bound")
        self.assertEqual(create_alert_call_count, 0)

    def test_null_bounds_keep_direction_behavior(self):
        result, create_alert_call_count = self._run_pipeline_for_price_rule(
            listing_price_krw=790000,
            resolved_fair_price={
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": 20.50,
                "target_buy_price_krw": 795000,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "min_price_krw": None,
                "max_price_krw": None,
                "source": "user_fair_prices",
            },
        )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("is_alert_target"))
        self.assertEqual(create_alert_call_count, 1)

    def test_should_fetch_detail_for_new_listing(self):
        should_fetch, reason = should_fetch_detail(
            {"title": "맥북 팝니다", "price": 1000000},
            "new",
            {"parse_success": True, "chip": "M2", "ram_gb": 8, "ssd_gb": 256},
            target_price_krw=900000,
        )

        self.assertTrue(should_fetch)
        self.assertEqual(reason, "new")

    def test_should_not_fetch_detail_for_unchanged_listing(self):
        should_fetch, reason = should_fetch_detail(
            {"title": "맥북 팝니다", "price": 1000000},
            "unchanged",
            {"parse_success": False, "parse_failure_reason": "missing_required_fields"},
            target_price_krw=900000,
        )

        self.assertFalse(should_fetch)
        self.assertEqual(reason, "unchanged")

    def test_should_fetch_detail_when_title_parse_failed(self):
        should_fetch, reason = should_fetch_detail(
            {"title": "상태좋고 저렴합니다", "price": 1000000},
            "price_changed",
            {"parse_success": False, "parse_failure_reason": "missing_required_fields"},
            target_price_krw=900000,
        )

        self.assertTrue(should_fetch)
        self.assertEqual(reason, "title_parse_failed")

    def test_should_fetch_detail_when_product_name_only_and_specs_missing(self):
        should_fetch, reason = should_fetch_detail(
            {"title": "맥북에어 급처", "price": 1000000},
            "price_changed",
            {
                "parse_success": False,
                "parse_failure_reason": "missing_required_fields",
                "missing_fields": ["chip", "ram_gb", "ssd_gb"],
            },
            target_price_krw=900000,
        )

        self.assertTrue(should_fetch)
        self.assertEqual(reason, "product_only_spec_missing")

    def test_should_fetch_detail_when_price_is_cheap(self):
        should_fetch, reason = should_fetch_detail(
            {"title": "맥북에어 M2 8GB 256GB", "price": 700000},
            "price_changed",
            {"parse_success": True, "chip": "M2", "ram_gb": 8, "ssd_gb": 256},
            target_price_krw=800000,
        )

        self.assertTrue(should_fetch)
        self.assertEqual(reason, "price_cheap")

    def test_unchanged_listing_skips_detail_fetch_function_call(self):
        fake_cursor = _FakeCursor()
        fake_connection = _FakeConnection(fake_cursor)
        job = self._build_job()
        job["trigger_reason"] = "unchanged"

        with patch("src.listing_analysis_pipeline.get_connection", return_value=fake_connection):
            with patch("src.listing_analysis_pipeline.fetch_html") as mock_fetch_html:
                result = analyze_product_for_watch_rule(job)

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("analysis_skipped"))
        self.assertEqual(result.get("analysis_skip_reason"), "unchanged")
        self.assertFalse(result.get("detail_fetch_performed"))
        self.assertEqual(result.get("detail_skipped_reason"), "unchanged")
        self.assertEqual(mock_fetch_html.call_count, 0)

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
