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

    return {
        "title": title,
        "description": description,
        "listing_price_krw": listing_price_krw,
    }
