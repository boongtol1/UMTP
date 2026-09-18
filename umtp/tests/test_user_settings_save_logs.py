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
    def __init__(self, *, fail_on_main_upsert=False, fail_on_log_insert=False, persisted_rule_id=14):
        self.fail_on_main_upsert = fail_on_main_upsert
        self.fail_on_log_insert = fail_on_log_insert
        self.executed = []
        self.save_log_rows = []
        self._last_query = ""
        self.lastrowid = None
        self._next_log_id = 1000
        self.persisted_rule_id = persisted_rule_id

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
        if self._last_query.startswith("select id from user_fair_prices"):
            return (self.persisted_rule_id,)
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


class _PersistedRuleCursor(_SaveLogFakeCursor):
    """Model rows by the real unique key without mocking the rule lookup."""

    def __init__(self, *, missing_columns=(), fail_after_upsert=False, fail_id_lookup=False):
        super().__init__()
        self.rules = {}
        self.missing_columns = missing_columns
        self.fail_after_upsert = fail_after_upsert
        self.fail_id_lookup = fail_id_lookup
        self._next_rule_id = 300
        self._last_params = None

    def execute(self, query, params=None):
        normalized_query = " ".join(query.lower().split())
        if "user_fair_prices" in normalized_query:
            for column in self.missing_columns:
                if column in normalized_query:
                    raise RuntimeError(f"Unknown column '{column}' in 'field list'")
        super().execute(query, params)
        self._last_params = params
        if normalized_query.startswith("insert into user_fair_prices"):
            key = tuple(params[:6])
            if key not in self.rules:
                self._next_rule_id += 1
                self.rules[key] = {"id": self._next_rule_id}
            self.rules[key].update({
                "fair_price_krw": params[6],
                "alert_drop_rate_percent": params[7],
                "target_buy_price_krw": int(params[6] * (1 - params[7] / 100)),
                "alert_price_direction": "BELOW_OR_EQUAL",
                "condition_change_candidate_notice_enabled": False,
                "enabled": True,
            })
            # Duplicate-key/no-op upserts need not expose a new insert ID.
            self.lastrowid = 0
        elif normalized_query.startswith("update user_fair_prices"):
            if self.fail_after_upsert:
                raise RuntimeError("post-upsert update failed")
            self.lastrowid = 0

    def fetchone(self):
        if "from user_fair_prices" in self._last_query:
            if self.fail_id_lookup and self._last_query.startswith("select id from"):
                return None
            row = self.rules.get(tuple(self._last_params))
            if row is None:
                return None
            columns = self._last_query.removeprefix("select ").split(" from ", 1)[0].split(", ")
            return tuple(row.get(column) for column in columns)
        return super().fetchone()


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


class PersistedWatchRuleSaveLogsTest(unittest.TestCase):
    # Cover all four requested lineups and the existing shared save path.
    LINEUPS = (
        ("MacBook Pro", "M1 Pro", 14, 16, 512),
        ("MacBook Neo", "A18 Pro", 13, 8, 256),
        ("iMac", "M1", 24, 8, 256),
        ("Mac Studio", "M1 Max", 0, 32, 512),
        ("MacBook Air", "M1", 13, 8, 256),
        ("Mac mini", "M1", 0, 8, 256),
    )

    def _save(self, spec, *, user_id="save-log-user"):
        return upsert_user_fair_price_setting(
            user_id, *spec, fair_price_krw=1000000,
            alert_drop_rate_percent=20, enabled=True,
        )

    def _assert_linked(self, cursor, result, expected_id, action):
        self.assertTrue(result["ok"])
        self.assertEqual(result["item"]["id"], expected_id)
        log = cursor.save_log_rows[-1]
        self.assertEqual(log[1], expected_id)
        self.assertEqual(log[2], action)
        self.assertEqual(log[5], 1)
        self.assertEqual(json.loads(log[4])["item"]["id"], expected_id)

    def test_first_and_repeated_save_link_the_exact_persisted_rule_for_every_lineup(self):
        for spec in self.LINEUPS:
            with self.subTest(spec=spec):
                cursor = _PersistedRuleCursor()
                key = ("save-log-user",) + spec
                # Rules owned by another user or for another capacity must not match.
                cursor.rules[("other-user",) + spec] = {"id": 88}
                cursor.rules[key[:-1] + (spec[-1] * 2,)] = {"id": 89}
                with patch("src.user_settings_service.get_connection",
                           side_effect=lambda: _SaveLogFakeConnection(cursor)):
                    created = self._save(spec)
                    expected_id = cursor.rules[key]["id"]
                    self.assertNotIn(expected_id, (88, 89))
                    self._assert_linked(cursor, created, expected_id, "create_watch_rule")
                    updated = self._save(spec)
                    self._assert_linked(cursor, updated, expected_id, "update_watch_rule")
                self.assertEqual(len(cursor.rules), 3)
                self.assertEqual(len(cursor.save_log_rows), 2)

    def test_legacy_optional_column_fallbacks_still_link_created_and_updated_rules(self):
        schemas = (
            ("condition_change_candidate_notice_enabled",),
            ("min_price_krw", "max_price_krw"),
            ("min_price_krw", "max_price_krw", "alert_price_direction"),
            ("alert_price_direction",),
            ("saved_at", "priority"),
        )
        for spec in self.LINEUPS[:4]:
            for missing_columns in schemas:
                with self.subTest(spec=spec, missing_columns=missing_columns):
                    cursor = _PersistedRuleCursor(missing_columns=missing_columns)
                    with patch("src.user_settings_service.get_connection",
                               side_effect=lambda: _SaveLogFakeConnection(cursor)):
                        created = self._save(spec)
                        expected_id = cursor.rules[("save-log-user",) + spec]["id"]
                        self._assert_linked(cursor, created, expected_id, "create_watch_rule")
                        updated = self._save(spec)
                        self._assert_linked(cursor, updated, expected_id, "update_watch_rule")

    def test_rolled_back_new_rule_is_not_referenced_by_the_failure_log(self):
        for spec in self.LINEUPS[:4]:
            with self.subTest(spec=spec):
                cursor = _PersistedRuleCursor(fail_after_upsert=True)
                connection = _SaveLogFakeConnection(cursor)
                log_cursor = _SaveLogFakeCursor()
                with patch("src.user_settings_service.get_connection", side_effect=[
                    connection, _SaveLogFakeConnection(log_cursor),
                ]):
                    with self.assertRaisesRegex(RuntimeError, "post-upsert update failed"):
                        self._save(spec)
                self.assertEqual(connection.rollback_called, 1)
                self.assertEqual(connection.commit_called, 0)
                self.assertIsNone(log_cursor.save_log_rows[0][1])
                self.assertEqual(log_cursor.save_log_rows[0][5], 0)

    def test_failed_update_keeps_its_preexisting_rule_reference(self):
        cursor = _PersistedRuleCursor()
        spec = self.LINEUPS[1]
        with patch("src.user_settings_service.get_connection",
                   side_effect=lambda: _SaveLogFakeConnection(cursor)):
            saved = self._save(spec)
        cursor.fail_after_upsert = True
        connection = _SaveLogFakeConnection(cursor)
        log_cursor = _SaveLogFakeCursor()
        with patch("src.user_settings_service.get_connection", side_effect=[
            connection, _SaveLogFakeConnection(log_cursor),
        ]):
            with self.assertRaisesRegex(RuntimeError, "post-upsert update failed"):
                self._save(spec)
        self.assertEqual(connection.rollback_called, 1)
        self.assertEqual(log_cursor.save_log_rows[0][1], saved["item"]["id"])
        self.assertEqual(log_cursor.save_log_rows[0][2], "update_watch_rule")
        self.assertEqual(log_cursor.save_log_rows[0][5], 0)

    def test_missing_persisted_rule_id_cannot_commit_a_successful_null_reference(self):
        cursor = _PersistedRuleCursor(fail_id_lookup=True)
        connection = _SaveLogFakeConnection(cursor)
        log_cursor = _SaveLogFakeCursor()
        with patch("src.user_settings_service.get_connection", side_effect=[
            connection, _SaveLogFakeConnection(log_cursor),
        ]):
            with self.assertRaisesRegex(RuntimeError, "rule ID could not be resolved"):
                self._save(self.LINEUPS[1])
        self.assertEqual(connection.commit_called, 0)
        self.assertEqual(connection.rollback_called, 1)
        self.assertIsNone(log_cursor.save_log_rows[0][1])
        self.assertEqual(log_cursor.save_log_rows[0][5], 0)


if __name__ == "__main__":
    unittest.main()
