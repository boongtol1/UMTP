import os
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import api_server, user_settings_service as settings


def seed_rows():
    sql = (Path(PROJECT_ROOT) / "sql/seed_silicon_macbook_pro_fair_prices.sql").read_text()
    return [
        dict(product_type="MacBook Pro", chip=chip, screen_inch=int(screen),
             ram_gb=int(ram), ssd_gb=int(ssd), fair_price_krw=int(price))
        for chip, screen, ram, ssd, price in re.findall(
            r"\('MacBook Pro', '([^']+)', (\d+), (\d+), (\d+), (\d+)\)", sql
        )
    ]


def unit_key(row):
    return tuple(row[field] for field in ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb"))


class SettingsCursor:
    def __init__(self, system_rows=(), user_rows=()):
        self.system_rows = list(system_rows)
        self.user_rows = list(user_rows)
        self.executed = []
        self.query = ""
        self.rowcount = 1

    def execute(self, query, params=None):
        self.query = " ".join(query.lower().split())
        self.executed.append((self.query, params))

    def fetchone(self):
        if self.query.startswith("select current_timestamp"):
            return (datetime(2026, 9, 18, 12, 0),)
        if self.query.startswith("select id from user_fair_prices "):
            return (14,)
        return None

    def fetchall(self):
        if "from mac_fair_prices" in self.query:
            return [dict(row) for row in self.system_rows]
        if "from user_fair_prices" in self.query:
            return [dict(row) for row in self.user_rows]
        return []

    def close(self):
        pass


class SettingsConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def is_connected(self):
        return True

    def close(self):
        pass


class MacBookProSettingsTest(unittest.TestCase):
    def test_catalog_endpoint_exposes_exact_seed_units_in_chip_order(self):
        response = api_server.macbook_air_units()
        self.assertTrue(response["ok"])
        units = [unit for unit in response["units"] if unit["product_type"] == "MacBook Pro"]
        self.assertEqual({unit_key(unit) for unit in units}, {unit_key(row) for row in seed_rows()})
        self.assertEqual(
            list(dict.fromkeys(unit["chip"] for unit in units)),
            [f"M{generation}{tier}" for generation in range(1, 6) for tier in ("", " Pro", " Max")],
        )

    def test_settings_load_every_seed_price_and_keep_new_rules_disabled(self):
        rows = seed_rows()
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            items = settings.get_user_fair_price_settings("test-pro-user")
        pro_items = {unit_key(item): item for item in items if item["product_type"] == "MacBook Pro"}
        self.assertEqual(len(pro_items), len(rows))
        for row in rows:
            with self.subTest(spec=unit_key(row)):
                item = pro_items[unit_key(row)]
                self.assertEqual(item["system_fair_price_krw"], row["fair_price_krw"])
                self.assertEqual(item["effective_fair_price_krw"], row["fair_price_krw"])
                self.assertEqual(item["effective_target_buy_price_krw"], row["fair_price_krw"] * 80 // 100)
                self.assertEqual(item["recommended_search_keyword"], row["chip"].lower().replace(" ", "") + " 맥북프로")
                self.assertFalse(item["enabled"])
                self.assertFalse(item["has_user_override"])
        self.assertTrue(all("MacBook Pro" in params for _, params in cursor.executed))

    def test_user_override_wins_over_seed_price(self):
        row = next(row for row in seed_rows() if row["chip"] == "M3 Max")
        override = dict(row, id=123, fair_price_krw=2500000, alert_drop_rate_percent=10,
                        enabled=True, search_keyword="맥북프로 작업용", priority="FAST")
        cursor = SettingsCursor(system_rows=[row], user_rows=[override])
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            items = settings.get_user_fair_price_settings("test-pro-user")
        item = next(item for item in items if unit_key(item) == unit_key(row))
        self.assertEqual(item["system_fair_price_krw"], row["fair_price_krw"])
        self.assertEqual(item["effective_fair_price_krw"], 2500000)
        self.assertEqual(item["effective_target_buy_price_krw"], 2250000)
        self.assertEqual(item["effective_search_keyword"], "맥북프로 작업용")
        self.assertEqual(item["priority"], "FAST")
        self.assertTrue(item["enabled"])

    def test_save_all_chip_tiers_normalizes_names_and_requests_polling(self):
        by_chip = {}
        for row in seed_rows():
            by_chip.setdefault(row["chip"], row)
        for chip, row in by_chip.items():
            with self.subTest(chip=chip):
                cursor = SettingsCursor()
                connection = SettingsConnection(cursor)
                with patch.object(settings, "get_connection", return_value=connection):
                    result = settings.upsert_user_fair_price_setting(
                        user_id="test-pro-user", product_type=row["product_type"],
                        chip=chip.lower().replace(" ", ""), screen_inch=row["screen_inch"],
                        ram_gb=row["ram_gb"], ssd_gb=row["ssd_gb"],
                        fair_price_krw=row["fair_price_krw"], alert_drop_rate_percent=20,
                        enabled=True,
                    )
                self.assertTrue(result["ok"], result)
                self.assertTrue(connection.committed)
                insert = next(params for query, params in cursor.executed if query.startswith("insert into user_fair_prices"))
                self.assertEqual(insert[1:6], unit_key(row))
                self.assertEqual(insert[13], chip.lower().replace(" ", "") + " 맥북프로")
                self.assertTrue(result["immediate_poll_requested"])
                self.assertEqual(insert[-2:], (True, True))

    def test_save_rejects_specs_absent_from_seed_before_connecting(self):
        with patch.object(settings, "get_connection") as connection:
            for chip, screen, ram, ssd in (("M1", 14, 8, 256), ("M3 Pro", 14, 16, 512), ("M5 Max", 16, 8, 256)):
                with self.subTest(chip=chip):
                    result = settings.upsert_user_fair_price_setting(
                        "test-pro-user", "MacBook Pro", chip, screen, ram, ssd, 1000000, 20, True
                    )
                    self.assertEqual(result, {"ok": False, "reason": "invalid_silicon_unit"})
            connection.assert_not_called()

    def test_bulk_controls_scope_updates_to_macbook_pro(self):
        for action in (
            lambda: settings.bulk_set_user_watch_rules_enabled("test-pro-user", True, product_type="MacBook Pro"),
            lambda: settings.bulk_update_user_fair_price_drop_rate("test-pro-user", 15, product_type="MacBook Pro"),
        ):
            cursor = SettingsCursor()
            with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
                result = action()
            self.assertTrue(result["ok"], result)
            for query, params in cursor.executed:
                if query.startswith("update"):
                    self.assertIn("and product_type = %s", query)
                    self.assertEqual(params[-1], "MacBook Pro")

    def test_reset_uses_seed_prices_and_does_not_create_other_product_rules(self):
        rows = seed_rows()
        cursor = SettingsCursor(system_rows=rows)
        with patch.object(settings, "get_connection", return_value=SettingsConnection(cursor)):
            result = settings.reset_user_fair_prices_to_system_market_prices("test-pro-user", product_type="MacBook Pro")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["inserted_count"], len(rows))
        inserts = [params for query, params in cursor.executed if query.startswith("insert into user_fair_prices")]
        self.assertEqual({params[1:6]: params[6] for params in inserts}, {unit_key(row): row["fair_price_krw"] for row in rows})
        self.assertTrue(all(params[11] is False for params in inserts))


if __name__ == "__main__":
    unittest.main()
