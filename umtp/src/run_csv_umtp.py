import csv
from pathlib import Path

from spec_parser import parse_listing_title

CSV_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_listings.csv"
REQUIRED_COLUMNS = ("title", "listing_price_krw")
REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}


def iter_csv_rows(csv_path):
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        header = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing_columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {', '.join(missing_columns)}")

        for index, row in enumerate(reader, start=1):
            title = (row.get("title") or "").strip()
            listing_price_krw = (row.get("listing_price_krw") or "").strip()
            yield index, title, listing_price_krw


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
        for index, title, listing_price_krw in iter_csv_rows(CSV_FILE_PATH):
            print(f"[{index}] {title}")
            print(f"매물가: {listing_price_krw}원")

            parsed_spec = parse_listing_title(title)
            missing_spec_fields = find_missing_spec_fields(parsed_spec)
            if missing_spec_fields:
                missing_labels = [FIELD_LABELS[field] for field in missing_spec_fields]
                print(f"분석 실패: 제목 스펙 추출 실패 ({', '.join(missing_labels)} 누락)")
                print("DB 저장 안 함")
                print()
                continue

            print_parsed_spec(parsed_spec)
            print()
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
