from src.analysis_log import save_failed_log, save_success_log
from src.db import get_connection
from src.listing_page_parser import fetch_html, parse_joongna_listing_page
from src.spec_parser import parse_listing_title
from src.telegram_notifier import send_telegram_alert
from src.url_history import find_existing_url_record, save_duplicate_url_record
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
INVALID_UNIT_REASON = "invalid_macbook_air_unit"


def _find_missing_spec_fields(parsed_spec):
    return [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]


def _save_listing_analysis_result(
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


def _build_telegram_message(title, listing_price_krw, fair_price_krw, diff_ratio, url):
    return (
        "[UMTP 알림]\n"
        f"{title}\n\n"
        f"가격: {listing_price_krw:,}원\n"
        f"공정가: {fair_price_krw:,}원\n"
        f"저평가율: {round(diff_ratio, 1)}%\n\n"
        "URL:\n"
        f"{url}"
    )


def _build_failed_response(url, reason, *, unit_valid=None, unit_validation_reason=None):
    response = {
        "ok": False,
        "status": "failed",
        "url": url,
        "reason": reason,
    }
    response["unit_valid"] = unit_valid
    response["unit_validation_reason"] = unit_validation_reason
    return response


def analyze_url_for_user(user_id, url):
    if not isinstance(user_id, str) or not user_id.strip():
        return _build_failed_response(url if isinstance(url, str) else "", "user_id가 비어 있습니다.")
    if not isinstance(url, str) or not url.strip():
        return _build_failed_response("", "url이 비어 있습니다.")

    user_id = user_id.strip()
    url = url.strip()

    connection = None
    cursor = None
    title = None
    listing_price_krw = None
    parsed_spec = {}

    unit_valid = None
    unit_validation_reason = None

    def fail(reason, *, source=None):
        if connection is not None and cursor is not None:
            try:
                save_failed_log(
                    cursor,
                    user_id=user_id,
                    url=url,
                    reason=reason,
                    source=source,
                    title=title,
                    listing_price_krw=listing_price_krw,
                    parsed_spec=parsed_spec,
                )
                connection.commit()
            except Exception as log_exc:
                print(f"실패 로그 저장 실패: {log_exc}")
        return _build_failed_response(
            url,
            reason,
            unit_valid=unit_valid,
            unit_validation_reason=unit_validation_reason,
        )

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
        except Exception as exc:
            return _build_failed_response(url, f"DB 연결 실패: {exc}")

        existing = find_existing_url_record(cursor, user_id, url)
        if existing:
            try:
                save_duplicate_url_record(cursor, user_id, url, source=SOURCE_NAME, reason="이미 분석된 URL")
                connection.commit()
            except Exception as dup_exc:
                print(f"중복 로그 저장 실패: {dup_exc}")

            return {
                "ok": True,
                "status": "duplicate",
                "url": url,
                "unit_valid": None,
                "unit_validation_reason": None,
                "telegram_sent": False,
                "message": "이미 분석된 URL",
            }

        try:
            html = fetch_html(url)
        except RuntimeError as exc:
            return fail(f"URL 요청 실패: {exc}", source=SOURCE_NAME)

        try:
            parsed_page = parse_joongna_listing_page(html)
        except ValueError as exc:
            return fail(str(exc), source=SOURCE_NAME)

        title = parsed_page["title"]
        description = parsed_page["description"]
        listing_price_krw = parsed_page["listing_price_krw"]

        parsed_spec = parse_listing_title(f"{title} {description}")
        unit_valid = parsed_spec.get("unit_valid")
        unit_validation_reason = parsed_spec.get("unit_validation_reason")

        if unit_validation_reason == INVALID_UNIT_REASON:
            return fail("유효하지 않은 MacBook Air 조합", source=SOURCE_NAME)

        if not parsed_spec.get("parse_success", False):
            missing_spec_fields = _find_missing_spec_fields(parsed_spec)
            missing_labels = [FIELD_LABELS[field] for field in missing_spec_fields]
            return fail(f"스펙 추출 실패: {', '.join(missing_labels)} 누락", source=SOURCE_NAME)

        missing_spec_fields = _find_missing_spec_fields(parsed_spec)
        if missing_spec_fields:
            missing_labels = [FIELD_LABELS[field] for field in missing_spec_fields]
            return fail(f"스펙 추출 실패: {', '.join(missing_labels)} 누락", source=SOURCE_NAME)

        user_fair_price = fetch_user_fair_price(cursor, user_id, parsed_spec)
        if user_fair_price is None:
            return fail("사용자 공정가 조회 실패: 해당 user_id/스펙 조합이 없습니다.", source=SOURCE_NAME)

        fair_price_krw = user_fair_price["fair_price_krw"]
        if fair_price_krw <= 0:
            return fail("사용자 공정가 조회 실패: 공정가가 0보다 커야 합니다.", source=SOURCE_NAME)

        diff_amount_krw = fair_price_krw - listing_price_krw
        diff_ratio = (diff_amount_krw / fair_price_krw) * 100
        is_alert_target = diff_ratio >= user_fair_price["alert_drop_rate_percent"]

        listing = {
            "title": title,
            "listing_price_krw": listing_price_krw,
            **parsed_spec,
        }
        _save_listing_analysis_result(
            cursor,
            listing,
            fair_price_krw,
            diff_amount_krw,
            diff_ratio,
            is_alert_target,
        )
        save_success_log(
            cursor,
            user_id=user_id,
            url=url,
            source=SOURCE_NAME,
            title=title,
            listing_price_krw=listing_price_krw,
            parsed_spec=parsed_spec,
            fair_price_krw=fair_price_krw,
            diff_ratio=diff_ratio,
            is_alert_target=is_alert_target,
        )
        connection.commit()

        telegram_sent = False
        message = "알림 대상 아님"
        if is_alert_target:
            message = "알림 대상"
            telegram_sent = send_telegram_alert(
                _build_telegram_message(
                    title=title,
                    listing_price_krw=listing_price_krw,
                    fair_price_krw=fair_price_krw,
                    diff_ratio=diff_ratio,
                    url=url,
                )
            )

        return {
            "ok": True,
            "status": "success",
            "user_id": user_id,
            "url": url,
            "title": title,
            "product_type": parsed_spec["product_type"],
            "chip": parsed_spec["chip"],
            "screen_inch": parsed_spec["screen_inch"],
            "ram_gb": parsed_spec["ram_gb"],
            "ssd_gb": parsed_spec["ssd_gb"],
            "unit_valid": True,
            "unit_validation_reason": None,
            "listing_price_krw": listing_price_krw,
            "fair_price_krw": fair_price_krw,
            "diff_amount_krw": diff_amount_krw,
            "diff_ratio": round(diff_ratio, 1),
            "is_alert_target": is_alert_target,
            "telegram_sent": telegram_sent,
            "message": message,
        }
    except Exception as exc:
        return fail(f"분석 처리 실패: {exc}", source=SOURCE_NAME)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
