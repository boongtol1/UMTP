import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import resale_trade_journeys as journeys  # noqa: E402


class ResaleTradeJourneysTest(unittest.TestCase):
    def test_extract_product_id_from_url(self):
        product_id = journeys._extract_product_id_from_url("https://web.joongna.com/product/12345")
        self.assertEqual(product_id, "12345")

    def test_merge_priority_prefers_user_over_existing_and_sources(self):
        existing_row = {
            "id": 1,
            "title": "existing-title",
            "listing_price_krw": 500000,
            "fair_price_krw": None,
        }
        user_values = {
            "title": "user-title",
            "fair_price_krw": 640000,
        }
        source_candidates = [
            {"title": "alert-title", "fair_price_krw": 630000, "listing_price_krw": 490000},
            {"title": "analysis-title", "fair_price_krw": 620000},
        ]

        updates = journeys._merge_by_priority(
            user_values=user_values,
            existing_row=existing_row,
            source_candidates=source_candidates,
            writable_columns={"title", "listing_price_krw", "fair_price_krw"},
        )

        self.assertEqual(updates.get("title"), "user-title")
        self.assertEqual(updates.get("fair_price_krw"), 640000)
        self.assertNotIn("listing_price_krw", updates)

    def test_merge_priority_uses_source_for_blank_existing(self):
        existing_row = {
            "id": 2,
            "listing_price_krw": None,
            "seller_nickname": "",
        }
        user_values = {}
        source_candidates = [
            {"listing_price_krw": 520000},
            {"listing_price_krw": 510000, "seller_nickname": "seller-from-search"},
        ]

        updates = journeys._merge_by_priority(
            user_values=user_values,
            existing_row=existing_row,
            source_candidates=source_candidates,
            writable_columns={"listing_price_krw", "seller_nickname"},
        )

        self.assertEqual(updates.get("listing_price_krw"), 520000)
        self.assertEqual(updates.get("seller_nickname"), "seller-from-search")

    def test_prepare_sparse_updates_skips_null_and_empty(self):
        updates = journeys._prepare_sparse_updates(
            {
                "purchase_price_krw": "",
                "inspection_notes": "  ",
                "shipping_cost_krw": "123",
                "money_sent_at": None,
            },
            journeys.PURCHASE_PATCH_FIELDS,
            {"purchase_price_krw", "inspection_notes", "shipping_cost_krw", "money_sent_at"},
        )

        self.assertEqual(updates, {"shipping_cost_krw": 123})

    def test_prepare_sparse_updates_accepts_all_payload_keys_when_allowed_fields_none(self):
        updates = journeys._prepare_sparse_updates(
            {
                "seller_nickname": "seller-a",
                "listing_price_krw": "720000",
                "id": 99,
                "url_digest": "abc",
            },
            None,
            {"seller_nickname", "listing_price_krw", "id", "url_digest"},
        )

        self.assertEqual(
            updates,
            {
                "seller_nickname": "seller-a",
                "listing_price_krw": 720000,
            },
        )

    def test_prepare_sparse_updates_purchase_fields_are_enforced(self):
        updates = journeys._prepare_sparse_updates(
            {
                "purchase_price_krw": "650000",
                "final_result_notes": "memo",
                "purchase_contact_record": "010-1111-2222",
                "purchase_conversation_text": "상태 좋다고 답변받음",
                "money_sent_at": "2026-05-25 12:30",
                "money_received_at": "2026-05-26 09:10:00",
                "purchase_account_number": " 123-456-7890 ",
                "inspection_notes": "  상태 양호  ",
                "sale_price_krw": "820000",
                "listing_price_krw": "700000",
            },
            journeys.PURCHASE_PATCH_FIELDS,
            {
                "purchase_price_krw",
                "final_result_notes",
                "purchase_contact_record",
                "purchase_conversation_text",
                "money_sent_at",
                "money_received_at",
                "purchase_account_number",
                "inspection_notes",
                "sale_price_krw",
                "listing_price_krw",
            },
        )

        self.assertEqual(
            updates,
            {
                "purchase_price_krw": 650000,
                "final_result_notes": "memo",
                "purchase_contact_record": "010-1111-2222",
                "purchase_conversation_text": "상태 좋다고 답변받음",
                "money_sent_at": datetime(2026, 5, 25, 12, 30, 0),
                "purchase_account_number": "123-456-7890",
                "inspection_notes": "상태 양호",
            },
        )

    def test_prepare_sparse_updates_purchase_fields_drop_removed_field(self):
        updates = journeys._prepare_sparse_updates(
            {
                "seller_location": "  서울 강남구  ",
                "purchase_contact_record": " 010-1111-2222 ",
                "url": "https://example.com/product/1",
            },
            journeys.PURCHASE_PATCH_FIELDS,
            {"seller_location", "purchase_contact_record", "url"},
        )

        self.assertEqual(
            updates,
            {
                "purchase_contact_record": "010-1111-2222",
            },
        )

    def test_prepare_sparse_updates_resale_record_allows_sold_fields(self):
        updates = journeys._prepare_sparse_updates(
            {
                "resale_contact_record": "카톡 boongtol",
                "resale_conversation_text": "입금 확인 후 발송 약속",
                "money_sent_at": "2026-05-25T10:00:00",
                "money_received_at": "2026-05-25T11:00:00",
                "resale_account_number": "2222-3333-4444",
                "resale_listing_price_krw": "790000",
                "sale_price_krw": "810000",
                "purchase_price_krw": "700000",
                "current_stage": "SOLD",
            },
            journeys.RESALE_RECORD_PATCH_FIELDS,
            {
                "resale_contact_record",
                "resale_conversation_text",
                "money_sent_at",
                "money_received_at",
                "resale_account_number",
                "resale_listing_price_krw",
                "sale_price_krw",
                "purchase_price_krw",
                "current_stage",
            },
        )

        self.assertEqual(
            updates,
            {
                "resale_contact_record": "카톡 boongtol",
                "resale_conversation_text": "입금 확인 후 발송 약속",
                "money_received_at": datetime(2026, 5, 25, 11, 0, 0),
                "resale_account_number": "2222-3333-4444",
                "resale_listing_price_krw": 790000,
                "sale_price_krw": 810000,
                "current_stage": "SOLD",
            },
        )

    def test_alert_event_mapping_hydrates_core_fields(self):
        mapped = journeys._build_alert_mapping(
            {
                "source": "joongna",
                "product_id": "228",
                "url": "https://web.joongna.com/product/228",
                "title": "M2 16GB",
                "sort_date": "2026-05-24 10:00:00",
                "created_at": "2026-05-24 10:05:00",
                "price_krw": 700000,
                "fair_price_krw": 860000,
                "drop_rate_percent": 18.6,
                "risk_keywords": ["급처", "풀박스"],
                "seller_store_seq": 11,
                "seller_store_name": "seller-a",
            }
        )

        self.assertEqual(mapped.get("source"), "joongna")
        self.assertEqual(mapped.get("product_id"), "228")
        self.assertEqual(mapped.get("listing_price_krw"), 700000)
        self.assertEqual(mapped.get("fair_price_krw"), 860000)
        self.assertEqual(mapped.get("seller_shop_id"), "11")
        self.assertEqual(mapped.get("seller_nickname"), "seller-a")
        self.assertIsNotNone(mapped.get("reason_tags"))

    def test_seen_product_mapping_hydrates_core_fields(self):
        mapped = journeys._build_seen_product_mapping(
            {
                "seq": 228,
                "product_url": "https://web.joongna.com/product/228",
                "last_title": "M1 16GB",
                "last_price_krw": 690000,
                "last_sort_date": "2026-05-24 09:00:00",
                "first_seen_at": "2026-05-24 08:00:00",
                "image_url": "https://img.example.com/a.jpg",
            }
        )

        self.assertEqual(mapped.get("source"), "joongna")
        self.assertEqual(mapped.get("product_id"), "228")
        self.assertEqual(mapped.get("title"), "M1 16GB")
        self.assertEqual(mapped.get("listing_price_krw"), 690000)
        self.assertIsNotNone(mapped.get("image_urls"))

    def test_stage_after_purchase_becomes_inspected(self):
        stage = journeys._derive_stage_after_purchase(
            {"current_stage": journeys.STAGE_DISCOVERED},
            {"purchased_at": "2026-05-24 10:00:00"},
        )
        self.assertEqual(stage, journeys.STAGE_INSPECTED)

    def test_stage_after_purchase_prefers_manual_stage(self):
        stage = journeys._derive_stage_after_purchase(
            {"current_stage": journeys.STAGE_DISCOVERED},
            {"purchased_at": "2026-05-24 10:00:00", "current_stage": "RESALE_LISTED"},
        )
        self.assertEqual(stage, "RESALE_LISTED")

    def test_stage_after_resale_or_sold(self):
        stage_listed = journeys._derive_stage_after_resale_or_sold(
            {
                "sale_price_krw": None,
                "sold_at": None,
                "resale_listing_price_krw": 780000,
                "resale_platform": "joongna",
                "resale_url": None,
                "resale_listing_created_at": None,
                "current_stage": journeys.STAGE_INSPECTED,
            }
        )
        self.assertEqual(stage_listed, journeys.STAGE_RESALE_LISTED)

        stage_sold = journeys._derive_stage_after_resale_or_sold(
            {
                "sale_price_krw": 820000,
                "sold_at": None,
                "current_stage": journeys.STAGE_RESALE_LISTED,
            }
        )
        self.assertEqual(stage_sold, journeys.STAGE_SOLD)

    def test_stage_after_resale_or_sold_prefers_manual_stage(self):
        stage = journeys._derive_stage_after_resale_or_sold(
            {
                "sale_price_krw": None,
                "sold_at": None,
                "current_stage": journeys.STAGE_RESALE_LISTED,
            },
            {"current_stage": "INSPECTED"},
        )
        self.assertEqual(stage, "INSPECTED")

    @patch("src.resale_trade_journeys._fetch_journey_by_key", return_value={"id": 99})
    def test_insert_or_get_journey_id_reuses_existing_row(self, _mock_fetch):
        cursor = MagicMock()
        row_id = journeys._insert_or_get_journey_id(
            cursor,
            user_id="user1",
            source="joongna",
            product_id="123",
            writable_columns={"user_id", "source", "product_id", "current_stage"},
        )

        self.assertEqual(row_id, 99)
        cursor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
