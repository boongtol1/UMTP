from db import get_connection


ALERT_THRESHOLD_RATIO = 20.0

FIXED_PRODUCT_SPEC = {
    "product_type": "MacBook Air",
    "chip": "M1",
    "screen_inch": 13,
    "ram_gb": 8,
    "ssd_gb": 256,
}


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


def read_listing_from_input():
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

    return {
        "title": title,
        "listing_price_krw": listing_price_krw,
        **FIXED_PRODUCT_SPEC,
    }


def main():
    connection = None
    cursor = None
    try:
        listing = read_listing_from_input()

        connection = get_connection()
        cursor = connection.cursor()

        fair_price_krw = fetch_fair_price(cursor, listing)
        if fair_price_krw is None:
            raise RuntimeError("해당 스펙의 공정가가 DB에 없습니다.")

        listing_price_krw = listing["listing_price_krw"]
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
