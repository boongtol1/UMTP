import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import api_server  # noqa: E402


class ApiServerUserRegistrationTest(unittest.TestCase):
    def test_units_endpoint_alias_is_registered(self):
        paths = {route.path for route in api_server.app.routes}
        self.assertIn("/macbook-air-units", paths)
        self.assertIn("/silicon-mac-units", paths)

    @patch("src.api_server.get_user_fair_price_settings", return_value=[])
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_user_fair_prices_registers_user_before_loading(self, mock_register_user, mock_get_settings):
        response = api_server.user_fair_prices("  boongtol ")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("user_id"), "boongtol")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_get_settings.assert_called_once_with("boongtol")

    @patch("src.api_server.upsert_user_fair_price_setting", return_value={"ok": True})
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_user_fair_price_upsert_registers_user_before_upsert(self, mock_register_user, mock_upsert_setting):
        request = api_server.UserFairPriceUpsertRequest(
            user_id="boongtol",
            product_type="MacBook Air",
            chip="M1",  # type: ignore[arg-type]
            screen_inch=13,
            ram_gb=8,
            ssd_gb=256,
            fair_price_krw=700000,
            alert_drop_rate_percent=15,
            enabled=True,
            search_keyword="m1맥북에어",
            poll_interval_seconds=60,
        )

        response = api_server.user_fair_prices_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert_setting.assert_called_once()
        self.assertEqual(mock_upsert_setting.call_args.kwargs.get("user_id"), "boongtol")
        self.assertFalse(
            mock_upsert_setting.call_args.kwargs.get("condition_change_candidate_notice_enabled")
        )

    @patch("src.api_server.upsert_user_fair_price_setting", return_value={"ok": True})
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_user_fair_price_upsert_accepts_negative_drop_and_direction(self, mock_register_user, mock_upsert_setting):
        request = api_server.UserFairPriceUpsertRequest(
            user_id="boongtol",
            product_type="MacBook Air",
            chip="M2",  # type: ignore[arg-type]
            screen_inch=13,
            ram_gb=8,
            ssd_gb=256,
            fair_price_krw=1000000,
            alert_drop_rate_percent=-10.0,
            alert_price_direction="ABOVE_OR_EQUAL",
            min_price_krw=None,
            max_price_krw=1100000,
            enabled=True,
            search_keyword="m2맥북에어",
            poll_interval_seconds=60,
        )

        response = api_server.user_fair_prices_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert_setting.assert_called_once()
        self.assertEqual(mock_upsert_setting.call_args.kwargs.get("alert_drop_rate_percent"), -10.0)
        self.assertEqual(mock_upsert_setting.call_args.kwargs.get("alert_price_direction"), "ABOVE_OR_EQUAL")
        self.assertIsNone(mock_upsert_setting.call_args.kwargs.get("min_price_krw"))
        self.assertEqual(mock_upsert_setting.call_args.kwargs.get("max_price_krw"), 1100000)
        self.assertFalse(
            mock_upsert_setting.call_args.kwargs.get("condition_change_candidate_notice_enabled")
        )

    @patch("src.api_server.upsert_user_fair_price_setting", return_value={"ok": True})
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_user_fair_price_upsert_passes_condition_change_candidate_notice_flag(
        self,
        mock_register_user,
        mock_upsert_setting,
    ):
        request = api_server.UserFairPriceUpsertRequest(
            user_id="boongtol",
            product_type="MacBook Air",
            chip="M3",  # type: ignore[arg-type]
            screen_inch=13,
            ram_gb=16,
            ssd_gb=512,
            fair_price_krw=1500000,
            alert_drop_rate_percent=12.0,
            enabled=True,
            condition_change_candidate_notice_enabled=True,
            search_keyword="m3맥북에어",
            poll_interval_seconds=60,
        )

        response = api_server.user_fair_prices_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert_setting.assert_called_once()
        self.assertTrue(
            mock_upsert_setting.call_args.kwargs.get("condition_change_candidate_notice_enabled")
        )

    @patch("src.api_server.upsert_user_fair_price_setting", return_value={"ok": True})
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_user_fair_price_upsert_accepts_mac_mini_pro_chip(self, mock_register_user, mock_upsert_setting):
        request = api_server.UserFairPriceUpsertRequest(
            user_id="boongtol",
            product_type="Mac mini",
            chip="M2 Pro",
            screen_inch=0,
            ram_gb=16,
            ssd_gb=512,
            fair_price_krw=1250000,
            alert_drop_rate_percent=12.0,
            enabled=True,
            search_keyword="m2pro 맥미니",
            poll_interval_seconds=60,
        )

        response = api_server.user_fair_prices_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert_setting.assert_called_once()
        self.assertEqual(mock_upsert_setting.call_args.kwargs.get("chip"), "M2 Pro")

    @patch("src.api_server.register_user", return_value={"ok": False, "reason": "duplicate_device_conflict"})
    def test_user_fair_prices_returns_registration_failure(self, mock_register_user):
        response = api_server.user_fair_prices("boongtol")

        self.assertFalse(response.get("ok"))
        self.assertIn("사용자 등록 실패", response.get("reason", ""))
        mock_register_user.assert_called_once_with(user_id="boongtol")

    @patch(
        "src.api_server.list_alert_events_for_user",
        return_value=[
            {
                "id": 1,
                "user_id": "boongtol",
                "title": "맥북에어 m2 기본형",
                "listing_price_krw": 600000,
                "fair_price_krw": 800000,
                "diff_ratio": 25.0,
                "is_alert_target": True,
                "product_url": "https://web.joongna.com/product/1",
                "created_at": "2026-05-16T00:00:00",
            }
        ],
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_alerts_registers_user_before_listing_events(self, mock_register_user, mock_list_alerts):
        response = api_server.alerts(" boongtol ", limit=10)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("user_id"), "boongtol")
        self.assertEqual(len(response.get("items", [])), 1)
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_list_alerts.assert_called_once_with("boongtol", limit=10, is_read="0")

    @patch(
        "src.api_server.list_alert_events_for_user",
        return_value=[],
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_alert_events_accepts_read_filter(self, mock_register_user, mock_list_alerts):
        response = api_server.alert_events("boongtol", limit=50, is_read="all")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("is_read_filter"), "all")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_list_alerts.assert_called_once_with("boongtol", limit=50, is_read="all")

    @patch(
        "src.api_server.mark_alert_event_read_for_user",
        return_value={"ok": True, "alert_event_id": 11, "is_read": True, "already_read": False},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_mark_single_alert_read(self, mock_register_user, mock_mark_read):
        response = api_server.mark_alert_event_as_read(11, "boongtol")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("user_id"), "boongtol")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_mark_read.assert_called_once_with(user_id="boongtol", alert_event_id=11)

    @patch(
        "src.api_server.mark_all_alert_events_read_for_user",
        return_value={"ok": True, "updated_count": 4},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_mark_all_alerts_read(self, mock_register_user, mock_mark_all_read):
        response = api_server.mark_all_alert_events_as_read("boongtol")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("updated_count"), 4)
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_mark_all_read.assert_called_once_with(user_id="boongtol")

    @patch(
        "src.api_server.clear_all_read_alert_events_for_user",
        return_value={"ok": True, "cleared_count": 3},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_clear_all_read_archive(self, mock_register_user, mock_clear_all):
        response = api_server.clear_all_read_alert_events("boongtol")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("cleared_count"), 3)
        self.assertEqual(response.get("user_id"), "boongtol")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_clear_all.assert_called_once_with(user_id="boongtol")

    @patch(
        "src.api_server.clear_selected_read_alert_events_for_user",
        return_value={"ok": True, "requested_count": 2, "cleared_count": 2, "skipped_count": 0, "not_found_ids": []},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_clear_selected_read_archive(self, mock_register_user, mock_clear_selected):
        request = api_server.ClearSelectedReadArchiveRequest(alert_event_ids=[11, 12])
        response = api_server.clear_selected_read_alert_events("boongtol", request)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("requested_count"), 2)
        self.assertEqual(response.get("cleared_count"), 2)
        self.assertEqual(response.get("user_id"), "boongtol")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_clear_selected.assert_called_once_with(user_id="boongtol", alert_event_ids=[11, 12])

    @patch(
        "src.api_server.list_grouped_read_alert_events_for_user",
        return_value={"M1": {"13": [{"id": 7}]}},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_grouped_read_alert_events(self, mock_register_user, mock_grouped):
        response = api_server.grouped_read_alert_events("boongtol")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("groups"), {"M1": {"13": [{"id": 7}]}})
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_grouped.assert_called_once_with(user_id="boongtol", limit=500)

    @patch(
        "src.api_server.refresh_user_fair_price_saved_at_for_active_rules",
        return_value={"ok": True, "refreshed_rule_count": 2},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_refresh_user_rules_saved_at_registers_user_before_refresh(
        self,
        mock_register_user,
        mock_refresh_rules,
    ):
        response = api_server.refresh_user_rules_saved_at(" boongtol ")

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("user_id"), "boongtol")
        self.assertEqual(response.get("refreshed_rule_count"), 2)
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_refresh_rules.assert_called_once_with("boongtol")

    @patch(
        "src.api_server.refresh_user_fair_price_saved_at_for_single_rule",
        return_value={"ok": False, "reason": "active_rule_not_found"},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_refresh_single_rule_returns_not_found_when_rule_is_not_active(
        self,
        mock_register_user,
        mock_refresh_single_rule,
    ):
        response = api_server.refresh_single_user_rule_saved_at("boongtol", 321)

        self.assertFalse(response.get("ok"))
        self.assertEqual(response.get("reason"), "active_rule_not_found")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_refresh_single_rule.assert_called_once_with("boongtol", 321)

    @patch(
        "src.api_server.upsert_user_push_token",
        return_value={"ok": True, "message": "푸시 토큰 저장 완료"},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_push_token_endpoint_registers_user_and_upserts_token(
        self,
        mock_register_user,
        mock_upsert_push_token,
    ):
        request = api_server.PushTokenRequest(token="x" * 128, platform="android")
        response = api_server.users_push_token_upsert(" boongtol ", request)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("message"), "푸시 토큰 저장 완료")
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert_push_token.assert_called_once_with(
            user_id="boongtol",
            token="x" * 128,
            platform="android",
        )

    @patch("src.api_server.register_user", return_value={"ok": False, "reason": "user_not_registered"})
    def test_push_token_endpoint_handles_registration_failure(self, mock_register_user):
        request = api_server.PushTokenRequest(token="x" * 128, platform="android")
        response = api_server.users_push_token_upsert("boongtol", request)

        self.assertFalse(response.get("ok"))
        self.assertIn("사용자 등록 실패", response.get("reason", ""))
        mock_register_user.assert_called_once_with(user_id="boongtol")


if __name__ == "__main__":
    unittest.main()
