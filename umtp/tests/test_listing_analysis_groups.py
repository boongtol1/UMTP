"""Offline regressions for shared analysis and atomic recipient publication."""
import os
import sys
import unittest
from contextlib import ExitStack, nullcontext
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import listing_analysis_pipeline as pipeline


SPEC = {"parse_success": True, "product_type": "MacBook Air", "chip": "M2", "screen_inch": 13, "ram_gb": 8, "ssd_gb": 256}


def rule(rule_id, user_id, **overrides):
    return dict({"id": rule_id, "user_id": user_id, **SPEC, "enabled": True,
                 "fair_price_krw": 1000000, "alert_drop_rate_percent": 20,
                 "alert_price_direction": "BELOW_OR_EQUAL", "target_buy_price_krw": 800000,
                 "saved_at": "2026-09-01 00:00:00"}, **overrides)


def job(rule_id, user_id):
    return {"id": rule_id, "source": "joongna", "product_id": "123", "watch_rule_id": rule_id,
            "user_id": user_id, "url": "https://web.joongna.com/product/123",
            "title": "맥북에어 M2 8GB 256GB", "price_krw": 600000,
            "trigger_reason": "new", "sort_date": "2026-09-17 10:00:00", "change_fingerprint": "revision-1"}


class Cursor:
    description = []

    def __init__(self, rules):
        self.rules, self.executed, self.lastrowid = rules, [], 100

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()).lower(), params))
        if query.lstrip().lower().startswith("insert"):
            self.lastrowid += 1

    def fetchone(self):
        return None

    def fetchall(self):
        return self.rules

    def close(self):
        pass


class Connection:
    def __init__(self, rules):
        self.query_cursor = Cursor(rules)
        self.commits, self.rollbacks, self.closed = 0, 0, False

    def cursor(self):
        return self.query_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def is_connected(self):
        return not self.closed

    def close(self):
        self.closed = True


class ListingAnalysisGroupsTest(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.fetch = self.mock("fetch_html", return_value="<html>")
        self.page = self.mock("parse_joongna_listing_page", return_value={
            "title": "맥북에어 M2 8GB 256GB", "description": "정상 작동", "listing_price_krw": 600000,
            "self_check_fields": {},
        })
        self.spec = self.mock("parse_listing_title", return_value=SPEC)
        self.risk = self.mock("analyze_risk", return_value={"risk_score": 0, "risk_level": "LOW"})
        self.snapshot = self.mock("update_seen_product_content_snapshot")
        self.enrichment = self.mock("persist_latest_search_result_enrichment")
        self.mock("get_seen_product", return_value={})
        self.seller = self.mock(
            "_resolve_seller_info_for_alert",
            return_value={"seller_store_seq": 1234, "seller_store_name": "seller"},
        )
        self.store = self.mock("_ensure_store_snapshots_before_fraud_scoring")
        self.fraud = self.mock("score_alert_fraud_probability_comparison", return_value={})
        self.failed = self.mock("mark_analysis_job_failed")
        self.mock("_mark_seen_product_status")
        self.mock("save_success_log")
        self.single_dispatch = self.mock("dispatch_alert_event_immediately")
        self.batch_dispatch = self.mock("dispatch_alert_events_immediately", return_value={"results": []})

    def mock(self, name, **kwargs):
        return self.stack.enter_context(patch.object(pipeline, name, **kwargs))

    def connect(self, rules):
        connection = Connection(rules)
        self.mock("get_connection", return_value=connection)
        return connection

    def test_two_users_share_fetch_parse_risk_and_publish_after_one_commit(self):
        connection = self.connect([rule(1, "u1"), rule(2, "u2", fair_price_krw=900000)])

        def send(alert_ids):
            self.assertEqual(connection.commits, 1)
            self.assertTrue(connection.closed)
            self.assertEqual(len(alert_ids), 2)
            self.assertTrue(any("update analysis_jobs set status = 'done'" in query for query, _ in connection.query_cursor.executed))
            return {"results": [{"alert_id": value, "status": "sent"} for value in alert_ids]}

        self.batch_dispatch.side_effect = send
        results = pipeline.process_analysis_group([job(1, "u1"), job(2, "u2")])
        self.assertTrue(all(item["ok"] for item in results))
        self.assertEqual([item["result"]["fair_price_krw"] for item in results], [1000000, 900000])
        self.fetch.assert_called_once()
        self.page.assert_called_once()
        self.risk.assert_called_once()
        self.seller.assert_called_once()
        self.snapshot.assert_called_once()
        self.enrichment.assert_called_once()
        self.store.assert_called_once()
        self.assertEqual(self.fraud.call_count, 2)  # personal discount is a model feature
        self.batch_dispatch.assert_called_once()
        self.single_dispatch.assert_not_called()
        queries = [query for query, _ in connection.query_cursor.executed]
        self.assertEqual(sum("from user_fair_prices" in query for query in queries), 1)

    def test_matching_prices_reuse_fraud_scoring(self):
        self.connect([rule(1, "u1"), rule(2, "u2")])
        pipeline.process_analysis_group([job(1, "u1"), job(2, "u2")])
        self.fraud.assert_called_once()

    def test_bulk_rules_preserve_enable_owner_specs_saved_window_and_bounds(self):
        rows = [rule(1, "u1"), rule(2, "u2", enabled=False), rule(3, "other"),
                rule(4, "u4", chip="M3"), rule(5, "u5", saved_at="2026-09-18 00:00:00"),
                rule(6, "u6", min_price_krw=700000), rule(7, "u7", target_buy_price_krw=500000)]
        self.connect(rows)
        results = pipeline.process_analysis_group([job(index, f"u{index}") for index in range(1, 8)])
        self.assertEqual([row["result"]["alert_created"] for row in results], [True, False, False, False, False, False, False])
        self.assertEqual(results[1]["result"]["alert_skip_reason"], "watch_rule_disabled")
        self.assertEqual(results[2]["result"]["alert_skip_reason"], "watch_rule_user_mismatch")
        self.assertEqual(results[3]["result"]["alert_skip_reason"], "watch_rule_spec_mismatch")
        self.assertEqual(results[4]["result"]["alert_skip_reason"], "sort_date_before_saved_at")
        self.assertEqual(results[5]["result"]["alert_skip_reason"], "below_min_price_bound")

    def test_above_direction_and_saved_at_equality_still_match(self):
        self.connect([rule(1, "u1", alert_price_direction="ABOVE_OR_EQUAL", target_buy_price_krw=500000,
                           max_price_krw=600000, saved_at="2026-09-17 10:00:00")])
        results = pipeline.process_analysis_group([job(1, "u1")])
        self.assertTrue(results[0]["result"]["alert_created"])

    def test_recipient_error_rolls_back_all_alerts_without_partial_send(self):
        connection = self.connect([rule(1, "u1"), rule(2, "u2")])
        self.mock("save_listing_analysis_result", side_effect=[{"diff_ratio": 0}, RuntimeError("disk full")])
        results = pipeline.process_analysis_group([job(1, "u1"), job(2, "u2")])
        self.assertTrue(all(not result["ok"] for result in results))
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.batch_dispatch.assert_not_called()
        self.assertEqual(self.failed.call_count, 2)

    def test_dispatch_failure_preserves_committed_work_for_notification_retry(self):
        connection = self.connect([rule(1, "u1")])
        self.batch_dispatch.side_effect = RuntimeError("FCM down")
        result = pipeline.process_analysis_group([job(1, "u1")])[0]
        self.assertTrue(result["ok"])
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.failed.assert_not_called()

    def test_detail_failure_does_not_erase_previously_observed_body(self):
        self.connect([rule(1, "u1")])
        self.fetch.side_effect = RuntimeError("timeout")
        results = pipeline.process_analysis_group([job(1, "u1")])
        self.assertTrue(results[0]["ok"])
        self.snapshot.assert_not_called()
        self.assertEqual(results[0]["result"]["detail_fetch_error"], "timeout")

    def test_worker_limit_counts_events_without_splitting_recipients(self):
        self.connect([rule(index, f"u{index}") for index in range(1, 25)])
        jobs = [job(index, f"u{index}") for index in range(1, 25)]
        claim = self.mock("claim_pending_analysis_group", return_value=nullcontext(jobs))
        stats = pipeline.process_pending_analysis_jobs(limit=1)
        self.assertEqual(stats["done"], 24)
        self.assertEqual(stats["detail_fetch_count"], 1)
        self.assertEqual(stats["event_groups"], 1)
        claim.assert_called_once()
        self.fetch.assert_called_once()

    def test_mixed_revisions_rejected_before_fetch(self):
        jobs = [job(1, "u1"), dict(job(2, "u2"), change_fingerprint="revision-2")]
        with self.assertRaisesRegex(ValueError, "mixed_analysis_group"):
            pipeline.process_analysis_group(jobs)
        self.fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
