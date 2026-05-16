import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.alert_price_direction import (  # noqa: E402
    ABOVE_OR_EQUAL,
    BELOW_OR_EQUAL,
    compute_target_buy_price_krw,
    is_listing_alert_match,
)


class AlertPriceDirectionTest(unittest.TestCase):
    def test_compute_target_buy_price_with_positive_drop_rate(self):
        self.assertEqual(compute_target_buy_price_krw(1000000, 20.50), 795000)

    def test_compute_target_buy_price_with_negative_drop_rate(self):
        self.assertEqual(compute_target_buy_price_krw(1000000, -10.00), 1100000)

    def test_below_or_equal_alert_match(self):
        self.assertTrue(is_listing_alert_match(790000, 795000, BELOW_OR_EQUAL))

    def test_above_or_equal_alert_match_true(self):
        self.assertTrue(is_listing_alert_match(1150000, 1100000, ABOVE_OR_EQUAL))

    def test_above_or_equal_alert_match_false(self):
        self.assertFalse(is_listing_alert_match(1050000, 1100000, ABOVE_OR_EQUAL))

    def test_below_or_equal_alert_match_with_negative_drop_rate_target(self):
        self.assertTrue(is_listing_alert_match(1050000, 1100000, BELOW_OR_EQUAL))


if __name__ == "__main__":
    unittest.main()
