import re


SCREEN_VALUES = (13, 14, 15, 16)
RAM_VALUES = (8, 16, 18, 24, 32, 36, 48, 64, 96, 128)
SSD_VALUES = (256, 512, 1024, 2048, 4096, 8192)
RAM_PATTERN = "|".join(map(str, RAM_VALUES))
SSD_PATTERN = "|".join(map(str, SSD_VALUES))
TB_PATTERN = r"(?:1|2|4|8)\s*(?:tb|t|테라)"
SCREEN_PATTERN = r"(?:13|14|15|16)(?:\.\d+)?"
SCREEN_UNIT_PATTERN = r'''(?:인치|inch|형|"|”|''|′′)'''
TB_TO_GB_MAP = {
    f"{size}{suffix}": size * 1024
    for size in (1, 2, 4, 8)
    for suffix in ("tb", "t", "테라")
}


def _add_candidate(result, field_name, value, raw_pattern):
    target_key = {
        "screen_inch": "screen_candidates",
        "ram_gb": "ram_candidates",
        "ssd_gb": "ssd_candidates",
    }[field_name]
    if value not in result[target_key]:
        result[target_key].append(value)
    result["detected_patterns"].setdefault(field_name, raw_pattern)


def _parse_ssd_token(token):
    if not isinstance(token, str):
        return None
    normalized = re.sub(r"\s+", "", token.lower())
    if normalized in TB_TO_GB_MAP:
        return TB_TO_GB_MAP[normalized]
    match = re.match(r"\d+", normalized)
    if match is None:
        return None
    value = int(match.group())
    return value if value in SSD_VALUES else None


def extract_numeric_candidates(text, screen_values=SCREEN_VALUES):
    result = {
        "screen_candidates": [],
        "ram_candidates": [],
        "ssd_candidates": [],
        "screen_ram_ambiguous": False,
        "detected_patterns": {},
    }
    if not isinstance(text, str) or not text.strip():
        return result

    lowered_text = text.lower()
    # Explicit units own their numbers: 16-inch is never RAM, 16GB is never a
    # display, and the 8 in 8TB is never 8GB RAM.
    occupied = []

    def overlaps(match):
        return any(match.start() < end and start < match.end() for start, end in occupied)

    # A complete ordered display/RAM/SSD triple disambiguates bare 16. A lone
    # "16 512" cannot establish both a 16-inch display and 16GB RAM.
    screens = "|".join(map(str, screen_values))
    triple = rf"(?<![\d.])({screens})\s+({RAM_PATTERN})\s+({TB_PATTERN}|{SSD_PATTERN})(?!\d)"
    for match in re.finditer(triple, lowered_text):
        _add_candidate(result, "screen_inch", int(match.group(1)), match.group())
        _add_candidate(result, "ram_gb", int(match.group(2)), match.group())
        _add_candidate(result, "ssd_gb", _parse_ssd_token(match.group(3)), match.group())
        occupied.append(match.span())

    shorthand = rf"(?<!\d)({RAM_PATTERN})\s*/\s*({TB_PATTERN}|{SSD_PATTERN})(?!\d)"
    for match in re.finditer(shorthand, lowered_text):
        _add_candidate(result, "ram_gb", int(match.group(1)), match.group())
        _add_candidate(result, "ssd_gb", _parse_ssd_token(match.group(2)), match.group())
        occupied.append(match.span())

    allowed_screen_pattern = "|".join(map(str, sorted(set(SCREEN_VALUES) | set(screen_values))))
    screen_pattern = rf"(?<![\d.])((?:{allowed_screen_pattern})(?:\.\d+)?)(?:\s*{SCREEN_UNIT_PATTERN}|-inch)(?!\d)"
    for match in re.finditer(screen_pattern, lowered_text):
        screen = int(float(match.group(1)))
        if screen in screen_values:
            _add_candidate(result, "screen_inch", screen, match.group())
        occupied.append(match.span())

    ram_patterns = (
        rf"(?<!\d)({RAM_PATTERN})\s*(?:gb|기가|램|ram)(?!\d)",
        rf"(?<!\d)({RAM_PATTERN})\s*g(?![a-z0-9가-힣])",
        rf"(?:램|ram|메모리|memory)\s*({RAM_PATTERN})(?!\d)",
    )
    for pattern in ram_patterns:
        for match in re.finditer(pattern, lowered_text):
            if overlaps(match):
                continue
            _add_candidate(result, "ram_gb", int(match.group(1)), match.group())
            occupied.append(match.span())

    ssd_pattern = rf"(?<!\d)({SSD_PATTERN})\s*(?:gb|기가|ssd)(?!\d)"
    for match in re.finditer(ssd_pattern, lowered_text):
        if not overlaps(match):
            _add_candidate(result, "ssd_gb", int(match.group(1)), match.group())
            occupied.append(match.span())
    for match in re.finditer(rf"(?<!\d){TB_PATTERN}(?![a-z0-9가-힣])", lowered_text):
        if not overlaps(match):
            _add_candidate(result, "ssd_gb", _parse_ssd_token(match.group()), match.group())
            occupied.append(match.span())

    has_explicit_screen = bool(result["screen_candidates"])
    has_explicit_ram = len(result["ram_candidates"]) == 1
    bare_matches = [
        match for match in re.finditer(r"(?<![\d.])\d+(?![\d.])", lowered_text)
        if not overlaps(match)
    ]
    bare_screen_count = sum(int(match.group()) in screen_values for match in bare_matches)
    for match in bare_matches:
        value = int(match.group())
        shared_screen_ram = value in screen_values and value in RAM_VALUES
        if shared_screen_ram and has_explicit_ram:
            if not has_explicit_screen and bare_screen_count == 1:
                # An independent "32GB" or "32/1TB" fixes RAM's role, so the
                # sole remaining display number can safely identify 16 inches.
                _add_candidate(result, "screen_inch", value, match.group())
                continue
            result["screen_ram_ambiguous"] = True
        if shared_screen_ram and not has_explicit_screen:
            result["screen_ram_ambiguous"] = True
        for field, values in (
            ("screen_inch", screen_values),
            ("ram_gb", RAM_VALUES),
            ("ssd_gb", SSD_VALUES),
        ):
            if field == "screen_inch" and shared_screen_ram:
                continue
            if value in values:
                _add_candidate(result, field, value, match.group())

    return result
