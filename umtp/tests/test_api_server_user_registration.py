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

    @patch("src.api_server.upsert_user_watch_rule", return_value={"ok": True})
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_watch_rule_upsert_registers_user_before_upsert(self, mock_register_user, mock_upsert_watch_rule):
        request = api_server.UserWatchRuleUpsertRequest(
            user_id="boongtol",
            product_type="MacBook Air",
            chip="M1",
            screen_inch=13,
            ram_gb=8,
            ssd_gb=256,
            search_keyword="m1맥북에어",
            enabled=True,
            poll_interval_seconds=60,
            target_price_krw=None,
            fair_price_krw=None,
        )

        response = api_server.user_watch_rules_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert_watch_rule.assert_called_once()
        self.assertEqual(mock_upsert_watch_rule.call_args.kwargs.get("user_id"), "boongtol")

    @patch("src.api_server.register_user", return_value={"ok": False, "reason": "duplicate_device_conflict"})
    def test_user_watch_rules_returns_registration_failure(self, mock_register_user):
        response = api_server.user_watch_rules("boongtol")

        self.assertFalse(response.get("ok"))
        self.assertIn("사용자 등록 실패", response.get("reason", ""))
        mock_register_user.assert_called_once_with(user_id="boongtol")


if __name__ == "__main__":
    unittest.main()
