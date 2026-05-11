import re

try:
    from src.risk_keywords import RISK_KEYWORDS
except ImportError:
    from risk_keywords import RISK_KEYWORDS


SCORE_BY_LEVEL = {
    "exclude": 100,
    "high": 60,
    "medium": 30,
    "low": 10,
}

EXCHANGE_STRONG_SCORE = 80
EXCHANGE_WEAK_SCORE = 30
EXCHANGE_NEGATION_SCORE = -80

EXCLUDE_EXCHANGE_TERMS = {
    "교환만",
    "판매안함",
    "판매아님",
    "판매x",
}

EXCLUDE_DAMAGE_TERMS = {
    "부품용",
    "고장품",
    "폐급",
    "사용불가",
}

HIGH_BATTERY_TERMS = {
    "충전불량",
    "배터리불량",
    "서비스권장",
}

HIGH_REPAIR_TERMS = {
    "보드교체",
    "사설수리",
    "비정품",
}

MEDIUM_PRICE_TRADE_TERMS = {
    "예약금",
    "선입금",
    "택배거래만",
    "직거래불가",
}

LOW_PRICE_TRADE_TERMS = {
    "급처",
    "급매",
    "네고",
    "협의",
}

LOW_PHYSICAL_DAMAGE_TERMS = {
    "찍힘",
    "기스",
    "스크래치",
}


def _normalize_text(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip().lower()


def _normalize_no_space(value):
    return re.sub(r"\s+", "", _normalize_text(value))


def _build_risk_target_text(text, self_check_fields=None):
    base = text if isinstance(text, str) else ""
    extra_values = []
    if isinstance(self_check_fields, dict):
        for value in self_check_fields.values():
            if isinstance(value, str) and value.strip():
                extra_values.append(value.strip())
    return " ".join([base.strip(), *extra_values]).strip()


def _append_unique(target, value):
    if value not in target:
        target.append(value)


def _match_keywords(category_name, source_text_norm, source_text_nospace):
    matched = []
    for keyword in RISK_KEYWORDS.get(category_name, []):
        key_norm = _normalize_text(keyword)
        key_nospace = _normalize_no_space(keyword)
        if not key_norm:
            continue

        if key_norm in source_text_norm or key_nospace in source_text_nospace:
            _append_unique(matched, keyword)

    return matched


def _to_token(keyword):
    return _normalize_no_space(keyword)


def _is_low_physical_keyword(keyword):
    token = _to_token(keyword)
    return any(low_token in token for low_token in LOW_PHYSICAL_DAMAGE_TERMS)


def _classify_non_exchange_risk_level(category_name, keyword):
    token = _to_token(keyword)

    if category_name in {"display_damage", "power_boot", "lock"}:
        return "exclude"

    if category_name == "damage_strong":
        if any(ex_term in token for ex_term in EXCLUDE_DAMAGE_TERMS):
            return "exclude"
        return "high"

    if category_name == "physical_damage":
        if _is_low_physical_keyword(keyword):
            return "low"
        return "high"

    if category_name == "input_port":
        return "high"

    if category_name == "battery_charging":
        if any(high_term in token for high_term in HIGH_BATTERY_TERMS):
            return "high"
        return "medium"

    if category_name == "repair_history":
        if any(high_term in token for high_term in HIGH_REPAIR_TERMS):
            return "high"
        return "medium"

    if category_name == "missing_item":
        return "medium"

    if category_name == "price_trade_risk":
        if any(med_term in token for med_term in MEDIUM_PRICE_TRADE_TERMS):
            return "medium"
        if any(low_term in token for low_term in LOW_PRICE_TRADE_TERMS):
            return "low"
        return "medium"

    return None


def _compute_risk_level(risk_score, has_exclude_signal):
    if has_exclude_signal or risk_score >= 100:
        return "exclude"
    if risk_score >= 60:
        return "high"
    if risk_score >= 30:
        return "medium"
    if risk_score >= 10:
        return "low"
    return "none"


def analyze_risk(text, self_check_fields=None):
    target_text = _build_risk_target_text(text, self_check_fields=self_check_fields)
    norm_text = _normalize_text(target_text)
    norm_nospace_text = _normalize_no_space(target_text)

    risk_categories = {}
    risk_keywords = []
    risk_score = 0
    has_exclude_signal = False

    exchange_strong_hits = _match_keywords("exchange_strong", norm_text, norm_nospace_text)
    exchange_weak_hits = _match_keywords("exchange_weak", norm_text, norm_nospace_text)
    exchange_negation_hits = _match_keywords("exchange_negation", norm_text, norm_nospace_text)

    if exchange_strong_hits:
        risk_categories["exchange_strong"] = exchange_strong_hits
    if exchange_weak_hits:
        risk_categories["exchange_weak"] = exchange_weak_hits
    if exchange_negation_hits:
        risk_categories["exchange_negation"] = exchange_negation_hits

    exchange_score = 0
    if exchange_strong_hits:
        exchange_score += EXCHANGE_STRONG_SCORE
    if exchange_weak_hits:
        exchange_score += EXCHANGE_WEAK_SCORE
    if exchange_negation_hits:
        exchange_score += EXCHANGE_NEGATION_SCORE
    exchange_score = max(0, exchange_score)

    exchange_strength = "none"
    is_exchange_post = False

    if exchange_strong_hits and not exchange_negation_hits:
        exchange_strength = "strong"
        is_exchange_post = True
    elif exchange_weak_hits:
        exchange_strength = "weak"
        is_exchange_post = True

    exchange_keywords = []
    if exchange_strength == "strong":
        exchange_keywords = exchange_strong_hits + exchange_weak_hits
    elif exchange_strength == "weak":
        exchange_keywords = exchange_weak_hits

    for keyword in exchange_keywords:
        _append_unique(risk_keywords, keyword)

    for keyword in exchange_strong_hits:
        token = _to_token(keyword)
        if any(ex_token in token for ex_token in EXCLUDE_EXCHANGE_TERMS):
            has_exclude_signal = True

    risk_score += exchange_score

    for category_name in (
        "damage_strong",
        "display_damage",
        "physical_damage",
        "power_boot",
        "battery_charging",
        "input_port",
        "lock",
        "repair_history",
        "missing_item",
        "price_trade_risk",
    ):
        hits = _match_keywords(category_name, norm_text, norm_nospace_text)
        if not hits:
            continue

        risk_categories[category_name] = hits
        for keyword in hits:
            _append_unique(risk_keywords, keyword)
            level = _classify_non_exchange_risk_level(category_name, keyword)
            if level is None:
                continue

            risk_score += SCORE_BY_LEVEL[level]
            if level == "exclude":
                has_exclude_signal = True

    risk_level = _compute_risk_level(risk_score, has_exclude_signal)

    return {
        "risk_detected": risk_level != "none" or len(risk_keywords) > 0,
        "risk_level": risk_level,
        "risk_score": int(risk_score),
        "risk_keywords": risk_keywords,
        "risk_categories": risk_categories,
        "is_exchange_post": is_exchange_post,
        "exchange_strength": exchange_strength,
        "exchange_keywords": exchange_keywords,
        "trade_type": "exchange" if is_exchange_post else "sale",
    }
