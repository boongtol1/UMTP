import json
import logging
import re

import requests
from bs4 import BeautifulSoup

try:
    from src.outbound_rate_limiter import joongna_detail_limiter
except ModuleNotFoundError:
    from outbound_rate_limiter import joongna_detail_limiter


REQUEST_TIMEOUT_SECONDS = 10
logger = logging.getLogger("umtp.outbound_rate_limit")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
SELF_CHECK_PRIORITY_KEYS = ("모델명", "램 용량", "SSD용량", "CPU종류", "컬러")
SELF_CHECK_IGNORED_TOKENS = ("스펙보기",)
MANUAL_VERIFICATION_SELF_CHECK_KEYWORDS = (
    "일련번호",
    "시리얼",
    "serial",
    "모델번호",
    "modelnumber",
    "cpu코어",
    "gpu코어",
    "배터리사이클",
    "배터리효율",
    "배터리성능",
    "applecare",
    "애플케어",
    "활성화잠금",
    "activationlock",
    "mdm",
)


def fetch_html(url):
    try:
        sleep_seconds = joongna_detail_limiter.wait()
        if sleep_seconds > 0:
            logger.debug(
                "[outbound_rate_limit] type=detail sleep_seconds=%.2f",
                sleep_seconds,
            )
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"HTML 요청 실패: {exc}") from exc

    return response.text


def parse_price_to_int(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("가격 문자열이 비어 있습니다.")

    digits = re.findall(r"\d+", text)
    if not digits:
        raise ValueError("가격 문자열에서 숫자를 찾을 수 없습니다.")

    price = int("".join(digits))
    if price <= 0:
        raise ValueError("가격은 0보다 커야 합니다.")

    return price


def find_price_text(soup):
    required_classes = {
        "whitespace-pre-line",
        "text-32",
        "font-bold",
        "max-md:text-24",
    }

    for span in soup.find_all("span"):
        class_tokens = set(span.get("class") or [])
        if required_classes.issubset(class_tokens):
            candidate = span.get_text(strip=True)
            if candidate:
                return candidate

    return None


def _normalize_text(text):
    if not isinstance(text, str):
        return ""
    return " ".join(text.split()).strip()


def _clean_self_check_dd_text(dd_tag):
    if dd_tag is None:
        return ""

    # 원본 노드를 건드리지 않기 위해 복제본에서 버튼/부가 UI 텍스트를 제거한다.
    dd_clone = BeautifulSoup(str(dd_tag), "html.parser").find("dd")
    if dd_clone is None:
        dd_clone = dd_tag

    for button_tag in dd_clone.find_all("button"):
        button_tag.decompose()

    text = _normalize_text(dd_clone.get_text(" ", strip=True))
    for ignored_token in SELF_CHECK_IGNORED_TOKENS:
        text = text.replace(ignored_token, " ")

    return _normalize_text(text)


def _is_manual_verification_self_check_key(key_text):
    normalized_key = _normalize_text(key_text)
    if not normalized_key:
        return False

    compact = re.sub(r"[\s/_-]+", "", normalized_key.lower())
    return any(keyword in compact for keyword in MANUAL_VERIFICATION_SELF_CHECK_KEYWORDS)


def extract_self_check_fields(soup):
    # 셀프검수 영역은 선택 정보이므로 실패 시 빈 dict를 반환한다.
    try:
        extracted = {}
        for dl_tag in soup.find_all("dl"):
            local_map = {}
            for dt_tag in dl_tag.find_all("dt"):
                key = _normalize_text(dt_tag.get_text(" ", strip=True))
                if not key:
                    continue
                if _is_manual_verification_self_check_key(key):
                    continue

                dd_tag = dt_tag.find_next_sibling("dd")
                if dd_tag is None:
                    continue

                value = _clean_self_check_dd_text(dd_tag)
                if not value:
                    continue

                if key not in local_map:
                    local_map[key] = value

            has_priority_key = any(key in local_map for key in SELF_CHECK_PRIORITY_KEYS)
            if not has_priority_key:
                continue

            for key, value in local_map.items():
                if key not in extracted:
                    extracted[key] = value

        return extracted
    except Exception:
        return {}


_SITE_DESCRIPTIONS = {
    "안심결제부터 보상제도까지. 중고나라는 이제 안심할 수 있는 중고거래 플랫폼입니다.",
    "중고나라 - 안심되는 중고거래",
    "중고나라 - 국내 최대 중고마켓",
}
_UNAVAILABLE_LISTING_NOTICES = {
    "이 상품은 더 이상 판매되지 않아요.",
    "페이지를 찾을 수 없습니다.",
    "상품을 찾을 수 없습니다.",
    "존재하지 않는 상품입니다.",
    "삭제된 상품입니다.",
    "삭제된 게시글입니다.",
    "404: This page could not be found.",
    "404 Not Found",
}


def _listing_body_candidate(value):
    if not isinstance(value, str):
        return None
    # Preserve paragraph breaks; only normalize platform-specific line endings.
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = " ".join(value.split())
    if not normalized or normalized in _SITE_DESCRIPTIONS or normalized in _UNAVAILABLE_LISTING_NOTICES:
        return None
    return value


def _listing_page_unavailable(soup):
    for tag in soup.find_all(["title", "h1", "h2", "p", "span"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if text in _UNAVAILABLE_LISTING_NOTICES:
            return True
        if tag.name == "title" and re.match(r"^404(?:\s|:|$)", text, re.IGNORECASE):
            return True
    return False


def _structured_listing_products(soup):
    # Joongna serves the current listing as Product in a JSON-LD @graph.
    # Do not search arbitrary nested data: recommendation cards are other listings.
    products = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            document = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        entries = document if isinstance(document, list) else [document]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            graph = entry.get("@graph")
            nodes = [entry] + (graph if isinstance(graph, list) else [])
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_types = node.get("@type")
                node_types = node_types if isinstance(node_types, list) else [node_types]
                if "Product" in node_types and isinstance(node.get("name"), str) and node["name"].strip():
                    products.append(node)
    return products


def _page_product_id(soup):
    canonical = soup.find("link", attrs={"rel": "canonical"})
    og_url = soup.find("meta", attrs={"property": "og:url"})
    for url in (canonical.get("href") if canonical else None, og_url.get("content") if og_url else None):
        match = re.search(r"(?:^|/)product/(\d+)(?:[/?#]|$)", url or "")
        if match:
            return match.group(1)
    return None


def _product_matches_page(product, product_id):
    if product_id is None:
        return True
    identifiers = [product.get("sku"), product.get("productID")]
    if any(str(value) == product_id for value in identifiers if value is not None):
        return True
    offers = product.get("offers")
    offers = offers if isinstance(offers, dict) else {}
    for url in (product.get("url"), product.get("@id"), offers.get("url")):
        if isinstance(url, str) and re.search(r"/product/" + re.escape(product_id) + r"(?:[/?#]|$)", url):
            return True
    return False


def _extract_listing_body_from_soup(soup):
    if _listing_page_unavailable(soup):
        return None
    page_title = " ".join(soup.title.get_text(" ", strip=True).split()) if soup.title else ""
    if page_title == "중고나라" or page_title in _SITE_DESCRIPTIONS:
        return None
    for attrs in ({"name": "twitter:description"}, {"property": "og:description"}):
        for tag in soup.find_all("meta", attrs=attrs):
            body = _listing_body_candidate(tag.get("content"))
            if body is not None:
                return body

    product_id = _page_product_id(soup)
    products = [product for product in _structured_listing_products(soup) if _product_matches_page(product, product_id)]
    # Without a page identity, multiple Product objects are ambiguous.
    if len(products) == 1:
        body = _listing_body_candidate(products[0].get("description"))
        if body is not None:
            return body
    if product_id is not None or len(products) == 1:
        for tag in soup.find_all("meta", attrs={"name": "description"}):
            body = _listing_body_candidate(tag.get("content"))
            if body is not None:
                return body
    return None


def extract_listing_body_text(html):
    """Return a listing's body independently of title/price, or None if absent.

    Only listing metadata and explicit Product JSON-LD are eligible. Navigation,
    error-page text and unrelated structured descriptions must never become body.
    """
    if not isinstance(html, str) or not html.strip():
        return None
    return _extract_listing_body_from_soup(BeautifulSoup(html, "html.parser"))


def parse_joongna_listing_page(html):
    if not isinstance(html, str) or not html.strip():
        raise ValueError("HTML 내용이 비어 있습니다.")

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("meta", attrs={"name": "twitter:title"})
    title = (title_tag.get("content") if title_tag else "").strip()
    if not title:
        raise ValueError("제목 추출 실패: twitter:title meta 태그를 찾지 못했습니다.")

    description = _extract_listing_body_from_soup(soup)
    if not description:
        raise ValueError("본문 추출 실패: 상품 본문 메타데이터를 찾지 못했습니다.")

    price_text = find_price_text(soup)
    if not price_text:
        raise ValueError("가격 추출 실패: 지정 span 태그를 찾지 못했습니다.")

    try:
        listing_price_krw = parse_price_to_int(price_text)
    except ValueError as exc:
        raise ValueError(f"가격 추출 실패: {exc}") from exc

    self_check_fields = extract_self_check_fields(soup)

    return {
        "title": title,
        "description": description,
        "listing_price_krw": listing_price_krw,
        "self_check_fields": self_check_fields,
    }
