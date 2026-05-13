import re

import requests


SEARCH_API_URL = "https://search-api.joongna.com/v3/search/all"
REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://web.joongna.com",
    "os-type": "2",
}
DEFAULT_FIRST_QUANTITY = 50
DEFAULT_CATEGORY_FILTER = [{"categoryDepth": 0, "categorySeq": 0}]
DEFAULT_PRICE_FILTER = {"minPrice": 0, "maxPrice": 100000000}


def _coerce_int(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"[^0-9-]", "", value)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "y", "yes"}:
            return True
        if normalized in {"false", "0", "n", "no"}:
            return False
    return False


def _coerce_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        joined = " ".join(str(token).strip() for token in value if str(token).strip())
        return joined.strip()
    return str(value).strip()


def _extract_item_seq(item):
    for key in ("seq", "productSeq", "id", "productId"):
        seq = _coerce_int(item.get(key))
        if seq is not None and seq > 0:
            return seq
    return None


def _extract_image_url(item):
    for key in ("url", "imageUrl", "image_url", "thumbnailUrl", "thumbnail"):
        image_url = _coerce_text(item.get(key))
        if image_url:
            return image_url
    return ""


def _extract_location_names(item):
    for key in ("locationNames", "location_names", "locationName"):
        if key not in item:
            continue

        value = item.get(key)
        if isinstance(value, list):
            tokens = [str(token).strip() for token in value if str(token).strip()]
            return ", ".join(tokens)

        if isinstance(value, dict):
            tokens = [str(token).strip() for token in value.values() if str(token).strip()]
            return ", ".join(tokens)

        text = _coerce_text(value)
        if text:
            return text

    return ""


def _looks_like_items_list(candidate):
    if not isinstance(candidate, list) or not candidate:
        return False

    dict_count = 0
    for entry in candidate[:10]:
        if isinstance(entry, dict):
            dict_count += 1
            if any(key in entry for key in ("seq", "title", "price", "sortDate", "url")):
                return True

    return dict_count > 0


def _extract_items_from_dict(obj):
    if not isinstance(obj, dict):
        return None

    for key in (
        "items",
        "list",
        "content",
        "searchItems",
        "searchItemList",
        "products",
        "resultList",
    ):
        candidate = obj.get(key)
        if _looks_like_items_list(candidate):
            return candidate

    for key in (
        "data",
        "result",
        "payload",
        "searchResult",
        "searchResults",
    ):
        nested = obj.get(key)
        if isinstance(nested, dict):
            extracted = _extract_items_from_dict(nested)
            if extracted is not None:
                return extracted
        elif _looks_like_items_list(nested):
            return nested

    for value in obj.values():
        if isinstance(value, dict):
            extracted = _extract_items_from_dict(value)
            if extracted is not None:
                return extracted
        elif _looks_like_items_list(value):
            return value

    return None


def _extract_items(response_json):
    if _looks_like_items_list(response_json):
        return response_json

    if not isinstance(response_json, dict):
        return []

    extracted = _extract_items_from_dict(response_json)
    if extracted is not None:
        return extracted

    return []


def _normalize_item(item):
    seq = _extract_item_seq(item)
    title = _coerce_text(item.get("title") or item.get("productName") or item.get("name"))
    price = _coerce_int(item.get("price") or item.get("salePrice") or item.get("priceText"))
    sort_date = _coerce_text(item.get("sortDate") or item.get("sort_date") or item.get("createdAt"))
    location_names = _extract_location_names(item)
    wish_count = _coerce_int(item.get("wishCount") or item.get("wish_count"))
    chat_count = _coerce_int(item.get("chatCount") or item.get("chat_count"))
    self_audit_flag = _coerce_bool(item.get("selfAuditFlag") or item.get("self_audit_flag"))
    image_url = _extract_image_url(item)
    product_url = f"https://web.joongna.com/product/{seq}" if seq is not None else ""

    return {
        "seq": seq,
        "title": title,
        "price": price,
        "sort_date": sort_date,
        "location_names": location_names,
        "wish_count": wish_count,
        "chat_count": chat_count,
        "self_audit_flag": self_audit_flag,
        "image_url": image_url,
        "product_url": product_url,
    }


def _build_search_payload(search_word, page, quantity):
    return {
        "osType": 2,
        "firstQuantity": DEFAULT_FIRST_QUANTITY,
        "quantity": quantity,
        "jnPayYn": "ALL",
        "categoryFilter": DEFAULT_CATEGORY_FILTER,
        "priceFilter": DEFAULT_PRICE_FILTER,
        "sort": "RECENT_SORT",
        "saleYn": "SALE_N",
        "parcelFeeYn": "ALL",
        "page": page,
        "searchWord": search_word,
        "adjustSearchKeyword": True,
        "keywordSource": "INPUT_KEYWORD",
        "registPeriod": "ALL",
    }


def search_joongna_products(search_word, page=0, quantity=50):
    if not isinstance(search_word, str) or not search_word.strip():
        raise ValueError("search_word가 비어 있습니다.")

    payload = _build_search_payload(search_word=search_word.strip(), page=page, quantity=quantity)

    try:
        response = requests.post(
            SEARCH_API_URL,
            headers=DEFAULT_HEADERS,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"중고나라 Search API 요청 실패: {exc}") from exc

    try:
        response_json = response.json()
    except ValueError as exc:
        raise RuntimeError(f"중고나라 Search API JSON 파싱 실패: {exc}") from exc

    normalized_items = []
    for raw_item in _extract_items(response_json):
        if not isinstance(raw_item, dict):
            continue
        normalized_items.append(_normalize_item(raw_item))

    return normalized_items
