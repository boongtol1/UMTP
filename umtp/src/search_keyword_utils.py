import re


MAX_SEARCH_KEYWORD_LEN = 255
MIN_SEARCH_KEYWORD_LEN = 1


def normalize_search_keyword(keyword):
    if keyword is None:
        return ""
    if not isinstance(keyword, str):
        keyword = str(keyword)
    normalized = re.sub(r"\s+", " ", keyword).strip()
    return normalized


def validate_search_keyword(keyword):
    normalized = normalize_search_keyword(keyword)
    if not normalized:
        raise ValueError("invalid_search_keyword")
    if len(normalized) < MIN_SEARCH_KEYWORD_LEN or len(normalized) > MAX_SEARCH_KEYWORD_LEN:
        raise ValueError("invalid_search_keyword")
    # 최소 1개 이상의 의미 있는 문자(한글/영문/숫자)를 요구한다.
    if re.search(r"[0-9A-Za-z가-힣]", normalized) is None:
        raise ValueError("invalid_search_keyword")
    return normalized


def dedupe_keywords_keep_order(keywords):
    if not keywords:
        return []

    deduped = []
    seen = set()
    for keyword in keywords:
        normalized = normalize_search_keyword(keyword)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)

    return deduped


def _normalize_chip(chip):
    if chip is None:
        return None
    normalized = normalize_search_keyword(chip).upper()
    return normalized or None


def _normalize_product_type(product_type):
    if product_type is None:
        return None
    normalized = normalize_search_keyword(product_type)
    return normalized or None


def build_default_keyword_for_watch_rule(rule):
    if not isinstance(rule, dict):
        return None

    product_type = _normalize_product_type(rule.get("product_type"))
    chip = _normalize_chip(rule.get("chip"))

    if product_type == "MacBook Air" and chip:
        return normalize_search_keyword(f"{chip.lower()}맥북에어")

    if chip and product_type:
        return normalize_search_keyword(f"{product_type} {chip}")

    if chip:
        return normalize_search_keyword(f"맥북 {chip}")

    if product_type == "MacBook Air":
        return "맥북에어"

    if product_type:
        return normalize_search_keyword(product_type)

    return None


def build_recommended_keywords_for_spec(product_type, chip, ram_gb=None, ssd_gb=None):
    normalized_product_type = _normalize_product_type(product_type)
    normalized_chip = _normalize_chip(chip)

    keywords = []

    if normalized_product_type == "MacBook Air" and normalized_chip:
        lower_chip = normalized_chip.lower()
        keywords.append(f"{lower_chip}맥북에어")
        keywords.append(f"맥북에어 {normalized_chip}")
        keywords.append(f"맥북 {normalized_chip}")

        if ram_gb is not None and ssd_gb is not None:
            keywords.append(f"{lower_chip} 맥북에어 {ram_gb} {ssd_gb}")
            keywords.append(f"맥북에어 {normalized_chip} {ram_gb} {ssd_gb}")

    if normalized_product_type and normalized_chip:
        keywords.append(f"{normalized_product_type} {normalized_chip}")

    if normalized_product_type:
        keywords.append(normalized_product_type)

    if normalized_chip:
        keywords.append(f"맥북 {normalized_chip}")

    return dedupe_keywords_keep_order(keywords)
