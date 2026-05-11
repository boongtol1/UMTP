import re


SCREEN_VALUES = (13, 15)
RAM_VALUES = (8, 16, 24, 32)
SSD_VALUES = (256, 512, 1024, 2048, 4096)
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
EXCLUDED_YEARS = {"2020", "2021", "2022", "2023", "2024", "2025", "2026"}


def _append_unique(target, value):
    if value not in target:
        target.append(value)


def _set_detected_pattern(detected_patterns, field_name, raw_value):
    if field_name not in detected_patterns and raw_value:
        detected_patterns[field_name] = raw_value


def _add_candidate(result, field_name, value, raw_pattern):
    key_by_field = {
        "screen_inch": "screen_candidates",
        "ram_gb": "ram_candidates",
        "ssd_gb": "ssd_candidates",
    }
    target_key = key_by_field[field_name]
    _append_unique(result[target_key], value)
    _set_detected_pattern(result["detected_patterns"], field_name, raw_pattern)


def _normalize_tb_token(token):
    return re.sub(r"\s+", "", token.lower())


def _parse_ssd_token(token):
    if not isinstance(token, str):
        return None

    normalized = _normalize_tb_token(token)
    if normalized in TB_TO_GB_MAP:
        return TB_TO_GB_MAP[normalized]

    digits = re.findall(r"\d+", normalized)
    if not digits:
        return None

    value = int("".join(digits))
    if value in SSD_VALUES:
        return value
    return None


def extract_numeric_candidates(text):
    result = {
        "screen_candidates": [],
        "ram_candidates": [],
        "ssd_candidates": [],
        "detected_patterns": {},
    }

    if not isinstance(text, str) or not text.strip():
        return result

    lowered_text = text.lower()

    # 축약 표현 우선 처리: 16/512, 24/1TB
    shorthand_pattern = re.compile(
        r"(?<!\d)(8|16|24|32)\s*/\s*(256|512|1024|2048|4096|1\s*tb|2\s*tb|4\s*tb|1\s*t|2\s*t|4\s*t|1\s*테라|2\s*테라|4\s*테라)(?!\d)",
        flags=re.IGNORECASE,
    )
    for match in shorthand_pattern.finditer(lowered_text):
        ram_gb = int(match.group(1))
        ssd_gb = _parse_ssd_token(match.group(2))
        _add_candidate(result, "ram_gb", ram_gb, match.group(0))
        if ssd_gb is not None:
            _add_candidate(result, "ssd_gb", ssd_gb, match.group(0))

    for match in re.finditer(r"(?<!\d)(13|15)\s*(?:인치|inch)(?!\d)", lowered_text, flags=re.IGNORECASE):
        _add_candidate(result, "screen_inch", int(match.group(1)), match.group(0))

    for match in re.finditer(r"(?<!\d)(13|15)-inch(?!\d)", lowered_text, flags=re.IGNORECASE):
        _add_candidate(result, "screen_inch", int(match.group(1)), match.group(0))

    for match in re.finditer(r"(?<!\d)(13|15)(?!\d)", lowered_text):
        _add_candidate(result, "screen_inch", int(match.group(1)), match.group(0))

    ram_patterns = (
        r"(?<!\d)(8|16|24|32)\s*gb(?!\d)",
        r"(?<!\d)(8|16|24|32)\s*기가(?!\d)",
        r"램\s*(8|16|24|32)(?!\d)",
        r"(?<!\d)(8|16|24|32)\s*램(?!\d)",
    )
    for pattern in ram_patterns:
        for match in re.finditer(pattern, lowered_text, flags=re.IGNORECASE):
            _add_candidate(result, "ram_gb", int(match.group(1)), match.group(0))

    for match in re.finditer(r"(?<!\d)(8|16|24|32)(?!\d)", lowered_text):
        token = match.group(1)
        if token in EXCLUDED_YEARS:
            continue
        _add_candidate(result, "ram_gb", int(token), match.group(0))

    ssd_patterns = (
        r"(?<!\d)(256|512|1024|2048|4096)\s*gb(?!\d)",
        r"(?<!\d)(256|512|1024|2048|4096)\s*기가(?!\d)",
        r"(?<!\d)(256|512|1024|2048|4096)\s*ssd(?!\d)",
    )
    for pattern in ssd_patterns:
        for match in re.finditer(pattern, lowered_text, flags=re.IGNORECASE):
            _add_candidate(result, "ssd_gb", int(match.group(1)), match.group(0))

    for match in re.finditer(r"(?<!\d)(256|512|1024|2048|4096)(?!\d)", lowered_text):
        token = match.group(1)
        if token in EXCLUDED_YEARS:
            continue
        _add_candidate(result, "ssd_gb", int(token), match.group(0))

    tb_pattern = re.compile(r"(?<!\d)(1|2|4)\s*(tb|t|테라)(?![a-zA-Z0-9가-힣])", flags=re.IGNORECASE)
    for match in tb_pattern.finditer(lowered_text):
        ssd_gb = _parse_ssd_token(match.group(0))
        if ssd_gb is None:
            continue
        _add_candidate(result, "ssd_gb", ssd_gb, match.group(0))

    return result
