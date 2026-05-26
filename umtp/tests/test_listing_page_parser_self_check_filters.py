import os
import sys
import unittest

from bs4 import BeautifulSoup


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.listing_page_parser import extract_self_check_fields  # noqa: E402


class ListingPageParserSelfCheckFilterTest(unittest.TestCase):
    def test_extract_self_check_fields_skips_manual_verification_keys(self):
        html = """
        <html>
          <body>
            <dl>
              <dt>모델명</dt><dd>MacBook Air M2</dd>
              <dt>램 용량</dt><dd>16GB</dd>
              <dt>SSD용량</dt><dd>512GB</dd>
              <dt>일련번호</dt><dd>C02XX0ABC123</dd>
              <dt>MDM 잠금 없음 확인</dt><dd>예</dd>
              <dt>활성화 잠금 해제 확인</dt><dd>예</dd>
              <dt>AppleCare 상태</dt><dd>2027-01-31까지</dd>
            </dl>
          </body>
        </html>
        """

        fields = extract_self_check_fields(BeautifulSoup(html, "html.parser"))

        self.assertEqual(fields.get("모델명"), "MacBook Air M2")
        self.assertEqual(fields.get("램 용량"), "16GB")
        self.assertEqual(fields.get("SSD용량"), "512GB")
        self.assertNotIn("일련번호", fields)
        self.assertNotIn("MDM 잠금 없음 확인", fields)
        self.assertNotIn("활성화 잠금 해제 확인", fields)
        self.assertNotIn("AppleCare 상태", fields)


if __name__ == "__main__":
    unittest.main()
