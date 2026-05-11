import re

try:
    from src.macbook_air_units import is_valid_macbook_air_unit
except ImportError:
    from macbook_air_units import is_valid_macbook_air_unit


PRODUCT_TYPE = "MacBook Air"
DEFAULT_SCREEN_INCH = 13
SUPPORTED_CHIPS = ("M1", "M2", "M3", "M4", "M5")
SUPPORTED_RAM_GB = (8, 16, 24, 32)
SUPPORTED_SSD_GB = (256, 512, 1024, 2048, 4096)
REQUIRED_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
INVALID_UNIT_REASON = "invalid_macbook_air_unit"


def _contains_product_type(title):
    lowered = title.lower()
    normalized = re.sub(r"\s+", "", lowered)
    return (
        "macbook air" in lowered
        or "macbookair" in normalized
        or "맥북에어" in normalized
    )


def _extract_chip(title):
    for chip in SUPPORTED_CHIPS:
        if re.search(rf"\b{chip}\b", title, flags=re.IGNORECASE):
            return chip
    return None


def _extract_screen_inch(title):
    if re.search(r"(?<!\d)15\s*(인치|inch|\")", title, flags=re.IGNORECASE):
        return 15

    if re.search(r"(?<!\d)13(\.3)?\s*(인치|inch|\")", title, flags=re.IGNORECASE):
        return 13

    if re.search(r"38\.\d+\s*cm", title, flags=re.IGNORECASE):
        return 15
    if re.search(r"33\.\d+\s*cm", title, flags=re.IGNORECASE):
        return 13

    return DEFAULT_SCREEN_INCH


def _extract_ram_gb(title):
    for ram_gb in SUPPORTED_RAM_GB:
        if re.search(rf"(?<!\d){ram_gb}\s*gb(?!\d)", title, flags=re.IGNORECASE):
            return ram_gb
        if re.search(rf"(?<!\d){ram_gb}\s*기가(?!\d)", title):
            return ram_gb
    return None


def _extract_ssd_gb(title):
    if re.search(r"(?<!\d)1\s*tb(?!\d)", title, flags=re.IGNORECASE):
        return 1024
    if re.search(r"(?<!\d)2\s*tb(?!\d)", title, flags=re.IGNORECASE):
        return 2048
    if re.search(r"(?<!\d)4\s*tb(?!\d)", title, flags=re.IGNORECASE):
        return 4096

    for ssd_gb in SUPPORTED_SSD_GB:
        if re.search(rf"(?<!\d){ssd_gb}\s*gb(?!\d)", title, flags=re.IGNORECASE):
            return ssd_gb
        if re.search(rf"(?<!\d){ssd_gb}\s*기가(?!\d)", title):
            return ssd_gb
    return None


def parse_listing_title(title):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("매물 제목은 비어 있을 수 없습니다.")

    parsed = {
        "product_type": PRODUCT_TYPE if _contains_product_type(title) else None,
        "chip": _extract_chip(title),
        "screen_inch": _extract_screen_inch(title),
        "ram_gb": _extract_ram_gb(title),
        "ssd_gb": _extract_ssd_gb(title),
    }

    missing_fields = [field for field in REQUIRED_FIELDS if parsed.get(field) is None]
    unit_valid = None
    unit_validation_reason = None
    parse_success = len(missing_fields) == 0
    reason = None

    if parse_success and parsed["product_type"] == PRODUCT_TYPE:
        unit_valid = is_valid_macbook_air_unit(
            parsed["chip"],
            parsed["screen_inch"],
            parsed["ram_gb"],
            parsed["ssd_gb"],
        )
        if not unit_valid:
            parse_success = False
            unit_validation_reason = INVALID_UNIT_REASON
            reason = INVALID_UNIT_REASON
            missing_fields.append(INVALID_UNIT_REASON)
    elif parsed["product_type"] == PRODUCT_TYPE:
        unit_valid = False if missing_fields else None

    parsed["missing_fields"] = missing_fields
    parsed["parse_success"] = parse_success
    parsed["unit_valid"] = unit_valid
    parsed["unit_validation_reason"] = unit_validation_reason
    parsed["reason"] = reason
    return parsed
