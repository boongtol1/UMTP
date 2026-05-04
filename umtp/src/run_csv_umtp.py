import csv
from pathlib import Path

from db import get_connection
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
ALERT_THRESHOLD_RATIO = 20.0


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


def parse_listing_price(raw_price):
    cleaned_price = raw_price.replace(",", "")
    try:
        listing_price_krw = int(cleaned_price)
    except ValueError as exc:
        raise ValueError("매물 가격은 숫자여야 합니다.") from exc

    if listing_price_krw <= 0:
        raise ValueError("매물 가격은 0보다 커야 합니다.")

    return listing_price_krw


def find_missing_spec_fields(parsed_spec):
    return [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]


def fetch_fair_price(cursor, listing):
    cursor.execute(
        """
        SELECT fair_price_krw
        FROM mac_fair_prices
        WHERE product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
        (
            listing["product_type"],
            listing["chip"],
            listing["screen_inch"],
            listing["ram_gb"],
            listing["ssd_gb"],
        ),
    )
    row = cursor.fetchone()
    return int(row[0]) if row else None


def save_analysis_result(
    cursor,
    listing,
    fair_price_krw,
    diff_amount_krw,
    diff_ratio,
    is_alert_target,
):
    cursor.execute(
        """
        INSERT INTO listing_analysis_results (
            title,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            listing_price_krw,
            fair_price_krw,
            diff_amount_krw,
            diff_ratio,
            is_alert_target
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            listing["title"],
            listing["product_type"],
            listing["chip"],
            listing["screen_inch"],
            listing["ram_gb"],
            listing["ssd_gb"],
            listing["listing_price_krw"],
            fair_price_krw,
            diff_amount_krw,
            round(diff_ratio, 2),
            is_alert_target,
        ),
    )


def main():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        for index, title, raw_price in iter_csv_rows(CSV_FILE_PATH):
            print(f"[{index}] {title}")

            try:
                listing_price_krw = parse_listing_price(raw_price)
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

            listing = {
                "title": title,
                "listing_price_krw": listing_price_krw,
                **parsed_spec,
            }
            fair_price_krw = fetch_fair_price(cursor, listing)

            if fair_price_krw is None:
                print("분석 실패: 공정가 조회 실패 (현재 지원하지 않는 제품이거나 공정가가 없습니다.)")
                print("DB 저장 안 함")
                print()
                continue

            diff_amount_krw = fair_price_krw - listing_price_krw
            diff_ratio = (diff_amount_krw / fair_price_krw) * 100
            is_alert_target = diff_ratio >= ALERT_THRESHOLD_RATIO

            save_analysis_result(
                cursor,
                listing,
                fair_price_krw,
                diff_amount_krw,
                diff_ratio,
                is_alert_target,
            )
            connection.commit()

            print(f"공정가: {fair_price_krw}원")
            print(f"매물가: {listing_price_krw}원")
            print(f"차이금액: {diff_amount_krw}원")
            print(f"차이비율: {round(diff_ratio, 1)}%")
            print(f"결과: {'알림 대상' if is_alert_target else '알림 대상 아님'}")
            print("DB 저장 완료")
            print()

    except Exception as exc:
        print(f"오류: {exc}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
