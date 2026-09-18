import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import api_server, user_settings_service as settings
from src.macbook_air_units import generate_units_for_product, get_product_base_spec, is_valid_silicon_unit
from src.search_keyword_utils import build_default_keyword_for_watch_rule, build_recommended_keywords_for_spec
from test_macbook_pro_settings import SettingsConnection, SettingsCursor, unit_key


def seed_rows():
    seed = (Path(PROJECT_ROOT) / "sql/seed_silicon_macbook_neo_fair_prices.sql").read_text()
    return [dict(product_type="MacBook Neo", chip=chip, screen_inch=int(screen), ram_gb=int(ram),
                 ssd_gb=int(ssd), fair_price_krw=int(price))
            for chip, screen, ram, ssd, price in re.findall(
                r"\('MacBook Neo', '([^']+)', (\d+), (\d+), (\d+), (\d+)\)", seed)]


class MacBookNeoSettingsTest(unittest.TestCase):
    def test_catalog_and_endpoint_match_exact_two_seed_configurations(self):
        expected = {("MacBook Neo", "A18 Pro", 13, 8, 256), ("MacBook Neo", "A18 Pro", 13, 8, 512)}
        self.assertEqual({unit_key(row) for row in seed_rows()}, expected)
        units = generate_units_for_product("MacBook Neo")
        self.assertEqual(len(units), 2)
        self.assertEqual({unit_key(row) for row in units}, expected)
        self.assertEqual({unit_key(row) for row in api_server.macbook_air_units()["units"]
                          if row["product_type"] == "MacBook Neo"}, expected)
        self.assertEqual(get_product_base_spec("MacBook Neo", "A18 Pro", 13), {"ram_gb": 8, "ssd_gb": 256})

    def test_settings_use_seed_prices_and_disabled_defaults(self):
        rows = seed_rows()
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            items = settings.get_user_fair_price_settings("neo-user")
        neo = [item for item in items if item["product_type"] == "MacBook Neo"]
        self.assertEqual(len(neo), 2)
        self.assertEqual([item["system_fair_price_krw"] for item in neo], [850000, 900000])
        self.assertEqual([item["effective_target_buy_price_krw"] for item in neo], [680000, 720000])
        self.assertTrue(all(not item["enabled"] and not item["has_user_override"] for item in neo))
        self.assertTrue(all(item["recommended_search_keyword"] == "맥북 네오" for item in neo))
        self.assertTrue(all("MacBook Neo" in params for _, params in cursor.executed))

    def test_override_wins_over_seed_and_save_normalizes_a18_pro(self):
        row = seed_rows()[1]
        override = dict(row, id=123, fair_price_krw=1000000, alert_drop_rate_percent=10,
                        enabled=True, search_keyword="맥북네오 512", priority="FAST")
        cursor = SettingsCursor(system_rows=[row], user_rows=[override])
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            items = settings.get_user_fair_price_settings("neo-user")
        item = next(item for item in items if unit_key(item) == unit_key(row))
        self.assertEqual(item["system_fair_price_krw"], 900000)
        self.assertEqual(item["effective_fair_price_krw"], 1000000)
        self.assertEqual(item["effective_target_buy_price_krw"], 900000)
        self.assertEqual(item["effective_search_keyword"], "맥북네오 512")
        self.assertEqual(item["priority"], "FAST")
        for chip in ("A18 Pro", "a18pro", "a18 pro", " A18  PRO "):
            with self.subTest(chip=chip):
                cursor = SettingsCursor()
                connection = SettingsConnection(cursor)
                with patch.object(settings, "get_connection", return_value=connection):
                    result = settings.upsert_user_fair_price_setting(
                        "neo-user", "MacBook Neo", chip, 13, 8, 512, 900000, 20, True)
                self.assertTrue(result["ok"], result)
                self.assertTrue(result["immediate_poll_requested"])
                self.assertTrue(connection.committed)
                insert = next(params for query, params in cursor.executed if query.startswith("insert into user_fair_prices"))
                self.assertEqual(insert[1:6], unit_key(row))
                self.assertEqual(insert[13], "맥북 네오")

    def test_invalid_specs_reject_before_database_access(self):
        with patch.object(settings, "get_connection") as connection:
            for spec in (("A18", 13, 8, 256), ("A18 Max", 13, 8, 256), ("M1", 13, 8, 256),
                         ("A18 Pro", 13, 16, 256), ("A18 Pro", 13, 8, 1024), ("A18 Pro", 14, 8, 256)):
                with self.subTest(spec=spec):
                    self.assertFalse(is_valid_silicon_unit("MacBook Neo", *spec))
                    result = settings.upsert_user_fair_price_setting("neo-user", "MacBook Neo", *spec, 900000, 20, True)
                    self.assertEqual(result, {"ok": False, "reason": "invalid_silicon_unit"})
            connection.assert_not_called()

    def test_bulk_and_reset_are_scoped_to_neo(self):
        for action in (
            lambda: settings.bulk_set_user_watch_rules_enabled("neo-user", True, product_type="MacBook Neo"),
            lambda: settings.bulk_update_user_fair_price_drop_rate("neo-user", 15, product_type="MacBook Neo"),
        ):
            cursor = SettingsCursor()
            with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
                result = action()
            self.assertTrue(result["ok"], result)
            for query, params in cursor.executed:
                if query.startswith("update"):
                    self.assertIn("and product_type = %s", query)
                    self.assertEqual(params[-1], "MacBook Neo")
        cursor = SettingsCursor(system_rows=seed_rows())
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            result = settings.reset_user_fair_prices_to_system_market_prices("neo-user", product_type="MacBook Neo")
        self.assertEqual(result["inserted_count"], 2)
        inserts = [params for query, params in cursor.executed if query.startswith("insert into user_fair_prices")]
        self.assertEqual({params[1:6]: params[6] for params in inserts}, {unit_key(row): row["fair_price_krw"] for row in seed_rows()})
        self.assertTrue(all(params[11] is False for params in inserts))

    def test_keywords_keep_korean_product_and_canonical_chip(self):
        self.assertEqual(build_default_keyword_for_watch_rule({"product_type": "MacBook Neo"}), "맥북 네오")
        self.assertEqual(
            build_default_keyword_for_watch_rule({"product_type": "MacBook Neo", "chip": "A18 Pro"}),
            "맥북 네오",
        )
        keywords = build_recommended_keywords_for_spec("MacBook Neo", "a18pro", 8, 512)
        self.assertEqual(keywords[0], "맥북 네오")
        self.assertIn("MacBook Neo A18 Pro", keywords)
        self.assertIn("맥북 네오 A18 Pro", keywords)


if __name__ == "__main__":
    unittest.main()
