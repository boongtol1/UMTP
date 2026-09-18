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
        self.assert_neo("맥북네오 8GB 256GB")

    def test_missing_chip_is_inferred_from_unique_neo_catalog_chip(self):
        for name in ("맥북네오", "맥북 네오", "MacBook Neo", "macbookneo"):
            for ssd in (256, 512):
                for capacity in (str(ssd), f"{ssd}GB", f"8/{ssd}"):
                    with self.subTest(name=name, capacity=capacity):
                        parsed = self.assert_neo(f"{name} {capacity} 미개봉", ssd)
                        self.assertTrue(parsed["chip_defaulted"])
                        self.assertEqual(parsed["detected_patterns"]["chip"]["source"], "inferred_single_product_chip")
                        explicit = parse_listing_title(f"{name} A18 Pro {capacity} 미개봉")
                        self.assertFalse(explicit["chip_defaulted"])
                        self.assertLess(parsed["confidence_score"], explicit["confidence_score"])

    def test_missing_chip_inference_uses_storage_in_body_or_structured_fields(self):
        for kwargs in ({"body_text": "512GB 모델 판매합니다"},
                       {"self_check_fields": {"모델명": "MacBook Neo", "SSD용량": "512GB"}}):
            with self.subTest(kwargs=kwargs):
                parsed = parse_listing_text("맥북 네오 판매", **kwargs)
                self.assertTrue(parsed["parse_success"], parsed)
                self.assertEqual((parsed["chip"], parsed["ram_gb"], parsed["ssd_gb"]), ("A18 Pro", 8, 512))
                self.assertTrue(parsed["chip_defaulted"])

    def test_structured_neo_cpu_family_has_a_unique_catalog_refinement(self):
        parsed = parse_listing_text("맥북 네오 512GB 판매", self_check_fields={
            "모델명": "맥북 네오 NEO", "CPU종류": "A18", "램 용량": "8GB", "SSD용량": "512GB",
        })
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual(parsed["chip"], "A18 Pro")
        self.assertTrue(parsed["chip_defaulted"])
        self.assertEqual(parsed["detected_patterns"]["chip"], {
            "value": "A18 Pro", "source": "inferred_structured_chip_family", "raw": "A18",
        })
        self.assertTrue(parsed["original_text"].endswith("A18"), parsed["original_text"])
        for text in ("맥북 네오 A18 8GB 512GB", "맥북 네오 M1 8GB 512GB"):
            parsed = parse_listing_text(text, self_check_fields={"CPU종류": "A18"})
            self.assertFalse(parsed["parse_success"], parsed)

    def test_body_only_neo_mention_cannot_infer_chip_for_another_listing(self):
        for title in ("아이폰 256GB 판매", "노트북 256GB 판매"):
            parsed = parse_listing_text(title, body_text="맥북 네오도 쓰고 있어요")
            self.assertFalse(parsed["parse_success"], parsed)
            self.assertFalse(parsed["chip_defaulted"])
        parsed = parse_listing_text("노트북 512GB 판매", self_check_fields={"모델명": "MacBook Neo"})
        self.assertTrue(parsed["parse_success"], parsed)

    def test_inferred_chip_does_not_guess_between_storage_options(self):
        for title in ("맥북 네오 판매", "맥북 네오 8GB", "맥북 네오 13인치"):
            with self.subTest(title=title):
                parsed = parse_listing_title(title)
                self.assertFalse(parsed["parse_success"])
                self.assertIn("ssd_gb", parsed["missing_fields"])
        self.assert_neo("맥북 네오 기본형")

    def test_chip_inference_does_not_override_unsupported_or_ambiguous_hardware(self):
        for detail in ("A18", "A18 Max", "A19 Pro", "M1", "M6", "M10", "Intel", "i7", "Ryzen",
                       "A18 Pro M6", "A18 Pro Intel", "MacBook Air", "iMac", "Mac Studio"):
            with self.subTest(detail=detail):
                parsed = parse_listing_title(f"맥북 네오 {detail} 8GB 256GB")
                self.assertFalse(parsed["parse_success"], parsed)
                self.assertFalse(parsed["chip_defaulted"])
        for cpu in ("Intel", "M6", "unknown processor"):
            parsed = parse_listing_text("맥북 네오 256GB", self_check_fields={"CPU종류": cpu})
            self.assertFalse(parsed["parse_success"], parsed)
        for title in ("MacBook Neo A19Pro256GB", "맥북네오 M6max256GB"):
            parsed = parse_listing_title(title)
            self.assertFalse(parsed["parse_success"], parsed)
            self.assertFalse(parsed["chip_defaulted"])
        for detail in ("16GB 256GB", "8GB 1TB", "14인치 8GB 256GB", "8GB 256GB 512GB"):
            self.assertFalse(parse_listing_title("맥북 네오 " + detail)["parse_success"])

    def test_chipless_accessory_box_only_and_wanted_titles_are_not_inferred(self):
        for title in ("맥북 네오 256GB 케이스", "맥북네오 512GB 파우치 판매", "맥북 네오 256 박스만",
                      "맥북네오 256GB 구합니다", "맥북네오 512GB 삽니다", "MacBook Neo 256GB case",
                      "MacBook Neo 512GB box only", "WTB MacBook Neo 256GB"):
            with self.subTest(title=title):
                parsed = parse_listing_title(title)
                self.assertFalse(parsed["parse_success"], parsed)
                self.assertFalse(parsed["chip_defaulted"])
        self.assert_neo("맥북 네오 256GB 케이스 포함 판매")

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
