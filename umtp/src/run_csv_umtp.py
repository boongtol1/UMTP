import csv
from pathlib import Path


CSV_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_listings.csv"
REQUIRED_COLUMNS = ("title", "listing_price_krw")


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


def main():
    try:
        for index, title, listing_price_krw in iter_csv_rows(CSV_FILE_PATH):
            print(f"[{index}] title: {title}")
            print(f"listing_price_krw: {listing_price_krw}")
            print()
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
