import re
import unittest
from unittest.mock import patch

from test_macbook_pro_settings import (
    PROJECT_ROOT, Path, SettingsConnection, SettingsCursor, api_server, settings, unit_key,
)
from src.macbook_air_units import generate_units_for_product
from src.search_keyword_utils import build_recommended_keywords_for_spec
from src.spec_parser import parse_listing_text, parse_listing_title


def seed_rows():
    sql = (Path(PROJECT_ROOT) / "sql/seed_silicon_mac_studio_fair_prices.sql").read_text()
    return [dict(product_type="Mac Studio", chip=chip, screen_inch=int(screen), ram_gb=int(ram),
                 ssd_gb=int(ssd), fair_price_krw=int(price))
            for chip, screen, ram, ssd, price in re.findall(
                r"\('Mac Studio', '([^']+)', (\d+), (\d+), (\d+), (\d+)\)", sql)]


class MacStudioSettingsTest(unittest.TestCase):
    def test_catalog_and_parser_match_every_seed_specification(self):
        rows = seed_rows()
        self.assertEqual(len(rows), 80)
        units = [unit for unit in api_server.macbook_air_units()["units"] if unit["product_type"] == "Mac Studio"]
        self.assertEqual({unit_key(unit) for unit in units}, {unit_key(row) for row in rows})
        self.assertEqual(list(dict.fromkeys(unit["chip"] for unit in units)),
                         ["M1 Max", "M1 Ultra", "M2 Max", "M2 Ultra", "M3 Ultra", "M4 Max"])
        for row in rows:
            for title in (f"Mac Studio {row['chip']} {row['ram_gb']}GB {row['ssd_gb']}GB",
                          f"맥 스튜디오 {row['chip']} 램 {row['ram_gb']} SSD {row['ssd_gb']}"):
                with self.subTest(title=title):
                    parsed = parse_listing_title(title)
                    self.assertTrue(parsed["parse_success"], parsed)
                    self.assertEqual(unit_key(parsed), unit_key(row))
                    self.assertFalse(parsed["screen_inch_defaulted"])

    def test_korean_compact_tiers_and_high_ram_do_not_become_storage(self):
        for title in ("맥스튜디오 M3울트라 512/16TB", "MacStudio M3-Ultra 512GB 16T",
                      "맥 스튜디오 M 3 Ultra 메모리512기가 16테라",
                      "Mac Studio M3 Ultra SSD 16TB RAM 512",
                      "맥스튜디오 M3 Ultra 512 16384"):
            with self.subTest(title=title):
                parsed = parse_listing_title(title)
                self.assertTrue(parsed["parse_success"], parsed)
                self.assertEqual((parsed["ram_gb"], parsed["ssd_gb"]), (512, 16384))
        parsed = parse_listing_text("맥스튜디오 판매", self_check_fields={
            "모델명": "Mac Studio", "CPU종류": "M3 울트라", "램 용량": "512GB", "SSD용량": "16TB"})
        self.assertTrue(parsed["parse_success"], parsed)
        self.assertEqual((parsed["ram_gb"], parsed["ssd_gb"]), (512, 16384))
        self.assertEqual(parse_listing_title("맥스튜디오 M2맥스 기본형")["ram_gb"], 32)

    def test_invalid_seed_combinations_and_ambiguous_listings_are_rejected(self):
        for title in ("Mac Studio M3 Max 36GB 1TB", "Mac Studio M4 Ultra 128GB 1TB",
                      "Mac Studio M5 Max 36GB 1TB", "Mac Studio M3 96GB 1TB",
                      "Mac Studio Intel i7 32GB 512GB", "Mac Studio M3 Ultra 192GB 1TB",
                      "Mac Studio M2 Ultra 64GB 16TB", "Mac Studio M1 Max 16GB 512GB",
                      "Mac Studio M3 Ultra RAM 384GB SSD1TB",
                      "Mac Studio M3 Ultra RAM96 SSD32TB",
                      "Mac Studio M3 Ultra 384GB 1TB", "Mac Studio M3 Ultra 96GB 32TB",
                      "Mac Studio Mac mini M2 Max 32GB 512GB",
                      "Mac Studio MacBook Pro M1 Max 32GB 1TB",
                      "Mac Studio M1 Max M2 Max 32GB 512GB",
                      "Mac Studio M1 Max 13인치 32GB 512GB"):
            with self.subTest(title=title):
                self.assertFalse(parse_listing_title(title)["parse_success"])

    def test_existing_catalog_storage_does_not_become_high_capacity_ram(self):
        for product in ("MacBook Air", "Mac mini", "MacBook Pro"):
            for unit in generate_units_for_product(product):
                screen = f" {unit['screen_inch']}인치" if unit["screen_inch"] else ""
                parsed = parse_listing_title(f"{product} {unit['chip']}{screen} {unit['ram_gb']}GB {unit['ssd_gb']}GB")
                with self.subTest(unit=unit):
                    self.assertTrue(parsed["parse_success"], parsed)
                    self.assertEqual(unit_key(parsed), unit_key(unit))

    def test_settings_prices_keywords_and_disabled_defaults_match_seed(self):
        rows = seed_rows()
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            items = {unit_key(item): item for item in settings.get_user_fair_price_settings("studio-user")
                     if item["product_type"] == "Mac Studio"}
        self.assertEqual(len(items), 80)
        for row in rows:
            item = items[unit_key(row)]
            self.assertEqual(item["effective_fair_price_krw"], row["fair_price_krw"])
            self.assertEqual(item["effective_target_buy_price_krw"], row["fair_price_krw"] * 4 // 5)
            self.assertEqual(item["recommended_search_keyword"], row["chip"].lower().replace(" ", "") + " 맥스튜디오")
            self.assertFalse(item["enabled"])
        keywords = build_recommended_keywords_for_spec("Mac Studio", "m3ultra", 512, 16384)
        self.assertEqual(keywords[0], "m3ultra 맥스튜디오")
        self.assertIn("mac studio m3ultra", keywords)
        self.assertFalse(any("맥북" in keyword for keyword in keywords))

    def test_save_normalizes_all_seed_tiers_and_preserves_screen_zero(self):
        by_chip = {row["chip"]: row for row in seed_rows()}
        for chip, row in by_chip.items():
            cursor = SettingsCursor()
            connection = SettingsConnection(cursor)
            with patch.object(settings, "get_connection", return_value=connection):
                result = settings.upsert_user_fair_price_setting(
                    "studio-user", "Mac Studio", chip.lower().replace(" ", ""), 0,
                    row["ram_gb"], row["ssd_gb"], row["fair_price_krw"], 20, True)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["immediate_poll_requested"])
            inserted = next(params for query, params in cursor.executed if query.startswith("insert into user_fair_prices"))
            self.assertEqual(inserted[1:6], unit_key(row))
            self.assertTrue(connection.committed)

    def test_invalid_saves_do_not_connect_to_database(self):
        with patch.object(settings, "get_connection") as connection:
            for chip, screen, ram, ssd in (("M3 Max", 0, 36, 1024), ("M4 Ultra", 0, 128, 1024),
                                          ("M5 Max", 0, 36, 1024), ("M3 Ultra", 0, 192, 1024),
                                          ("M1 Max", 13, 32, 512)):
                result = settings.upsert_user_fair_price_setting("studio-user", "Mac Studio", chip, screen, ram, ssd, 1000000, 20, True)
                self.assertEqual(result, {"ok": False, "reason": "invalid_silicon_unit"})
            connection.assert_not_called()

    def test_bulk_and_reset_are_limited_to_studio(self):
        for action in (
            lambda: settings.bulk_set_user_watch_rules_enabled("studio-user", True, product_type="Mac Studio"),
            lambda: settings.bulk_update_user_fair_price_drop_rate("studio-user", 15, product_type="Mac Studio"),
        ):
            cursor = SettingsCursor()
            with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
                self.assertTrue(action()["ok"])
            for query, params in cursor.executed:
                if query.startswith("update"):
                    self.assertIn("and product_type = %s", query)
                    self.assertEqual(params[-1], "Mac Studio")
        rows = seed_rows()
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            result = settings.reset_user_fair_prices_to_system_market_prices("studio-user", product_type="Mac Studio")
        self.assertEqual(result["inserted_count"], 80)
        inserts = [params for query, params in cursor.executed if query.startswith("insert into user_fair_prices")]
        self.assertEqual({params[1:6]: params[6] for params in inserts}, {unit_key(row): row["fair_price_krw"] for row in rows})
