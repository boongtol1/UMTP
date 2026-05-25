from datetime import datetime

from src.resale_trade_journeys import upsert_resale_trade_after_purchase


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
    print("[UMTP] 되팔이 - 구매 후 입력")
    user_id = _ask_optional_text("user_id(옵션)")
    source = _ask_optional_text("source(기본 joongna)") or "joongna"
    product_id = _ask_optional_text("product_id(없으면 URL에서 추출)")
    url = _ask_optional_text("url(옵션)")

    purchase_contact_record = _ask_optional_text("연락처 기록")
    purchase_conversation_text = _ask_optional_text("대화내용 기록")
    purchase_account_number = _ask_optional_text("계좌번호")
    contacted_at = _ask_optional_datetime("판매자 연락 시각")
    seller_response_at = _ask_optional_datetime("판매자 답변 시각")
    purchased_at = _ask_optional_datetime("구매 시각")
    purchase_price_krw = _ask_optional_int("구매 금액")
    purchase_method = _ask_optional_text("구매 방식(직거래/택배)")
    purchase_location = _ask_optional_text("구매 장소")
    transport_cost_krw = _ask_optional_int("이동비")
    shipping_cost_krw = _ask_optional_int("배송비")
    payment_method = _ask_optional_text("결제 수단")
    money_sent_at = _ask_optional_datetime("돈 보낸 시각")
    inspection_notes = _ask_optional_text("검수 메모")
    final_result_notes = _ask_optional_text("최종 메모")

    payload = {
        "user_id": user_id,
        "source": source,
        "product_id": product_id,
        "url": url,
        "purchase_contact_record": purchase_contact_record,
        "purchase_conversation_text": purchase_conversation_text,
        "purchase_account_number": purchase_account_number,
        "contacted_at": contacted_at,
        "seller_response_at": seller_response_at,
        "purchased_at": purchased_at,
        "purchase_price_krw": purchase_price_krw,
        "purchase_method": purchase_method,
        "purchase_location": purchase_location,
        "transport_cost_krw": transport_cost_krw,
        "shipping_cost_krw": shipping_cost_krw,
        "payment_method": payment_method,
        "money_sent_at": money_sent_at,
        "inspection_notes": inspection_notes,
        "final_result_notes": final_result_notes,
    }

    payload = {key: value for key, value in payload.items() if value is not None}

    result = upsert_resale_trade_after_purchase(**payload)

    print("\n저장 결과")
    print(f"ok: {result.get('ok')}")
    print(f"id: {result.get('id')}")
    print(f"stage: {result.get('current_stage')}")
    print(f"product_id: {result.get('product_id')}")
    print(f"url: {result.get('url')}")


if __name__ == "__main__":
    main()
