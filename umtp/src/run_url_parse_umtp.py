from listing_page_parser import fetch_html, parse_joongna_listing_page
from spec_parser import parse_listing_title


FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}
REQUIRED_SPEC_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
SOURCE_NAME = "joongna"


def read_listing_url():
    url = input("매물 URL 입력: ").strip()
    if not url:
        raise ValueError("URL 입력값이 비어 있습니다.")
    return url


def find_missing_spec_fields(parsed_spec):
    return [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]


def print_parsed_spec(parsed_spec):
    print("추출된 스펙:")
    print(f"{FIELD_LABELS['product_type']}: {parsed_spec['product_type']}")
    print(f"{FIELD_LABELS['chip']}: {parsed_spec['chip']}")
    print(f"{FIELD_LABELS['screen_inch']}: {parsed_spec['screen_inch']}인치")
    print(f"{FIELD_LABELS['ram_gb']}: {parsed_spec['ram_gb']}GB")
    print(f"{FIELD_LABELS['ssd_gb']}: {parsed_spec['ssd_gb']}GB")


def main():
    try:
        url = read_listing_url()
        html = fetch_html(url)
        parsed_page = parse_joongna_listing_page(html)

        title = parsed_page["title"]
        description = parsed_page["description"]
        listing_price_krw = parsed_page["listing_price_krw"]

        print()
        print("추출된 제목:")
        print(title)
        print()
        print("추출된 본문:")
        print(description)
        print()
        print("추출된 가격:")
        print(f"{listing_price_krw}원")
        print()

        parsed_spec = parse_listing_title(f"{title} {description}")
        missing_fields = find_missing_spec_fields(parsed_spec)
        if missing_fields:
            missing_labels = [FIELD_LABELS[field] for field in missing_fields]
            print(f"분석 실패: 제목+본문 스펙 추출 실패 ({', '.join(missing_labels)} 누락)")
            print(f"출처: {SOURCE_NAME}")
            print(f"URL: {url}")
            return

        print_parsed_spec(parsed_spec)
        print()
        print(f"출처: {SOURCE_NAME}")
        print(f"URL: {url}")
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
