import json
from pathlib import Path

from spec_parser import parse_listing_title


JSON_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_crawled_listings.json"
REQUIRED_JSON_FIELDS = ("title", "listing_price_krw", "source", "url")
REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}


def load_crawled_listings(json_path):
    with json_path.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError("JSON 루트는 매물 객체 리스트여야 합니다.")

    return data


def parse_listing_price(raw_price):
    if isinstance(raw_price, bool):
        raise ValueError("매물 가격은 숫자여야 합니다.")

    if isinstance(raw_price, int):
        listing_price_krw = raw_price
    elif isinstance(raw_price, str):
        cleaned_price = raw_price.strip().replace(",", "")
        try:
            listing_price_krw = int(cleaned_price)
        except ValueError as exc:
            raise ValueError("매물 가격은 숫자여야 합니다.") from exc
    else:
        raise ValueError("매물 가격은 숫자여야 합니다.")

    if listing_price_krw <= 0:
        raise ValueError("매물 가격은 0보다 커야 합니다.")

    return listing_price_krw


def find_missing_spec_fields(parsed_spec):
    return [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]


def main():
    try:
        listings = load_crawled_listings(JSON_FILE_PATH)

        for index, listing in enumerate(listings, start=1):
            missing_json_fields = [field for field in REQUIRED_JSON_FIELDS if field not in listing]
            if missing_json_fields:
                print(f"[{index}] 분석 실패: JSON 필드 누락 ({', '.join(missing_json_fields)})")
                print("DB 저장 안 함")
                print()
                continue

            title = str(listing["title"]).strip()
            source = str(listing["source"]).strip()
            url = str(listing["url"]).strip()

            print(f"[{index}] {title}")
            print(f"출처: {source}")
            print(f"URL: {url}")

            try:
                listing_price_krw = parse_listing_price(listing["listing_price_krw"])
            except ValueError as exc:
                print(f"분석 실패: {exc}")
                print("DB 저장 안 함")
                print()
                continue

            parsed_spec = parse_listing_title(title)
            missing_spec_fields = find_missing_spec_fields(parsed_spec)

            if missing_spec_fields:
                missing_labels = [FIELD_LABELS[field] for field in missing_spec_fields]
                print(f"분석 실패: 제목 스펙 추출 실패 ({', '.join(missing_labels)} 누락)")
                print("DB 저장 안 함")
                print()
                continue

            print("추출 스펙:")
            print(f"- 제품: {parsed_spec['product_type']}")
            print(f"- 칩: {parsed_spec['chip']}")
            print(f"- 화면: {parsed_spec['screen_inch']}인치")
            print(f"- RAM: {parsed_spec['ram_gb']}GB")
            print(f"- SSD: {parsed_spec['ssd_gb']}GB")
            print(f"매물가: {listing_price_krw}원")
            print("DB 저장 안 함 (다음 단계에서 DB 연동 예정)")
            print()
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
