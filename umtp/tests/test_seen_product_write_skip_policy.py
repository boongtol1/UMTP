import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import upsert_seen_product_and_detect_change  # noqa: E402


def _base_observed_product():
    return {
        "product_id": 1001,
        "title": "M2 맥북에어 16/512",
        "price": 1200000,
        "sort_date": "2026-05-15 12:28:52",
        "refresh_key": "rk-1",
        "product_url": "https://web.joongna.com/product/1001",
        "image_url": "https://example.com/image.jpg",
        "search_word": "맥북 m2",
    }


def _base_existing_seen():
    return {
        "seq": 1001,
        "last_title": "M2 맥북에어 16/512",
        "last_price_krw": 1200000,
        "last_sort_date": "2026-05-15 12:28:52",
        "last_refresh_key": "rk-1",
    }


class SeenProductWriteSkipPolicyTest(unittest.TestCase):
    def _call_with_existing(self, existing_seen, observed_product):
        with patch("src.joongna_polling_service.get_seen_product", return_value=existing_seen):
            with patch("src.joongna_polling_service.upsert_seen_product_observation") as mock_upsert:
                result = upsert_seen_product_and_detect_change(
                    object(),
                    observed_product,
                    seen_db_ready=True,
                    on_db_error=self.fail,
                )
        return result, mock_upsert

    def test_new_listing_is_inserted(self):
        observed = _base_observed_product()
        result, mock_upsert = self._call_with_existing(None, observed)

        self.assertEqual(result.get("change_reason"), "new")
        self.assertTrue(result.get("write_performed"))
        self.assertEqual(result.get("write_action"), "inserted")
        self.assertEqual(mock_upsert.call_count, 1)

    def test_price_changed_listing_is_updated(self):
        existing = _base_existing_seen()
        observed = _base_observed_product()
        observed["price"] = 1100000

        result, mock_upsert = self._call_with_existing(existing, observed)

        self.assertEqual(result.get("change_reason"), "price_changed")
        self.assertTrue(result.get("write_performed"))
        self.assertEqual(result.get("write_action"), "updated")
        self.assertEqual(mock_upsert.call_count, 1)

    def test_title_changed_listing_is_updated(self):
        existing = _base_existing_seen()
        observed = _base_observed_product()
        observed["title"] = "M2 맥북에어 24/512"

        result, mock_upsert = self._call_with_existing(existing, observed)

        self.assertEqual(result.get("change_reason"), "title_changed")
        self.assertTrue(result.get("write_performed"))
        self.assertEqual(result.get("write_action"), "updated")
        self.assertEqual(mock_upsert.call_count, 1)

    def test_sort_date_changed_listing_is_updated(self):
        existing = _base_existing_seen()
        existing["last_sort_date"] = "2026-05-15 10:00:00"
        observed = _base_observed_product()

        result, mock_upsert = self._call_with_existing(existing, observed)

        self.assertEqual(result.get("change_reason"), "sort_date_changed")
        self.assertTrue(result.get("write_performed"))
        self.assertEqual(result.get("write_action"), "updated")
        self.assertEqual(mock_upsert.call_count, 1)

    def test_refresh_key_changed_listing_is_updated(self):
        existing = _base_existing_seen()
        observed = _base_observed_product()
        observed["refresh_key"] = "rk-2"

        result, mock_upsert = self._call_with_existing(existing, observed)

        self.assertEqual(result.get("change_reason"), "refresh_key_changed")
        self.assertTrue(result.get("write_performed"))
        self.assertEqual(result.get("write_action"), "updated")
        self.assertEqual(mock_upsert.call_count, 1)

    def test_unchanged_listing_skips_update(self):
        existing = _base_existing_seen()
        observed = _base_observed_product()

        result, mock_upsert = self._call_with_existing(existing, observed)

        self.assertEqual(result.get("change_reason"), "unchanged")
        self.assertFalse(result.get("write_performed"))
        self.assertEqual(result.get("write_action"), "skipped")
        self.assertFalse(result.get("should_analyze"))
        self.assertEqual(mock_upsert.call_count, 0)

    def test_unchanged_listing_does_not_touch_last_seen_at(self):
        existing = _base_existing_seen()
        observed = _base_observed_product()

        result, mock_upsert = self._call_with_existing(existing, observed)

        self.assertEqual(result.get("change_reason"), "unchanged")
        # unchanged면 UPSERT 자체를 건너뛰므로 last_seen_at 갱신도 일어나지 않는다.
        self.assertEqual(mock_upsert.call_count, 0)


if __name__ == "__main__":
    unittest.main()
