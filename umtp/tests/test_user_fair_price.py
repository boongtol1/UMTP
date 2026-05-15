import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.user_fair_price import is_user_fair_price_target_enabled, resolve_fair_price_for_user  # noqa: E402


class UserFairPriceTest(unittest.TestCase):
    def _spec(self):
        return {
            "product_type": "MacBook Air",
            "chip": "M1",
            "screen_inch": 13,
            "ram_gb": 8,
            "ssd_gb": 256,
        }

    def test_resolve_returns_none_when_toggle_disabled(self):
        with patch("src.user_fair_price._has_enabled_user_target", return_value=False):
            result = resolve_fair_price_for_user(cursor=object(), user_id="boongtol", parsed_spec=self._spec())

        self.assertIsNone(result)

    def test_resolve_falls_back_to_system_when_enabled_and_no_override(self):
        with patch("src.user_fair_price._has_enabled_user_target", return_value=True):
            with patch("src.user_fair_price._fetch_user_fair_price_row", return_value=None):
                with patch("src.user_fair_price._fetch_system_fair_price_row", return_value=(800000,)):
                    result = resolve_fair_price_for_user(
                        cursor=object(),
                        user_id="boongtol",
                        parsed_spec=self._spec(),
                    )

        self.assertEqual(result.get("fair_price_krw"), 800000)
        self.assertEqual(result.get("source"), "mac_fair_prices")

    def test_is_user_fair_price_target_enabled(self):
        with patch("src.user_fair_price._has_enabled_user_target", return_value=True):
            enabled = is_user_fair_price_target_enabled(cursor=object(), user_id="boongtol", parsed_spec=self._spec())

        self.assertTrue(enabled)


if __name__ == "__main__":
    unittest.main()
