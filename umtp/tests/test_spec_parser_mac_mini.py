import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.spec_parser import INVALID_UNIT_REASON, parse_listing_title  # noqa: E402


class SpecParserMacMiniTest(unittest.TestCase):
    def test_parse_mac_mini_m2_basic(self):
        parsed = parse_listing_title("맥미니 M2 16GB 512GB 팝니다")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "Mac mini")
        self.assertEqual(parsed["chip"], "M2")
        self.assertEqual(parsed["screen_inch"], 0)
        self.assertEqual(parsed["ram_gb"], 16)
        self.assertEqual(parsed["ssd_gb"], 512)

    def test_parse_mac_mini_m2_pro_compact_token(self):
        parsed = parse_listing_title("맥미니 m2pro 16g 1t")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "Mac mini")
        self.assertEqual(parsed["chip"], "M2 Pro")
        self.assertEqual(parsed["screen_inch"], 0)
        self.assertEqual(parsed["ram_gb"], 16)
        self.assertEqual(parsed["ssd_gb"], 1024)

    def test_parse_mac_mini_m2_pro_spaced_token(self):
        parsed = parse_listing_title("Mac mini M2 Pro 16GB 1TB")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "Mac mini")
        self.assertEqual(parsed["chip"], "M2 Pro")
        self.assertEqual(parsed["screen_inch"], 0)
        self.assertEqual(parsed["ram_gb"], 16)
        self.assertEqual(parsed["ssd_gb"], 1024)

    def test_parse_mac_mini_m4_pro_with_48gb(self):
        parsed = parse_listing_title("맥미니 m4pro 48g 2t")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "Mac mini")
        self.assertEqual(parsed["chip"], "M4 Pro")
        self.assertEqual(parsed["screen_inch"], 0)
        self.assertEqual(parsed["ram_gb"], 48)
        self.assertEqual(parsed["ssd_gb"], 2048)

    def test_parse_mac_mini_m4_pro_not_downgraded_to_m4(self):
        parsed = parse_listing_title("Mac mini M4 Pro 24GB 512GB")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "Mac mini")
        self.assertEqual(parsed["chip"], "M4 Pro")
        self.assertEqual(parsed["screen_inch"], 0)
        self.assertEqual(parsed["ram_gb"], 24)
        self.assertEqual(parsed["ssd_gb"], 512)

    def test_mac_mini_with_screen_inch_is_invalid(self):
        parsed = parse_listing_title("Mac mini M2 13인치 16GB 512GB")
        self.assertFalse(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "Mac mini")
        self.assertEqual(parsed["screen_inch"], 0)
        self.assertEqual(parsed["unit_validation_reason"], INVALID_UNIT_REASON)


if __name__ == "__main__":
    unittest.main()
