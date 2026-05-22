import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import (  # noqa: E402
    _has_analysis_job_for_target,
    _build_keyword_targets_from_watch_rules,
    parse_sort_date,
    poll_once,
)


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self._search_query_id = 1
        self._fetchone_result = None

    def execute(self, query, params=None):
        self.executed.append((query, params))
        normalized = " ".join((query or "").split()).lower()
        if normalized.startswith("select id from search_queries"):
            self._fetchone_result = (self._search_query_id,)
        else:
            self._fetchone_result = None

    def fetchone(self):
        return self._fetchone_result

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


class _AnalysisLookupCursor:
    def __init__(self, *, existing_params=None, raise_sort_date_unknown=False):
        self.executed = []
        self._fetchone_result = None
        self._existing_params = set(existing_params or set())
        self._raise_sort_date_unknown = raise_sort_date_unknown

    def execute(self, query, params=None):
        normalized = " ".join((query or "").split()).lower()
        self.executed.append((normalized, params))
        if self._raise_sort_date_unknown and "and sort_date = %s" in normalized:
            raise RuntimeError("Unknown column 'sort_date' in 'where clause'")
        if params in self._existing_params:
            self._fetchone_result = {"id": 1}
        else:
            self._fetchone_result = None

    def fetchone(self):
        return self._fetchone_result


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

    def test_analysis_job_lookup_uses_sort_date_for_backfill_identity(self):
        target = {"user_id": "boongtol", "setting_id": 25}
        cursor = _AnalysisLookupCursor(
            existing_params={
                ("boongtol", "228861602", 25, datetime(2026, 5, 22, 16, 44, 19)),
            }
        )

        self.assertTrue(
            _has_analysis_job_for_target(
                cursor,
                target,
                "228861602",
                sort_date="2026-05-22 16:44:19",
            )
        )
        self.assertFalse(
            _has_analysis_job_for_target(
                cursor,
                target,
                "228861602",
                sort_date="2026-05-22 12:42:47",
            )
        )
        self.assertTrue(any("and sort_date = %s" in query for query, _ in cursor.executed))

    def test_analysis_job_lookup_falls_back_when_sort_date_column_missing(self):
        target = {"user_id": "boongtol", "setting_id": 25}
        cursor = _AnalysisLookupCursor(
            existing_params={("boongtol", "228861602", 25)},
            raise_sort_date_unknown=True,
        )

        self.assertTrue(
            _has_analysis_job_for_target(
                cursor,
                target,
                "228861602",
                sort_date="2026-05-22 16:44:19",
            )
        )
        self.assertTrue(any("and sort_date = %s" in query for query, _ in cursor.executed))
        self.assertTrue(
            any(
                "and watch_rule_id = %s" in query and "and sort_date = %s" not in query
                for query, _ in cursor.executed
            )
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

    def test_build_keyword_targets_keeps_rules_per_setting(self):
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
        self.assertEqual(len(targets["맥북 m1"]), 2)
        self.assertEqual(targets["맥북 m1"][0].get("setting_ids"), [1])
        self.assertEqual(targets["맥북 m1"][1].get("setting_ids"), [2])

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
                "saved_at": "2026-05-15 10:00:00",
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
                "saved_at": "2026-05-15 10:00:00",
            },
        ]

        mock_item = {
            "seq": 1001,
            "product_id": 1001,
            "title": "맥북에어 M2 16GB 512GB",
            "price": 1200000,
            "sort_date": "2026-05-15 12:28:52",
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
        self.assertEqual(enqueue_args[2], "new")
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
                "saved_at": "2026-05-15 10:00:00",
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

    def test_poll_once_backfills_jobs_for_unchanged_when_rule_not_analyzed_yet(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "m3맥북에어",
                "saved_at": "2026-05-15 10:00:00",
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
                                mock_enqueue.return_value = {
                                    "ok": True,
                                    "created_jobs": [{"job_id": 1}],
                                    "skipped_jobs": [],
                                }
                                stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 1)
        enqueue_args = mock_enqueue.call_args.args
        self.assertEqual(enqueue_args[2], "unchanged_backfill")
        self.assertEqual(stats.get("unchanged_skipped_count"), 1)
        self.assertEqual(stats.get("unchanged_backfill_target_count"), 1)
        self.assertEqual(stats.get("alert_created_count"), 1)
        self.assertEqual(stats.get("skipped_seen"), 1)

    def test_poll_once_keeps_skipping_unchanged_when_rule_already_analyzed(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "m3맥북에어",
                "saved_at": "2026-05-15 10:00:00",
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
                            with patch(
                                "src.joongna_polling_service._has_analysis_job_for_target",
                                return_value=True,
                            ):
                                with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                                    stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 0)
        self.assertEqual(stats.get("unchanged_backfill_target_count"), 0)
        self.assertEqual(stats.get("unchanged_skipped_count"), 1)

    def test_poll_once_excludes_listings_before_saved_at(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "m3맥북에어",
                "saved_at": "2026-05-15 13:00:00",
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

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                        stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 0)
        self.assertEqual(stats.get("skipped_before_saved_at"), 1)

    def test_poll_once_fetches_once_for_same_source_and_keyword(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "u1",
                "search_keyword": "맥북 m2",
                "saved_at": "2026-05-15 10:00:00",
            },
            {
                "id": 2,
                "user_id": "u2",
                "search_keyword": "맥북 m2",
                "saved_at": "2026-05-15 10:00:00",
            },
            {
                "id": 3,
                "user_id": "u3",
                "search_keyword": "맥북 m2",
                "saved_at": "2026-05-15 10:00:00",
            },
        ]
        mock_item = {
            "seq": 1010,
            "product_id": 1010,
            "title": "맥북에어 M2 16GB 512GB",
            "price": 1200000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-1010",
            "product_url": "https://web.joongna.com/product/1010",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]) as mock_search:
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                        mock_enqueue.return_value = {
                            "ok": True,
                            "created_jobs": [{"job_id": 1}, {"job_id": 2}, {"job_id": 3}],
                            "skipped_jobs": [],
                        }
                        stats = poll_once()

        self.assertEqual(mock_search.call_count, 1)
        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(stats.get("polling_group_count"), 1)
        self.assertEqual(stats.get("external_api_calls"), 1)

    def test_poll_once_matches_same_listing_to_multiple_watch_rules(self):
        due_rules = [
            {
                "id": 11,
                "user_id": "user_a",
                "search_keyword": "맥북 m3",
                "saved_at": "2026-05-15 10:00:00",
            },
            {
                "id": 12,
                "user_id": "user_b",
                "search_keyword": "맥북 m3",
                "saved_at": "2026-05-15 10:00:00",
            },
        ]
        mock_item = {
            "seq": 2020,
            "product_id": 2020,
            "title": "맥북에어 M3 8GB 256GB",
            "price": 1100000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-2020",
            "product_url": "https://web.joongna.com/product/2020",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                        mock_enqueue.return_value = {
                            "ok": True,
                            "created_jobs": [{"job_id": 11}, {"job_id": 12}],
                            "skipped_jobs": [],
                        }
                        stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(stats.get("matched_watch_rules"), 2)
        self.assertEqual(stats.get("created_alert_count"), 2)

    def test_poll_once_continues_when_one_group_fetch_fails(self):
        due_rules = [
            {
                "id": 21,
                "user_id": "user_fail",
                "search_keyword": "실패 키워드",
                "saved_at": "2026-05-15 10:00:00",
            },
            {
                "id": 22,
                "user_id": "user_ok",
                "search_keyword": "정상 키워드",
                "saved_at": "2026-05-15 10:00:00",
            },
        ]
        mock_item = {
            "seq": 3030,
            "product_id": 3030,
            "title": "맥북에어 M2 8GB 256GB",
            "price": 980000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-3030",
            "product_url": "https://web.joongna.com/product/3030",
            "image_url": "",
        }

        def _search_side_effect(keyword):
            if keyword == "실패 키워드":
                raise RuntimeError("temporary upstream error")
            return [mock_item]

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", side_effect=_search_side_effect) as mock_search:
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.mark_watch_rule_polled") as mock_mark_polled:
                        with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                            mock_enqueue.return_value = {
                                "ok": True,
                                "created_jobs": [{"job_id": 22}],
                                "skipped_jobs": [],
                            }
                            stats = poll_once()

        self.assertEqual(mock_search.call_count, 2)
        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(mock_mark_polled.call_count, 1)
        self.assertEqual(stats.get("search_errors"), 1)
        self.assertEqual(stats.get("analysis_jobs_created"), 1)

    def test_poll_once_keeps_duplicate_skip_count_from_enqueue_result(self):
        due_rules = [
            {
                "id": 31,
                "user_id": "user_dup",
                "search_keyword": "중복 키워드",
                "saved_at": "2026-05-15 10:00:00",
            }
        ]
        mock_item = {
            "seq": 4040,
            "product_id": 4040,
            "title": "맥북에어 M1 8GB 256GB",
            "price": 700000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-4040",
            "product_url": "https://web.joongna.com/product/4040",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                        mock_enqueue.return_value = {
                            "ok": True,
                            "created_jobs": [],
                            "skipped_jobs": [{"reason": "duplicate_identity_job"}],
                        }
                        stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(stats.get("analysis_jobs_created"), 0)
        self.assertEqual(stats.get("analysis_jobs_skipped_duplicate"), 1)
        self.assertEqual(stats.get("created_alert_count"), 0)

    def test_poll_once_changed_listing_keeps_duplicate_skip_count(self):
        due_rules = [
            {
                "id": 41,
                "user_id": "user_dup",
                "search_keyword": "변경 중복 키워드",
                "saved_at": "2026-05-15 10:00:00",
            }
        ]
        mock_item = {
            "seq": 5050,
            "product_id": 5050,
            "title": "맥북에어 M2 16GB 512GB",
            "price": 1500000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-new",
            "product_url": "https://web.joongna.com/product/5050",
            "image_url": "",
        }
        existing_seen = {
            "seq": 5050,
            "last_title": "맥북에어 M2 16GB 512GB",
            "last_price_krw": 1500000,
            "last_refresh_key": "rk-old",
            "last_sort_date": "2026-05-15 12:28:52",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", return_value=_FakeConnection()):
                    with patch("src.joongna_polling_service.get_seen_product", return_value=existing_seen):
                        with patch("src.joongna_polling_service.upsert_seen_product_observation"):
                            with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                                mock_enqueue.return_value = {
                                    "ok": True,
                                    "created_jobs": [],
                                    "skipped_jobs": [{"reason": "duplicate_identity_job"}],
                                }
                                stats = poll_once()

        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(stats.get("changed_count"), 1)
        self.assertEqual(stats.get("analysis_jobs_skipped_duplicate"), 1)
        self.assertEqual(stats.get("created_alert_count"), 0)

    def test_poll_once_saves_search_results_per_group(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "u1",
                "search_keyword": "맥북 m2",
                "saved_at": "2026-05-15 10:00:00",
            }
        ]
        mock_item = {
            "seq": 6001,
            "product_id": 6001,
            "title": "맥북에어 M2 16GB 512GB",
            "price": 1190000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-6001",
            "product_url": "https://web.joongna.com/product/6001",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", return_value=_FakeConnection()):
                    with patch("src.joongna_polling_service.get_seen_product", return_value=None):
                        with patch("src.joongna_polling_service.upsert_seen_product_observation"):
                            with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                                mock_enqueue.return_value = {
                                    "ok": True,
                                    "created_jobs": [{"job_id": 1}],
                                    "skipped_jobs": [],
                                }
                                stats = poll_once()

        self.assertEqual(stats.get("search_results_saved"), 1)
        self.assertEqual(stats.get("search_results_save_errors"), 0)
        self.assertEqual(mock_enqueue.call_count, 1)

    def test_poll_once_continues_when_search_cache_save_fails(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "u1",
                "search_keyword": "맥북 m3",
                "saved_at": "2026-05-15 10:00:00",
            }
        ]
        mock_item = {
            "seq": 7001,
            "product_id": 7001,
            "title": "맥북에어 M3 16GB 512GB",
            "price": 1490000,
            "sort_date": "2026-05-15 12:28:52",
            "refresh_key": "rk-7001",
            "product_url": "https://web.joongna.com/product/7001",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", return_value=_FakeConnection()):
                    with patch(
                        "src.joongna_polling_service.save_group_search_results",
                        side_effect=RuntimeError("cache table missing"),
                    ):
                        with patch("src.joongna_polling_service.get_seen_product", return_value=None):
                            with patch("src.joongna_polling_service.upsert_seen_product_observation"):
                                with patch("src.joongna_polling_service.enqueue_analysis_for_product") as mock_enqueue:
                                    mock_enqueue.return_value = {
                                        "ok": True,
                                        "created_jobs": [{"job_id": 1}],
                                        "skipped_jobs": [],
                                    }
                                    stats = poll_once()

        self.assertEqual(stats.get("search_results_saved"), 0)
        self.assertEqual(stats.get("search_results_save_errors"), 1)
        self.assertEqual(mock_enqueue.call_count, 1)


if __name__ == "__main__":
    unittest.main()
