from spec_parser import parse_listing_title


FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}

REQUIRED_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")


def read_listing_input():
    title = input("매물 제목 입력: ").strip()
    if not title:
        raise ValueError("매물 제목은 비어 있을 수 없습니다.")

    raw_price = input("매물 가격 입력: ").strip().replace(",", "")
    try:
        listing_price_krw = int(raw_price)
    except ValueError as exc:
        raise ValueError("매물 가격은 숫자로 입력해야 합니다.") from exc

    if listing_price_krw <= 0:
        raise ValueError("매물 가격은 0보다 커야 합니다.")

    return title, listing_price_krw


def find_missing_fields(parsed_spec):
    return [field for field in REQUIRED_FIELDS if parsed_spec[field] is None]


def print_parsed_spec(parsed_spec):
    print("추출된 스펙:")
    print(f"{FIELD_LABELS['product_type']}: {parsed_spec['product_type']}")
    print(f"{FIELD_LABELS['chip']}: {parsed_spec['chip']}")
    print(f"{FIELD_LABELS['screen_inch']}: {parsed_spec['screen_inch']}인치")
    print(f"{FIELD_LABELS['ram_gb']}: {parsed_spec['ram_gb']}GB")
    print(f"{FIELD_LABELS['ssd_gb']}: {parsed_spec['ssd_gb']}GB")


def main():
    try:
        title, listing_price_krw = read_listing_input()
        parsed_spec = parse_listing_title(title)

        missing_fields = find_missing_fields(parsed_spec)
        if missing_fields:
            missing_labels = [FIELD_LABELS[field] for field in missing_fields]
            print(f"스펙 추출 실패 항목: {', '.join(missing_labels)}")
            return

        print_parsed_spec(parsed_spec)
        print()
        print(f"입력 매물가: {listing_price_krw}원")
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
