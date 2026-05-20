import json
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_settings_service import (  # noqa: E402
    USER_SETTINGS_SAVE_LOG_ERROR_CONDITION_CHANGE_NOTICE_INSERT_FAILED,
    USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED,
    upsert_user_fair_price_setting,
)


class _SaveLogFakeCursor:
    def __init__(self, *, fail_on_main_upsert=False, fail_on_log_insert=False):
        self.fail_on_main_upsert = fail_on_main_upsert
        self.fail_on_log_insert = fail_on_log_insert
        self.executed = []
        self.save_log_rows = []
        self._last_query = ""
        self.lastrowid = None
        self._next_log_id = 1000

    def execute(self, query, params=None):
        normalized_query = " ".join((query or "").lower().split())
        self.executed.append((normalized_query, params))
        self._last_query = normalized_query

        if self.fail_on_main_upsert and "insert into user_fair_prices" in normalized_query:
            raise RuntimeError("main save failed")

        if "insert into user_settings_save_logs" in normalized_query:
            if self.fail_on_log_insert:
                raise RuntimeError("save log insert failed")
            self._next_log_id += 1
            self.lastrowid = self._next_log_id
            self.save_log_rows.append(params)

    def fetchone(self):
        if self._last_query.startswith("select current_timestamp"):
            return (datetime(2026, 5, 20, 21, 0, 0),)
        return None

    def close(self):
        return None


class _SaveLogFakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commit_called = 0
        self.rollback_called = 0
        self._closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commit_called += 1

    def rollback(self):
        self.rollback_called += 1

    def is_connected(self):
        return not self._closed

    def close(self):
        self._closed = True


class UserSettingsSaveLogsTest(unittest.TestCase):
    def _existing_state(self):
        return {
            "rule_id": 14,
            "previous_saved_at": datetime(2026, 5, 20, 20, 0, 0),
            "rule_snapshot": {
                "fair_price_krw": 900000,
                "alert_drop_rate_percent": 20.0,
                "target_buy_price_krw": 720000,
                "alert_price_direction": "BELOW_OR_EQUAL",
                "enabled": True,
            },
            "condition_change_candidate_notice_enabled": True,
        }

    def _call_upsert(self):
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

    def test_save_success_creates_user_settings_save_log_row(self):
        cursor = _SaveLogFakeCursor()
        connection = _SaveLogFakeConnection(cursor)

        with patch("src.user_settings_service.get_connection", return_value=connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"):
                    with patch(
                        "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                        return_value=self._existing_state(),
                    ):
                        with patch(
                            "src.user_settings_service._insert_user_fair_price_history_if_changed",
                            return_value={"created": False},
                        ):
                            with patch(
                                "src.user_settings_service._collect_missed_candidates_between_saved_windows",
                                return_value={"missed_count": 0, "candidate_rows": 0, "representative_candidate": None},
                            ):
                                result = self._call_upsert()

        self.assertTrue(result.get("ok"))
        self.assertEqual(len(cursor.save_log_rows), 1)

        save_log_params = cursor.save_log_rows[0]
        self.assertEqual(save_log_params[0], "boongtol")
        self.assertEqual(save_log_params[1], 14)
        self.assertEqual(save_log_params[2], "update_watch_rule")
        self.assertEqual(save_log_params[5], 1)
        self.assertIsNone(save_log_params[6])
        self.assertIsNone(save_log_params[7])

        request_json = json.loads(save_log_params[3])
        metadata_json = json.loads(save_log_params[8])
        self.assertEqual(request_json.get("search_keyword"), "m1 맥북에어")
        self.assertEqual(metadata_json.get("missed_candidate_count"), 0)
        self.assertIn("save_log_id", result)

    def test_condition_change_notice_insert_failure_is_logged_as_partial_failure(self):
        cursor = _SaveLogFakeCursor()
        connection = _SaveLogFakeConnection(cursor)

        with patch("src.user_settings_service.get_connection", return_value=connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"):
                    with patch(
                        "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                        return_value=self._existing_state(),
                    ):
                        with patch(
                            "src.user_settings_service._insert_user_fair_price_history_if_changed",
                            return_value={"created": False},
                        ):
                            with patch(
                                "src.user_settings_service._collect_missed_candidates_between_saved_windows",
                                return_value={
                                    "missed_count": 2,
                                    "candidate_rows": 2,
                                    "representative_candidate": {
                                        "product_id": "101",
                                        "title": "m1 맥북에어",
                                        "url": "https://web.joongna.com/product/101",
                                        "source": "joongna",
                                        "price_krw": 700000,
                                        "sort_date": datetime(2026, 5, 20, 20, 10, 0),
                                    },
                                },
                            ):
                                with patch(
                                    "src.user_settings_service._insert_condition_change_candidate_notice_alert_event",
                                    side_effect=RuntimeError("duplicate key"),
                                ):
                                    result = self._call_upsert()

        self.assertTrue(result.get("ok"))
        self.assertEqual(len(cursor.save_log_rows), 1)

        save_log_params = cursor.save_log_rows[0]
        self.assertEqual(save_log_params[5], 1)
        self.assertEqual(
            save_log_params[6],
            USER_SETTINGS_SAVE_LOG_ERROR_CONDITION_CHANGE_NOTICE_INSERT_FAILED,
        )
        self.assertIn("duplicate key", save_log_params[7])

        metadata_json = json.loads(save_log_params[8])
        self.assertEqual(metadata_json.get("missed_candidate_count"), 2)
        self.assertFalse(metadata_json.get("condition_change_notice_created"))

    def test_save_failure_creates_failed_save_log(self):
        main_cursor = _SaveLogFakeCursor(fail_on_main_upsert=True)
        main_connection = _SaveLogFakeConnection(main_cursor)
        log_cursor = _SaveLogFakeCursor()
        log_connection = _SaveLogFakeConnection(log_cursor)

        with patch("src.user_settings_service.get_connection", side_effect=[main_connection, log_connection]):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"):
                    with patch(
                        "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                        return_value=self._existing_state(),
                    ):
                        with self.assertRaises(RuntimeError):
                            self._call_upsert()

        self.assertEqual(main_connection.rollback_called, 1)
        self.assertEqual(len(log_cursor.save_log_rows), 1)

        save_log_params = log_cursor.save_log_rows[0]
        self.assertEqual(save_log_params[5], 0)
        self.assertEqual(save_log_params[6], USER_SETTINGS_SAVE_LOG_ERROR_SAVE_FAILED)
        self.assertIn("main save failed", save_log_params[7])
        self.assertIsNotNone(save_log_params[3])
        self.assertIsNone(save_log_params[4])

    def test_save_log_insert_failure_does_not_block_save_success(self):
        cursor = _SaveLogFakeCursor(fail_on_log_insert=True)
        connection = _SaveLogFakeConnection(cursor)

        with patch("src.user_settings_service.get_connection", return_value=connection):
            with patch("src.user_settings_service.is_valid_silicon_unit", return_value=True):
                with patch("src.user_settings_service._resolve_setting_search_keyword", return_value="m1 맥북에어"):
                    with patch(
                        "src.user_settings_service._fetch_existing_user_fair_price_rule_state",
                        return_value=self._existing_state(),
                    ):
                        with patch(
                            "src.user_settings_service._insert_user_fair_price_history_if_changed",
                            return_value={"created": False},
                        ):
                            with patch(
                                "src.user_settings_service._collect_missed_candidates_between_saved_windows",
                                return_value={"missed_count": 0, "candidate_rows": 0, "representative_candidate": None},
                            ):
                                result = self._call_upsert()

        self.assertTrue(result.get("ok"))
        self.assertEqual(len(cursor.save_log_rows), 0)
        self.assertEqual(connection.commit_called, 1)


if __name__ == "__main__":
    unittest.main()
