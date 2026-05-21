import os
import sys
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import (  # noqa: E402
    _build_rule_snapshot,
    _collect_missed_candidates_between_saved_windows,
    _count_missed_candidates_between_saved_windows,
)


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows


class UserSettingsMissedCandidateNoticeTest(unittest.TestCase):
    def setUp(self):
        self.previous_saved_at = datetime(2026, 5, 18, 15, 0, 0)
        self.current_saved_at = datetime(2026, 5, 18, 16, 0, 0)
        self.spec_args = {
            "product_type": "MacBook Air",
            "chip": "M1",
            "screen_inch": 13,
            "ram_gb": 8,
            "ssd_gb": 256,
        }

    def test_counts_between_window_new_match_old_not_match(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "p-52",
                    "sort_date": datetime(2026, 5, 18, 15, 10, 0),
                    "listing_price_krw": 520000,
                    "price_krw": 520000,
                    "title": "candidate",
                    "url": "https://web.joongna.com/product/p-52",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=550000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 1)
        self.assertEqual(
            cursor.executed[0][1],
            ("boongtol", "joongna", self.previous_saved_at, self.current_saved_at, 7, "MacBook Air", "M1", 13, 8, 256),
        )

    def test_excludes_listing_that_already_matched_old_rule(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "p-49",
                    "sort_date": datetime(2026, 5, 18, 15, 20, 0),
                    "listing_price_krw": 490000,
                    "price_krw": 490000,
                    "title": "candidate",
                    "url": "https://web.joongna.com/product/p-49",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=550000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 0)

    def test_excludes_listing_after_current_saved_at(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "p-after",
                    "sort_date": datetime(2026, 5, 18, 16, 5, 0),
                    "listing_price_krw": 520000,
                    "price_krw": 520000,
                    "title": "candidate",
                    "url": "https://web.joongna.com/product/p-after",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=550000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 0)

    def test_excludes_when_new_rule_is_stricter(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "p-52",
                    "sort_date": datetime(2026, 5, 18, 15, 10, 0),
                    "listing_price_krw": 520000,
                    "price_krw": 520000,
                    "title": "candidate",
                    "url": "https://web.joongna.com/product/p-52",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=550000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 0)

    def test_excludes_rows_without_sort_date(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "p-no-sort",
                    "sort_date": None,
                    "listing_price_krw": 520000,
                    "price_krw": 520000,
                    "title": "candidate",
                    "url": "https://web.joongna.com/product/p-no-sort",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=550000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 0)

    def test_query_uses_watch_rule_and_spec_scope_not_keyword_only(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "228796648",
                    "sort_date": datetime(2026, 5, 18, 15, 10, 0),
                    "listing_price_krw": 650000,
                    "price_krw": 650000,
                    "title": "candidate",
                    "url": "https://web.joongna.com/product/228796648",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=640000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=650000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=14,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 1)
        self.assertEqual(
            cursor.executed[0][1],
            ("boongtol", "joongna", self.previous_saved_at, self.current_saved_at, 14, "MacBook Air", "M1", 13, 8, 256),
        )

    def test_collects_all_missed_candidates_as_notice_targets(self):
        cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "p-1",
                    "sort_date": datetime(2026, 5, 18, 15, 10, 0),
                    "listing_price_krw": 520000,
                    "price_krw": 520000,
                    "title": "first",
                    "url": "https://web.joongna.com/product/1",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
                {
                    "product_id": "p-1",
                    "sort_date": datetime(2026, 5, 18, 15, 20, 0),
                    "listing_price_krw": 530000,
                    "price_krw": 530000,
                    "title": "first-update",
                    "url": "https://web.joongna.com/product/1",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
                {
                    "product_id": "p-2",
                    "sort_date": datetime(2026, 5, 18, 15, 30, 0),
                    "listing_price_krw": 540000,
                    "price_krw": 540000,
                    "title": "second",
                    "url": "https://web.joongna.com/product/2",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=550000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        stats = _collect_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m4 맥미니",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(stats.get("missed_count"), 2)
        missed_candidates = stats.get("missed_candidates") or []
        self.assertEqual(len(missed_candidates), 2)
        self.assertEqual(missed_candidates[0].get("product_id"), "p-1")
        self.assertEqual(missed_candidates[1].get("product_id"), "p-2")
        self.assertEqual(missed_candidates[0].get("title"), "first-update")

    def test_consecutive_threshold_updates_only_notifies_when_new_rule_matches_and_spec_is_exact(self):
        first_cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "listing-600",
                    "sort_date": datetime(2026, 5, 18, 15, 30, 0),
                    "listing_price_krw": 600000,
                    "price_krw": 600000,
                    "title": "M1 Air 8/256",
                    "url": "https://web.joongna.com/product/600",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                }
            ]
        )
        second_cursor = _FakeCursor(
            rows=[
                {
                    "product_id": "listing-600",
                    "sort_date": datetime(2026, 5, 18, 16, 30, 0),
                    "listing_price_krw": 600000,
                    "price_krw": 600000,
                    "title": "M1 Air 8/256",
                    "url": "https://web.joongna.com/product/600",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 8,
                    "ssd_gb": 256,
                },
                {
                    "product_id": "listing-600-other-spec",
                    "sort_date": datetime(2026, 5, 18, 16, 35, 0),
                    "listing_price_krw": 600000,
                    "price_krw": 600000,
                    "title": "M1 Air 16/512",
                    "url": "https://web.joongna.com/product/601",
                    "source": "joongna",
                    "product_type": "MacBook Air",
                    "chip": "M1",
                    "screen_inch": 13,
                    "ram_gb": 16,
                    "ssd_gb": 512,
                },
            ]
        )

        old_rule_50 = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule_58 = _build_rule_snapshot(
            fair_price_krw=580000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule_62 = _build_rule_snapshot(
            fair_price_krw=620000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        first_stats = _collect_missed_candidates_between_saved_windows(
            first_cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m1 맥북에어",
            previous_saved_at=datetime(2026, 5, 18, 15, 0, 0),
            current_saved_at=datetime(2026, 5, 18, 16, 0, 0),
            old_rule_snapshot=old_rule_50,
            new_rule_snapshot=new_rule_58,
            **self.spec_args,
        )
        self.assertEqual(first_stats.get("missed_count"), 0)

        second_stats = _collect_missed_candidates_between_saved_windows(
            second_cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m1 맥북에어",
            previous_saved_at=datetime(2026, 5, 18, 16, 0, 0),
            current_saved_at=datetime(2026, 5, 18, 17, 0, 0),
            old_rule_snapshot=new_rule_58,
            new_rule_snapshot=new_rule_62,
            **self.spec_args,
        )
        self.assertEqual(second_stats.get("missed_count"), 1)
        self.assertEqual((second_stats.get("missed_candidates") or [])[0].get("product_id"), "listing-600")


if __name__ == "__main__":
    unittest.main()
