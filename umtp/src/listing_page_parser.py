import re

import requests


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
