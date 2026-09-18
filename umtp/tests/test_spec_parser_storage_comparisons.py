import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.spec_parser import parse_listing_text  # noqa: E402


class StorageComparisonAsideTest(unittest.TestCase):
    TITLES = (
        "맥북프로 M1 Pro 14인치 16GB 512GB",
        "맥북 네오 512GB",
        "아이맥 M1 24인치 8GB 512GB",
        "맥스튜디오 M1 Max 32GB 512GB",
    )

    def test_agreeing_title_and_structured_storage_exclude_only_comparison_asides(self):
        for title in self.TITLES:
            for aside in ("(256GB는 안돼요)", "(256GB는 터치아이디 미지원)"):
                with self.subTest(title=title, aside=aside):
                    body = f"512GB 판매합니다. {aside}"
                    parsed = parse_listing_text(title, body_text=body, self_check_fields={"SSD용량": "512GB"})
                    self.assertTrue(parsed["parse_success"], parsed)
                    self.assertEqual(parsed["ssd_gb"], 512)
                    self.assertIn(aside, parsed["original_text"])
                    self.assertIn(aside, parsed["removed_noise_fragments"])
                    self.assertNotIn(aside.lower(), parsed["normalized_text"])

    def test_actual_neo_title_body_and_structured_family_remain_consistent(self):
        parsed = parse_listing_text(
            "맥북 네오 512GB 터치아이디 가능 배터리성능 100% 풀박스 급처해요",
            body_text="특S급 맥북 네오 인디고 색상 512GB 판매해요. 네오 512GB라 터치아이디도 됩니다(256GB는 안돼요)",
            self_check_fields={"CPU종류": "A18", "SSD용량": "512GB", "모델명": "맥북 네오 NEO", "램 용량": "8GB"},
        )
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual((parsed["chip"], parsed["screen_inch"], parsed["ram_gb"], parsed["ssd_gb"]),
                         ("A18 Pro", 13, 8, 512))

    def test_sale_spec_conflicts_and_multiple_listings_are_not_hidden(self):
        for title in self.TITLES:
            for body in ("실제 판매 모델은 256GB입니다", "(256GB 모델 판매합니다)",
                         "512GB와 256GB 두 대 판매합니다", "외장 SSD 256GB 포함",
                         "(256GB는 안돼요) 실제 판매 모델은 256GB입니다"):
                with self.subTest(title=title, body=body):
                    parsed = parse_listing_text(title, body_text=body, self_check_fields={"SSD용량": "512GB"})
                    self.assertFalse(parsed["parse_success"], parsed)

    def test_no_independent_agreement_keeps_storage_conflict_visible(self):
        for title in self.TITLES:
            for fields in ({}, {"SSD용량": "256GB"}):
                with self.subTest(title=title, fields=fields):
                    parsed = parse_listing_text(title, body_text="(256GB는 안돼요)", self_check_fields=fields)
                    self.assertFalse(parsed["parse_success"], parsed)
                    self.assertNotIn("(256GB는 안돼요)", parsed["removed_noise_fragments"])


if __name__ == "__main__":
    unittest.main()
