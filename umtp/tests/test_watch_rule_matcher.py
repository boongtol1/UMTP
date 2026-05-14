import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.watch_rule_matcher import matches_watch_rule  # noqa: E402


class WatchRuleMatcherTest(unittest.TestCase):
    def test_matches_all_fields(self):
        parsed_spec = {
            "product_type": "MacBook Air",
            "chip": "M1",
            "screen_inch": 13,
            "ram_gb": 8,
            "ssd_gb": 256,
        }
        watch_rule = {
            "product_type": "MacBook Air",
            "chip": "m1",
            "screen_inch": 13,
            "ram_gb": 8,
            "ssd_gb": 256,
        }
        self.assertTrue(matches_watch_rule(parsed_spec, watch_rule))

    def test_rule_null_fields_are_ignored(self):
        parsed_spec = {
            "product_type": "MacBook Air",
            "chip": "M2",
            "screen_inch": 13,
            "ram_gb": 16,
            "ssd_gb": 512,
        }
        watch_rule = {
            "product_type": "MacBook Air",
            "chip": None,
            "screen_inch": None,
            "ram_gb": None,
            "ssd_gb": None,
        }
        self.assertTrue(matches_watch_rule(parsed_spec, watch_rule))

    def test_mismatch_returns_false(self):
        parsed_spec = {
            "product_type": "MacBook Air",
            "chip": "M3",
            "screen_inch": 13,
            "ram_gb": 16,
            "ssd_gb": 512,
        }
        watch_rule = {
            "product_type": "MacBook Air",
            "chip": "M2",
            "screen_inch": 13,
            "ram_gb": 16,
            "ssd_gb": 512,
        }
        self.assertFalse(matches_watch_rule(parsed_spec, watch_rule))


if __name__ == "__main__":
    unittest.main()
