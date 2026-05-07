import json
from pathlib import Path


JSON_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_crawled_listings.json"
REQUIRED_FIELDS = ("title", "listing_price_krw", "source", "url")


def load_crawled_listings(json_path):
    with json_path.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError("JSON 루트는 매물 객체 리스트여야 합니다.")

    return data


def main():
    try:
        listings = load_crawled_listings(JSON_FILE_PATH)

        for index, listing in enumerate(listings, start=1):
            missing_fields = [field for field in REQUIRED_FIELDS if field not in listing]
            if missing_fields:
                print(f"[{index}] 분석 실패: JSON 필드 누락 ({', '.join(missing_fields)})")
                print()
                continue

            title = listing["title"]
            listing_price_krw = listing["listing_price_krw"]
            source = listing["source"]
            url = listing["url"]

            print(f"[{index}] {title}")
            print(f"매물가: {listing_price_krw}원")
            print(f"출처: {source}")
            print(f"URL: {url}")
            print()
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
