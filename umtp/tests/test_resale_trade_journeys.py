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
                "purchase_contact_record": "010-1111-2222",
                "purchase_conversation_text": "상태 좋다고 답변받음",
                "contacted_at": "2026-05-25 12:00",
                "seller_response_at": "2026-05-25 12:30",
                "purchase_account_number": " 123-456-7890 ",
                "inspection_notes": "  상태 양호  ",
                "sale_platform": "  joongna  ",
                "sale_price_krw": "820000",
                "listing_price_krw": "700000",
            },
            journeys.PURCHASE_PATCH_FIELDS,
            {
                "purchase_price_krw",
                "purchase_contact_record",
                "purchase_conversation_text",
                "contacted_at",
                "seller_response_at",
                "purchase_account_number",
                "inspection_notes",
                "sale_platform",
                "sale_price_krw",
                "listing_price_krw",
            },
        )

        self.assertEqual(
            updates,
            {
                "purchase_price_krw": 650000,
                "listing_price_krw": 700000,
                "contacted_at": datetime(2026, 5, 25, 12, 0, 0),
                "seller_response_at": datetime(2026, 5, 25, 12, 30, 0),
                "inspection_notes": "상태 양호",
                "sale_platform": "joongna",
            },
        )

    def test_prepare_sparse_updates_purchase_fields_allow_seller_location_and_drop_removed_fields(self):
        updates = journeys._prepare_sparse_updates(
            {
                "seller_location": "  서울 강남구  ",
                "purchase_contact_record": " 010-1111-2222 ",
                "money_sent_at": "2026-05-25 12:30",
                "url": "https://example.com/product/1",
            },
            journeys.PURCHASE_PATCH_FIELDS,
            {"seller_location", "purchase_contact_record", "money_sent_at", "url"},
        )

        self.assertEqual(updates, {"seller_location": "서울 강남구"})

    def test_prepare_sparse_updates_purchase_fields_include_manual_verification_fields(self):
        updates = journeys._prepare_sparse_updates(
            {
                "serial_number": " C02XX0ABC123 ",
                "model_number": "A3113",
                "cpu_core_count": "8",
                "gpu_core_count": "10",
                "battery_cycle_count": "121",
                "battery_health_percent": "96",
                "applecare_status": "2027-01-31",
                "activation_lock_off": "true",
                "mdm_lock_none": "false",
            },
            journeys.PURCHASE_PATCH_FIELDS,
            {
                "serial_number",
                "model_number",
                "cpu_core_count",
                "gpu_core_count",
                "battery_cycle_count",
                "battery_health_percent",
                "applecare_status",
                "activation_lock_off",
                "mdm_lock_none",
            },
        )

        self.assertEqual(
            updates,
            {
                "serial_number": "C02XX0ABC123",
                "model_number": "A3113",
                "battery_cycle_count": 121,
                "battery_health_percent": 96,
                "activation_lock_off": True,
                "mdm_lock_none": False,
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
        self.assertNotIn("seller_shop_id", mapped)
        self.assertNotIn("risk_score", mapped)
        self.assertNotIn("reason_tags", mapped)
        self.assertEqual(mapped.get("seller_nickname"), "seller-a")

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

    def test_build_trade_prefill_uses_priority_and_latest_listing_state(self):
        result = journeys._build_trade_prefill_from_source_rows(
            user_id="boongtol",
            product_id="228",
            alert_row={
                "source": "joongna",
                "product_id": "228",
                "url": "https://web.joongna.com/product/228",
                "title": "오래된 알림 제목",
                "price_krw": 760000,
                "sort_date": "2026-05-20 09:00:00",
                "product_type": "MacBook Air",
                "chip": "M1",
                "screen_inch": 13,
                "ram_gb": 8,
                "ssd_gb": 256,
                "risk_score": 80,
                "risk_keywords": ["급처"],
            },
            listing_analysis_row={
                "product_type": "MacBook Air",
                "chip": "M2",
                "screen_inch": 13,
                "ram_gb": 16,
                "ssd_gb": 512,
                "fair_price_krw": 930000,
                "updated_at": "2026-05-21 09:00:00",
            },
            url_analysis_row={},
            seen_product_row={
                "seq": 228,
                "product_url": "https://web.joongna.com/product/228",
                "last_title": "최신 캐시 제목",
                "last_price_krw": 720000,
                "last_sort_date": "2026-05-22 09:00:00",
                "image_url": "https://img.example.com/new.jpg",
                "seller_store_name": "최신판매자",
                "seller_location": "서울",
            },
            search_result_row={},
        )

        row = result.get("row", {})
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("sources"), ["alert_events", "listing_analysis_results", "joongna_seen_products"])
        self.assertEqual(row.get("title"), "최신 캐시 제목")
        self.assertEqual(row.get("listing_price_krw"), 720000)
        self.assertEqual(row.get("seller_nickname"), "최신판매자")
        self.assertEqual(row.get("chip"), "M2")
        self.assertEqual(row.get("ram_gb"), 16)
        self.assertEqual(row.get("ssd_gb"), 512)
        self.assertNotIn("risk_score", row)
        self.assertNotIn("reason_tags", row)

    def test_build_trade_prefill_parses_missing_specs_from_text(self):
        result = journeys._build_trade_prefill_from_source_rows(
            user_id="boongtol",
            product_id="229",
            alert_row={},
            listing_analysis_row={},
            url_analysis_row={},
            seen_product_row={},
            search_result_row={
                "product_id": "229",
                "title": "맥북에어 M2 13인치 16GB 512GB",
                "price": 820000,
                "raw_json": '{"image_url": "https://img.example.com/229.jpg", "location_names": ["서울", "강남구"]}',
                "created_at": "2026-05-22 09:00:00",
            },
        )

        row = result.get("row", {})
        self.assertTrue(result.get("ok"))
        self.assertIsNotNone(row.get("product_type"))
        self.assertEqual(row.get("chip"), "M2")
        self.assertEqual(row.get("screen_inch"), 13)
        self.assertEqual(row.get("ram_gb"), 16)
        self.assertEqual(row.get("ssd_gb"), 512)
        self.assertIn("img.example.com/229.jpg", row.get("image_urls") or "")
        self.assertEqual(row.get("seller_location"), "서울, 강남구")

    def test_build_trade_prefill_returns_not_found_when_no_existing_records(self):
        result = journeys._build_trade_prefill_from_source_rows(
            user_id="boongtol",
            product_id="230",
            alert_row={},
            listing_analysis_row={},
            url_analysis_row={},
            seen_product_row={},
            search_result_row={},
        )

        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("reason"), "not_found")
        self.assertEqual(result.get("message"), "기존 DB 기록 없음")
        self.assertEqual(result.get("row", {}).get("product_id"), "230")
        self.assertNotIn("purchase_price_krw", result.get("row", {}))
        self.assertNotIn("risk_score", result.get("row", {}))

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

    @patch(
        "src.resale_trade_journeys.start_or_prefill_resale_trade_journey_from_product",
        return_value={"ok": True, "id": 14, "trade_journey_id": 14, "existing": False},
    )
    @patch("src.resale_trade_journeys._fetch_latest_alert_event_by_reference", return_value={})
    @patch("src.resale_trade_journeys.get_connection")
    def test_start_resale_trade_journey_from_url(
        self,
        mock_get_connection,
        _mock_fetch_alert,
        mock_start_or_prefill,
    ):
        connection = MagicMock()
        connection.cursor.return_value = MagicMock()
        connection.is_connected.return_value = True
        mock_get_connection.return_value = connection

        response = journeys.start_resale_trade_journey_from_url(
            user_id="boongtol",
            url="https://web.joongna.com/product/228826879",
        )

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("trade_journey_id"), 14)
        kwargs = mock_start_or_prefill.call_args.kwargs
        self.assertEqual(kwargs.get("user_id"), "boongtol")
        self.assertEqual(kwargs.get("source"), "joongna")
        self.assertEqual(kwargs.get("product_id"), "228826879")
        self.assertEqual(
            kwargs.get("seed_values", {}).get("url"),
            "https://web.joongna.com/product/228826879",
        )

    @patch(
        "src.resale_trade_journeys.start_or_prefill_resale_trade_journey_from_product",
        return_value={"ok": True, "id": 15, "trade_journey_id": 15, "existing": False},
    )
    @patch("src.resale_trade_journeys._fetch_latest_alert_event_by_reference", return_value={})
    @patch("src.resale_trade_journeys.get_connection")
    def test_start_resale_trade_journey_from_url_accepts_product_id(
        self,
        mock_get_connection,
        _mock_fetch_alert,
        mock_start_or_prefill,
    ):
        connection = MagicMock()
        connection.cursor.return_value = MagicMock()
        connection.is_connected.return_value = True
        mock_get_connection.return_value = connection

        response = journeys.start_resale_trade_journey_from_url(
            user_id="boongtol",
            url="228826879",
        )

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("trade_journey_id"), 15)
        kwargs = mock_start_or_prefill.call_args.kwargs
        self.assertEqual(kwargs.get("user_id"), "boongtol")
        self.assertEqual(kwargs.get("source"), "joongna")
        self.assertEqual(kwargs.get("product_id"), "228826879")
        self.assertEqual(kwargs.get("seed_values", {}).get("product_id"), "228826879")

    @patch(
        "src.resale_trade_journeys.start_or_prefill_resale_trade_journey_from_product",
        return_value={"ok": True, "id": 16, "trade_journey_id": 16, "existing": False},
    )
    @patch(
        "src.resale_trade_journeys._fetch_latest_alert_event_by_reference",
        return_value={
            "source": "bunjang",
            "product_id": "listing-998",
            "url": "https://example.com/listings/listing-998",
            "title": "M2 16GB",
            "price_krw": 700000,
            "chip": "M2",
            "ram_gb": 16,
            "ssd_gb": 512,
        },
    )
    @patch("src.resale_trade_journeys.get_connection")
    def test_start_resale_trade_journey_from_url_uses_alert_event_reference(
        self,
        mock_get_connection,
        mock_fetch_alert,
        mock_start_or_prefill,
    ):
        connection = MagicMock()
        connection.cursor.return_value = MagicMock()
        connection.is_connected.return_value = True
        mock_get_connection.return_value = connection

        response = journeys.start_resale_trade_journey_from_url(
            user_id="boongtol",
            url="listing-998",
        )

        self.assertTrue(response.get("ok"))
        mock_fetch_alert.assert_called_once()
        kwargs = mock_start_or_prefill.call_args.kwargs
        self.assertEqual(kwargs.get("source"), "bunjang")
        self.assertEqual(kwargs.get("product_id"), "listing-998")
        seed_values = kwargs.get("seed_values", {})
        self.assertEqual(seed_values.get("url"), "https://example.com/listings/listing-998")
        self.assertEqual(seed_values.get("title"), "M2 16GB")
        self.assertEqual(seed_values.get("listing_price_krw"), 700000)
        self.assertEqual(seed_values.get("chip"), "M2")
        self.assertEqual(seed_values.get("ram_gb"), 16)

    @patch("src.resale_trade_journeys._build_prefill_row_by_product", return_value={"current_stage": journeys.STAGE_DISCOVERED})
    @patch("src.resale_trade_journeys._hydrate_row_by_product")
    @patch("src.resale_trade_journeys._fetch_journey_by_key", return_value=None)
    @patch("src.resale_trade_journeys._get_resale_columns", return_value=(set(), set()))
    @patch("src.resale_trade_journeys.get_connection")
    def test_start_or_prefill_does_not_create_row_when_not_existing(
        self,
        mock_get_connection,
        _mock_columns,
        _mock_fetch,
        mock_hydrate,
        _mock_prefill,
    ):
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value = cursor
        connection.is_connected.return_value = True
        mock_get_connection.return_value = connection

        response = journeys.start_or_prefill_resale_trade_journey_from_product(
            user_id="boongtol",
            source="joongna",
            product_id="228826879",
            seed_values={"url": "https://web.joongna.com/product/228826879"},
        )

        self.assertTrue(response.get("ok"))
        self.assertFalse(response.get("existing"))
        self.assertIsNone(response.get("id"))
        self.assertIsNone(response.get("trade_journey_id"))
        mock_hydrate.assert_not_called()
        connection.commit.assert_not_called()
        executed_sql = " ".join(
            str(call.args[0]).lower()
            for call in cursor.execute.call_args_list
            if call.args
        )
        self.assertNotIn("insert into resale_trade_journeys", executed_sql)
        self.assertNotIn("update resale_trade_journeys", executed_sql)

    @patch("src.resale_trade_journeys._build_prefill_row_by_product")
    @patch("src.resale_trade_journeys._hydrate_row_by_product", return_value={"id": 55, "current_stage": journeys.STAGE_INSPECTED})
    @patch("src.resale_trade_journeys._fetch_journey_by_key", return_value={"id": 55, "source": "joongna", "product_id": "228826879"})
    @patch("src.resale_trade_journeys._get_resale_columns", return_value=(set(), {"current_stage"}))
    @patch("src.resale_trade_journeys.get_connection")
    def test_start_or_prefill_opens_existing_row_without_creating_new(
        self,
        mock_get_connection,
        _mock_columns,
        _mock_fetch,
        mock_hydrate,
        mock_prefill,
    ):
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value = cursor
        connection.is_connected.return_value = True
        mock_get_connection.return_value = connection

        response = journeys.start_or_prefill_resale_trade_journey_from_product(
            user_id="boongtol",
            source="joongna",
            product_id="228826879",
            seed_values={"title": "M2"},
        )

        self.assertTrue(response.get("ok"))
        self.assertTrue(response.get("existing"))
        self.assertEqual(response.get("id"), 55)
        self.assertEqual(response.get("trade_journey_id"), 55)
        mock_hydrate.assert_called_once()
        mock_prefill.assert_not_called()
        connection.commit.assert_called_once()

    def test_build_read_archive_mapping(self):
        mapped = journeys._build_read_archive_mapping(
            {
                "alert_source": "joongna",
                "alert_product_id": "123",
                "alert_url": "https://web.joongna.com/product/123",
                "alert_title": "M2 16GB",
                "alert_sort_date": "2026-05-26 10:00:00",
                "alert_price_krw": 780000,
                "alert_fair_price_krw": 930000,
                "alert_drop_rate_percent": 16.1,
                "alert_product_type": "macbook_air",
                "alert_chip": "M2",
                "alert_screen_inch": 13,
                "alert_ram_gb": 16,
                "alert_ssd_gb": 512,
                "alert_risk_keywords": "[\"급처\"]",
                "alert_body_text": "본문 원문",
                "alert_listing_image_url": "https://img.example.com/a.jpg",
            }
        )

        self.assertEqual(mapped.get("source"), "joongna")
        self.assertEqual(mapped.get("product_id"), "123")
        self.assertEqual(mapped.get("url"), "https://web.joongna.com/product/123")
        self.assertEqual(mapped.get("listing_price_krw"), 780000)
        self.assertEqual(mapped.get("fair_price_krw"), 930000)
        self.assertEqual(mapped.get("chip"), "M2")
        self.assertEqual(mapped.get("screen_inch"), 13)
        self.assertEqual(mapped.get("ram_gb"), 16)
        self.assertEqual(mapped.get("ssd_gb"), 512)
        self.assertIn("img.example.com", mapped.get("image_urls") or "")

    @patch("src.resale_trade_journeys._safe_fetchall", return_value=[{"id": 1}])
    @patch("src.resale_trade_journeys.get_connection")
    def test_list_purchased_resale_trade_journeys_excludes_sold_stage(
        self,
        mock_get_connection,
        mock_fetchall,
    ):
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value = cursor
        connection.is_connected.return_value = True
        mock_get_connection.return_value = connection

        result = journeys.list_purchased_resale_trade_journeys(
            user_id="boongtol",
            limit=77,
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("items"), [{"id": 1}])
        query = mock_fetchall.call_args.args[1]
        params = mock_fetchall.call_args.args[2]
        self.assertIn("purchased_at IS NOT NULL", query)
        self.assertIn("current_stage <> %s", query)
        self.assertEqual(params, ("boongtol", journeys.STAGE_SOLD, 77))

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
