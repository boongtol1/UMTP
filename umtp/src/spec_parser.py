import re


PRODUCT_TYPE = "MacBook Air"
DEFAULT_SCREEN_INCH = 13


def _contains_product_type(title):
    lowered = title.lower()
    normalized = re.sub(r"\s+", "", lowered)
    return (
        "macbook air" in lowered
        or "macbookair" in normalized
        or "맥북에어" in normalized
    )


def _contains_m1(title):
    return re.search(r"\bm1\b", title, flags=re.IGNORECASE) is not None


def _contains_8gb_ram(title):
    return (
        re.search(r"(?<!\d)8\s*gb(?!\d)", title, flags=re.IGNORECASE) is not None
        or re.search(r"(?<!\d)8\s*기가(?!\d)", title) is not None
    )


def _contains_256gb_ssd(title):
    return (
        re.search(r"(?<!\d)256\s*gb(?!\d)", title, flags=re.IGNORECASE) is not None
        or re.search(r"(?<!\d)256\s*기가(?!\d)", title) is not None
    )


def parse_listing_title(title):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("매물 제목은 비어 있을 수 없습니다.")

    parsed = {
        "product_type": PRODUCT_TYPE if _contains_product_type(title) else None,
        "chip": "M1" if _contains_m1(title) else None,
        "screen_inch": DEFAULT_SCREEN_INCH,
        "ram_gb": 8 if _contains_8gb_ram(title) else None,
        "ssd_gb": 256 if _contains_256gb_ssd(title) else None,
    }
    return parsed
