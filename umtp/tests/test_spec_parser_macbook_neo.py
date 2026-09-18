import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.numeric_candidate_extractor import extract_numeric_candidates
from src.spec_parser import parse_listing_text, parse_listing_title


class SpecParserMacBookNeoTest(unittest.TestCase):
    def assert_neo(self, title, ssd=256):
        parsed = parse_listing_title(title)
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual((parsed["product_type"], parsed["chip"], parsed["screen_inch"], parsed["ram_gb"], parsed["ssd_gb"]),
                         ("MacBook Neo", "A18 Pro", 13, 8, ssd))
        return parsed

    def test_both_seed_specs_and_korean_english_aliases(self):
        for name in ("맥북네오", "맥북 네오", "MacBook Neo", "macbookneo"):
            for chip in ("A18 Pro", "a18pro", "A18-Pro", "A18 프로", "A 18 Pro"):
                for ssd in (256, 512):
                    with self.subTest(name=name, chip=chip, ssd=ssd):
                        self.assert_neo(f"{name} {chip} 13인치 8GB {ssd}GB", ssd)

    def test_numeric_chip_generation_never_becomes_ram(self):
        for chip in ("A18 Pro", "a18pro", "A 18 Pro", "A18 프로"):
            with self.subTest(chip=chip):
                self.assertEqual(extract_numeric_candidates(chip)["ram_candidates"], [])
                self.assert_neo(f"맥북네오 {chip} 512GB", 512)
                self.assert_neo(f"맥북네오 {chip} 13 8 256")
                self.assert_neo(f"맥북네오 {chip} 8/512", 512)

    def test_missing_screen_ram_storage_follow_seed_base(self):
        parsed = self.assert_neo("맥북네오 A18 Pro 기본형")
        self.assertTrue(parsed["screen_inch_defaulted"])
        self.assertEqual(parsed["detected_patterns"]["ram_gb"]["source"], "fallback_base_model")
        self.assert_neo("MacBook Neo A18 Pro 8GB")
        self.assertFalse(parse_listing_title("맥북네오 8GB 256GB")["parse_success"])

    def test_self_check_preserves_a18_pro_and_storage(self):
        parsed = parse_listing_text("맥북 네오 판매", self_check_fields={
            "모델명": "MacBook Neo 13형", "CPU종류": "A18 Pro", "램 용량": "8GB", "SSD용량": "512GB"})
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual(parsed["chip"], "A18 Pro")
        self.assertEqual(parsed["ssd_gb"], 512)

    def test_invalid_or_mixed_chip_spec_and_product_are_rejected(self):
        for title in (
            "맥북네오 A18 8GB 256GB", "맥북네오 A18 Max 8GB 256GB", "맥북네오 M1 8GB 256GB",
            "맥북네오 A18 Pro M3 8GB 256GB", "맥북네오 A18 Pro A19 Pro 8GB 256GB",
            "맥북네오 A18 Pro 16GB 256GB", "맥북네오 A18 Pro 8GB 1TB",
            "맥북네오 A18 Pro 14인치 8GB 256GB", "맥북네오 A18 Pro 15인치 8GB 256GB",
            "맥북네오 A18 Pro 16인치 8GB 256GB", "맥북네오 A18 Pro 27인치 8GB 256GB",
            "맥북네오 A18 Pro 맥북프로 M3 8GB 256GB",
        ):
            with self.subTest(title=title):
                self.assertFalse(parse_listing_title(title)["parse_success"])

    def test_unseeded_explicit_capacities_do_not_disappear_into_base_fallback(self):
        for detail in ("RAM 12GB SSD256GB", "13인치 12GB 256GB", "램12 256GB", "8GB SSD128GB",
                       "8GB SSD 768", "8GB 3TB", "8GB SSD128", "12g 512g", "8GB 0.75TB"):
            with self.subTest(detail=detail):
                self.assertFalse(parse_listing_title("MacBook Neo A18 Pro " + detail)["parse_success"])
        for ram, ssd in (("12GB", "256GB"), ("12", "512"), ("8GB", "128GB"), ("8", "768")):
            with self.subTest(ram=ram, ssd=ssd):
                parsed = parse_listing_text("MacBook Neo A18 Pro", self_check_fields={"램 용량": ram, "SSD용량": ssd})
                self.assertFalse(parsed["parse_success"], parsed)

    def test_capacity_labels_own_their_numbers_before_suffixes(self):
        for detail, ssd in (("램 용량 8GB SSD 용량 256GB", 256), ("memory 8GB storage 512GB", 512),
                            ("메모리 8GB 저장공간 256GB", 256), ("8GB RAM 512GB SSD", 512),
                            ("SSD 512GB RAM 8GB", 512), ("512GB SSD 8GB RAM", 512)):
            with self.subTest(detail=detail):
                self.assert_neo("맥북네오 A18 Pro " + detail, ssd)


if __name__ == "__main__":
    unittest.main()
