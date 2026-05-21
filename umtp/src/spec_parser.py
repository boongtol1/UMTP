import re
from typing import Optional

try:
    from src.macbook_air_units import (
        MACBOOK_AIR_PRODUCT_TYPE,
        MAC_MINI_PRODUCT_TYPE,
        get_product_base_spec,
        is_valid_silicon_unit,
    )
    from src.numeric_candidate_extractor import extract_numeric_candidates
except ImportError:
    from macbook_air_units import (
        MACBOOK_AIR_PRODUCT_TYPE,
        MAC_MINI_PRODUCT_TYPE,
        get_product_base_spec,
        is_valid_silicon_unit,
    )
    from numeric_candidate_extractor import extract_numeric_candidates


PRODUCT_TYPE = MACBOOK_AIR_PRODUCT_TYPE
DEFAULT_SCREEN_INCH = 13
DEFAULT_MAC_MINI_SCREEN_INCH = 0
SUPPORTED_CHIPS = ("M1", "M2", "M3", "M4", "M5")
SUPPORTED_MAC_MINI_CHIPS = ("M1", "M2", "M2 Pro", "M4", "M4 Pro")
SUPPORTED_RAM_GB = (8, 16, 24, 32, 48, 64)
SUPPORTED_SSD_GB = (256, 512, 1024, 2048, 4096, 8192)
REQUIRED_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
MISSING_REQUIRED_REASON = "missing_required_fields"
INVALID_UNIT_REASON = "invalid_silicon_mac_unit"
MULTIPLE_CHIPS_REASON = "multiple_chips_found"
AMBIGUOUS_NUMERIC_REASON = "ambiguous_numeric_candidates"
MULTIPLE_PRODUCT_TYPES_REASON = "multiple_product_types_found"

TB_TO_GB_MAP = {
    "1tb": 1024,
    "2tb": 2048,
    "4tb": 4096,
    "8tb": 8192,
    "1t": 1024,
    "2t": 2048,
    "4t": 4096,
    "8t": 8192,
    "1테라": 1024,
    "2테라": 2048,
    "4테라": 4096,
    "8테라": 8192,
}

BASE_MODEL_KEYWORD_PATTERN = re.compile(r"(기본형|기본사양|깡통)")

NOISE_CONTEXT_KEYWORDS = {
    "date": ["월", "일", "년", "년식"],
    "time": ["시", "분", "시간", "오전", "오후"],
    "phone": ["010", "011", "016", "017", "018", "019"],
    "price": ["원", "만원", "만", "가격", "판매가", "택배비", "예약금", "네고"],
    "location": ["번 출구", "출구", "동", "호", "층", "거리", "km", "m"],
    "quantity": ["대", "개", "번 사용", "회", "번"],
    "battery": ["배터리", "성능", "효율", "사이클", "cycle", "충전기", "w", "와트"],
    "model": ["모델", "모델명", "모델번호", "시리얼", "serial", "주문번호"],
    "os": ["macos", "ios", "sonoma", "sequoia", "ventura", "monterey"],
    "core": ["코어", "core", "cpu", "gpu"],
    "display": ["hz", "니트", "해상도"],
    "port": ["포트", "usb", "hdmi", "썬더볼트", "thunderbolt"],
    "condition": ["상태", "점", "찍힘", "기스", "흠집", "곳"],
    "warranty": ["보증", "애케플", "applecare", "apple care", "개월", "년 남음"],
}

SPEC_CONTEXT_KEYWORDS = [
    "m1",
    "m2",
    "m3",
    "m4",
    "m5",
    "인치",
    "inch",
    "\"",
    "”",
    "''",
    "′′",
    "형",
    "ram",
    "램",
    "메모리",
    "memory",
    "ssd",
    "저장공간",
    "용량",
    "storage",
    "mini",
    "pro",
    "맥미니",
    "맥 미니",
    "mac mini",
    "macmini",
    "gb",
    "기가",
    "tb",
    "테라",
]

RAM_SHORT_TOKENS = ["8g", "16g", "24g", "32g"]
SSD_SHORT_TOKENS = ["1t", "2t", "4t"]

_SPEC_WINDOW_SIZE = 20

_STRONG_NOISE_PATTERNS = (
    re.compile(r"\b01[0-9][-\s]?\d{3,4}[-\s]?\d{4}\b", flags=re.IGNORECASE),
    re.compile(r"\b0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}\b", flags=re.IGNORECASE),
    re.compile(r"\b20\d{2}[./-]\d{1,2}[./-]\d{1,2}\b", flags=re.IGNORECASE),
    re.compile(r"\b(?:1[0-2]|0?[1-9])/(?:3[01]|[12]?\d)\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s*월\s*\d{1,2}\s*일\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{2,4}\s*년(?:식)?\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s*:\s*\d{2}\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s*분\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*시간\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{1,3}(?:,\d{3})+\s*원\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*만원\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*만\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*번\s*출구\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*동\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*호\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*층\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*회\b", flags=re.IGNORECASE),
    re.compile(r"(?:배터리|효율|성능)\s*\d{1,3}\s*%", flags=re.IGNORECASE),
    re.compile(r"(?:사이클|cycle)\s*\d+", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*w\b", flags=re.IGNORECASE),
    re.compile(r"(?:macos|ios|sonoma|sequoia|ventura|monterey)\s*\d+(?:\.\d+)?", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:코어|core)\b", flags=re.IGNORECASE),
    re.compile(r"\b(?:cpu|gpu)\s*\d+\s*(?:코어|core)?\b", flags=re.IGNORECASE),
    re.compile(r"\b\d{3,4}\s*[x×]\s*\d{3,4}\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*hz\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*니트\b", flags=re.IGNORECASE),
    re.compile(r"(?:usb|hdmi|썬더볼트|thunderbolt)\s*\d+(?:\.\d+)?", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*/\s*10\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*점\b", flags=re.IGNORECASE),
    re.compile(r"(?:찍힘|기스|흠집|곳)\s*\d+\s*개?", flags=re.IGNORECASE),
    re.compile(r"(?:보증|애케플|applecare|apple care)\s*\d+\s*(?:개월|년|년까지)?", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*개월\b", flags=re.IGNORECASE),
    re.compile(r"\b\d+\s*년\s*남음\b", flags=re.IGNORECASE),
)

_SPEC_SPAN_PATTERNS = (
    re.compile(r"m\s*(?:2|4)\s*[-]?\s*pro", flags=re.IGNORECASE),
    re.compile(r"m[1-5]", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(13(?:\.\d+)?|15(?:\.\d+)?)\s*(?:인치|inch|형|\"|”|''|′′)(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(13(?:\.\d+)?|15(?:\.\d+)?)-inch(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(8|16|24|32|48|64)\s*gb(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(8|16|24|32|48|64)\s*기가(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(8|16|24|32|48|64)\s*g(?![a-z0-9가-힣])", flags=re.IGNORECASE),
    re.compile(r"램\s*(8|16|24|32|48|64)(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(8|16|24|32|48|64)\s*램(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(256|512|1024|2048|4096|8192)\s*gb(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(256|512|1024|2048|4096|8192)\s*기가(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(256|512|1024|2048|4096|8192)\s*ssd(?!\d)", flags=re.IGNORECASE),
    re.compile(r"(?<!\d)(1|2|4|8)\s*(?:tb|t|테라)(?![a-z0-9가-힣])", flags=re.IGNORECASE),
    re.compile(
        r"(?<!\d)(8|16|24|32|48|64)\s*/\s*(256|512|1024|2048|4096|8192|1\s*tb|2\s*tb|4\s*tb|8\s*tb|1\s*t|2\s*t|4\s*t|8\s*t|1\s*테라|2\s*테라|4\s*테라|8\s*테라)(?!\d)",
        flags=re.IGNORECASE,
    ),
)

_NUMERIC_TOKEN_PATTERN = re.compile(r"\d+(?:\.\d+)?")
_NOISE_CONTEXT_KEYWORDS_LOWER = sorted(
    {keyword.lower() for keywords in NOISE_CONTEXT_KEYWORDS.values() for keyword in keywords if keyword},
    key=len,
    reverse=True,
)
_SPEC_CONTEXT_KEYWORDS_LOWER = [keyword.lower() for keyword in SPEC_CONTEXT_KEYWORDS]


def _span_overlaps(spans, start, end):
    for span_start, span_end in spans:
        if start < span_end and end > span_start:
            return True
    return False


def _merge_spans(spans):
    if not spans:
        return []

    ordered = sorted(spans, key=lambda item: (item[0], item[1]))
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _collect_spec_spans(text):
    spans = []
    for pattern in _SPEC_SPAN_PATTERNS:
        spans.extend((match.start(), match.end()) for match in pattern.finditer(text))
    return _merge_spans(spans)


def _normalize_screen_inch_value(raw_value):
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None

    if 12.7 <= value <= 13.9:
        return 13
    if 14.7 <= value <= 15.9:
        return 15
    if value in (13.0, 15.0):
        return int(value)
    return None


def _extract_screen_inch_candidates_from_text(text):
    if not isinstance(text, str) or not text:
        return []

    candidates = []
    patterns = (
        r"(?<!\d)(13(?:\.\d+)?|15(?:\.\d+)?)\s*(?:인치|inch|형|\"|”|''|′′)(?!\d)",
        r"(?<!\d)(13(?:\.\d+)?|15(?:\.\d+)?)-inch(?!\d)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            normalized = _normalize_screen_inch_value(match.group(1))
            if normalized in (13, 15) and normalized not in candidates:
                candidates.append(normalized)
    return candidates


def _extract_ram_gb_candidates_from_text(text):
    if not isinstance(text, str) or not text:
        return []

    candidates = []
    patterns = (
        r"(?<!\d)(8|16|24|32|48|64)\s*gb(?!\d)",
        r"(?<!\d)(8|16|24|32|48|64)\s*기가(?!\d)",
        r"램\s*(8|16|24|32|48|64)(?!\d)",
        r"(?<!\d)(8|16|24|32|48|64)\s*램(?!\d)",
        r"(?<!\d)(8|16|24|32|48|64)\s*g(?![a-z0-9가-힣])",
        r"^(8|16|24|32|48|64)$",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            ram_gb = int(match.group(1))
            if ram_gb in SUPPORTED_RAM_GB and ram_gb not in candidates:
                candidates.append(ram_gb)
    return candidates


def _extract_ssd_gb_candidates_from_text(text):
    if not isinstance(text, str) or not text:
        return []

    candidates = []
    lowered = text.lower()

    for pattern in (
        r"(?<!\d)(1|2|4|8)\s*(?:tb|t|테라)(?![a-z0-9가-힣])",
        r"(?<!\d)(256|512|1024|2048|4096|8192)\s*gb(?!\d)",
        r"(?<!\d)(256|512|1024|2048|4096|8192)\s*기가(?!\d)",
        r"(?<!\d)(256|512|1024|2048|4096|8192)\s*ssd(?!\d)",
        r"^(256|512|1024|2048|4096|8192)$",
    ):
        for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            token = match.group(0)
            if pattern.startswith("(?<!\\d)(1|2|4)"):
                ssd_gb = TB_TO_GB_MAP.get(re.sub(r"\s+", "", token.lower()))
            else:
                ssd_gb = int(match.group(1))
            if ssd_gb in SUPPORTED_SSD_GB and ssd_gb not in candidates:
                candidates.append(ssd_gb)
    return candidates


def _apply_removal_mask(text, mask):
    chars = list(text)
    for index, should_remove in enumerate(mask):
        if should_remove:
            chars[index] = " "
    return "".join(chars)


def _normalize_for_spec_parsing_with_meta(text):
    raw_text = _normalize_text(text)
    if not raw_text:
        return "", []

    lowered = raw_text.lower()
    removed_noise_fragments = []

    strong_noise_mask = [False] * len(lowered)
    protected_spans = _collect_spec_spans(lowered)
    for pattern in _STRONG_NOISE_PATTERNS:
        for match in pattern.finditer(lowered):
            start, end = match.start(), match.end()
            if _span_overlaps(protected_spans, start, end):
                continue
            fragment = lowered[start:end].strip()
            if fragment:
                removed_noise_fragments.append(fragment)
            for idx in range(start, end):
                strong_noise_mask[idx] = True
    lowered = _apply_removal_mask(lowered, strong_noise_mask)

    context_noise_mask = [False] * len(lowered)
    protected_spans = _collect_spec_spans(lowered)
    for match in _NUMERIC_TOKEN_PATTERN.finditer(lowered):
        start, end = match.start(), match.end()
        if _span_overlaps(protected_spans, start, end):
            continue

        window_start = max(0, start - _SPEC_WINDOW_SIZE)
        window_end = min(len(lowered), end + _SPEC_WINDOW_SIZE)
        window = lowered[window_start:window_end]

        has_spec_context = any(keyword in window for keyword in _SPEC_CONTEXT_KEYWORDS_LOWER)
        has_noise_context = any(keyword in window for keyword in _NOISE_CONTEXT_KEYWORDS_LOWER)
        if has_noise_context and not has_spec_context:
            fragment = lowered[start:end].strip()
            if fragment:
                removed_noise_fragments.append(fragment)
            for idx in range(start, end):
                context_noise_mask[idx] = True

    lowered = _apply_removal_mask(lowered, context_noise_mask)
    normalized = _normalize_text(lowered)
    dedup_removed = list(dict.fromkeys(fragment for fragment in removed_noise_fragments if fragment))
    return normalized, dedup_removed


def normalize_for_spec_parsing(text: str) -> str:
    normalized_text, _ = _normalize_for_spec_parsing_with_meta(text)
    return normalized_text


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
    return bool(_detect_product_types(text))


def _detect_product_types(text):
    if not isinstance(text, str):
        return []
    lowered = text.lower()
    normalized = re.sub(r"\s+", "", lowered)
    detected = []
    if (
        "macbook air" in lowered
        or "macbookair" in normalized
        or "맥북에어" in normalized
    ):
        detected.append(MACBOOK_AIR_PRODUCT_TYPE)
    if (
        "mac mini" in lowered
        or "macmini" in normalized
        or "맥미니" in normalized
    ):
        detected.append(MAC_MINI_PRODUCT_TYPE)
    return detected


def _extract_unique_mac_mini_chip_candidates(text):
    if not isinstance(text, str):
        return []

    normalized_text = text.lower()
    candidates = []

    # IMPORTANT: Pro variants must be checked first to avoid parsing as M2/M4.
    if re.search(r"m\s*2\s*[-]?\s*pro", normalized_text, flags=re.IGNORECASE):
        candidates.append("M2 Pro")
    if re.search(r"m\s*4\s*[-]?\s*pro", normalized_text, flags=re.IGNORECASE):
        candidates.append("M4 Pro")

    for match in re.finditer(r"m\s*(1|2|4)\b(?!\s*[-]?\s*pro)", normalized_text, flags=re.IGNORECASE):
        value = match.group(1)
        if value == "1":
            candidates.append("M1")
        elif value == "2":
            candidates.append("M2")
        elif value == "4":
            candidates.append("M4")

    deduped = list(dict.fromkeys(candidates))
    chip_sort_order = {chip: idx for idx, chip in enumerate(SUPPORTED_MAC_MINI_CHIPS, start=1)}
    return sorted(deduped, key=lambda chip: chip_sort_order.get(chip, 999))


def _extract_chip(text):
    unique_chips = _extract_unique_chip_candidates(text)
    if len(unique_chips) != 1:
        return None
    return unique_chips[0]


def _extract_unique_chip_candidates(text):
    if not isinstance(text, str):
        return []

    chip_candidates = re.findall(r"m[1-5]", text.lower())
    unique_chips = sorted(set(chip_candidates))
    return [chip.upper() for chip in unique_chips]


def _extract_chip_candidates_for_product(text, product_type):
    return _extract_unique_chip_candidates(text)


def _extract_screen_inch_from_text(text):
    screen_candidates = _extract_screen_inch_candidates_from_text(text)
    if len(screen_candidates) != 1:
        return None
    return screen_candidates[0]


def _extract_ram_gb_from_text(text):
    ram_candidates = _extract_ram_gb_candidates_from_text(text)
    if len(ram_candidates) != 1:
        return None
    return ram_candidates[0]


def _extract_ssd_gb_from_text(text):
    ssd_candidates = _extract_ssd_gb_candidates_from_text(text)
    if len(ssd_candidates) != 1:
        return None
    return ssd_candidates[0]


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


def parse_listing_text(title: str, body_text: Optional[str] = None, self_check_text: Optional[str] = None, self_check_fields=None):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("매물 제목/본문 텍스트는 비어 있을 수 없습니다.")

    normalized_self_check = _normalize_self_check_fields(self_check_fields)
    model_name_raw = normalized_self_check.get("모델명")
    cpu_raw = normalized_self_check.get("CPU종류")
    ram_raw = normalized_self_check.get("램 용량")
    ssd_raw = normalized_self_check.get("SSD용량")

    self_check_segments = []
    if isinstance(self_check_text, str) and self_check_text.strip():
        self_check_segments.append(self_check_text)
    self_check_segments.extend(value for value in normalized_self_check.values() if value)

    combined_text = _normalize_text(" ".join([title, body_text or "", " ".join(self_check_segments)]))
    normalized_text, removed_noise_fragments = _normalize_for_spec_parsing_with_meta(combined_text)
    parsing_text = normalized_text or _normalize_text(title.lower())

    detected_patterns = {}
    detected_conflicts = []
    ambiguous_reasons = []

    product_type = None
    product_type_ambiguous = False
    chip = None
    chip_ambiguous = False
    screen_inch = None
    ram_gb = None
    ssd_gb = None
    screen_inch_defaulted = False
    mini_screen_conflict = False
    screen_ambiguous = False
    ram_ambiguous = False
    ssd_ambiguous = False

    model_product_types = _detect_product_types(model_name_raw)
    text_product_types = _detect_product_types(parsing_text)
    if not text_product_types:
        text_product_types = _detect_product_types(combined_text)

    model_product_type = model_product_types[0] if len(model_product_types) == 1 else None
    text_product_type = text_product_types[0] if len(text_product_types) == 1 else None

    if len(model_product_types) >= 2 or len(text_product_types) >= 2:
        product_type_ambiguous = True
    if (
        model_product_type is not None
        and text_product_type is not None
        and model_product_type != text_product_type
    ):
        product_type_ambiguous = True

    if model_product_type is not None:
        product_type = model_product_type
        _record_pattern(detected_patterns, "product_type", product_type, "self_check", model_name_raw)
    elif text_product_type is not None:
        product_type = text_product_type
        _record_pattern(detected_patterns, "product_type", product_type, "text", title)

    if product_type is None:
        parse_failure_reason = MISSING_REQUIRED_REASON
        return {
            "parse_success": False,
            "product_type": None,
            "chip": None,
            "screen_inch": None,
            "screen_inch_defaulted": False,
            "ram_gb": None,
            "ssd_gb": None,
            "confidence_score": 0,
            "unit_valid": False,
            "unit_validation_reason": MISSING_REQUIRED_REASON,
            "missing_fields": list(REQUIRED_FIELDS),
            "detected_patterns": detected_patterns,
            "detected_conflicts": detected_conflicts,
            "original_text": combined_text,
            "normalized_text": parsing_text,
            "removed_noise_fragments": removed_noise_fragments,
            "parsed_chip": None,
            "parsed_screen_inch": None,
            "parsed_ram_gb": None,
            "parsed_ssd_gb": None,
            "parse_failure_reason": parse_failure_reason,
            "ambiguous_reason": None,
        }

    model_chip_candidates = _extract_chip_candidates_for_product(model_name_raw, product_type)
    if len(model_chip_candidates) == 1:
        chip = model_chip_candidates[0]
        _record_pattern(detected_patterns, "chip", chip, "self_check", model_name_raw)
    elif len(model_chip_candidates) >= 2:
        chip_ambiguous = True
        _record_conflict(detected_conflicts, "chip", "unresolved", None, "self_check", model_chip_candidates)

    cpu_chip_candidates = _extract_chip_candidates_for_product(cpu_raw, product_type)
    if len(cpu_chip_candidates) == 1:
        chip_cpu = cpu_chip_candidates[0]
        if chip is not None and chip != chip_cpu:
            chip_ambiguous = True
            _record_conflict(detected_conflicts, "chip", "self_check", chip, "self_check", chip_cpu)
        chip = chip_cpu
        _record_pattern(detected_patterns, "chip", chip_cpu, "self_check", cpu_raw)
    elif len(cpu_chip_candidates) >= 2:
        chip_ambiguous = True
        _record_conflict(detected_conflicts, "chip", "unresolved", None, "self_check", cpu_chip_candidates)

    ram_self_candidates = _extract_ram_gb_candidates_from_text(normalize_for_spec_parsing(ram_raw))
    ram_self_candidate, ram_self_ambiguous = _choose_numeric_candidate(ram_self_candidates)
    if ram_self_candidate is not None:
        ram_gb = ram_self_candidate
        _record_pattern(detected_patterns, "ram_gb", ram_self_candidate, "self_check", ram_raw)
    if ram_self_ambiguous:
        ram_ambiguous = True
        _record_conflict(detected_conflicts, "ram_gb", "unresolved", None, "self_check", ram_self_candidates)

    ssd_self_candidates = _extract_ssd_gb_candidates_from_text(normalize_for_spec_parsing(ssd_raw))
    ssd_self_candidate, ssd_self_ambiguous = _choose_numeric_candidate(ssd_self_candidates)
    if ssd_self_candidate is not None:
        ssd_gb = ssd_self_candidate
        _record_pattern(detected_patterns, "ssd_gb", ssd_self_candidate, "self_check", ssd_raw)
    if ssd_self_ambiguous:
        ssd_ambiguous = True
        _record_conflict(detected_conflicts, "ssd_gb", "unresolved", None, "self_check", ssd_self_candidates)

    model_screen_candidates = _extract_screen_inch_candidates_from_text(normalize_for_spec_parsing(model_name_raw))
    model_screen_candidate, model_screen_ambiguous = _choose_numeric_candidate(model_screen_candidates)
    if model_screen_candidate is not None:
        screen_inch = model_screen_candidate
        _record_pattern(detected_patterns, "screen_inch", model_screen_candidate, "self_check", model_name_raw)
    if model_screen_ambiguous:
        screen_ambiguous = True
        _record_conflict(detected_conflicts, "screen_inch", "unresolved", None, "self_check", model_screen_candidates)

    text_chip_candidates = _extract_chip_candidates_for_product(parsing_text, product_type)
    if len(text_chip_candidates) == 1:
        chip_from_text = text_chip_candidates[0]
        if chip is None:
            chip = chip_from_text
            _record_pattern(detected_patterns, "chip", chip_from_text, "text", chip_from_text)
        elif chip != chip_from_text:
            chip_ambiguous = True
            _record_conflict(detected_conflicts, "chip", "self_check", chip, "text", chip_from_text)
    elif len(text_chip_candidates) >= 2:
        chip_ambiguous = True
        _record_conflict(detected_conflicts, "chip", "unresolved", None, "text", text_chip_candidates)

    text_screen_candidates = _extract_screen_inch_candidates_from_text(parsing_text)
    text_screen_candidate, text_screen_ambiguous = _choose_numeric_candidate(text_screen_candidates)
    if screen_inch is None and text_screen_candidate is not None:
        screen_inch = text_screen_candidate
        _record_pattern(detected_patterns, "screen_inch", text_screen_candidate, "text", text_screen_candidate)
    elif screen_inch is not None and text_screen_candidate is not None and screen_inch != text_screen_candidate:
        screen_ambiguous = True
        _record_conflict(detected_conflicts, "screen_inch", "self_check", screen_inch, "text", text_screen_candidate)
    if text_screen_ambiguous:
        screen_ambiguous = True
        _record_conflict(detected_conflicts, "screen_inch", "unresolved", None, "text", text_screen_candidates)

    text_ram_candidates = _extract_ram_gb_candidates_from_text(parsing_text)
    text_ram_candidate, text_ram_ambiguous = _choose_numeric_candidate(text_ram_candidates)
    if ram_gb is None and text_ram_candidate is not None:
        ram_gb = text_ram_candidate
        _record_pattern(detected_patterns, "ram_gb", text_ram_candidate, "text", text_ram_candidate)
    elif ram_gb is not None and text_ram_candidate is not None and ram_gb != text_ram_candidate:
        ram_ambiguous = True
        _record_conflict(detected_conflicts, "ram_gb", "self_check", ram_gb, "text", text_ram_candidate)
    if text_ram_ambiguous:
        ram_ambiguous = True
        _record_conflict(detected_conflicts, "ram_gb", "unresolved", None, "text", text_ram_candidates)

    text_ssd_candidates = _extract_ssd_gb_candidates_from_text(parsing_text)
    text_ssd_candidate, text_ssd_ambiguous = _choose_numeric_candidate(text_ssd_candidates)
    if ssd_gb is None and text_ssd_candidate is not None:
        ssd_gb = text_ssd_candidate
        _record_pattern(detected_patterns, "ssd_gb", text_ssd_candidate, "text", text_ssd_candidate)
    elif ssd_gb is not None and text_ssd_candidate is not None and ssd_gb != text_ssd_candidate:
        ssd_ambiguous = True
        _record_conflict(detected_conflicts, "ssd_gb", "self_check", ssd_gb, "text", text_ssd_candidate)
    if text_ssd_ambiguous:
        ssd_ambiguous = True
        _record_conflict(detected_conflicts, "ssd_gb", "unresolved", None, "text", text_ssd_candidates)

    numeric_candidates = extract_numeric_candidates(parsing_text)

    screen_candidate, numeric_screen_ambiguous = _choose_numeric_candidate(numeric_candidates["screen_candidates"])
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
        screen_ambiguous = True
        _record_conflict(detected_conflicts, "screen_inch", "self_check", screen_inch, "text", screen_candidate)

    ram_candidate, numeric_ram_ambiguous = _choose_numeric_candidate(numeric_candidates["ram_candidates"])
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
        ram_ambiguous = True
        _record_conflict(detected_conflicts, "ram_gb", "self_check", ram_gb, "text", ram_candidate)

    ssd_candidate, numeric_ssd_ambiguous = _choose_numeric_candidate(numeric_candidates["ssd_candidates"])
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
        ssd_ambiguous = True
        _record_conflict(detected_conflicts, "ssd_gb", "self_check", ssd_gb, "text", ssd_candidate)

    if numeric_screen_ambiguous and screen_inch is None:
        screen_ambiguous = True
        _record_conflict(
            detected_conflicts,
            "screen_inch",
            "default",
            DEFAULT_SCREEN_INCH,
            "text",
            numeric_candidates["screen_candidates"],
        )
    if numeric_ram_ambiguous and ram_gb is None:
        ram_ambiguous = True
        _record_conflict(detected_conflicts, "ram_gb", "unresolved", None, "text", numeric_candidates["ram_candidates"])
    if numeric_ssd_ambiguous and ssd_gb is None:
        ssd_ambiguous = True
        _record_conflict(detected_conflicts, "ssd_gb", "unresolved", None, "text", numeric_candidates["ssd_candidates"])

    if product_type == MACBOOK_AIR_PRODUCT_TYPE and screen_inch is None:
        screen_inch = DEFAULT_SCREEN_INCH
        screen_inch_defaulted = True
        _record_pattern(detected_patterns, "screen_inch", DEFAULT_SCREEN_INCH, "default", None)
    elif product_type == MAC_MINI_PRODUCT_TYPE:
        if screen_inch is not None and screen_inch != DEFAULT_MAC_MINI_SCREEN_INCH:
            mini_screen_conflict = True
            _record_conflict(
                detected_conflicts,
                "screen_inch",
                "default",
                DEFAULT_MAC_MINI_SCREEN_INCH,
                "text",
                screen_inch,
            )
        screen_inch = DEFAULT_MAC_MINI_SCREEN_INCH
        screen_inch_defaulted = False

    has_base_model_keyword = contains_base_model_keyword(parsing_text) or contains_base_model_keyword(model_name_raw)
    should_apply_base_fallback = (
        product_type in (MACBOOK_AIR_PRODUCT_TYPE, MAC_MINI_PRODUCT_TYPE)
        and chip is not None
        and (ram_gb is None or ssd_gb is None)
    )
    if should_apply_base_fallback:
        base_spec = get_product_base_spec(product_type, chip, screen_inch)
        if isinstance(base_spec, dict):
            fallback_source = "기본형/기본사양/깡통" if has_base_model_keyword else "missing_ram_or_ssd"
            if ram_gb is None:
                ram_gb = base_spec.get("ram_gb")
                if ram_gb is not None:
                    _record_pattern(detected_patterns, "ram_gb", ram_gb, "fallback_base_model", fallback_source)
            if ssd_gb is None:
                ssd_gb = base_spec.get("ssd_gb")
                if ssd_gb is not None:
                    _record_pattern(detected_patterns, "ssd_gb", ssd_gb, "fallback_base_model", fallback_source)

    parsed_fields = {"product_type": product_type, "chip": chip, "ram_gb": ram_gb, "ssd_gb": ssd_gb}
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

    if product_type_ambiguous:
        parse_success = False
        product_type = None
        unit_validation_reason = MULTIPLE_PRODUCT_TYPES_REASON
        ambiguous_reasons.append(MULTIPLE_PRODUCT_TYPES_REASON)
    elif chip_ambiguous:
        parse_success = False
        chip = None
        unit_validation_reason = MULTIPLE_CHIPS_REASON
        ambiguous_reasons.append(MULTIPLE_CHIPS_REASON)
    elif not parse_success:
        unit_validation_reason = MISSING_REQUIRED_REASON
    elif product_type == MAC_MINI_PRODUCT_TYPE and mini_screen_conflict:
        unit_valid = False
        parse_success = False
        unit_validation_reason = INVALID_UNIT_REASON
    elif product_type in (MACBOOK_AIR_PRODUCT_TYPE, MAC_MINI_PRODUCT_TYPE):
        unit_valid = is_valid_silicon_unit(product_type, chip, screen_inch, ram_gb, ssd_gb)
        if not unit_valid:
            parse_success = False
            unit_validation_reason = INVALID_UNIT_REASON
    else:
        unit_validation_reason = MISSING_REQUIRED_REASON

    if screen_ambiguous:
        ambiguous_reasons.append("screen_inch_ambiguous")
    if ram_ambiguous:
        ambiguous_reasons.append("ram_gb_ambiguous")
    if ssd_ambiguous:
        ambiguous_reasons.append("ssd_gb_ambiguous")
    if parse_success and any([screen_ambiguous, ram_ambiguous, ssd_ambiguous]):
        parse_success = False
        unit_validation_reason = AMBIGUOUS_NUMERIC_REASON

    if parse_success:
        unit_valid = True

    ambiguous_reason = ", ".join(list(dict.fromkeys(ambiguous_reasons))) if ambiguous_reasons else None
    parse_failure_reason = None if parse_success else (ambiguous_reason or unit_validation_reason or MISSING_REQUIRED_REASON)

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
        "original_text": combined_text,
        "normalized_text": parsing_text,
        "removed_noise_fragments": removed_noise_fragments,
        "parsed_chip": chip,
        "parsed_screen_inch": screen_inch,
        "parsed_ram_gb": ram_gb,
        "parsed_ssd_gb": ssd_gb,
        "parse_failure_reason": parse_failure_reason,
        "ambiguous_reason": ambiguous_reason,
    }


def parse_listing_title(text, self_check_fields=None):
    return parse_listing_text(title=text, self_check_fields=self_check_fields)
