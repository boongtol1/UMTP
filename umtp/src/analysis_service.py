from src.db import get_connection
from src.listing_page_parser import fetch_html, parse_joongna_listing_page
from src.notifier import send_alert
from src.spec_parser import parse_listing_title
from src.user_fair_price import fetch_user_fair_price


FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "screen_inch": "화면",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}
REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
SOURCE_NAME = "joongna"


def _fail(reason):
    return {"ok": False, "reason": reason}


def _find_missing_spec_fields(parsed_spec):
    return [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]


def _save_analysis_result(
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


def _build_alert_message(user_id, url, title, listing_price_krw, fair_price_krw, diff_ratio):
    return (
        f"user={user_id} 알림 대상 매물 발견 | "
        f"title={title} | listing_price={listing_price_krw}원 | "
        f"fair_price={fair_price_krw}원 | diff_ratio={round(diff_ratio, 1)}% | url={url}"
    )


def analyze_url_for_user(user_id, url):
    if not isinstance(user_id, str) or not user_id.strip():
        return _fail("user_id가 비어 있습니다.")
    if not isinstance(url, str) or not url.strip():
        return _fail("url이 비어 있습니다.")

    user_id = user_id.strip()
    url = url.strip()

    try:
        html = fetch_html(url)
    except RuntimeError as exc:
        return _fail(f"URL 요청 실패: {exc}")

    try:
        parsed_page = parse_joongna_listing_page(html)
    except ValueError as exc:
        return _fail(str(exc))

    title = parsed_page["title"]
    description = parsed_page["description"]
    listing_price_krw = parsed_page["listing_price_krw"]

    parsed_spec = parse_listing_title(f"{title} {description}")
    missing_spec_fields = _find_missing_spec_fields(parsed_spec)
    if missing_spec_fields:
        missing_labels = [FIELD_LABELS[field] for field in missing_spec_fields]
        return _fail(f"스펙 추출 실패: {', '.join(missing_labels)} 누락")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        user_fair_price = fetch_user_fair_price(cursor, user_id, parsed_spec)
        if user_fair_price is None:
            return _fail("사용자 공정가 조회 실패: 해당 user_id/스펙 조합이 없습니다.")

        fair_price_krw = user_fair_price["fair_price_krw"]
        alert_drop_rate_percent = user_fair_price["alert_drop_rate_percent"]
        if fair_price_krw <= 0:
            return _fail("사용자 공정가 조회 실패: 공정가가 0보다 커야 합니다.")

        diff_amount_krw = fair_price_krw - listing_price_krw
        diff_ratio = (diff_amount_krw / fair_price_krw) * 100
        is_alert_target = diff_ratio >= alert_drop_rate_percent

        listing = {
            "title": title,
            "listing_price_krw": listing_price_krw,
            **parsed_spec,
        }
        _save_analysis_result(
            cursor,
            listing,
            fair_price_krw,
            diff_amount_krw,
            diff_ratio,
            is_alert_target,
        )
        connection.commit()

        message = "알림 대상" if is_alert_target else "알림 대상 아님"
        if is_alert_target:
            send_alert(
                _build_alert_message(
                    user_id=user_id,
                    url=url,
                    title=title,
                    listing_price_krw=listing_price_krw,
                    fair_price_krw=fair_price_krw,
                    diff_ratio=diff_ratio,
                )
            )

        return {
            "ok": True,
            "user_id": user_id,
            "url": url,
            "source": SOURCE_NAME,
            "title": title,
            "listing_price_krw": listing_price_krw,
            "fair_price_krw": fair_price_krw,
            "diff_amount_krw": diff_amount_krw,
            "diff_ratio": round(diff_ratio, 1),
            "alert_drop_rate_percent": alert_drop_rate_percent,
            "is_alert_target": is_alert_target,
            "message": message,
        }
    except Exception as exc:
        return _fail(f"분석 처리 실패: {exc}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
