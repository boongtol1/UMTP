import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import (  # noqa: E402
    _build_keyword_targets_from_watch_rules,
    poll_once,
)


class IMacPollingAliasesTest(unittest.TestCase):
    def _rule(self, **overrides):
        rule = {
            "id": 81,
            "user_id": "imac-user",
            "product_type": "iMac",
            "chip": "M1",
            "screen_inch": 24,
            "ram_gb": 8,
            "ssd_gb": 256,
            "search_keyword": "m1 아이맥",
            "enabled": True,
            "saved_at": "2026-09-18 10:00:00",
        }
        rule.update(overrides)
        return rule

    def test_default_imac_setting_expands_to_korean_and_english_queries(self):
        for chip in ("M1", "M3", "M4"):
            with self.subTest(chip=chip):
                compact = chip.lower()
                targets = _build_keyword_targets_from_watch_rules([
                    self._rule(chip=chip, search_keyword=f"{compact} 아이맥")
                ])

                self.assertEqual(list(targets), [f"{compact} 아이맥", f"imac {compact}"])
                self.assertEqual(targets[f"{compact} 아이맥"][0]["setting_id"], 81)
                self.assertEqual(targets[f"imac {compact}"][0]["setting_id"], 81)

    def test_custom_imac_keyword_and_other_products_are_not_expanded(self):
        targets = _build_keyword_targets_from_watch_rules([
            self._rule(id=82, search_keyword="아이맥 작업용"),
            self._rule(
                id=83,
                product_type="MacBook Air",
                chip="M1",
                search_keyword="m1 맥북에어",
            ),
        ])

        self.assertEqual(list(targets), ["아이맥 작업용", "m1 맥북에어"])

    def test_two_queries_merge_same_listing_before_analysis_enqueue(self):
        listing = {
            "seq": 8181,
            "product_id": 8181,
            "title": "iMac M1 8GB 256GB",
            "price": 700000,
            "sort_date": "2026-09-18 12:00:00",
            "refresh_key": "rk-8181",
            "product_url": "https://web.joongna.com/product/8181",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=[self._rule()]):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[listing]) as search:
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.mark_watch_rules_polled", return_value=1) as mark_polled:
                        with patch("src.joongna_polling_service.enqueue_analysis_for_product") as enqueue:
                            enqueue.return_value = {
                                "ok": True,
                                "created_jobs": [{"job_id": 8181}],
                                "skipped_jobs": [],
                            }
                            stats = poll_once()

        self.assertEqual([call.args[0] for call in search.call_args_list], ["m1 아이맥", "imac m1"])
        enqueue.assert_called_once()
        mark_polled.assert_called_once_with([81])
        self.assertEqual(stats["polling_group_count"], 2)
        self.assertEqual(stats["external_api_calls"], 2)
        self.assertEqual(stats["matched_watch_rules"], 1)
        self.assertEqual(stats["analysis_jobs_created"], 1)

    def test_english_query_finds_listing_missing_from_korean_results(self):
        listing = {
            "seq": 8383,
            "product_id": 8383,
            "title": "iMac M3 24-inch 24GB 1TB",
            "price": 1200000,
            "sort_date": "2026-09-18 12:00:00",
            "refresh_key": "rk-8383",
            "product_url": "https://web.joongna.com/product/8383",
            "image_url": "",
        }
        rule = self._rule(id=83, chip="M3", ram_gb=24, ssd_gb=1024, search_keyword="m3 아이맥")

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=[rule]):
            with patch("src.joongna_polling_service.search_joongna_products", side_effect=[[], [listing]]) as search:
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.mark_watch_rules_polled", return_value=1):
                        with patch("src.joongna_polling_service.enqueue_analysis_for_product") as enqueue:
                            enqueue.return_value = {
                                "ok": True,
                                "created_jobs": [{"job_id": 8383}],
                                "skipped_jobs": [],
                            }
                            stats = poll_once()

        self.assertEqual([call.args[0] for call in search.call_args_list], ["m3 아이맥", "imac m3"])
        enqueue.assert_called_once()
        self.assertEqual(stats["fetched_count"], 1)
        self.assertEqual(stats["analysis_jobs_created"], 1)


if __name__ == "__main__":
    unittest.main()
