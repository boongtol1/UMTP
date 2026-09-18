import os
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import listing_analysis_pipeline as pipeline, notification_worker as worker
from src.analysis_service import _build_telegram_message as analysis_message
from src.spec_parser import parse_listing_title


class IMacNotificationsTest(unittest.TestCase):
    def analyze(self, title, price, enabled=True):
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = None
        stored_alert = {}

        def save_alert(cursor, **values):
            stored_alert.update(values)
            stored_alert.update(values["parsed_spec"])
            stored_alert["id"] = 71
            return {"created": True, "alert_id": 71}

        job = dict(id=1, user_id="imac-user", product_id="1001", url="https://web.joongna.com/product/1001",
                   title=title, price_krw=price, trigger_reason="new", search_keyword="m4 아이맥")
        page = dict(title=title, description="정상 판매합니다.", listing_price_krw=price, self_check_fields={})
        # Keep parsing, eligibility, dispatch, and formatting real; isolate
        # persistence, listing HTTP, and Telegram/FCM delivery boundaries.
        with ExitStack() as stack:
            for module, name, value in [
                (pipeline, "get_connection", connection), (pipeline, "fetch_html", "<html></html>"),
                (pipeline, "parse_joongna_listing_page", page), (pipeline, "get_seen_product", {}),
                (pipeline, "persist_latest_search_result_enrichment", None),
                (pipeline, "update_seen_product_content_snapshot", None),
                (pipeline, "is_user_fair_price_target_enabled", enabled),
                (pipeline, "resolve_fair_price_for_user", dict(fair_price_krw=1500000, alert_drop_rate_percent=20, source="user_fair_prices")),
                (pipeline, "save_listing_analysis_result", {"diff_ratio": 33.33}),
                (pipeline, "save_success_log", None),
                (worker, "mark_alert_event_sending", True), (worker, "get_alert_event_by_id", stored_alert),
                (worker, "resolve_user_alert_delivery_policy", dict(enabled=True, telegram_chat_id="123456", allow_global_fallback=False)),
                (worker, "_enrich_alert_for_display", None), (worker, "_ensure_alert_fraud_probability_for_delivery", None),
                (worker, "_send_fcm_to_user", dict(sent=0, attempted=0)), (worker, "_telegram_configured", True),
                (worker, "_fetch_listing_image_url_by_product_id", None), (worker, "mark_alert_event_sent", None),
            ]:
                stack.enter_context(patch.object(module, name, return_value=value))
            create_alert = stack.enter_context(patch.object(pipeline, "maybe_create_alert_event", side_effect=save_alert))
            send = stack.enter_context(patch.object(worker, "send_telegram_alert", return_value=True))
            result = pipeline.analyze_product_for_watch_rule(job)
        return result, create_alert, send

    def test_imac_title_hints_and_default_screen_analysis_message(self):
        for title in ("아이맥 판매", "아이 맥 판매", "iMac 판매"):
            self.assertTrue(pipeline._contains_mac_product_name(title))
            self.assertTrue(pipeline._is_title_product_name_only_spec_missing(title, parse_listing_title(title)))
        self.assertTrue(pipeline._title_has_explicit_core_specs("iMac M4 24인치 32GB 2TB"))
        self.assertFalse(pipeline._title_has_explicit_core_specs("iMac M4 24인치 2TB"))
        parsed = parse_listing_title("iMac M4 16GB 256GB")
        message = analysis_message("iMac M4", 1000000, 1500000, 33.33, "https://web.joongna.com/product/1001", {},
                                   screen_inch_defaulted=parsed["screen_inch_defaulted"], screen_inch=parsed["screen_inch"])
        self.assertIn("화면 크기: 24인치 기본값 사용", message)

    def test_each_chip_dispatches_same_telegram_format_with_complete_specs(self):
        for chip, ram, ssd in (("M1", 8, 256), ("M3", 24, 1024), ("M4", 32, 2048)):
            for title in (
                f"아이맥 {chip} 24인치 {ram}GB {ssd}GB",
                f"iMac {chip} 24-inch {ram}GB {ssd}GB",
            ):
                with self.subTest(chip=chip, title=title):
                    result, create_alert, send = self.analyze(title, 1000000)
                    self.assertTrue(result["alert_created"], result)
                    self.assertEqual(result["alert_dispatch_status"], "sent")
                    self.assertEqual(create_alert.call_args.kwargs["parsed_spec"]["product_type"], "iMac")
                    send.assert_called_once()
                    message = send.call_args.args[0]
                    for field in ("제품 분류\niMac", f"칩\n{chip}", "화면 크기\n24인치", f"RAM\n{ram}GB", f"SSD\n{ssd}GB",
                                  "등록 가격\n1,000,000원", "내가 생각한 시장가\n1,500,000원", "알림 기준 가격\n1,200,000원"):
                        self.assertIn(field, message)
                    self.assertEqual(send.call_args.kwargs["chat_id"], "123456")
                    self.assertFalse(send.call_args.kwargs["allow_global_fallback"])

    def test_price_threshold_and_disabled_settings_prevent_delivery(self):
        for price, enabled, reason in ((1300000, True, "drop_rate_below_threshold"), (1000000, False, "user_target_disabled")):
            result, create_alert, send = self.analyze("아이맥 M4 24인치 16GB 256GB", price, enabled)
            self.assertEqual(result["alert_skip_reason"], reason)
            create_alert.assert_not_called()
            send.assert_not_called()

    def test_read_alert_groups_keep_generation_order_and_24_inch_group(self):
        rows = [dict(id=index, product_type="iMac", chip=chip, screen_inch=24)
                for index, chip in enumerate(("M4", "M1", "M3"), start=1)]
        with patch.object(worker, "list_alert_events_for_user", return_value=rows):
            groups = worker.list_grouped_read_alert_events_for_user("imac-user")
        self.assertEqual(list(groups), ["M1", "M3", "M4"])
        self.assertEqual(groups["M4"]["24"][0]["id"], 1)


if __name__ == "__main__":
    unittest.main()
