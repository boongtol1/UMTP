from datetime import datetime

from src.resale_trade_journeys import upsert_resale_trade_after_resale


def _ask_optional_text(label):
    value = input(f"{label}: ").strip()
    return value or None


def _ask_optional_int(label):
    value = input(f"{label}: ").strip().replace(",", "")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{label}는 숫자로 입력해야 합니다.")


def _ask_optional_datetime(label):
    value = input(f"{label} (YYYY-MM-DD HH:MM, 비우면 스킵): ").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"{label} 형식이 올바르지 않습니다.")


def main():
    print("[UMTP] 되팔이 - 판매 후 입력")
    user_id = _ask_optional_text("user_id(옵션)")
    source = _ask_optional_text("source(기본 joongna)") or "joongna"
    product_id = _ask_optional_text("product_id(없으면 URL에서 추출)")
    url = _ask_optional_text("url(옵션)")
    resale_listing_price_krw = _ask_optional_int("되팔이 게시가")
    resale_platform = _ask_optional_text("되팔이 플랫폼")
    resale_url = _ask_optional_text("되팔이 URL")

    sold_at = _ask_optional_datetime("판매 완료 시각")
    sale_price_krw = _ask_optional_int("최종 판매 금액")
    sale_method = _ask_optional_text("판매 방식(직거래/택배)")
    sale_location = _ask_optional_text("판매 장소")
    sale_platform = _ask_optional_text("판매 플랫폼")

    payload = {
        "user_id": user_id,
        "source": source,
        "product_id": product_id,
        "url": url,
        "resale_listing_price_krw": resale_listing_price_krw,
        "resale_platform": resale_platform,
        "resale_url": resale_url,
        "sold_at": sold_at,
        "sale_price_krw": sale_price_krw,
        "sale_method": sale_method,
        "sale_location": sale_location,
        "sale_platform": sale_platform,
    }

    payload = {key: value for key, value in payload.items() if value is not None}

    result = upsert_resale_trade_after_resale(**payload)

    print("\n저장 결과")
    print(f"ok: {result.get('ok')}")
    print(f"id: {result.get('id')}")
    print(f"stage: {result.get('current_stage')}")
    print(f"product_id: {result.get('product_id')}")
    print(f"url: {result.get('url')}")


if __name__ == "__main__":
    main()
