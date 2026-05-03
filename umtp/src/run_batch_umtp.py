from db import get_connection
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

REQUIRED_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
FAIL_MESSAGE = "분석 실패: 현재 지원하지 않는 제품이거나 공정가가 없습니다."
ALERT_THRESHOLD_RATIO = 20.0


def find_missing_fields(parsed_spec):
    return [field for field in REQUIRED_FIELDS if parsed_spec[field] is None]


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
        total_count = len(TEST_LISTINGS)
        db_saved_count = 0
        alert_target_count = 0

        for index, listing in enumerate(TEST_LISTINGS, start=1):
            print(f"[{index}] {listing['title']}")
            parsed_spec = parse_listing_title(listing["title"])
            missing_fields = find_missing_fields(parsed_spec)

            if missing_fields:
                print(FAIL_MESSAGE)
                print()
                continue

            analyzed_listing = {**listing, **parsed_spec}
            fair_price_krw = fetch_fair_price(cursor, analyzed_listing)
            if fair_price_krw is None:
                print(FAIL_MESSAGE)
                print()
                continue

            listing_price_krw = analyzed_listing["listing_price_krw"]
            diff_amount_krw = fair_price_krw - listing_price_krw
            diff_ratio = (diff_amount_krw / fair_price_krw) * 100
            is_alert_target = diff_ratio >= ALERT_THRESHOLD_RATIO

            save_analysis_result(
                cursor,
                analyzed_listing,
                fair_price_krw,
                diff_amount_krw,
                diff_ratio,
                is_alert_target,
            )
            connection.commit()
            db_saved_count += 1
            if is_alert_target:
                alert_target_count += 1

            print(f"공정가: {fair_price_krw}원")
            print(f"매물가: {listing_price_krw}원")
            print(f"차이금액: {diff_amount_krw}원")
            print(f"차이비율: {round(diff_ratio, 1)}%")
            print(f"결과: {'알림 대상' if is_alert_target else '알림 대상 아님'}")
            print("DB 저장 완료")
            print()

        print("요약:")
        print(f"전체 매물: {total_count}개")
        print(f"DB 저장 성공: {db_saved_count}개")
        print(f"알림 대상: {alert_target_count}개")
    except Exception as exc:
        print(f"오류: {exc}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
