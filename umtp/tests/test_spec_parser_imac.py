import os
from pathlib import Path
import re
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.macbook_air_units import generate_units_for_product
from src.spec_parser import parse_listing_text, parse_listing_title


def seed_rows():
    sql = (Path(PROJECT_ROOT) / "sql/seed_silicon_imac_fair_prices.sql").read_text()
    return [dict(product_type="iMac", chip=chip, screen_inch=int(screen), ram_gb=int(ram),
                 ssd_gb=int(ssd), fair_price_krw=int(price))
            for chip, screen, ram, ssd, price in re.findall(
                r"\('iMac', '([^']+)', (\d+), (\d+), (\d+), (\d+)\)", sql)]


def unit_key(row):
    return tuple(row[field] for field in ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb"))


class SpecParserIMacTest(unittest.TestCase):
    def assert_spec(self, text, chip, ram, ssd, **kwargs):
        parsed = parse_listing_text(text, **kwargs)
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual(unit_key(parsed), ("iMac", chip, 24, ram, ssd))
        return parsed

    def test_catalog_and_parser_match_every_seed_configuration(self):
        rows = seed_rows()
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({unit_key(row) for row in rows}), 32)
        units = generate_units_for_product("iMac")
        self.assertEqual({unit_key(unit) for unit in units}, {unit_key(row) for row in rows})
        for row in rows:
            with self.subTest(spec=unit_key(row)):
                self.assert_spec(f"아이맥 {row['chip']} 24인치 {row['ram_gb']}GB {row['ssd_gb']}GB",
                                 row["chip"], row["ram_gb"], row["ssd_gb"])

    def test_product_aliases_display_sizes_and_storage_shorthand(self):
        for product in ("아이맥", "아이 맥", "iMac", "IMAC", "i Mac"):
            for screen in ("24인치", "24형", '24"', "24-inch", "23.5인치", "23.5-inch"):
                with self.subTest(product=product, screen=screen):
                    self.assert_spec(f"{product} M 3 {screen} 24/2TB", "M3", 24, 2048)

    def test_default_display_and_base_specs_follow_seed(self):
        for chip, ram in (("M1", 8), ("M3", 8), ("M4", 16)):
            parsed = self.assert_spec(f"아이맥 {chip} 기본형", chip, ram, 256)
            self.assertTrue(parsed["screen_inch_defaulted"])
        self.assert_spec("iMac M4 24GB 1TB", "M4", 24, 1024)
        self.assert_spec("iMac M3 24인치 기본형", "M3", 8, 256)
        self.assert_spec("iMac M3 23.5인치 기본형", "M3", 8, 256)

    def test_bare_display_and_ram_have_independent_evidence(self):
        for text in ("iMac M3 24 16 512", "iMac M3 24 16GB 512GB", "iMac M3 24 16/512"):
            self.assert_spec(text, "M3", 16, 512)
        self.assert_spec("iMac M3 24인치 24 512", "M3", 24, 512)
        self.assert_spec("iMac M3 24/512", "M3", 24, 512)
        for text in ("iMac M3 24 512", "iMac M3 24인치 24 16GB 512GB"):
            with self.subTest(text=text):
                self.assertFalse(parse_listing_title(text)["parse_success"])

    def test_structured_fields_and_body_supply_specs(self):
        self.assert_spec("아이맥 판매", "M4", 32, 2048, self_check_fields={
            "모델명": "iMac M4 23.5인치", "CPU종류": "M4", "램 용량": "32GB", "SSD용량": "2TB",
        })
        self.assert_spec("아이맥 M1 판매", "M1", 16, 512, body_text="24인치 램16 SSD 512")
        self.assert_spec("iMac M4 24인치 램 용량 24GB SSD 용량 512GB", "M4", 24, 512)
        self.assert_spec("iMac M4 24인치 memory 24GB storage 512GB", "M4", 24, 512)
        self.assert_spec("iMac M4", "M4", 24, 512, self_check_fields={"램 용량": "24", "SSD용량": "512"})

    def test_unsupported_models_and_unseeded_options_are_rejected(self):
        for text in (
            "아이맥 Intel i5 27인치 8GB 256GB", "iMac M1 Intel 24인치 8GB 256GB",
            "iMac M1 27인치 8GB 256GB", "iMac M1 21.5인치 8GB 256GB",
            "iMac M3 Pro 24인치 16GB 512GB", "iMac M4 Max 24인치 32GB 512GB",
            "iMac M4 울트라 24인치 32GB 512GB", "iMac M2 24인치 8GB 256GB",
            "iMac M5 24인치 16GB 256GB", "iMac M10 24인치 8GB 256GB",
            "iMac M1 24인치 24GB 256GB", "iMac M4 24인치 8GB 256GB",
            "iMac M3 24인치 16GB 4TB", "iMac Pro M1 24인치 8GB 256GB",
            "iMac M4 24인치 RAM12GB SSD256GB", "iMac M4 24인치 RAM16GB SSD128GB",
            "iMac M4 24인치 12GB 256GB", "iMac M3 24인치 16GB 1.5TB",
            "iMac M4 24인치 RAM12 SSD256", "iMac M3 24인치 16GB 250GB",
            "iMac M4 12/256", "iMac M4 16/250", "iMac M4 16/1.5TB",
            "아이맥 M4 12GB판매 256GB", "아이맥 M4 12기가판매 256기가",
        ):
            with self.subTest(text=text):
                self.assertFalse(parse_listing_title(text)["parse_success"])

    def test_unseeded_structured_capacity_cannot_fall_back_to_base(self):
        for ram, ssd in (("12", "256"), ("16", "128"), ("12GB", "256GB"), ("16", "1.5TB"), ("256GB", "512GB"), ("16GB", "24GB")):
            parsed = parse_listing_text("아이맥 M4", self_check_fields={"램 용량": ram, "SSD용량": ssd})
            self.assertFalse(parsed["parse_success"], parsed)

    def test_mixed_products_chips_and_displays_are_rejected(self):
        for text in (
            "아이맥 맥미니 M1 24인치 8GB 256GB", "아이맥 맥북에어 M1 24인치 8GB 256GB",
            "아이맥 맥북프로 M1 24인치 8GB 256GB", "iMac M1 M3 24인치 8GB 256GB",
            "iMac M1 24인치 27인치 8GB 256GB",
            "iMac Mac Studio M1 24인치 8GB 256GB", "아이맥 맥북네오 M1 24인치 8GB 256GB",
        ):
            with self.subTest(text=text):
                self.assertFalse(parse_listing_title(text)["parse_success"])


if __name__ == "__main__":
    unittest.main()
