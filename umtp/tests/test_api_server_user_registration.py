import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import api_server  # noqa: E402


class ApiServerUserRegistrationTest(unittest.TestCase):
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
        mock_list_alerts.assert_called_once_with("boongtol", limit=10)


if __name__ == "__main__":
    unittest.main()
