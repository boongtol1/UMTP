from src.macbook_air_units import generate_macbook_air_units


CHIP_SORT_ORDER = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
}


def get_all_macbook_air_units_sorted():
    units = generate_macbook_air_units()
    return sorted(
        units,
        key=lambda unit: (
            CHIP_SORT_ORDER.get(unit.get("chip"), 999),
            unit.get("screen_inch"),
            unit.get("ram_gb"),
            unit.get("ssd_gb"),
        ),
    )
