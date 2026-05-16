import re

try:
    from src.macbook_air_units import is_valid_macbook_air_unit
    from src.numeric_candidate_extractor import extract_numeric_candidates
except ImportError:
    from macbook_air_units import is_valid_macbook_air_unit
    from numeric_candidate_extractor import extract_numeric_candidates


PRODUCT_TYPE = "MacBook Air"
DEFAULT_SCREEN_INCH = 13
SUPPORTED_CHIPS = ("M1", "M2", "M3", "M4", "M5")
SUPPORTED_RAM_GB = (8, 16, 24, 32)
SUPPORTED_SSD_GB = (256, 512, 1024, 2048, 4096)
REQUIRED_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
MISSING_REQUIRED_REASON = "missing_required_fields"
INVALID_UNIT_REASON = "invalid_macbook_air_unit"

TB_TO_GB_MAP = {
    "1tb": 1024,
    "2tb": 2048,
    "4tb": 4096,
    "1t": 1024,
    "2t": 2048,
    "4t": 4096,
    "1테라": 1024,
    "2테라": 2048,
    "4테라": 4096,
}

BASE_MODEL_KEYWORD_PATTERN = re.compile(r"(?<![가-힣])(기본형|깡통)(?![가-힣])")


def _normalize_text(text):
    if not isinstance(text, str):
        return ""
    return " ".join(text.split()).strip()


def contains_base_model_keyword(text):
    if not isinstance(text, str) or not text.strip():
        return False
    return BASE_MODEL_KEYWORD_PATTERN.search(text) is not None


def _normalize_self_check_fields(self_check_fields):
    if not isinstance(self_check_fields, dict):
        return {}

    normalized = {}
    for key, value in self_check_fields.items():
        key_norm = _normalize_text(key)
        value_norm = _normalize_text(value)
        if key_norm and value_norm:
            normalized[key_norm] = value_norm
    return normalized


def _contains_product_type(text):
    lowered = text.lower()
    normalized = re.sub(r"\s+", "", lowered)
    return (
        "macbook air" in lowered
        or "macbookair" in normalized
        or "맥북에어" in normalized
        or re.search(r"\bair\b", lowered) is not None
    )


def _extract_chip(text):
    if not isinstance(text, str):
        return None

    match = re.search(r"\b(m[1-5])\b", text, flags=re.IGNORECASE)
    if not match:
        return None

    chip = match.group(1).upper()
    if chip in SUPPORTED_CHIPS:
        return chip
    return None


def _extract_screen_inch_from_text(text):
    if not isinstance(text, str):
        return None

    match = re.search(r"(?<!\d)(13|15)\s*(인치|inch)(?!\d)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    match = re.search(r"(?<!\d)(13|15)-inch(?!\d)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _extract_ram_gb_from_text(text):
    if not isinstance(text, str):
        return None

    patterns = (
        r"(?<!\d)(8|16|24|32)\s*gb(?!\d)",
        r"(?<!\d)(8|16|24|32)\s*기가(?!\d)",
        r"램\s*(8|16|24|32)(?!\d)",
        r"(?<!\d)(8|16|24|32)\s*램(?!\d)",
        r"^(8|16|24|32)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        ram_gb = int(match.group(1))
        if ram_gb in SUPPORTED_RAM_GB:
            return ram_gb

    return None


def _extract_ssd_gb_from_text(text):
    if not isinstance(text, str):
        return None

    lowered = text.lower()
    normalized = re.sub(r"\s+", "", lowered)
    for token, converted in TB_TO_GB_MAP.items():
        if token in normalized:
            return converted

    patterns = (
        r"(?<!\d)(256|512|1024|2048|4096)\s*gb(?!\d)",
        r"(?<!\d)(256|512|1024|2048|4096)\s*기가(?!\d)",
        r"(?<!\d)(256|512|1024|2048|4096)\s*ssd(?!\d)",
        r"^(256|512|1024|2048|4096)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        ssd_gb = int(match.group(1))
        if ssd_gb in SUPPORTED_SSD_GB:
            return ssd_gb

    return None


def _record_pattern(detected_patterns, field_name, value, source, raw):
    detected_patterns[field_name] = {
        "value": value,
        "source": source,
        "raw": raw,
    }


def _record_conflict(detected_conflicts, field_name, preferred_source, preferred_value, other_source, other_value):
    detected_conflicts.append(
        {
            "field": field_name,
            "preferred_source": preferred_source,
            "preferred_value": preferred_value,
            "other_source": other_source,
            "other_value": other_value,
        }
    )


def _choose_numeric_candidate(values):
    unique_values = list(dict.fromkeys(values))
    if len(unique_values) == 1:
        return unique_values[0], False
    if len(unique_values) > 1:
        return None, True
    return None, False


def parse_listing_title(text, self_check_fields=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("매물 제목/본문 텍스트는 비어 있을 수 없습니다.")

    normalized_self_check = _normalize_self_check_fields(self_check_fields)
    detected_patterns = {}
    detected_conflicts = []

    product_type = None
    chip = None
    screen_inch = None
    ram_gb = None
    ssd_gb = None
    screen_inch_defaulted = False

    model_name_raw = normalized_self_check.get("모델명")
    if model_name_raw and _contains_product_type(model_name_raw):
        product_type = PRODUCT_TYPE
        _record_pattern(detected_patterns, "product_type", PRODUCT_TYPE, "self_check", model_name_raw)

    chip_model = _extract_chip(model_name_raw)
    if chip_model:
        chip = chip_model
        _record_pattern(detected_patterns, "chip", chip_model, "self_check", model_name_raw)

    cpu_raw = normalized_self_check.get("CPU종류")
    chip_cpu = _extract_chip(cpu_raw)
    if chip_cpu:
        if chip is not None and chip != chip_cpu:
            _record_conflict(detected_conflicts, "chip", "self_check", chip_cpu, "self_check", chip)
        chip = chip_cpu
        _record_pattern(detected_patterns, "chip", chip_cpu, "self_check", cpu_raw)

    ram_raw = normalized_self_check.get("램 용량")
    ram_from_self_check = _extract_ram_gb_from_text(ram_raw)
    if ram_from_self_check is not None:
        ram_gb = ram_from_self_check
        _record_pattern(detected_patterns, "ram_gb", ram_from_self_check, "self_check", ram_raw)

    ssd_raw = normalized_self_check.get("SSD용량")
    ssd_from_self_check = _extract_ssd_gb_from_text(ssd_raw)
    if ssd_from_self_check is not None:
        ssd_gb = ssd_from_self_check
        _record_pattern(detected_patterns, "ssd_gb", ssd_from_self_check, "self_check", ssd_raw)

    screen_from_model = _extract_screen_inch_from_text(model_name_raw)
    if screen_from_model is not None:
        screen_inch = screen_from_model
        _record_pattern(detected_patterns, "screen_inch", screen_from_model, "self_check", model_name_raw)

    if product_type is None and _contains_product_type(text):
        product_type = PRODUCT_TYPE
        _record_pattern(detected_patterns, "product_type", PRODUCT_TYPE, "text", text)

    chip_from_text = _extract_chip(text)
    if chip is None and chip_from_text is not None:
        chip = chip_from_text
        _record_pattern(detected_patterns, "chip", chip_from_text, "text", chip_from_text)
    elif chip is not None and chip_from_text is not None and chip != chip_from_text:
        _record_conflict(detected_conflicts, "chip", "self_check", chip, "text", chip_from_text)

    numeric_candidates = extract_numeric_candidates(text)

    screen_candidate, screen_ambiguous = _choose_numeric_candidate(numeric_candidates["screen_candidates"])
    if screen_inch is None and screen_candidate is not None:
        screen_inch = screen_candidate
        _record_pattern(
            detected_patterns,
            "screen_inch",
            screen_candidate,
            "text",
            numeric_candidates["detected_patterns"].get("screen_inch"),
        )
    elif screen_inch is not None and screen_candidate is not None and screen_inch != screen_candidate:
        _record_conflict(detected_conflicts, "screen_inch", "self_check", screen_inch, "text", screen_candidate)

    ram_candidate, ram_ambiguous = _choose_numeric_candidate(numeric_candidates["ram_candidates"])
    if ram_gb is None and ram_candidate is not None:
        ram_gb = ram_candidate
        _record_pattern(
            detected_patterns,
            "ram_gb",
            ram_candidate,
            "text",
            numeric_candidates["detected_patterns"].get("ram_gb"),
        )
    elif ram_gb is not None and ram_candidate is not None and ram_gb != ram_candidate:
        _record_conflict(detected_conflicts, "ram_gb", "self_check", ram_gb, "text", ram_candidate)

    ssd_candidate, ssd_ambiguous = _choose_numeric_candidate(numeric_candidates["ssd_candidates"])
    if ssd_gb is None and ssd_candidate is not None:
        ssd_gb = ssd_candidate
        _record_pattern(
            detected_patterns,
            "ssd_gb",
            ssd_candidate,
            "text",
            numeric_candidates["detected_patterns"].get("ssd_gb"),
        )
    elif ssd_gb is not None and ssd_candidate is not None and ssd_gb != ssd_candidate:
        _record_conflict(detected_conflicts, "ssd_gb", "self_check", ssd_gb, "text", ssd_candidate)

    if screen_ambiguous and screen_inch is None:
        _record_conflict(
            detected_conflicts,
            "screen_inch",
            "default",
            DEFAULT_SCREEN_INCH,
            "text",
            numeric_candidates["screen_candidates"],
        )

    if ram_ambiguous and ram_gb is None:
        _record_conflict(
            detected_conflicts,
            "ram_gb",
            "unresolved",
            None,
            "text",
            numeric_candidates["ram_candidates"],
        )

    if ssd_ambiguous and ssd_gb is None:
        _record_conflict(
            detected_conflicts,
            "ssd_gb",
            "unresolved",
            None,
            "text",
            numeric_candidates["ssd_candidates"],
        )

    if product_type == PRODUCT_TYPE and screen_inch is None:
        screen_inch = DEFAULT_SCREEN_INCH
        screen_inch_defaulted = True
        _record_pattern(detected_patterns, "screen_inch", DEFAULT_SCREEN_INCH, "default", None)

    parsed_fields = {
        "product_type": product_type,
        "chip": chip,
        "ram_gb": ram_gb,
        "ssd_gb": ssd_gb,
    }
    missing_fields = [field for field in REQUIRED_FIELDS if parsed_fields.get(field) is None]

    confidence_score = 0
    if product_type is not None:
        confidence_score += 20
    if chip is not None:
        confidence_score += 25
    if ram_gb is not None:
        confidence_score += 25
    if ssd_gb is not None:
        confidence_score += 25
    if screen_inch is not None and not screen_inch_defaulted:
        confidence_score += 5
    confidence_score = min(confidence_score, 100)

    unit_valid = False
    unit_validation_reason = None
    parse_success = len(missing_fields) == 0

    if not parse_success:
        unit_validation_reason = MISSING_REQUIRED_REASON
    elif product_type == PRODUCT_TYPE:
        unit_valid = is_valid_macbook_air_unit(chip, screen_inch, ram_gb, ssd_gb)
        if not unit_valid:
            parse_success = False
            unit_validation_reason = INVALID_UNIT_REASON
    else:
        unit_validation_reason = MISSING_REQUIRED_REASON

    if parse_success:
        unit_valid = True

    return {
        "parse_success": parse_success,
        "product_type": product_type,
        "chip": chip,
        "screen_inch": screen_inch,
        "screen_inch_defaulted": screen_inch_defaulted,
        "ram_gb": ram_gb,
        "ssd_gb": ssd_gb,
        "confidence_score": confidence_score,
        "unit_valid": unit_valid,
        "unit_validation_reason": unit_validation_reason,
        "missing_fields": missing_fields,
        "detected_patterns": detected_patterns,
        "detected_conflicts": detected_conflicts,
    }
