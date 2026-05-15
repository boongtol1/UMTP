import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import (  # noqa: E402
    _build_keyword_targets_from_watch_rules,
    parse_sort_date,
    poll_once,
)


class _FakeCursor:
    def close(self):
        return None


class _FakeConnection:
    def __init__(self):
        self._cursor = _FakeCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class PollingWatchRuleKeywordTest(unittest.TestCase):
    def test_parse_sort_date_from_sort_date_key(self):
        self.assertEqual(
            parse_sort_date({"sort_date": " 2026-05-15 12:28:52 "}),
            "2026-05-15 12:28:52",
        )

    def test_parse_sort_date_from_sortDate_key(self):
        self.assertEqual(
            parse_sort_date({"sortDate": "2026-05-15 12:28:52"}),
            "2026-05-15 12:28:52",
        )

    def test_build_keyword_targets_dedupes_keyword_and_keeps_multiple_users(self):
        targets = _build_keyword_targets_from_watch_rules(
            [
                {
                    "id": 1,
                    "user_id": "boongtol",
                    "search_keyword": " 맥북 m1 ",
                },
                {
                    "id": 2,
                    "user_id": "test_user",
                    "search_keyword": "맥북 m1",
                },
            ]
        )

        self.assertEqual(list(targets.keys()), ["맥북 m1"])
        self.assertEqual(len(targets["맥북 m1"]), 2)

    def test_build_keyword_targets_dedupes_same_user(self):
        targets = _build_keyword_targets_from_watch_rules(
            [
                {
                    "id": 1,
                    "user_id": "boongtol",
                    "search_keyword": "맥북 m1",
                },
                {
                    "id": 2,
                    "user_id": "boongtol",
                    "search_keyword": "맥북 m1",
                },
            ]
        )

        self.assertEqual(list(targets.keys()), ["맥북 m1"])
        self.assertEqual(len(targets["맥북 m1"]), 1)
        self.assertEqual(targets["맥북 m1"][0].get("setting_ids"), [1, 2])

    def test_build_keyword_targets_skips_rows_without_toggle_activation_marker(self):
        targets = _build_keyword_targets_from_watch_rules(
            [
                {
                    "id": 1,
                    "user_id": "boongtol",
                    "search_keyword": "m1맥북에어",
                    "enabled": True,
                    "last_poll_requested_at": None,
                },
                {
                    "id": 2,
                    "user_id": "boongtol",
                    "search_keyword": "m2맥북에어",
                    "enabled": True,
                    "last_poll_requested_at": "2026-05-15 12:00:00",
                },
            ]
        )

        self.assertEqual(list(targets.keys()), ["m2맥북에어"])
        self.assertEqual(len(targets["m2맥북에어"]), 1)

    def test_poll_once_enqueues_jobs_for_due_watch_rules(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "맥북",
                "product_type": "MacBook Air",
                "chip": "M1",
                "screen_inch": 13,
                "ram_gb": 8,
                "ssd_gb": 256,
                "target_price_krw": 900000,
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": 10.0,
            },
            {
                "id": 2,
                "user_id": "test_user",
                "search_keyword": "맥북",
                "product_type": "MacBook Air",
                "chip": "M2",
                "screen_inch": 13,
                "ram_gb": 16,
                "ssd_gb": 512,
                "target_price_krw": 1300000,
                "fair_price_krw": 1500000,
                "alert_drop_rate_percent": 13.33,
            },
        ]

        mock_item = {
            "seq": 1001,
            "product_id": 1001,
            "title": "맥북에어 M2 16GB 512GB",
            "price": 1200000,
            "refresh_key": "rk-1",
            "product_url": "https://web.joongna.com/product/1001",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.mark_watch_rule_polled") as mock_mark_polled:
                        with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                            mock_enqueue.return_value = {
                                "ok": True,
                                "created_jobs": [{"job_id": 1}, {"job_id": 2}],
                                "skipped_jobs": [],
                            }
                            stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 1)
        enqueue_args = mock_enqueue.call_args.args
        self.assertEqual(enqueue_args[0].get("product_id"), 1001)
        self.assertEqual(len(enqueue_args[1]), 2)
        self.assertEqual(enqueue_args[2], "new_product")
        self.assertEqual(mock_mark_polled.call_count, 2)
        self.assertEqual(stats.get("analysis_jobs_created"), 2)
        self.assertEqual(stats.get("analysis_jobs_processed"), 0)

    def test_poll_once_skips_when_no_enabled_targets(self):
        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=[]):
            with patch("src.joongna_polling_service.search_joongna_products") as mock_search:
                stats = poll_once()

        self.assertEqual(stats.get("settings_due"), 0)
        self.assertEqual(stats.get("analysis_jobs_created"), 0)
        self.assertEqual(mock_search.call_count, 0)

    def test_poll_once_cli_word_filters_to_enabled_targets_only(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "m1맥북에어",
            }
        ]

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products") as mock_search:
                stats = poll_once(search_words=["m3맥북에어"])

        self.assertEqual(stats.get("settings_due"), 1)
        self.assertEqual(stats.get("fetched_items"), 0)
        self.assertEqual(mock_search.call_count, 0)

    def test_poll_once_enqueues_jobs_for_sort_date_changed(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "m3맥북에어",
            }
        ]
        mock_item = {
            "seq": 1001,
            "product_id": 1001,
            "title": "맥북에어 M3 8GB 256GB",
            "price": 1200000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-1",
            "product_url": "https://web.joongna.com/product/1001",
            "image_url": "",
        }
        existing_seen = {
            "seq": 1001,
            "last_title": "맥북에어 M3 8GB 256GB",
            "last_price_krw": 1200000,
            "last_refresh_key": "rk-1",
            "last_sort_date": "2026-05-15 10:00:00",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", return_value=_FakeConnection()):
                    with patch("src.joongna_polling_service.get_seen_product", return_value=existing_seen):
                        with patch("src.joongna_polling_service.upsert_seen_product_observation"):
                            with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                                mock_enqueue.return_value = {
                                    "ok": True,
                                    "created_jobs": [{"job_id": 1}],
                                    "skipped_jobs": [],
                                }
                                stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 1)
        enqueue_args = mock_enqueue.call_args.args
        self.assertEqual(enqueue_args[2], "sort_date_changed")
        self.assertEqual(stats.get("new_items"), 1)

    def test_poll_once_does_not_enqueue_jobs_for_unchanged_sort_date(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "m3맥북에어",
            }
        ]
        mock_item = {
            "seq": 1001,
            "product_id": 1001,
            "title": "맥북에어 M3 8GB 256GB",
            "price": 1200000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-1",
            "product_url": "https://web.joongna.com/product/1001",
            "image_url": "",
        }
        existing_seen = {
            "seq": 1001,
            "last_title": "맥북에어 M3 8GB 256GB",
            "last_price_krw": 1200000,
            "last_refresh_key": "rk-1",
            "last_sort_date": "2026-05-15 12:28:52",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", return_value=_FakeConnection()):
                    with patch("src.joongna_polling_service.get_seen_product", return_value=existing_seen):
                        with patch("src.joongna_polling_service.upsert_seen_product_observation"):
                            with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                                stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 0)
        self.assertEqual(stats.get("skipped_seen"), 1)


if __name__ == "__main__":
    unittest.main()
