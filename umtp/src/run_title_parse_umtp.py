from db import get_connection
from spec_parser import parse_listing_title


FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}

REQUIRED_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
ALERT_THRESHOLD_RATIO = 20.0


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
        title, listing_price_krw = read_listing_input()
        parsed_spec = parse_listing_title(title)

        missing_fields = find_missing_fields(parsed_spec)
        if missing_fields:
            missing_labels = [FIELD_LABELS[field] for field in missing_fields]
            print(f"스펙 추출 실패 항목: {', '.join(missing_labels)}")
            return

        print_parsed_spec(parsed_spec)
        listing = {
            "title": title,
            "listing_price_krw": listing_price_krw,
            **parsed_spec,
        }

        connection = get_connection()
        cursor = connection.cursor()

        fair_price_krw = fetch_fair_price(cursor, listing)
        if fair_price_krw is None:
            raise RuntimeError("해당 스펙의 공정가가 DB에 없습니다.")

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

        print()
        print(f"공정가: {fair_price_krw}원")
        print(f"매물가: {listing_price_krw}원")
        print(f"차이금액: {diff_amount_krw}원")
        print(f"차이비율: {round(diff_ratio, 1)}%")
        print(f"결과: {'알림 대상' if is_alert_target else '알림 아님'}")
        print("DB 저장 완료")
    except Exception as exc:
        print(f"오류: {exc}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
