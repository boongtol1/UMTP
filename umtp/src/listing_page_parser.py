import re

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
SELF_CHECK_PRIORITY_KEYS = ("모델명", "램 용량", "SSD용량", "CPU종류", "컬러")
SELF_CHECK_IGNORED_TOKENS = ("스펙보기",)


def fetch_html(url):
    try:
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


def parse_joongna_listing_page(html):
    if not isinstance(html, str) or not html.strip():
        raise ValueError("HTML 내용이 비어 있습니다.")

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("meta", attrs={"name": "twitter:title"})
    title = (title_tag.get("content") if title_tag else "").strip()
    if not title:
        raise ValueError("제목 추출 실패: twitter:title meta 태그를 찾지 못했습니다.")

    description_tag = soup.find("meta", attrs={"name": "twitter:description"})
    description = (description_tag.get("content") if description_tag else "").strip()
    if not description:
        raise ValueError("본문 추출 실패: twitter:description meta 태그를 찾지 못했습니다.")

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
