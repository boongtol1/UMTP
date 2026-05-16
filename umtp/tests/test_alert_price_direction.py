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
    passes_price_bounds,
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

    def test_below_or_equal_min_price_bound_blocks_too_low_listing(self):
        self.assertFalse(
            passes_price_bounds(
                listing_price_krw=290000,
                alert_price_direction=BELOW_OR_EQUAL,
                min_price_krw=300000,
                max_price_krw=None,
            )
        )

    def test_above_or_equal_max_price_bound_blocks_too_high_listing(self):
        self.assertFalse(
            passes_price_bounds(
                listing_price_krw=910000,
                alert_price_direction=ABOVE_OR_EQUAL,
                min_price_krw=None,
                max_price_krw=900000,
            )
        )

    def test_null_bounds_keep_existing_behavior(self):
        self.assertTrue(
            passes_price_bounds(
                listing_price_krw=500000,
                alert_price_direction=BELOW_OR_EQUAL,
                min_price_krw=None,
                max_price_krw=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
