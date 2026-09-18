import os
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import listing_analysis_pipeline as pipeline, notification_worker as worker
from src.analysis_service import _build_telegram_message as build_analysis_message
from src.spec_parser import parse_listing_title


class MacBookNeoNotificationsTest(unittest.TestCase):
    def test_title_analysis_hints_recognize_a18_pro_without_treating_18_as_ram(self):
        for chip in ("A18 Pro", "a18pro", "A18-Pro", "A18 프로"):
            with self.subTest(chip=chip):
                self.assertTrue(pipeline._contains_mac_product_name("MacBook Neo " + chip))
                self.assertTrue(pipeline._title_has_explicit_core_specs(f"맥북 네오 {chip} 8GB 512GB"))
                self.assertFalse(pipeline._title_has_explicit_core_specs(f"맥북 네오 {chip} 512GB"))

    def test_url_analysis_telegram_reports_thirteen_inch_default(self):
        title = "맥북네오 A18 Pro 8GB 256GB"
        parsed = parse_listing_title(title)
        message = build_analysis_message(title, 600000, 850000, 29.4, "https://web.joongna.com/product/1001", {},
                                         screen_inch_defaulted=parsed["screen_inch_defaulted"], screen_inch=parsed["screen_inch"])
        self.assertIn("화면 크기: 13인치 기본값 사용", message)

    def test_read_alert_groups_sort_a18_pro_after_m_chips_before_unknown(self):
        rows = [{"id": index, "chip": chip, "screen_inch": 13}
                for index, chip in enumerate(("Intel", "A18 Pro", "M5 Max", "M1", ""), 1)]
        with patch.object(worker, "list_alert_events_for_user", return_value=rows):
            groups = worker.list_grouped_read_alert_events_for_user("neo-user")
        self.assertEqual(list(groups), ["M1", "M5 MAX", "A18 PRO", "INTEL", "기타"])

    def analyze(self, ssd, price, enabled=True, detail=None):
        fair_price = 850000 if ssd == 256 else 900000
        title = "맥북네오 A18 Pro " + (detail or f"13인치 8GB {ssd}GB")
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = None
        stored = {}

        def save_alert(cursor, **values):
            stored.update(values)
            stored.update(values["parsed_spec"])
            stored["id"] = 72
            return {"created": True, "alert_id": 72}

        job = dict(id=1, user_id="neo-user", product_id="1001", url="https://web.joongna.com/product/1001",
                   title=title, price_krw=price, trigger_reason="new", search_keyword="a18pro 맥북네오")
        page = dict(title=title, description="정상 판매합니다.", listing_price_krw=price, self_check_fields={})
        with ExitStack() as stack:
            for module, name, value in [
                (pipeline, "get_connection", connection), (pipeline, "fetch_html", "<html></html>"),
                (pipeline, "parse_joongna_listing_page", page), (pipeline, "get_seen_product", {}),
                (pipeline, "persist_latest_search_result_enrichment", None),
                (pipeline, "update_seen_product_content_snapshot", None),
                (pipeline, "is_user_fair_price_target_enabled", enabled),
                (pipeline, "resolve_fair_price_for_user", dict(fair_price_krw=fair_price, alert_drop_rate_percent=20, source="mac_fair_prices")),
                (pipeline, "save_listing_analysis_result", {"diff_ratio": (fair_price - price) * 100 / fair_price}),
                (pipeline, "save_success_log", None),
                (worker, "mark_alert_event_sending", True), (worker, "get_alert_event_by_id", stored),
                (worker, "resolve_user_alert_delivery_policy", dict(enabled=True, telegram_chat_id="123456", allow_global_fallback=False)),
                (worker, "_enrich_alert_for_display", None), (worker, "_ensure_alert_fraud_probability_for_delivery", None),
                (worker, "_send_fcm_to_user", dict(sent=0, attempted=0)), (worker, "_telegram_configured", True),
                (worker, "_fetch_listing_image_url_by_product_id", None), (worker, "mark_alert_event_sent", None),
            ]:
                stack.enter_context(patch.object(module, name, return_value=value))
            create = stack.enter_context(patch.object(pipeline, "maybe_create_alert_event", side_effect=save_alert))
            send = stack.enter_context(patch.object(worker, "send_telegram_alert", return_value=True))
            result = pipeline.analyze_product_for_watch_rule(job)
        return result, create, send

    def test_both_seed_configurations_reach_existing_telegram_format(self):
        for ssd, target in ((256, "680,000"), (512, "720,000")):
            with self.subTest(ssd=ssd):
                result, create, send = self.analyze(ssd, 600000)
                self.assertTrue(result["is_alert_target"], result)
                self.assertEqual(result["alert_dispatch_status"], "sent")
                self.assertEqual(create.call_args.kwargs["parsed_spec"]["chip"], "A18 Pro")
                send.assert_called_once()
                message = send.call_args.args[0]
                for row in ("제품 분류\nMacBook Neo", "칩\nA18 Pro", "화면 크기\n13인치", "RAM\n8GB",
                            f"SSD\n{ssd}GB", "등록 가격\n600,000원", f"알림 기준 가격\n{target}원"):
                    self.assertIn(row, message)
                self.assertEqual(send.call_args.kwargs["chat_id"], "123456")
                self.assertFalse(send.call_args.kwargs["allow_global_fallback"])

    def test_disabled_rules_and_prices_above_threshold_do_not_send(self):
        for price, enabled, reason in ((800000, True, "drop_rate_below_threshold"), (600000, False, "user_target_disabled")):
            with self.subTest(price=price, enabled=enabled):
                result, create, send = self.analyze(256, price, enabled)
                self.assertEqual(result["alert_skip_reason"], reason)
                create.assert_not_called()
                send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
