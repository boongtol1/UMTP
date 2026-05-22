import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import upsert_user_fair_price_setting  # noqa: E402


class _UpsertFakeCursor:
    def __init__(self):
        self._last_query = ""

    def execute(self, query, params=None):
        self._last_query = " ".join((query or "").lower().split())

    def fetchone(self):
        if "select current_timestamp" in self._last_query:
            return (datetime(2026, 5, 20, 20, 0, 0),)
        return None

    def close(self):
        return None


class _UpsertFakeConnection:
    def __init__(self):
        self._cursor = _UpsertFakeCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def is_connected(self):
        return True

    def close(self):
        return None


class UserSettingsConditionChangeNoticeResultTest(unittest.TestCase):
    def _base_existing_state(self):
        return {
            "rule_id": 14,
            "previous_saved_at": datetime(2026, 5, 20, 19, 0, 0),
            "rule_snapshot": {
                "fair_price_krw": 500000,
                "alert_drop_rate_percent": 0.0,
                "target_buy_price_krw": 500000,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "enabled": True,
            },
            "condition_change_candidate_notice_enabled": True,
        }

    def _run_upsert(self, *, missed_count, notice_result=None, notice_side_effect=None):
        fake_connection = _UpsertFakeConnection()

        patches = [
            patch("src.user_settings_service.get_connection", return_value=fake_connection),
            patch("src.user_settings_service.is_valid_silicon_unit", return_value=True),
            patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"),
            patch(
                "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                return_value=self._base_existing_state(),
            ),
            patch(
                "src.user_settings_service._insert_user_fair_price_history_if_changed",
                return_value={"created": False, "reason": "no_meaningful_change"},
            ),
            patch(
                "src.user_settings_service._collect_missed_candidates_between_saved_windows",
                return_value={
                    "missed_count": missed_count,
                    "candidate_rows": missed_count,
                    "missed_candidates": [
                        {
                            "product_id": "101",
                            "title": "m1 맥북에어",
                            "url": "https://web.joongna.com/product/101",
                            "source": "joongna",
                            "price_krw": 700000,
                            "sort_date": datetime(2026, 5, 20, 19, 10, 0),
                        }
                    ]
                    if missed_count > 0
                    else [],
                    "representative_candidate": {
                        "product_id": "101",
                        "title": "m1 맥북에어",
                        "url": "https://web.joongna.com/product/101",
                        "source": "joongna",
                        "price_krw": 700000,
                        "sort_date": datetime(2026, 5, 20, 19, 10, 0),
                    }
                    if missed_count > 0
                    else None,
                },
            ),
        ]

        if notice_side_effect is not None:
            patches.append(
                patch(
                    "src.user_settings_service._insert_condition_change_candidate_notice_alert_event",
                    side_effect=notice_side_effect,
                )
            )
        else:
            patches.append(
                patch(
                    "src.user_settings_service._insert_condition_change_candidate_notice_alert_event",
                    return_value=notice_result,
                )
            )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            return upsert_user_fair_price_setting(
                user_id="boongtol",
                product_type="MacBook Air",
                chip="M1",
                screen_inch=13,
                ram_gb=8,
                ssd_gb=256,
                fair_price_krw=1000000,
                alert_drop_rate_percent=20.0,
                enabled=True,
                search_keyword="m1 맥북에어",
                poll_interval_seconds=60,
                priority="NORMAL",
                condition_change_candidate_notice_enabled=True,
            )

    def test_missed_candidate_zero_keeps_default_save_message(self):
        result = self._run_upsert(missed_count=0, notice_result=None)

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("message"), "사용자 공정가 설정 저장 완료")
        self.assertEqual(result.get("missed_candidate_count"), 0)
        self.assertFalse(result.get("condition_change_notice_created"))
        self.assertIsNone(result.get("condition_change_notice_error"))

    def test_missed_candidate_with_insert_success_returns_notice_message(self):
        result = self._run_upsert(
            missed_count=1,
            notice_result={"created": True, "reason": "created", "product_id": "101"},
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("message"), "조건 변경 후보: 새 기준에 맞는 매물이 1개 있었어요.")
        self.assertEqual(result.get("missed_candidate_count"), 1)
        self.assertTrue(result.get("condition_change_notice_created"))
        self.assertIsNone(result.get("condition_change_notice_error"))

    def test_missed_candidate_with_insert_exception_returns_failure_message_but_saves(self):
        with patch("src.user_settings_service.logger.warning") as mock_warning:
            result = self._run_upsert(
                missed_count=1,
                notice_side_effect=RuntimeError("duplicate key"),
            )

        self.assertTrue(result.get("ok"))
        self.assertEqual(
            result.get("message"),
            "조건 변경 사이 후보는 찾았지만 참고 알림 생성에 실패했어요. 서버 로그를 확인해 주세요.",
        )
        self.assertEqual(result.get("missed_candidate_count"), 1)
        self.assertFalse(result.get("condition_change_notice_created"))
        self.assertIn("duplicate key", result.get("condition_change_notice_error") or "")
        self.assertTrue(mock_warning.called)
        self.assertTrue(any(call.kwargs.get("exc_info") is True for call in mock_warning.mock_calls))

    def test_insert_not_created_result_is_treated_as_failure(self):
        result = self._run_upsert(
            missed_count=1,
            notice_result={"created": False, "reason": "duplicate_notice"},
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(
            result.get("message"),
            "조건 변경 사이 후보는 찾았지만 참고 알림 생성에 실패했어요. 서버 로그를 확인해 주세요.",
        )
        self.assertFalse(result.get("condition_change_notice_created"))
        self.assertEqual(result.get("condition_change_notice_error"), "duplicate_notice")

    def test_missed_candidates_create_multiple_notice_alert_events(self):
        fake_connection = _UpsertFakeConnection()

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"):
                    with patch(
                        "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                        return_value=self._base_existing_state(),
                    ):
                        with patch(
                            "src.user_settings_service._insert_user_fair_price_history_if_changed",
                            return_value={"created": False, "reason": "no_meaningful_change"},
                        ):
                            with patch(
                                "src.user_settings_service._collect_missed_candidates_between_saved_windows",
                                return_value={
                                    "missed_count": 2,
                                    "candidate_rows": 2,
                                    "missed_candidates": [
                                        {
                                            "product_id": "101",
                                            "title": "m1 맥북에어 1",
                                            "url": "https://web.joongna.com/product/101",
                                            "source": "joongna",
                                            "price_krw": 700000,
                                            "sort_date": datetime(2026, 5, 20, 19, 10, 0),
                                        },
                                        {
                                            "product_id": "102",
                                            "title": "m1 맥북에어 2",
                                            "url": "https://web.joongna.com/product/102",
                                            "source": "joongna",
                                            "price_krw": 690000,
                                            "sort_date": datetime(2026, 5, 20, 19, 20, 0),
                                        },
                                    ],
                                    "representative_candidate": {
                                        "product_id": "102",
                                        "title": "m1 맥북에어 2",
                                        "url": "https://web.joongna.com/product/102",
                                        "source": "joongna",
                                        "price_krw": 690000,
                                        "sort_date": datetime(2026, 5, 20, 19, 20, 0),
                                    },
                                },
                            ):
                                with patch(
                                    "src.user_settings_service._insert_condition_change_candidate_notice_alert_event",
                                    return_value={"created": True, "reason": "created"},
                                ) as mock_notice_insert:
                                    result = upsert_user_fair_price_setting(
                                        user_id="boongtol",
                                        product_type="MacBook Air",
                                        chip="M1",
                                        screen_inch=13,
                                        ram_gb=8,
                                        ssd_gb=256,
                                        fair_price_krw=1000000,
                                        alert_drop_rate_percent=20.0,
                                        enabled=True,
                                        search_keyword="m1 맥북에어",
                                        poll_interval_seconds=60,
                                        priority="NORMAL",
                                        condition_change_candidate_notice_enabled=True,
                                    )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("condition_change_notice_created"))
        self.assertEqual(result.get("message"), "조건 변경 후보: 새 기준에 맞는 매물이 2개 있었어요.")
        self.assertEqual(mock_notice_insert.call_count, 2)

        first_call_kwargs = mock_notice_insert.call_args_list[0].kwargs
        second_call_kwargs = mock_notice_insert.call_args_list[1].kwargs
        self.assertEqual(first_call_kwargs.get("listing_product_id"), "101")
        self.assertEqual(second_call_kwargs.get("listing_product_id"), "102")

    def test_existing_alert_event_for_same_user_rule_product_is_excluded_before_notice_insert(self):
        fake_connection = _UpsertFakeConnection()

        with patch("src.user_settings_service.get_connection", return_value=fake_connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"):
                    with patch(
                        "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                        return_value=self._base_existing_state(),
                    ):
                        with patch(
                            "src.user_settings_service._insert_user_fair_price_history_if_changed",
                            return_value={"created": False, "reason": "no_meaningful_change"},
                        ):
                            with patch(
                                "src.user_settings_service._collect_missed_candidates_between_saved_windows",
                                return_value={
                                    "missed_count": 1,
                                    "candidate_rows": 1,
                                    "missed_candidates": [
                                        {
                                            "product_id": "101",
                                            "title": "m1 맥북에어",
                                            "url": "https://web.joongna.com/product/101",
                                            "source": "joongna",
                                            "price_krw": 700000,
                                            "sort_date": datetime(2026, 5, 20, 19, 10, 0),
                                        }
                                    ],
                                    "representative_candidate": {
                                        "product_id": "101",
                                        "title": "m1 맥북에어",
                                        "url": "https://web.joongna.com/product/101",
                                        "source": "joongna",
                                        "price_krw": 700000,
                                        "sort_date": datetime(2026, 5, 20, 19, 10, 0),
                                    },
                                },
                            ):
                                with patch(
                                    "src.user_settings_service._find_existing_alert_event_for_user_rule_product",
                                    return_value=777,
                                ):
                                    with patch(
                                        "src.user_settings_service._insert_condition_change_candidate_notice_alert_event",
                                    ) as mock_notice_insert:
                                        result = upsert_user_fair_price_setting(
                                            user_id="boongtol",
                                            product_type="MacBook Air",
                                            chip="M1",
                                            screen_inch=13,
                                            ram_gb=8,
                                            ssd_gb=256,
                                            fair_price_krw=1000000,
                                            alert_drop_rate_percent=20.0,
                                            enabled=True,
                                            search_keyword="m1 맥북에어",
                                            poll_interval_seconds=60,
                                            priority="NORMAL",
                                            condition_change_candidate_notice_enabled=True,
                                        )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("condition_change_notice_created"))
        self.assertEqual(result.get("condition_change_notice_error"), None)
        self.assertEqual(mock_notice_insert.call_count, 0)


if __name__ == "__main__":
    unittest.main()
