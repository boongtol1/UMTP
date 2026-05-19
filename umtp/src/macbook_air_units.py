MACBOOK_AIR_PRODUCT_TYPE = "MacBook Air"
MAC_MINI_PRODUCT_TYPE = "Mac mini"
PRODUCT_TYPE = MACBOOK_AIR_PRODUCT_TYPE
SUPPORTED_PRODUCT_TYPES = (
    MACBOOK_AIR_PRODUCT_TYPE,
    MAC_MINI_PRODUCT_TYPE,
)

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

VALID_MAC_MINI_UNITS = {
    "M1": {
        0: {
            "ram_gb": [8, 16],
            "ssd_gb": [256, 512, 1024, 2048],
        }
    },
    "M2": {
        0: {
            "ram_gb": [8, 16, 24],
            "ssd_gb": [256, 512, 1024, 2048],
        }
    },
    "M2 Pro": {
        0: {
            "ram_gb": [16, 32],
            "ssd_gb": [512, 1024, 2048, 4096, 8192],
        }
    },
    "M4": {
        0: {
            "ram_gb": [16, 24, 32],
            "ssd_gb": [256, 512, 1024, 2048],
        }
    },
    "M4 Pro": {
        0: {
            "ram_gb": [24, 48, 64],
            "ssd_gb": [512, 1024, 2048, 4096, 8192],
        }
    },
}

VALID_SILICON_UNITS_BY_PRODUCT = {
    MACBOOK_AIR_PRODUCT_TYPE: VALID_MACBOOK_AIR_UNITS,
    MAC_MINI_PRODUCT_TYPE: VALID_MAC_MINI_UNITS,
}
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


def is_supported_product_type(product_type):
    return product_type in VALID_SILICON_UNITS_BY_PRODUCT


def _get_product_units(product_type):
    return VALID_SILICON_UNITS_BY_PRODUCT.get(product_type)


def is_valid_silicon_unit(product_type, chip, screen_inch, ram_gb, ssd_gb):
    product_units = _get_product_units(product_type)
    if not isinstance(product_units, dict):
        return False

    chip_units = product_units.get(chip)
    if not isinstance(chip_units, dict):
        return False

    screen_units = chip_units.get(screen_inch)
    if not isinstance(screen_units, dict):
        return False

    return ram_gb in screen_units["ram_gb"] and ssd_gb in screen_units["ssd_gb"]


def get_product_base_spec(product_type, chip, screen_inch):
    product_units = _get_product_units(product_type)
    if not isinstance(product_units, dict):
        return None

    chip_units = product_units.get(chip)
    if not isinstance(chip_units, dict):
        return None

    screen_units = chip_units.get(screen_inch)
    if not isinstance(screen_units, dict):
        return None

    ram_options = screen_units.get("ram_gb")
    ssd_options = screen_units.get("ssd_gb")
    if not isinstance(ram_options, list) or not isinstance(ssd_options, list):
        return None
    if not ram_options or not ssd_options:
        return None

    return {
        "ram_gb": min(ram_options),
        "ssd_gb": min(ssd_options),
    }


def generate_units_for_product(product_type):
    product_units = _get_product_units(product_type)
    if not isinstance(product_units, dict):
        return []

    units = []
    for chip, screen_map in product_units.items():
        for screen_inch, options in screen_map.items():
            for ram_gb in options["ram_gb"]:
                for ssd_gb in options["ssd_gb"]:
                    units.append(
                        {
                            "product_type": product_type,
                            "chip": chip,
                            "screen_inch": screen_inch,
                            "ram_gb": ram_gb,
                            "ssd_gb": ssd_gb,
                        }
                    )
    return units


def generate_supported_units():
    units = []
    for product_type in SUPPORTED_PRODUCT_TYPES:
        units.extend(generate_units_for_product(product_type))
    return units


def is_valid_macbook_air_unit(chip, screen_inch, ram_gb, ssd_gb):
    return is_valid_silicon_unit(
        MACBOOK_AIR_PRODUCT_TYPE,
        chip,
        screen_inch,
        ram_gb,
        ssd_gb,
    )


def get_macbook_air_base_spec(chip, screen_inch):
    return get_product_base_spec(MACBOOK_AIR_PRODUCT_TYPE, chip, screen_inch)


def generate_macbook_air_units():
    return generate_units_for_product(MACBOOK_AIR_PRODUCT_TYPE)


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
