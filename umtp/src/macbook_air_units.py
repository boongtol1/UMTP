VALID_MACBOOK_AIR_UNITS = {
    "M1": {
        13: {
            "ram_gb": [8, 16],
            "ssd_gb": [256, 512, 1024, 2048],
        }
    },
    "M2": {
        13: {
            "ram_gb": [8, 16, 24],
            "ssd_gb": [256, 512, 1024, 2048],
        },
        15: {
            "ram_gb": [8, 16, 24],
            "ssd_gb": [256, 512, 1024, 2048],
        },
    },
    "M3": {
        13: {
            "ram_gb": [8, 16, 24],
            "ssd_gb": [256, 512, 1024, 2048],
        },
        15: {
            "ram_gb": [8, 16, 24],
            "ssd_gb": [256, 512, 1024, 2048],
        },
    },
    "M4": {
        13: {
            "ram_gb": [16, 24, 32],
            "ssd_gb": [256, 512, 1024, 2048],
        },
        15: {
            "ram_gb": [16, 24, 32],
            "ssd_gb": [256, 512, 1024, 2048],
        },
    },
    "M5": {
        13: {
            "ram_gb": [16, 24, 32],
            "ssd_gb": [512, 1024, 2048, 4096],
        },
        15: {
            "ram_gb": [16, 24, 32],
            "ssd_gb": [512, 1024, 2048, 4096],
        },
    },
}

PRODUCT_TYPE = "MacBook Air"
BASE_FAIR_PRICE_KRW = 550000

CHIP_PRICE_OFFSETS = {
    "M1": 0,
    "M2": 200000,
    "M3": 350000,
    "M4": 500000,
    "M5": 650000,
}

SCREEN_PRICE_OFFSETS = {
    13: 0,
    15: 150000,
}

RAM_PRICE_OFFSETS = {
    8: 0,
    16: 150000,
    24: 300000,
    32: 450000,
}

SSD_PRICE_OFFSETS = {
    256: 0,
    512: 120000,
    1024: 280000,
    2048: 500000,
    4096: 800000,
}


def is_valid_macbook_air_unit(chip, screen_inch, ram_gb, ssd_gb):
    chip_units = VALID_MACBOOK_AIR_UNITS.get(chip)
    if not chip_units:
        return False

    screen_units = chip_units.get(screen_inch)
    if not screen_units:
        return False

    return ram_gb in screen_units["ram_gb"] and ssd_gb in screen_units["ssd_gb"]


def generate_macbook_air_units():
    units = []
    for chip, screen_map in VALID_MACBOOK_AIR_UNITS.items():
        for screen_inch, options in screen_map.items():
            for ram_gb in options["ram_gb"]:
                for ssd_gb in options["ssd_gb"]:
                    units.append(
                        {
                            "product_type": PRODUCT_TYPE,
                            "chip": chip,
                            "screen_inch": screen_inch,
                            "ram_gb": ram_gb,
                            "ssd_gb": ssd_gb,
                        }
                    )
    return units


def calculate_rule_based_fair_price(chip, screen_inch, ram_gb, ssd_gb):
    if not is_valid_macbook_air_unit(chip, screen_inch, ram_gb, ssd_gb):
        raise ValueError(
            "invalid_macbook_air_unit: "
            f"chip={chip}, screen_inch={screen_inch}, ram_gb={ram_gb}, ssd_gb={ssd_gb}"
        )

    fair_price_krw = (
        BASE_FAIR_PRICE_KRW
        + CHIP_PRICE_OFFSETS[chip]
        + SCREEN_PRICE_OFFSETS[screen_inch]
        + RAM_PRICE_OFFSETS[ram_gb]
        + SSD_PRICE_OFFSETS[ssd_gb]
    )
    return int(fair_price_krw)
