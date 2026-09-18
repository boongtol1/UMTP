import os
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import listing_analysis_pipeline as pipeline
from src import notification_worker as worker
from src.analysis_service import _build_telegram_message as build_analysis_telegram_message
from src.spec_parser import parse_listing_title


class MacBookProNotificationsTest(unittest.TestCase):
    def test_url_analysis_telegram_uses_actual_default_screen_size(self):
        for title, screen in [
            ("맥북에어 M3 8GB 256GB", 13),
            ("맥북프로 M1 8GB 256GB", 13),
            ("맥북프로 M3 8GB 512GB", 14),
            ("맥북프로 M4 16GB 512GB", 14),
            ("맥북프로 M5 16GB 512GB", 14),
        ]:
            with self.subTest(title=title):
                parsed = parse_listing_title(title)
                self.assertTrue(parsed["parse_success"])
                self.assertTrue(parsed["screen_inch_defaulted"])
                message = build_analysis_telegram_message(
                    title, 500000, 800000, 37.5,
                    "https://web.joongna.com/product/1001", {},
                    screen_inch_defaulted=parsed["screen_inch_defaulted"],
                    screen_inch=parsed["screen_inch"],
                )
                self.assertIn(f"화면 크기: {screen}인치 기본값 사용", message)

    def test_title_hints_recognize_compact_pro_max_and_high_capacity_memory(self):
        for title in [
            "맥북프로 m1pro 14인치 16GB 512GB",
            "맥북프로 M3-Pro 14인치 18GB 1TB",
            "맥북프로 M3 Max 16인치 36GB 1TB",
            "맥북프로 M2맥스 16인치 96기가 4TB",
            "맥북프로 m5max 16인치 램128 8TB",
        ]:
            with self.subTest(title=title):
                self.assertTrue(pipeline._title_has_explicit_core_specs(title))
        self.assertFalse(pipeline._title_has_explicit_core_specs("맥북프로 M5 Max 16인치 8TB"))

    def test_telegram_feed_keeps_existing_format_for_all_mac_families(self):
        specs = [
            ("MacBook Air", "M1", 13, 8, 256),
            ("Mac mini", "M2 Pro", 0, 16, 512),
            ("MacBook Pro", "M1", 13, 8, 256),
            ("MacBook Pro", "M3 Pro", 14, 36, 512),
            ("MacBook Pro", "M5 Max", 16, 128, 8192),
        ]
        expected_labels = None
        for product, chip, screen, ram, ssd in specs:
            with self.subTest(product=product, chip=chip):
                message = worker._build_telegram_message({
                    "title": f"{product} {chip}",
                    "product_type": product,
                    "chip": chip,
                    "screen_inch": screen,
                    "ram_gb": ram,
                    "ssd_gb": ssd,
                    "price_krw": 3500000,
                    "fair_price_krw": 4000000,
                    "target_price_krw": 3600000,
                    "url": "https://web.joongna.com/product/1001",
                })
                labels = [section.split("\n")[0] for section in message.split("\n\n")]
                if expected_labels is None:
                    expected_labels = labels
                self.assertEqual(labels, expected_labels)
                self.assertIn(f"제품 분류\n{product}", message)
                self.assertIn(f"칩\n{chip}", message)
                self.assertIn(f"RAM\n{ram}GB", message)
                self.assertIn(f"SSD\n{ssd}GB", message)
                if screen:
                    self.assertIn(f"화면 크기\n{screen}인치", message)
                self.assertIn("등록 가격\n3,500,000원", message)
                self.assertIn("내가 생각한 시장가\n4,000,000원", message)
                self.assertIn("알림 기준 가격\n3,600,000원", message)

    def test_read_alert_groups_sort_pro_and_max_with_their_generation(self):
        rows = [
            {"id": index, "chip": chip, "screen_inch": 16}
            for index, chip in enumerate([
                "M5 Max", "M2", "M1 Max", "M1 Pro", "M1", "M2 Pro",
                "M5 Pro", "M2 Max", "M5", "Intel", "",
            ], start=1)
        ]
        with patch.object(worker, "list_alert_events_for_user", return_value=rows):
            groups = worker.list_grouped_read_alert_events_for_user("test-user")
        self.assertEqual(list(groups), [
            "M1", "M1 PRO", "M1 MAX", "M2", "M2 PRO", "M2 MAX",
            "M5", "M5 PRO", "M5 MAX", "INTEL", "기타",
        ])
        self.assertEqual(groups["M5 MAX"]["16"][0]["id"], 1)

    def _analyze_pro_listing(self, *, title, price, enabled=True):
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = None
        stored_alert = {}

        def save_alert(cursor, **values):
            stored_alert.update(values)
            stored_alert.update(values["parsed_spec"])
            stored_alert["id"] = 71
            return {"created": True, "alert_id": 71}

        job = {
            "id": 1,
            "user_id": "pro-user",
            "product_id": "1001",
            "url": "https://web.joongna.com/product/1001",
            "title": title,
            "price_krw": price,
            "trigger_reason": "new",
            "search_keyword": "m5max 맥북프로",
        }
        page = {
            "title": title,
            "description": "정상 판매합니다.",
            "listing_price_krw": price,
            "self_check_fields": {},
        }
        # Keep the parser, eligibility checks, dispatch, and formatter real;
        # replace persistence and external delivery boundaries only.
        with ExitStack() as stack:
            for module, name, value in [
                (pipeline, "get_connection", connection),
                (pipeline, "fetch_html", "<html></html>"),
                (pipeline, "parse_joongna_listing_page", page),
                (pipeline, "get_seen_product", {}),
                (pipeline, "persist_latest_search_result_enrichment", None),
                (pipeline, "update_seen_product_content_snapshot", None),
                (pipeline, "is_user_fair_price_target_enabled", enabled),
                (pipeline, "resolve_fair_price_for_user", {
                    "fair_price_krw": 4000000,
                    "alert_drop_rate_percent": 10,
                    "source": "user_fair_prices",
                }),
                (pipeline, "save_listing_analysis_result", {"diff_ratio": 12.5}),
                (pipeline, "save_success_log", None),
                (worker, "mark_alert_event_sending", True),
                (worker, "get_alert_event_by_id", stored_alert),
                (worker, "resolve_user_alert_delivery_policy", {
                    "enabled": True,
                    "telegram_chat_id": "123456",
                    "allow_global_fallback": False,
                }),
                (worker, "_enrich_alert_for_display", None),
                (worker, "_ensure_alert_fraud_probability_for_delivery", None),
                (worker, "_send_fcm_to_user", {"sent": 0, "attempted": 0}),
                (worker, "_telegram_configured", True),
                (worker, "_fetch_listing_image_url_by_product_id", None),
                (worker, "mark_alert_event_sent", None),
            ]:
                stack.enter_context(patch.object(module, name, return_value=value))
            create_alert = stack.enter_context(patch.object(
                pipeline, "maybe_create_alert_event", side_effect=save_alert,
            ))
            send_telegram = stack.enter_context(patch.object(
                worker, "send_telegram_alert", return_value=True,
            ))
            result = pipeline.analyze_product_for_watch_rule(job)
        return result, create_alert, send_telegram

    def test_eligible_pro_listings_reach_telegram_with_complete_specs(self):
        cases = [
            ("맥북프로 M1 13인치 8GB 256GB", "M1", 13, 8, 256),
            ("맥북프로 M3 Pro 14인치 36GB 512GB", "M3 Pro", 14, 36, 512),
            ("맥북프로 M5 Max 16인치 128GB 8TB", "M5 Max", 16, 128, 8192),
        ]
        for title, chip, screen, ram, ssd in cases:
            with self.subTest(chip=chip):
                result, create_alert, send_telegram = self._analyze_pro_listing(
                    title=title, price=3500000,
                )
                self.assertTrue(result["is_alert_target"])
                self.assertTrue(result["alert_created"])
                self.assertEqual(result["alert_dispatch_status"], "sent")
                parsed = create_alert.call_args.kwargs["parsed_spec"]
                self.assertEqual(parsed["product_type"], "MacBook Pro")
                self.assertEqual(parsed["chip"], chip)
                send_telegram.assert_called_once()
                message = send_telegram.call_args.args[0]
                for row in [
                    "제품 분류\nMacBook Pro", f"칩\n{chip}",
                    f"화면 크기\n{screen}인치", f"RAM\n{ram}GB", f"SSD\n{ssd}GB",
                    "등록 가격\n3,500,000원", "알림 기준 가격\n3,600,000원",
                ]:
                    self.assertIn(row, message)
                self.assertEqual(send_telegram.call_args.kwargs["chat_id"], "123456")
                self.assertFalse(send_telegram.call_args.kwargs["allow_global_fallback"])

    def test_pro_listings_respect_price_threshold_and_enabled_setting(self):
        for price, enabled, reason in [
            (3700000, True, "drop_rate_below_threshold"),
            (3500000, False, "user_target_disabled"),
        ]:
            with self.subTest(price=price, enabled=enabled):
                result, create_alert, send_telegram = self._analyze_pro_listing(
                    title="맥북프로 M5 Max 16인치 128GB 8TB",
                    price=price,
                    enabled=enabled,
                )
                self.assertFalse(result["alert_created"])
                self.assertEqual(result["alert_skip_reason"], reason)
                create_alert.assert_not_called()
                send_telegram.assert_not_called()


if __name__ == "__main__":
    unittest.main()
