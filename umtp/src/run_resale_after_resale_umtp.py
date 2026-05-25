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
    contact_record = _ask_optional_text("연락처 기록")
    conversation_text = _ask_optional_text("대화내용 기록")
    money_sent_at = _ask_optional_datetime("돈 보낸 시각")
    money_received_at = _ask_optional_datetime("돈 들어온 시각")
    account_number = _ask_optional_text("계좌번호")

    view_count = _ask_optional_int("조회수")
    favorite_count = _ask_optional_int("찜수")
    inquiry_count = _ask_optional_int("문의수")
    first_inquiry_at = _ask_optional_datetime("첫 문의 시각")
    negotiation_count = _ask_optional_int("네고 횟수")
    price_drop_count = _ask_optional_int("가격 인하 횟수")

    sold_at = _ask_optional_datetime("판매 완료 시각")
    sale_price_krw = _ask_optional_int("최종 판매 금액")
    sale_method = _ask_optional_text("판매 방식(직거래/택배)")
    sale_location = _ask_optional_text("판매 장소")
    final_shipping_cost_krw = _ask_optional_int("최종 배송비")
    platform_fee_krw = _ask_optional_int("플랫폼 수수료")
    refund_or_claim = _ask_optional_text("환불/클레임 여부")
    final_result_notes = _ask_optional_text("최종 정산 메모")

    payload = {
        "user_id": user_id,
        "source": source,
        "product_id": product_id,
        "url": url,
        "contact_record": contact_record,
        "conversation_text": conversation_text,
        "money_sent_at": money_sent_at,
        "money_received_at": money_received_at,
        "account_number": account_number,
        "view_count": view_count,
        "favorite_count": favorite_count,
        "inquiry_count": inquiry_count,
        "first_inquiry_at": first_inquiry_at,
        "negotiation_count": negotiation_count,
        "price_drop_count": price_drop_count,
        "sold_at": sold_at,
        "sale_price_krw": sale_price_krw,
        "sale_method": sale_method,
        "sale_location": sale_location,
        "final_shipping_cost_krw": final_shipping_cost_krw,
        "platform_fee_krw": platform_fee_krw,
        "refund_or_claim": refund_or_claim,
        "final_result_notes": final_result_notes,
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
