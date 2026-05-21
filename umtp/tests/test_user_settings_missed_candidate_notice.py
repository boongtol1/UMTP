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

    def test_counts_between_window_new_match_old_not_match(self):
        cursor = _FakeCursor(
            rows=[
                ("p-52", datetime(2026, 5, 18, 15, 10, 0), 520000),
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
        )

        self.assertEqual(count, 1)
        self.assertEqual(
            cursor.executed[0][1],
            ("boongtol", "joongna", "m4 맥미니", self.previous_saved_at, self.current_saved_at),
        )

    def test_excludes_listing_that_already_matched_old_rule(self):
        cursor = _FakeCursor(
            rows=[
                ("p-49", datetime(2026, 5, 18, 15, 20, 0), 490000),
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
        )

        self.assertEqual(count, 0)

    def test_excludes_listing_after_current_saved_at(self):
        cursor = _FakeCursor(
            rows=[
                ("p-after", datetime(2026, 5, 18, 16, 5, 0), 520000),
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
        )

        self.assertEqual(count, 0)

    def test_excludes_when_new_rule_is_stricter(self):
        cursor = _FakeCursor(
            rows=[
                ("p-52", datetime(2026, 5, 18, 15, 10, 0), 520000),
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
        )

        self.assertEqual(count, 0)

    def test_excludes_rows_without_sort_date(self):
        cursor = _FakeCursor(
            rows=[
                ("p-no-sort", None, 520000),
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
        )

        self.assertEqual(count, 0)

    def test_counts_keyword_scope_even_when_current_rule_id_differs(self):
        # Simulates: product observed under another watch_rule_id previously, but same user/source/search_keyword scope.
        cursor = _FakeCursor(
            rows=[
                ("228796648", datetime(2026, 5, 18, 15, 10, 0), 650000),
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
        )

        self.assertEqual(count, 1)
        self.assertEqual(
            cursor.executed[0][1],
            ("boongtol", "joongna", "m4 맥미니", self.previous_saved_at, self.current_saved_at),
        )

    def test_collects_all_missed_candidates_as_notice_targets(self):
        cursor = _FakeCursor(
            rows=[
                ("p-1", datetime(2026, 5, 18, 15, 10, 0), 520000, "first", "https://web.joongna.com/product/1", "joongna"),
                ("p-1", datetime(2026, 5, 18, 15, 20, 0), 530000, "first-update", "https://web.joongna.com/product/1", "joongna"),
                ("p-2", datetime(2026, 5, 18, 15, 30, 0), 540000, "second", "https://web.joongna.com/product/2", "joongna"),
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
        )

        self.assertEqual(stats.get("missed_count"), 2)
        missed_candidates = stats.get("missed_candidates") or []
        self.assertEqual(len(missed_candidates), 2)
        self.assertEqual(missed_candidates[0].get("product_id"), "p-1")
        self.assertEqual(missed_candidates[1].get("product_id"), "p-2")
        self.assertEqual(missed_candidates[0].get("title"), "first-update")


if __name__ == "__main__":
    unittest.main()
