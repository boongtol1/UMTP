import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.macbook_air_units import (  # noqa: E402
    MAC_MINI_PRODUCT_TYPE,
    MACBOOK_AIR_PRODUCT_TYPE,
    SUPPORTED_PRODUCT_TYPES,
    generate_supported_units,
    is_valid_silicon_unit,
)


class SiliconUnitsTest(unittest.TestCase):
    def test_supported_product_types_includes_air_and_mini(self):
        self.assertIn(MACBOOK_AIR_PRODUCT_TYPE, SUPPORTED_PRODUCT_TYPES)
        self.assertIn(MAC_MINI_PRODUCT_TYPE, SUPPORTED_PRODUCT_TYPES)

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
