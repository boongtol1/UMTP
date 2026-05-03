from spec_parser import parse_listing_title


TEST_LISTINGS = [
    {
        "title": "맥북에어 M1 8GB 256GB 급처",
        "listing_price_krw": 430000,
    },
    {
        "title": "맥북에어 M1 8GB 256GB 상태좋음",
        "listing_price_krw": 520000,
    },
    {
        "title": "맥북에어 M1 8기가 256기가 판매",
        "listing_price_krw": 450000,
    },
    {
        "title": "맥북프로 M2 16GB 512GB 판매",
        "listing_price_krw": 900000,
    },
]

FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}

REQUIRED_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
FAIL_MESSAGE = "분석 실패: 현재 지원하지 않는 제품이거나 공정가가 없습니다."


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
    for index, listing in enumerate(TEST_LISTINGS, start=1):
        print(f"[{index}] {listing['title']}")
        parsed_spec = parse_listing_title(listing["title"])
        missing_fields = find_missing_fields(parsed_spec)

        if missing_fields:
            print(FAIL_MESSAGE)
            print()
            continue

        print_parsed_spec(parsed_spec)
        print(f"매물가: {listing['listing_price_krw']}원")
        print()


if __name__ == "__main__":
    main()
