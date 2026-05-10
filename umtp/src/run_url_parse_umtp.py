from db import get_connection
from listing_page_parser import fetch_html, parse_joongna_listing_page
from spec_parser import parse_listing_title


FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}
REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
SOURCE_NAME = "joongna"
ALERT_THRESHOLD_RATIO = 20.0


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
        url = read_listing_url()
        html = fetch_html(url)

        try:
            parsed_page = parse_joongna_listing_page(html)
        except ValueError as exc:
            print(str(exc))
            print(f"출처: {SOURCE_NAME}")
            print(f"URL: {url}")
            return

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

        listing = {
            "title": title,
            "listing_price_krw": listing_price_krw,
            **parsed_spec,
        }

        connection = get_connection()
        cursor = connection.cursor()

        fair_price_krw = fetch_fair_price(cursor, listing)
        if fair_price_krw is None:
            print("분석 실패: 공정가 조회 실패 (현재 지원하지 않는 제품이거나 공정가가 없습니다.)")
            print(f"출처: {SOURCE_NAME}")
            print(f"URL: {url}")
            return

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
        print(f"결과: {'알림 대상' if is_alert_target else '알림 대상 아님'}")
        print()
        print(f"출처: {SOURCE_NAME}")
        print(f"URL: {url}")
        print()
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
