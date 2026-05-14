import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.joongna_polling_service import _build_keyword_targets_from_watch_rules, poll_once  # noqa: E402


class PollingWatchRuleKeywordTest(unittest.TestCase):
    def test_build_keyword_targets_dedupes_keyword_and_keeps_multiple_users(self):
        targets = _build_keyword_targets_from_watch_rules(
            [
                {
                    "id": 1,
                    "user_id": "boongtol",
                    "search_keyword": " 맥북 m1 ",
                },
                {
                    "id": 2,
                    "user_id": "test_user",
                    "search_keyword": "맥북 m1",
                },
            ]
        )

        self.assertEqual(list(targets.keys()), ["맥북 m1"])
        self.assertEqual(len(targets["맥북 m1"]), 2)

    def test_poll_once_applies_watch_rule_matching(self):
        due_rules = [
            {
                "id": 1,
                "user_id": "boongtol",
                "search_keyword": "맥북",
                "product_type": "MacBook Air",
                "chip": "M1",
                "screen_inch": 13,
                "ram_gb": 8,
                "ssd_gb": 256,
                "target_price_krw": 900000,
                "fair_price_krw": 1000000,
                "alert_drop_rate_percent": 10.0,
            },
            {
                "id": 2,
                "user_id": "test_user",
                "search_keyword": "맥북",
                "product_type": "MacBook Air",
                "chip": "M2",
                "screen_inch": 13,
                "ram_gb": 16,
                "ssd_gb": 512,
                "target_price_krw": 1300000,
                "fair_price_krw": 1500000,
                "alert_drop_rate_percent": 13.33,
            },
        ]

        mock_item = {
            "seq": 1001,
            "product_id": 1001,
            "title": "맥북에어 M2 16GB 512GB",
            "price": 1200000,
            "refresh_key": "rk-1",
            "product_url": "https://web.joongna.com/product/1001",
            "image_url": "",
        }

        with patch("src.joongna_polling_service.get_due_watch_rules", return_value=due_rules):
            with patch("src.joongna_polling_service.search_joongna_products", return_value=[mock_item]):
                with patch("src.joongna_polling_service.get_connection", side_effect=RuntimeError("db down")):
                    with patch("src.joongna_polling_service.mark_watch_rule_polled") as mock_mark_polled:
                        with patch("src.joongna_polling_service.analyze_url_for_user") as mock_analyze:
                            mock_analyze.return_value = {
                                "ok": True,
                                "status": "success",
                                "is_alert_target": True,
                                "telegram_sent": True,
                            }
                            stats = poll_once()

        self.assertEqual(mock_analyze.call_count, 1)
        call_kwargs = mock_analyze.call_args.kwargs
        self.assertEqual(call_kwargs.get("user_id"), "test_user")
        self.assertEqual(call_kwargs.get("fair_price_override_krw"), 1500000)
        self.assertEqual(call_kwargs.get("alert_drop_rate_percent_override"), 13.33)
        self.assertEqual(mock_mark_polled.call_count, 2)
        self.assertEqual(stats.get("skipped_rule_mismatch"), 1)


if __name__ == "__main__":
    unittest.main()
