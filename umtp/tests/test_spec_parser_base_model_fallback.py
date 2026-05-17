import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.macbook_air_units import get_macbook_air_base_spec  # noqa: E402
from src.spec_parser import contains_base_model_keyword, parse_listing_title  # noqa: E402


class SpecParserBaseModelFallbackTest(unittest.TestCase):
    def test_contains_base_model_keyword_matches_supported_tokens_only(self):
        self.assertTrue(contains_base_model_keyword("맥북에어 m2 기본형"))
        self.assertTrue(contains_base_model_keyword("맥북에어(m2)깡통"))
        self.assertFalse(contains_base_model_keyword("맥북에어 기본 충전기 포함"))
        self.assertFalse(contains_base_model_keyword("맥북에어 base model"))
        self.assertFalse(contains_base_model_keyword("맥북에어 베이스"))

    def test_macbook_air_m2_base_model_parses_with_fallback(self):
        parsed = parse_listing_title("맥북에어 m2 기본형")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "MacBook Air")
        self.assertEqual(parsed["chip"], "M2")
        self.assertEqual(parsed["screen_inch"], 13)
        self.assertEqual(parsed["ram_gb"], 8)
        self.assertEqual(parsed["ssd_gb"], 256)

    def test_macbook_air_m1_kkangtong_parses_with_fallback(self):
        parsed = parse_listing_title("맥북에어 m1 깡통")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "MacBook Air")
        self.assertEqual(parsed["chip"], "M1")
        self.assertEqual(parsed["screen_inch"], 13)
        self.assertEqual(parsed["ram_gb"], 8)
        self.assertEqual(parsed["ssd_gb"], 256)

    def test_macbook_air_m4_base_model_uses_table_minimum(self):
        parsed = parse_listing_title("맥북에어 m4 기본형")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["product_type"], "MacBook Air")
        self.assertEqual(parsed["chip"], "M4")
        self.assertEqual(parsed["screen_inch"], 13)
        self.assertEqual(parsed["ram_gb"], 16)
        self.assertEqual(parsed["ssd_gb"], 256)

    def test_partial_override_keeps_explicit_ram(self):
        parsed = parse_listing_title("맥북에어 m2 깡통 16GB")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["ram_gb"], 16)
        self.assertEqual(parsed["ssd_gb"], 256)

    def test_explicit_specs_take_precedence_over_fallback(self):
        parsed = parse_listing_title("맥북에어 m2 기본형 16GB 512GB")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["ram_gb"], 16)
        self.assertEqual(parsed["ssd_gb"], 512)

    def test_basic_charger_text_does_not_trigger_fallback(self):
        parsed = parse_listing_title("맥북에어 기본 충전기 포함")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["chip"])
        self.assertIsNone(parsed["ram_gb"])
        self.assertIsNone(parsed["ssd_gb"])

    def test_base_model_without_chip_stays_failed(self):
        parsed = parse_listing_title("맥북에어 기본형")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["chip"])
        self.assertIsNone(parsed["ram_gb"])
        self.assertIsNone(parsed["ssd_gb"])

    def test_macbook_pro_never_uses_air_fallback(self):
        parsed = parse_listing_title("맥북프로 m1 기본형")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["product_type"])
        self.assertIsNone(parsed["chip"])
        self.assertIsNone(parsed["ram_gb"])
        self.assertIsNone(parsed["ssd_gb"])

    def test_air_word_only_does_not_pass_product_type_gate(self):
        parsed = parse_listing_title("air m1 8gb 256gb")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["product_type"])
        self.assertIsNone(parsed["chip"])
        self.assertIsNone(parsed["ram_gb"])
        self.assertIsNone(parsed["ssd_gb"])

    def test_base_spec_resolver_reads_from_valid_units(self):
        self.assertEqual(get_macbook_air_base_spec("M1", 13), {"ram_gb": 8, "ssd_gb": 256})
        self.assertEqual(get_macbook_air_base_spec("M2", 13), {"ram_gb": 8, "ssd_gb": 256})
        self.assertEqual(get_macbook_air_base_spec("M4", 13), {"ram_gb": 16, "ssd_gb": 256})
        self.assertEqual(get_macbook_air_base_spec("M5", 13), {"ram_gb": 16, "ssd_gb": 512})
        self.assertIsNone(get_macbook_air_base_spec("M1", 15))
        self.assertIsNone(get_macbook_air_base_spec("M9", 13))

    def test_chip_parsing_accepts_embedded_chip_token(self):
        parsed = parse_listing_title("맥북에어 m1pro 8gb 256gb")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["chip"], "M1")

    def test_chip_parsing_fails_when_multiple_unique_chips_found(self):
        parsed = parse_listing_title("맥북에어 m1 m2 8gb 256gb")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["chip"])
        self.assertEqual(parsed["unit_validation_reason"], "multiple_chips_found")

    def test_chip_parsing_fails_for_slash_separated_multiple_chips(self):
        parsed = parse_listing_title("맥북에어 m1/m2 8gb 256gb")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["chip"])
        self.assertEqual(parsed["unit_validation_reason"], "multiple_chips_found")

    def test_chip_parsing_allows_duplicate_same_chip_tokens(self):
        parsed = parse_listing_title("맥북에어 m1 m1 8gb 256gb")
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["chip"], "M1")


if __name__ == "__main__":
    unittest.main()
