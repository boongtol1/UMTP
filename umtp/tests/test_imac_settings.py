import os
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import api_server, user_settings_service as settings
from src.search_keyword_utils import build_recommended_keywords_for_spec
from test_macbook_pro_settings import SettingsCursor, SettingsConnection
from test_spec_parser_imac import seed_rows, unit_key


class IMacSettingsTest(unittest.TestCase):
    def test_catalog_endpoint_and_settings_expose_exact_seed_and_prices(self):
        units = [unit for unit in api_server.macbook_air_units()["units"] if unit["product_type"] == "iMac"]
        rows = seed_rows()
        self.assertEqual({unit_key(unit) for unit in units}, {unit_key(row) for row in rows})
        self.assertEqual(list(dict.fromkeys(unit["chip"] for unit in units)), ["M1", "M3", "M4"])
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            items = settings.get_user_fair_price_settings("imac-user")
        imac = {unit_key(item): item for item in items if item["product_type"] == "iMac"}
        self.assertEqual(len(imac), 32)
        for row in rows:
            item = imac[unit_key(row)]
            self.assertEqual(item["system_fair_price_krw"], row["fair_price_krw"])
            self.assertEqual(item["effective_fair_price_krw"], row["fair_price_krw"])
            self.assertEqual(item["effective_target_buy_price_krw"], row["fair_price_krw"] * 80 // 100)
            self.assertEqual(item["recommended_search_keyword"], row["chip"].lower() + " 아이맥")
            self.assertFalse(item["enabled"])
            self.assertFalse(item["has_user_override"])

    def test_recommended_keywords_stay_scoped_to_imac(self):
        keywords = build_recommended_keywords_for_spec("iMac", "m3", 24, 1024)
        self.assertEqual(keywords[0], "m3 아이맥")
        self.assertIn("아이맥 M3", keywords)
        self.assertIn("imac m3", keywords)
        self.assertIn("m3 아이맥 24 1024", keywords)
        self.assertFalse(any("맥북" in keyword for keyword in keywords))

    def test_save_each_chip_requests_polling_and_preserves_spec(self):
        for chip, ram in (("M1", 8), ("M3", 24), ("M4", 32)):
            cursor = SettingsCursor()
            connection = SettingsConnection(cursor)
            with patch.object(settings, "get_connection", return_value=connection):
                result = settings.upsert_user_fair_price_setting(
                    "imac-user", "iMac", chip.lower(), 24, ram, 1024, 1500000, 20, True)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["immediate_poll_requested"])
            self.assertTrue(connection.committed)
            values = next(params for query, params in cursor.executed if query.startswith("insert into user_fair_prices"))
            self.assertEqual(values[1:6], ("iMac", chip, 24, ram, 1024))
            self.assertEqual(values[13], chip.lower() + " 아이맥")

    def test_user_override_wins_and_invalid_seed_combinations_never_connect(self):
        row = seed_rows()[0]
        override = dict(row, id=321, fair_price_krw=650000, alert_drop_rate_percent=10,
                        enabled=True, search_keyword="아이맥 작업용", priority="FAST")
        with patch.object(settings, "get_connection", return_value=SettingsConnection(SettingsCursor([row], [override]))):
            items = settings.get_user_fair_price_settings("imac-user")
        item = next(item for item in items if unit_key(item) == unit_key(row))
        self.assertEqual(item["effective_fair_price_krw"], 650000)
        self.assertEqual(item["effective_target_buy_price_krw"], 585000)
        self.assertEqual(item["effective_search_keyword"], "아이맥 작업용")
        self.assertTrue(item["enabled"])
        with patch.object(settings, "get_connection") as connection:
            for chip, screen, ram, ssd in (("M2", 24, 8, 256), ("M1", 27, 8, 256),
                                          ("M4", 24, 8, 256), ("M3 Pro", 24, 16, 512), ("M3", 24, 24, 4096)):
                result = settings.upsert_user_fair_price_setting(
                    "imac-user", "iMac", chip, screen, ram, ssd, 1000000, 20, True)
                self.assertEqual(result, {"ok": False, "reason": "invalid_silicon_unit"})
            connection.assert_not_called()

    def test_bulk_controls_and_reset_are_scoped_and_use_seed_prices(self):
        for action in (
            lambda: settings.bulk_set_user_watch_rules_enabled("imac-user", True, product_type="iMac"),
            lambda: settings.bulk_update_user_fair_price_drop_rate("imac-user", 15, product_type="iMac"),
        ):
            cursor = SettingsCursor()
            with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
                self.assertTrue(action()["ok"])
            for query, values in cursor.executed:
                if query.startswith("update"):
                    self.assertIn("and product_type = %s", query)
                    self.assertEqual(values[-1], "iMac")
        rows = seed_rows()
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            result = settings.reset_user_fair_prices_to_system_market_prices("imac-user", product_type="iMac")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["inserted_count"], 32)
        inserts = [values for query, values in cursor.executed if query.startswith("insert into user_fair_prices")]
        self.assertEqual({values[1:6]: values[6] for values in inserts}, {unit_key(row): row["fair_price_krw"] for row in rows})
        self.assertTrue(all(values[11] is False for values in inserts))


if __name__ == "__main__":
    unittest.main()
