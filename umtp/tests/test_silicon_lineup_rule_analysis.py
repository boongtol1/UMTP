import os
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import listing_analysis_pipeline as pipeline


CASES = (
    ("MacBook Pro", "M3 Pro", 14, 18, 512, "맥북프로 M3 Pro 14인치 18GB 512GB"),
    ("MacBook Neo", "A18 Pro", 13, 8, 512, "맥북 네오 512GB 터치아이디 가능 풀박스"),
    ("iMac", "M4", 24, 16, 256, "iMac M4 24인치 16GB 256GB"),
    ("Mac Studio", "M3 Ultra", 0, 512, 16384, "Mac Studio M3 Ultra RAM 512GB SSD 16TB"),
)
SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
SAVED_AT = datetime(2026, 9, 18, 10)


class SiliconLineupRuleAnalysisTest(unittest.TestCase):
    def _analyze(self, case, *, price=800000, direction="BELOW_OR_EQUAL", rule_changes=None,
                 sort_date=SAVED_AT, include_rule=True):
        spec = dict(zip(SPEC_FIELDS, case[:5]))
        rule = dict(spec, id=14, user_id="lineup-user", enabled=True, saved_at=SAVED_AT,
                    fair_price_krw=1000000, alert_drop_rate_percent=20,
                    alert_price_direction=direction)
        rule.update(rule_changes or {})
        job = dict(id=21, watch_rule_id=14, user_id="lineup-user", product_id="1001",
                   url="https://web.joongna.com/product/1001", title=case[5],
                   price_krw=price, trigger_reason="new", sort_date=sort_date)
        page = dict(title=case[5], listing_price_krw=price, description="정상 판매합니다.",
                    self_check_fields={})
        if case[0] == "MacBook Neo":
            page.update(
                description="네오 512GB라 터치아이디도 됩니다(256GB는 안돼요)",
                self_check_fields={"모델명": "맥북 네오", "CPU종류": "A18",
                                   "램 용량": "8GB", "SSD용량": "512GB"},
            )
        cursor = Mock()
        cursor.execute.side_effect = AssertionError("Unexpected database query")
        with ExitStack() as stack:
            no_connection = stack.enter_context(patch.object(
                pipeline, "get_connection", side_effect=AssertionError("Unexpected DB connection")))
            no_dispatch = stack.enter_context(patch.object(
                pipeline, "dispatch_alert_event_immediately", side_effect=AssertionError("Unexpected dispatch")))
            for name, value in (
                ("fetch_html", "<html>"), ("parse_joongna_listing_page", page),
                ("get_seen_product", {}), ("persist_latest_search_result_enrichment", None),
                ("update_seen_product_content_snapshot", None), ("_resolve_seller_info_for_alert", {}),
                ("analyze_risk", {"risk_level": "none", "risk_score": 0, "risk_keywords": [],
                                  "is_exchange_post": False, "trade_type": "sale"}),
                ("save_listing_analysis_result", {"diff_ratio": 20.0}), ("save_success_log", None),
            ):
                stack.enter_context(patch.object(pipeline, name, return_value=value))
            create = stack.enter_context(patch.object(
                pipeline, "maybe_create_alert_event", return_value={"created": True, "alert_id": 72}))
            # Keep actual detail parsing, spec matching, saved-window filtering,
            # and threshold calculation; replace only I/O boundaries.
            shared = pipeline.analyze_listing_once(job, cursor)
            self.assertTrue(shared["parsed_spec"]["parse_success"], shared["parsed_spec"])
            self.assertEqual({key: shared["parsed_spec"][key] for key in SPEC_FIELDS}, spec)
            result = pipeline.analyze_product_for_watch_rule(job, group_context={
                "connection": Mock(), "cursor": cursor, "shared": shared,
                "rules": {14: rule} if include_rule else {},
            })
            no_connection.assert_not_called()
            no_dispatch.assert_not_called()
            cursor.execute.assert_not_called()
        return result, create

    def test_all_four_lineups_match_the_bound_rule_and_queue_an_alert(self):
        for case in CASES:
            with self.subTest(product=case[0]):
                result, create = self._analyze(case)
                self.assertTrue(result["alert_created"], result)
                self.assertTrue(result["saved_window_allowed"])
                self.assertEqual(result["target_price_krw"], 800000)
                create.assert_called_once()
                self.assertEqual(create.call_args.kwargs["watch_rule_id"], 14)
                self.assertEqual(create.call_args.kwargs["user_id"], "lineup-user")
                self.assertEqual(create.call_args.kwargs["parsed_spec"]["product_type"], case[0])

    def test_price_threshold_is_inclusive_in_both_directions(self):
        for case in CASES:
            for direction in ("BELOW_OR_EQUAL", "ABOVE_OR_EQUAL"):
                for price in (799999, 800000, 800001):
                    with self.subTest(product=case[0], direction=direction, price=price):
                        result, create = self._analyze(case, price=price, direction=direction)
                        expected = price <= 800000 if direction == "BELOW_OR_EQUAL" else price >= 800000
                        self.assertEqual(result["is_alert_target"], expected, result)
                        self.assertEqual(create.call_count, int(expected))

    def test_rule_ownership_spec_enabled_and_saved_time_gates_are_enforced(self):
        cases = (
            ({"rule_changes": {"enabled": False}}, "watch_rule_disabled"),
            ({"rule_changes": {"user_id": "another-user"}}, "watch_rule_user_mismatch"),
            ({"rule_changes": {"ssd_gb": 1024}}, "watch_rule_spec_mismatch"),
            ({"rule_changes": {"saved_at": None}}, "saved_at_missing"),
            ({"sort_date": None}, "sort_date_missing"),
            ({"sort_date": SAVED_AT - timedelta(seconds=1)}, "sort_date_before_saved_at"),
            ({"include_rule": False}, "watch_rule_missing"),
        )
        for case in CASES:
            for options, reason in cases:
                with self.subTest(product=case[0], reason=reason):
                    result, create = self._analyze(case, **options)
                    self.assertFalse(result["is_alert_target"], result)
                    self.assertEqual(result["alert_skip_reason"], reason)
                    create.assert_not_called()

    def test_price_bounds_still_apply_after_rule_matching(self):
        for case in CASES:
            for direction, bounds, reason in (
                ("BELOW_OR_EQUAL", {"min_price_krw": 800001}, "below_min_price_bound"),
                ("ABOVE_OR_EQUAL", {"max_price_krw": 799999}, "above_max_price_bound"),
            ):
                with self.subTest(product=case[0], direction=direction):
                    result, create = self._analyze(case, direction=direction, rule_changes=bounds)
                    self.assertFalse(result["alert_created"], result)
                    self.assertEqual(result["alert_skip_reason"], reason)
                    create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
