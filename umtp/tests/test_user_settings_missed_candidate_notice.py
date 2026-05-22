import os
import sys
import unittest
from datetime import datetime, timedelta


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import (  # noqa: E402
    CONDITION_CHANGE_CANDIDATE_REEVALUATION_DAYS,
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

    def _row(self, **overrides):
        row = {
            "analysis_job_id": 1,
            "analysis_result_id": 1,
            "product_id": "p-1",
            "sort_date": datetime(2026, 5, 18, 14, 30, 0),
            "listing_price_krw": 600000,
            "price_krw": 600000,
            "title": "candidate",
            "url": "https://web.joongna.com/product/p-1",
            "source": "joongna",
            "product_type": "MacBook Air",
            "chip": "M1",
            "screen_inch": 13,
            "ram_gb": 8,
            "ssd_gb": 256,
            "analyzed_at": datetime(2026, 5, 18, 14, 40, 0),
        }
        row.update(overrides)
        return row

    def _collect(self, rows, *, old_rule, new_rule):
        cursor = _FakeCursor(rows=rows)
        stats = _collect_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m1 맥북에어",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )
        return cursor, stats

    def test_query_uses_recent_7_day_analyzed_window_without_watch_rule_filter(self):
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=620000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        cursor, _stats = self._collect([self._row()], old_rule=old_rule, new_rule=new_rule)

        query, params = cursor.executed[0]
        normalized_query = " ".join(query.lower().split())
        self.assertIn("coalesce(lar.created_at, aj.created_at) >= %s", normalized_query)
        self.assertNotIn("aj.watch_rule_id = %s", normalized_query)

        expected_cutoff = self.current_saved_at - timedelta(days=CONDITION_CHANGE_CANDIDATE_REEVALUATION_DAYS)
        self.assertEqual(
            params,
            ("boongtol", "joongna", expected_cutoff, "MacBook Air", "M1", 13, 8, 256),
        )

    def test_below_or_equal_rechecks_previously_analyzed_listing(self):
        row = self._row(
            product_id="listing-600",
            listing_price_krw=600000,
            price_krw=600000,
            analyzed_at=datetime(2026, 5, 18, 14, 40, 0),  # previous_saved_at 이전 분석
        )
        old_rule_58 = _build_rule_snapshot(
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
        new_rule_58 = _build_rule_snapshot(
            fair_price_krw=580000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        _cursor_no_candidate, no_candidate_stats = self._collect(
            [row],
            old_rule=old_rule_58,
            new_rule=new_rule_58,
        )
        self.assertEqual(no_candidate_stats.get("missed_count"), 0)

        _cursor_candidate, candidate_stats = self._collect(
            [row],
            old_rule=old_rule_58,
            new_rule=new_rule_62,
        )
        self.assertEqual(candidate_stats.get("missed_count"), 1)
        self.assertEqual((candidate_stats.get("missed_candidates") or [])[0].get("product_id"), "listing-600")

    def test_above_or_equal_transition_rule(self):
        row = self._row(
            product_id="listing-950",
            listing_price_krw=950000,
            price_krw=950000,
        )
        old_rule_100 = _build_rule_snapshot(
            fair_price_krw=1000000,
            alert_drop_rate_percent=0,
            alert_price_direction="ABOVE_OR_EQUAL",
            enabled=True,
        )
        new_rule_98 = _build_rule_snapshot(
            fair_price_krw=980000,
            alert_drop_rate_percent=0,
            alert_price_direction="ABOVE_OR_EQUAL",
            enabled=True,
        )
        new_rule_90 = _build_rule_snapshot(
            fair_price_krw=900000,
            alert_drop_rate_percent=0,
            alert_price_direction="ABOVE_OR_EQUAL",
            enabled=True,
        )

        _cursor_no_candidate, no_candidate_stats = self._collect(
            [row],
            old_rule=old_rule_100,
            new_rule=new_rule_98,
        )
        self.assertEqual(no_candidate_stats.get("missed_count"), 0)

        _cursor_candidate, candidate_stats = self._collect(
            [row],
            old_rule=old_rule_100,
            new_rule=new_rule_90,
        )
        self.assertEqual(candidate_stats.get("missed_count"), 1)
        self.assertEqual((candidate_stats.get("missed_candidates") or [])[0].get("product_id"), "listing-950")

    def test_excludes_rows_older_than_7_days_by_analyzed_at(self):
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=620000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        old_row = self._row(
            analyzed_at=self.current_saved_at - timedelta(days=8),
            listing_price_krw=600000,
            price_krw=600000,
        )

        _cursor, stats = self._collect([old_row], old_rule=old_rule, new_rule=new_rule)
        self.assertEqual(stats.get("missed_count"), 0)

    def test_excludes_other_specs(self):
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=620000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        other_spec_row = self._row(
            product_id="other-spec",
            ram_gb=16,
            ssd_gb=512,
            listing_price_krw=600000,
            price_krw=600000,
        )

        _cursor, stats = self._collect([other_spec_row], old_rule=old_rule, new_rule=new_rule)
        self.assertEqual(stats.get("missed_count"), 0)

    def test_dedupes_same_product_by_latest_analyzed_at_and_tie_breaks_by_result_id(self):
        old_rule = _build_rule_snapshot(
            fair_price_krw=500000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=620000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        rows = [
            self._row(
                analysis_job_id=10,
                analysis_result_id=100,
                product_id="p-latest",
                analyzed_at=datetime(2026, 5, 18, 13, 0, 0),
                listing_price_krw=600000,  # 후보 조건 만족
                price_krw=600000,
            ),
            self._row(
                analysis_job_id=11,
                analysis_result_id=101,
                product_id="p-latest",
                analyzed_at=datetime(2026, 5, 18, 15, 50, 0),
                listing_price_krw=450000,  # 최신 결과: old도 만족 -> 후보 제외
                price_krw=450000,
            ),
            self._row(
                analysis_job_id=12,
                analysis_result_id=200,
                product_id="p-tie",
                analyzed_at=datetime(2026, 5, 18, 15, 30, 0),
                listing_price_krw=600000,  # 후보 조건 만족
                price_krw=600000,
            ),
            self._row(
                analysis_job_id=13,
                analysis_result_id=201,
                product_id="p-tie",
                analyzed_at=datetime(2026, 5, 18, 15, 30, 0),  # 동률 analyzed_at
                listing_price_krw=450000,  # id 큰 최신 결과로 간주 -> 후보 제외
                price_krw=450000,
            ),
        ]

        _cursor, stats = self._collect(rows, old_rule=old_rule, new_rule=new_rule)
        self.assertEqual(stats.get("missed_count"), 0)
        self.assertEqual(stats.get("missed_candidates"), [])

    def test_count_wrapper_matches_collect_count(self):
        cursor = _FakeCursor(
            rows=[
                self._row(
                    product_id="listing-600",
                    listing_price_krw=600000,
                    price_krw=600000,
                )
            ]
        )
        old_rule = _build_rule_snapshot(
            fair_price_krw=580000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )
        new_rule = _build_rule_snapshot(
            fair_price_krw=620000,
            alert_drop_rate_percent=0,
            alert_price_direction="BELOW_OR_EQUAL",
            enabled=True,
        )

        count = _count_missed_candidates_between_saved_windows(
            cursor,
            user_id="boongtol",
            rule_id=7,
            source="joongna",
            search_keyword="m1 맥북에어",
            previous_saved_at=self.previous_saved_at,
            current_saved_at=self.current_saved_at,
            old_rule_snapshot=old_rule,
            new_rule_snapshot=new_rule,
            **self.spec_args,
        )

        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
