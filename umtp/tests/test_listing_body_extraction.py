import json
import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.listing_page_parser import extract_listing_body_text, parse_joongna_listing_page


def product_json_ld(description, **extra):
    product = {"@type": "Product", "name": "맥북", "description": description, **extra}
    return '<script type="application/ld+json">' + json.dumps({"@graph": [product]}) + '</script>'


class ListingBodyExtractionTest(unittest.TestCase):
    def test_twitter_body_without_title_or_price_preserves_paragraphs(self):
        html = '<meta name="twitter:description" content="  첫 줄&#10;&#10;둘째 줄 &amp; 구성품  ">'
        self.assertEqual(extract_listing_body_text(html), "첫 줄\n\n둘째 줄 & 구성품")

    def test_twitter_description_has_priority(self):
        html = '<meta property="og:description" content="요약"><meta name="twitter:description" content="원문">'
        self.assertEqual(extract_listing_body_text(html), "원문")

    def test_blank_twitter_falls_back_to_og(self):
        html = '<meta name="twitter:description" content="  "><meta property="og:description" content="상세 본문">'
        self.assertEqual(extract_listing_body_text(html), "상세 본문")

    def test_product_json_ld_fallback_preserves_line_breaks(self):
        self.assertEqual(extract_listing_body_text(product_json_ld("첫 줄\r\n둘째 줄")), "첫 줄\n둘째 줄")

    def test_structured_fallback_matches_current_product(self):
        html = '<link rel="canonical" href="https://web.joongna.com/product/123">'
        html += product_json_ld("다른 상품", sku="456") + product_json_ld("현재 상품", sku="123")
        self.assertEqual(extract_listing_body_text(html), "현재 상품")

    def test_unrelated_or_ambiguous_structured_descriptions_are_not_body(self):
        cases = [
            '<script type="application/ld+json">{"@type":"WebSite","description":"사이트 소개"}</script>',
            '<script type="application/ld+json">{broken</script>',
            '<link rel="canonical" href="https://web.joongna.com/product/123">' + product_json_ld("추천 상품", sku="456"),
            product_json_ld("상품 A") + product_json_ld("상품 B"),
        ]
        for html in cases:
            with self.subTest(html=html):
                self.assertIsNone(extract_listing_body_text(html))

    def test_generic_site_metadata_is_not_a_listing_body(self):
        generic = "안심결제부터 보상제도까지. 중고나라는 이제 안심할 수 있는 중고거래 플랫폼입니다."
        html = '<meta name="twitter:description" content="' + generic + '">'
        self.assertIsNone(extract_listing_body_text(html))
        self.assertIsNone(extract_listing_body_text('<title>중고나라 - 안심되는 중고거래</title>' + product_json_ld("추천상품")))

    def test_generic_meta_can_fall_back_to_actual_product_body(self):
        html = '<meta name="twitter:description" content="중고나라 - 안심되는 중고거래">' + product_json_ld("판매자의 본문")
        self.assertEqual(extract_listing_body_text(html), "판매자의 본문")

    def test_unavailable_or_404_page_does_not_return_stale_metadata(self):
        for notice in ("<span>이 상품은 더 이상 판매되지 않아요.</span>", "<h1>페이지를 찾을 수 없습니다.</h1>", "<title>404 Not Found</title>"):
            with self.subTest(notice=notice):
                self.assertIsNone(extract_listing_body_text(notice + '<meta name="twitter:description" content="이전 본문">'))

    def test_error_message_in_script_does_not_hide_valid_body(self):
        html = '<script>const fallback = "페이지를 찾을 수 없습니다.";</script><meta name="twitter:description" content="매물 본문">'
        self.assertEqual(extract_listing_body_text(html), "매물 본문")

    def test_general_description_requires_listing_identity(self):
        meta = '<meta name="description" content="설명 텍스트">'
        self.assertIsNone(extract_listing_body_text(meta))
        self.assertEqual(extract_listing_body_text('<link rel="canonical" href="https://web.joongna.com/product/123">' + meta), "설명 텍스트")

    def test_missing_body_does_not_fall_back_to_page_text(self):
        for html in (None, "", "  ", '<meta name="twitter:description">', '<h1>상품 이름</h1><p>메뉴 및 다른 상품</p>'):
            with self.subTest(html=html):
                self.assertIsNone(extract_listing_body_text(html))

    def test_full_parser_uses_body_fallback_and_keeps_title_price_contract(self):
        body = '<meta property="og:description" content="본문">'
        title = '<meta name="twitter:title" content="매물 제목">'
        price = '<span class="whitespace-pre-line text-32 font-bold max-md:text-24">120,000원</span>'
        parsed = parse_joongna_listing_page(title + body + price)
        self.assertEqual(parsed["description"], "본문")
        self.assertEqual(parsed["listing_price_krw"], 120000)
        with self.assertRaisesRegex(ValueError, "제목 추출 실패"):
            parse_joongna_listing_page(body + price)
        with self.assertRaisesRegex(ValueError, "가격 추출 실패"):
            parse_joongna_listing_page(title + body)
        self.assertEqual(extract_listing_body_text(title + body), "본문")


if __name__ == "__main__":
    unittest.main()
