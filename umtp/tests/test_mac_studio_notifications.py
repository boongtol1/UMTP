import unittest
from unittest.mock import patch

import test_macbook_pro_notifications as pro_notifications
from test_macbook_pro_notifications import pipeline, worker


class MacStudioNotificationsTest(unittest.TestCase):
    def analyze(self, title, price=3500000, enabled=True):
        return pro_notifications.MacBookProNotificationsTest()._analyze_pro_listing(title=title, price=price, enabled=enabled)

    def test_title_hints_require_independent_ram_and_storage(self):
        for title in ("Mac Studio M1 Max 32GB 512GB", "맥스튜디오 M2울트라 192GB 8TB",
                      "맥 스튜디오 M3 Ultra RAM512 SSD16TB", "MacStudio M3Ultra 512/16384"):
            with self.subTest(title=title):
                self.assertTrue(pipeline._title_has_explicit_core_specs(title))
        for title in ("Mac Studio M3 Ultra 16TB", "Mac Studio M3 Ultra RAM512",
                      "Mac Studio M3 Ultra", "Mac Studio M3 Ultra 512GB"):
            with self.subTest(title=title):
                self.assertFalse(pipeline._title_has_explicit_core_specs(title))

    def test_studio_eligible_listings_reach_telegram_with_complete_spec_and_prices(self):
        for chip, ram, ssd, storage in (("M1 Max", 32, 512, "512GB"),
                                        ("M2 Ultra", 192, 8192, "8TB"),
                                        ("M3 Ultra", 512, 16384, "16TB"),
                                        ("M4 Max", 128, 8192, "8TB")):
            with self.subTest(chip=chip):
                result, created, sent = self.analyze(f"맥스튜디오 {chip} RAM {ram}GB SSD {storage}")
                self.assertTrue(result["is_alert_target"], result)
                self.assertEqual(result["alert_dispatch_status"], "sent")
                spec = created.call_args.kwargs["parsed_spec"]
                self.assertEqual((spec["product_type"], spec["chip"], spec["screen_inch"]), ("Mac Studio", chip, 0))
                message = sent.call_args.args[0]
                for row in ("제품 분류\nMac Studio", f"칩\n{chip}", f"RAM\n{ram}GB", f"SSD\n{ssd}GB",
                            "등록 가격\n3,500,000원", "내가 생각한 시장가\n4,000,000원", "알림 기준 가격\n3,600,000원"):
                    self.assertIn(row, message)
                self.assertNotIn("0인치", message)
                sent.assert_called_once()

    def test_disabled_and_overpriced_studio_never_dispatch(self):
        for price, enabled, reason in ((3700000, True, "drop_rate_below_threshold"),
                                      (3500000, False, "user_target_disabled")):
            result, created, sent = self.analyze("Mac Studio M1 Max 32GB 512GB", price, enabled)
            self.assertFalse(result["alert_created"])
            self.assertEqual(result["alert_skip_reason"], reason)
            created.assert_not_called()
            sent.assert_not_called()

    def test_archive_groups_sort_ultra_with_its_generation(self):
        chips = ["M4 Max", "M3 Ultra", "M2 Ultra", "M1 Ultra", "M2 Max", "M1 Max"]
        rows = [dict(id=index, chip=chip, screen_inch=0) for index, chip in enumerate(chips)]
        with patch.object(worker, "list_alert_events_for_user", return_value=rows):
            groups = worker.list_grouped_read_alert_events_for_user("studio-user")
        self.assertEqual(list(groups), ["M1 MAX", "M1 ULTRA", "M2 MAX", "M2 ULTRA", "M3 ULTRA", "M4 MAX"])
        self.assertTrue(all(list(screens) == ["기타"] for screens in groups.values()))
