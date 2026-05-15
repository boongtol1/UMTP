import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_alert_settings import is_user_alert_enabled, resolve_user_alert_delivery_policy  # noqa: E402


class _FakeCursor:
    def close(self):
        return None


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def is_connected(self):
        return True

    def close(self):
        return None


class UserAlertSettingsTest(unittest.TestCase):
    def test_is_user_alert_enabled_uses_users_source_first(self):
        with patch("src.user_alert_settings.get_connection", return_value=_FakeConnection()):
            with patch(
                "src.user_alert_settings._resolve_enabled_from_users",
                return_value={"enabled": False, "source": "users.app_notification_enabled"},
            ) as users_resolver:
                with patch("src.user_alert_settings._resolve_enabled_from_user_fair_prices") as fair_prices_resolver:
                    enabled = is_user_alert_enabled("boongtol")

        self.assertFalse(enabled)
        self.assertEqual(users_resolver.call_count, 1)
        self.assertEqual(fair_prices_resolver.call_count, 0)

    def test_is_user_alert_enabled_falls_back_to_user_fair_prices(self):
        with patch("src.user_alert_settings.get_connection", return_value=_FakeConnection()):
            with patch("src.user_alert_settings._resolve_enabled_from_users", return_value=None):
                with patch(
                    "src.user_alert_settings._resolve_enabled_from_user_fair_prices",
                    return_value={"enabled": True, "source": "user_fair_prices.enabled"},
                ):
                    enabled = is_user_alert_enabled("boongtol")

        self.assertTrue(enabled)

    def test_resolve_user_alert_delivery_policy_with_user_chat_id(self):
        with patch("src.user_alert_settings.is_user_alert_enabled", return_value=True):
            with patch("src.user_alert_settings.resolve_user_telegram_chat_id", return_value="123456"):
                with patch("src.user_alert_settings.is_global_telegram_fallback_enabled", return_value=False):
                    policy = resolve_user_alert_delivery_policy("boongtol")

        self.assertTrue(policy.get("enabled"))
        self.assertEqual(policy.get("telegram_chat_id"), "123456")
        self.assertEqual(policy.get("telegram_chat_source"), "users.telegram_chat_id")
        self.assertFalse(policy.get("allow_global_fallback"))

    def test_resolve_user_alert_delivery_policy_without_chat_id(self):
        with patch("src.user_alert_settings.is_user_alert_enabled", return_value=True):
            with patch("src.user_alert_settings.resolve_user_telegram_chat_id", return_value=None):
                with patch("src.user_alert_settings.is_global_telegram_fallback_enabled", return_value=False):
                    policy = resolve_user_alert_delivery_policy("boongtol")

        self.assertTrue(policy.get("enabled"))
        self.assertIsNone(policy.get("telegram_chat_id"))
        self.assertFalse(policy.get("allow_global_fallback"))

    def test_resolve_user_alert_delivery_policy_allows_global_fallback_when_enabled(self):
        with patch("src.user_alert_settings.is_user_alert_enabled", return_value=True):
            with patch("src.user_alert_settings.resolve_user_telegram_chat_id", return_value=None):
                with patch("src.user_alert_settings.is_global_telegram_fallback_enabled", return_value=True):
                    policy = resolve_user_alert_delivery_policy("boongtol")

        self.assertTrue(policy.get("enabled"))
        self.assertIsNone(policy.get("telegram_chat_id"))
        self.assertTrue(policy.get("allow_global_fallback"))


if __name__ == "__main__":
    unittest.main()
