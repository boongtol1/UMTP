import os
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.macbook_air_units import (  # noqa: E402
    MAC_MINI_PRODUCT_TYPE,
    MACBOOK_AIR_PRODUCT_TYPE,
    MACBOOK_PRO_PRODUCT_TYPE,
    SUPPORTED_PRODUCT_TYPES,
    generate_units_for_product,
    get_product_base_spec,
    generate_supported_units,
    is_valid_silicon_unit,
)


class SiliconUnitsTest(unittest.TestCase):
    def test_supported_product_types_includes_air_mini_and_pro(self):
        self.assertIn(MACBOOK_AIR_PRODUCT_TYPE, SUPPORTED_PRODUCT_TYPES)
        self.assertIn(MAC_MINI_PRODUCT_TYPE, SUPPORTED_PRODUCT_TYPES)
        self.assertIn(MACBOOK_PRO_PRODUCT_TYPE, SUPPORTED_PRODUCT_TYPES)

    def test_macbook_pro_catalog_exactly_matches_sql_seed(self):
        seed = (Path(PROJECT_ROOT) / "sql" / "seed_silicon_macbook_pro_fair_prices.sql").read_text()
        rows = re.findall(r"\('MacBook Pro', '([^']+)', (\d+), (\d+), (\d+), \d+\)", seed)
        seeded_specs = {(chip, int(screen), int(ram), int(ssd)) for chip, screen, ram, ssd in rows}
        units = generate_units_for_product(MACBOOK_PRO_PRODUCT_TYPE)
        generated_specs = {(unit["chip"], unit["screen_inch"], unit["ram_gb"], unit["ssd_gb"]) for unit in units}
        self.assertEqual(len(seeded_specs), 276)
        self.assertEqual(len(units), len(generated_specs))
        self.assertEqual(generated_specs, seeded_specs)
        for spec in seeded_specs:
            with self.subTest(spec=spec):
                self.assertTrue(is_valid_silicon_unit(MACBOOK_PRO_PRODUCT_TYPE, *spec))

    def test_macbook_pro_base_spec_uses_seed_minimums(self):
        for chip, screen, expected in (
            ("M1", 13, {"ram_gb": 8, "ssd_gb": 256}),
            ("M3 Pro", 14, {"ram_gb": 18, "ssd_gb": 512}),
            ("M5 Pro", 16, {"ram_gb": 24, "ssd_gb": 1024}),
            ("M5 Max", 16, {"ram_gb": 36, "ssd_gb": 2048}),
        ):
            with self.subTest(chip=chip, screen=screen):
                self.assertEqual(get_product_base_spec(MACBOOK_PRO_PRODUCT_TYPE, chip, screen), expected)

    def test_macbook_pro_rejects_unseeded_combinations(self):
        for spec in (
            ("M1", 14, 8, 256),
            ("M3", 16, 8, 512),
            ("M3 Pro", 14, 16, 512),
            ("M4 Pro", 14, 64, 512),
            ("M4 Pro", 16, 24, 8192),
            ("M5 Max", 16, 36, 1024),
        ):
            with self.subTest(spec=spec):
                self.assertFalse(is_valid_silicon_unit(MACBOOK_PRO_PRODUCT_TYPE, *spec))

    def test_mac_mini_units_are_generated_with_screen_inch_zero(self):
        units = generate_supported_units()
        mac_mini_units = [unit for unit in units if unit.get("product_type") == MAC_MINI_PRODUCT_TYPE]

        self.assertGreater(len(mac_mini_units), 0)
        self.assertTrue(all(unit.get("screen_inch") == 0 for unit in mac_mini_units))

    def test_mac_mini_validation_requires_screen_inch_zero(self):
        self.assertTrue(
            is_valid_silicon_unit(
                MAC_MINI_PRODUCT_TYPE,
                "M2",
                0,
                16,
                512,
            )
        )

    def test_mac_mini_pro_chip_combinations(self):
        self.assertTrue(
            is_valid_silicon_unit(
                MAC_MINI_PRODUCT_TYPE,
                "M2 Pro",
                0,
                16,
                8192,
            )
        )
        self.assertTrue(
            is_valid_silicon_unit(
                MAC_MINI_PRODUCT_TYPE,
                "M4 Pro",
                0,
                64,
                4096,
            )
        )
        self.assertFalse(
            is_valid_silicon_unit(
                MAC_MINI_PRODUCT_TYPE,
                "M4 Pro",
                0,
                16,
                512,
            )
        )
        self.assertFalse(
            is_valid_silicon_unit(
                MAC_MINI_PRODUCT_TYPE,
                "M2",
                13,
                16,
                512,
            )
        )


if __name__ == "__main__":
    unittest.main()
