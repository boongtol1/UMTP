import os
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.spec_parser import parse_listing_text, parse_listing_title  # noqa: E402


class SpecParserMacBookProTest(unittest.TestCase):
    def assert_spec(self, text, chip, screen, ram, ssd):
        parsed = parse_listing_title(text)
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual(
            (parsed["product_type"], parsed["chip"], parsed["screen_inch"], parsed["ram_gb"], parsed["ssd_gb"]),
            ("MacBook Pro", chip, screen, ram, ssd),
        )

    def test_every_seed_configuration_can_be_parsed(self):
        seed = (Path(PROJECT_ROOT) / "sql" / "seed_silicon_macbook_pro_fair_prices.sql").read_text()
        rows = re.findall(r"\('MacBook Pro', '([^']+)', (\d+), (\d+), (\d+), \d+\)", seed)
        self.assertEqual(len(rows), 276)
        for chip, screen, ram, ssd in rows:
            with self.subTest(chip=chip, screen=screen, ram=ram, ssd=ssd):
                self.assert_spec(
                    f"맥북프로 {chip} {screen}인치 {ram}GB {ssd}GB",
                    chip, int(screen), int(ram), int(ssd),
                )

    def test_compact_korean_and_english_chip_tiers(self):
        for token in ("M3Pro", "M3-Pro", "M3 프로", "M 3 Pro"):
            with self.subTest(token=token):
                self.assert_spec(f"맥북 프로 {token} 14.2인치 18g 512GB", "M3 Pro", 14, 18, 512)
        for token in ("M5Max", "M5-Max", "M5 맥스"):
            with self.subTest(token=token):
                self.assert_spec(f"MacBook Pro {token} 16.2-inch 128g 8t", "M5 Max", 16, 128, 8192)

    def test_product_pro_does_not_change_base_chip(self):
        self.assert_spec("M1 맥북프로 13.3인치 8GB 256GB", "M1", 13, 8, 256)
        self.assert_spec("MacBook Pro M3 14-inch 8/512", "M3", 14, 8, 512)

    def test_shorthand_high_ram_and_storage(self):
        self.assert_spec("맥북프로 M2 Max 16인치 96/8TB", "M2 Max", 16, 96, 8192)
        self.assert_spec("맥북프로 M3 Pro 14인치 36/1TB", "M3 Pro", 14, 36, 1024)
        self.assert_spec("맥북프로 M4 Max 16형 128/8192", "M4 Max", 16, 128, 8192)

    def test_screen_and_terabytes_are_not_ram(self):
        self.assert_spec("맥북프로 M1 Pro 16인치 기본형", "M1 Pro", 16, 16, 512)
        self.assert_spec("맥북프로 M5 Max 16인치 8TB", "M5 Max", 16, 36, 8192)

    def test_ordered_bare_screen_ram_storage(self):
        self.assert_spec("맥북프로 M1 Pro 14 16 512", "M1 Pro", 14, 16, 512)
        self.assert_spec("맥북프로 M2 Max 16 32 1024", "M2 Max", 16, 32, 1024)
        self.assert_spec("맥북프로 M5 Max 16 128 8TB", "M5 Max", 16, 128, 8192)
        self.assert_spec("맥북프로 M1 Pro 14인치 16 512", "M1 Pro", 14, 16, 512)

    def test_single_bare_16_cannot_supply_both_screen_and_ram(self):
        parsed = parse_listing_title("맥북프로 M1 Pro 16 512")
        self.assertFalse(parsed["parse_success"])
        self.assertIsNone(parsed["screen_inch"])
        self.assertIn("screen_inch", parsed["missing_fields"])

    def test_bare_display_is_resolved_by_independent_explicit_ram(self):
        self.assert_spec("맥북프로 M2 Max 16 32/1TB", "M2 Max", 16, 32, 1024)
        self.assert_spec("맥북프로 16 M2 Max 32GB 1TB", "M2 Max", 16, 32, 1024)

    def test_bare_display_stays_ambiguous_with_conflicting_screen(self):
        for text in (
            "맥북프로 M2 Max 14인치 16 32/1TB",
            "맥북프로 14 16 M2 Max 32GB 1TB",
        ):
            with self.subTest(text=text):
                self.assertFalse(parse_listing_title(text)["parse_success"])

    def test_missing_screen_only_defaults_for_single_screen_chips(self):
        for chip, screen, ram, ssd in (("M1", 13, 8, 256), ("M2", 13, 8, 256), ("M3", 14, 8, 512), ("M4", 14, 16, 512), ("M5", 14, 16, 512)):
            self.assert_spec(f"맥북프로 {chip}", chip, screen, ram, ssd)
        for text in (
            "맥북프로 M3 Pro 18GB 512GB",
            "맥북프로 M1 Pro 16GB 512GB",
            "맥북프로 M1 Pro 16램 512GB",
            "맥북프로 M1 Pro 램16 512GB",
            "맥북프로 M1 Pro 16 RAM 512 SSD",
            "맥북프로 M1 Pro RAM 16 SSD 512",
            "맥북프로 M1 Pro 16/512",
            "맥북프로 M5 Max 128GB 8TB",
        ):
            with self.subTest(text=text):
                parsed = parse_listing_title(text)
                self.assertFalse(parsed["parse_success"], parsed)
                self.assertIsNone(parsed["screen_inch"])
                self.assertIn("screen_inch", parsed["missing_fields"])

    def test_self_check_high_capacity_storage_and_ram(self):
        parsed = parse_listing_text("맥북프로 판매", self_check_fields={
            "모델명": "MacBook Pro M5 Max 16.2인치",
            "CPU종류": "M5 Max",
            "램 용량": "128GB",
            "SSD용량": "8TB",
        })
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual(parsed["ssd_gb"], 8192)
        self.assertEqual(parsed["ram_gb"], 128)

    def test_unsupported_combinations_are_rejected(self):
        for text in (
            "맥북프로 M1 14인치 8GB 256GB",
            "맥북프로 M3 16인치 8GB 512GB",
            "맥북프로 M3 Pro 14인치 16GB 512GB",
            "맥북프로 M4 Pro 14인치 64GB 512GB",
            "맥북프로 M5 Max 16인치 36GB 1TB",
        ):
            with self.subTest(text=text):
                parsed = parse_listing_title(text)
                self.assertFalse(parsed["parse_success"], parsed)
                self.assertEqual(parsed["unit_validation_reason"], "invalid_silicon_mac_unit")

    def test_conflicting_products_chips_and_screens_are_rejected(self):
        for text in (
            "맥북프로 맥북에어 M3 14인치 8GB 512GB",
            "맥북프로 M3/M3 Pro 14인치 18GB 512GB",
            "맥북프로 M3 Pro/M3 Max 14인치 36GB 1TB",
            "맥북프로 M3 Pro 14인치 16인치 18GB 512GB",
        ):
            with self.subTest(text=text):
                self.assertFalse(parse_listing_title(text)["parse_success"])


if __name__ == "__main__":
    unittest.main()
