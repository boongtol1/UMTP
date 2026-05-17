from src.analysis_log import save_failed_log, save_success_log
from src.alert_price_direction import (
    DEFAULT_ALERT_PRICE_DIRECTION,
    compute_target_buy_price_krw,
    is_listing_alert_match,
    passes_price_bounds,
    is_valid_alert_drop_rate_percent,
    normalize_alert_price_direction,
)
from src.db import get_connection
from src.listing_page_parser import fetch_html, parse_joongna_listing_page
from src.risk_analyzer import analyze_risk
from src.spec_parser import parse_listing_title
from src.telegram_notifier import send_telegram_alert
from src.url_history import find_existing_url_record, save_duplicate_url_record
from src.user_alert_settings import resolve_user_alert_delivery_policy
from src.user_fair_price import fetch_user_fair_price


FIELD_LABELS = {
    "product_type": "제품",
    "chip": "칩",
    "ram_gb": "RAM",
    "ssd_gb": "SSD",
}
REQUIRED_SPEC_FIELDS = ("product_type", "chip", "ram_gb", "ssd_gb")
SOURCE_NAME = "joongna"
INVALID_UNIT_REASON = "invalid_macbook_air_unit"


def _default_risk_result():
    return {
        "risk_detected": False,
        "risk_level": "none",
        "risk_score": 0,
        "risk_keywords": [],
        "risk_categories": {},
        "is_exchange_post": False,
        "exchange_strength": "none",
        "exchange_keywords": [],
        "trade_type": "sale",
    }


def _find_missing_spec_fields(parsed_spec):
    missing_fields = parsed_spec.get("missing_fields")
    if isinstance(missing_fields, list):
        return missing_fields
    return [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]


def _save_listing_analysis_result(
    cursor,
    listing,
    fair_price_krw,
    diff_amount_krw,
    diff_ratio,
    is_alert_target,
):
    try:
        cursor.execute(
            """
            INSERT INTO listing_analysis_results (
                title,
                body_text,
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                listing["title"],
                listing.get("body_text"),
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
        return
    except Exception as exc:
        if "Unknown column" not in str(exc):
            raise

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


def _build_telegram_message(
    title,
    listing_price_krw,
    fair_price_krw,
    diff_ratio,
    url,
    risk_result,
    *,
    screen_inch_defaulted=False,
):
    risk_level = risk_result.get("risk_level", "none")
    is_exchange_post = bool(risk_result.get("is_exchange_post", False))

    prefix_parts = ["[UMTP 알림]"]
    if risk_level in {"medium", "high", "exclude"}:
        prefix_parts.append("[주의 필요]")
    if risk_level == "exclude":
        prefix_parts.append("[제외급 위험]")
    if is_exchange_post:
        prefix_parts.append("[교환글]")
    header = "".join(prefix_parts)

    defaulted_message = ""
    if screen_inch_defaulted:
        defaulted_message = "화면 크기: 13인치 기본값 사용\n"

    exclude_notice = ""
    if risk_level == "exclude":
        exclude_notice = "정상 현금 판매 매물로 보기 어려울 수 있음\n"

    exchange_notice = ""
    if is_exchange_post:
        exchange_notice = "현금 판매가 아닌 교환글일 수 있음\n"

    return (
        f"{header}\n"
        f"{title}\n\n"
        f"가격: {listing_price_krw:,}원\n"
        f"공정가: {fair_price_krw:,}원\n"
        f"저평가율: {round(diff_ratio, 1)}%\n"
        f"위험도: {risk_result.get('risk_level', 'none')}\n"
        f"위험 점수: {risk_result.get('risk_score', 0)}\n"
        f"위험 키워드: {', '.join(risk_result.get('risk_keywords', [])) or '-'}\n"
        f"교환 키워드: {', '.join(risk_result.get('exchange_keywords', [])) or '-'}\n"
        f"{defaulted_message}\n"
        f"{exclude_notice}"
        f"{exchange_notice}\n"
        "URL:\n"
        f"{url}"
    )


def _build_parse_failure_reason(parsed_spec):
    unit_validation_reason = parsed_spec.get("unit_validation_reason")
    missing_fields = _find_missing_spec_fields(parsed_spec)

    if unit_validation_reason == INVALID_UNIT_REASON:
        return "유효하지 않은 MacBook Air 조합"

    if missing_fields:
        return f"스펙 추출 실패: {', '.join(missing_fields)}"

    if unit_validation_reason:
        return f"스펙 추출 실패: {unit_validation_reason}"

    return "스펙 추출 실패"


def _build_failed_response(url, reason, *, parsed_spec=None, self_check_fields=None, risk_result=None, body_text=None):
    parsed_spec = parsed_spec or {}
    risk_result = risk_result or _default_risk_result()
    return {
        "ok": False,
        "status": "failed",
        "url": url,
        "reason": reason,
        "parse_success": parsed_spec.get("parse_success", False),
        "missing_fields": _find_missing_spec_fields(parsed_spec),
        "product_type": parsed_spec.get("product_type"),
        "chip": parsed_spec.get("chip"),
        "screen_inch": parsed_spec.get("screen_inch"),
        "screen_inch_defaulted": parsed_spec.get("screen_inch_defaulted"),
        "ram_gb": parsed_spec.get("ram_gb"),
        "ssd_gb": parsed_spec.get("ssd_gb"),
        "confidence_score": parsed_spec.get("confidence_score"),
        "unit_valid": parsed_spec.get("unit_valid"),
        "unit_validation_reason": parsed_spec.get("unit_validation_reason"),
        "self_check_fields": self_check_fields or {},
        "detected_patterns": parsed_spec.get("detected_patterns", {}),
        "detected_conflicts": parsed_spec.get("detected_conflicts", []),
        "risk_detected": risk_result.get("risk_detected", False),
        "risk_level": risk_result.get("risk_level", "none"),
        "risk_score": risk_result.get("risk_score", 0),
        "risk_keywords": risk_result.get("risk_keywords", []),
        "risk_categories": risk_result.get("risk_categories", {}),
        "is_exchange_post": risk_result.get("is_exchange_post", False),
        "exchange_strength": risk_result.get("exchange_strength", "none"),
        "exchange_keywords": risk_result.get("exchange_keywords", []),
        "trade_type": risk_result.get("trade_type", "sale"),
        "body_text": body_text,
        "telegram_sent": False,
    }


def analyze_url_for_user(
    user_id,
    url,
    *,
    force_reanalyze=False,
    fair_price_override_krw=None,
    alert_drop_rate_percent_override=None,
):
    if not isinstance(user_id, str) or not user_id.strip():
        return _build_failed_response(url if isinstance(url, str) else "", "user_id가 비어 있습니다.")
    if not isinstance(url, str) or not url.strip():
        return _build_failed_response("", "url이 비어 있습니다.")

    user_id = user_id.strip()
    url = url.strip()

    normalized_fair_price_override_krw = None
    normalized_alert_drop_rate_percent_override = None
    if fair_price_override_krw is not None:
        try:
            normalized_fair_price_override_krw = int(fair_price_override_krw)
        except (TypeError, ValueError):
            return _build_failed_response(url, "invalid_fair_price_override", risk_result=_default_risk_result())
        if normalized_fair_price_override_krw <= 0:
            return _build_failed_response(
                url,
                "invalid_fair_price_override",
                risk_result=_default_risk_result(),
            )
    if alert_drop_rate_percent_override is not None:
        try:
            normalized_alert_drop_rate_percent_override = float(alert_drop_rate_percent_override)
        except (TypeError, ValueError):
            return _build_failed_response(
                url,
                "invalid_alert_drop_rate_percent_override",
                risk_result=_default_risk_result(),
            )
        if not is_valid_alert_drop_rate_percent(normalized_alert_drop_rate_percent_override):
            return _build_failed_response(
                url,
                "invalid_alert_drop_rate_percent_override",
                risk_result=_default_risk_result(),
            )

    connection = None
    cursor = None
    title = None
    description = None
    listing_price_krw = None
    parsed_spec = {}
    self_check_fields = {}
    risk_result = _default_risk_result()

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
                    body_text=description,
                    listing_price_krw=listing_price_krw,
                    parsed_spec=parsed_spec,
                    risk_result=risk_result,
                )
                connection.commit()
            except Exception as log_exc:
                print(f"실패 로그 저장 실패: {log_exc}")

        return _build_failed_response(
            url,
            reason,
            parsed_spec=parsed_spec,
            self_check_fields=self_check_fields,
            risk_result=risk_result,
            body_text=description,
        )

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
        except Exception as exc:
            return _build_failed_response(url, f"DB 연결 실패: {exc}", risk_result=risk_result)

        if not force_reanalyze:
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
                    "parse_success": None,
                    "missing_fields": [],
                    "screen_inch": None,
                    "screen_inch_defaulted": None,
                    "confidence_score": None,
                    "unit_valid": None,
                    "unit_validation_reason": None,
                    "self_check_fields": {},
                    "detected_patterns": {},
                    "detected_conflicts": [],
                    "risk_detected": False,
                    "risk_level": "none",
                    "risk_score": 0,
                    "risk_keywords": [],
                    "risk_categories": {},
                    "is_exchange_post": False,
                    "exchange_strength": "none",
                    "exchange_keywords": [],
                    "trade_type": "sale",
                    "body_text": None,
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
        self_check_fields = parsed_page.get("self_check_fields") or {}

        parsing_source_text = f"{title} {description}"
        risk_result = analyze_risk(parsing_source_text, self_check_fields=self_check_fields)
        parsed_spec = parse_listing_title(parsing_source_text, self_check_fields=self_check_fields)

        if not parsed_spec.get("parse_success", False):
            return fail(_build_parse_failure_reason(parsed_spec), source=SOURCE_NAME)

        use_price_override = (
            normalized_fair_price_override_krw is not None
            and normalized_alert_drop_rate_percent_override is not None
        )
        if use_price_override:
            fair_price_krw = normalized_fair_price_override_krw
            alert_drop_rate_percent = normalized_alert_drop_rate_percent_override
            target_buy_price_krw = compute_target_buy_price_krw(
                fair_price_krw,
                alert_drop_rate_percent,
            )
            alert_price_direction = DEFAULT_ALERT_PRICE_DIRECTION
        else:
            user_fair_price = fetch_user_fair_price(cursor, user_id, parsed_spec)
            if user_fair_price is None:
                return fail("사용자 공정가 조회 실패: 해당 user_id/스펙 조합이 없습니다.", source=SOURCE_NAME)

            fair_price_krw = user_fair_price["fair_price_krw"]
            if fair_price_krw <= 0:
                return fail("사용자 공정가 조회 실패: 공정가가 0보다 커야 합니다.", source=SOURCE_NAME)
            alert_drop_rate_percent = user_fair_price["alert_drop_rate_percent"]
            target_buy_price_krw = user_fair_price.get("target_buy_price_krw")
            alert_price_direction = normalize_alert_price_direction(
                user_fair_price.get("alert_price_direction")
            )
            min_price_krw = user_fair_price.get("min_price_krw")
            max_price_krw = user_fair_price.get("max_price_krw")
            if target_buy_price_krw is None:
                target_buy_price_krw = compute_target_buy_price_krw(
                    fair_price_krw,
                    alert_drop_rate_percent,
                )
        if use_price_override:
            min_price_krw = None
            max_price_krw = None

        if alert_drop_rate_percent is None or target_buy_price_krw is None:
            return fail("사용자 공정가 조회 실패: 알림 기준 계산에 실패했습니다.", source=SOURCE_NAME)

        diff_amount_krw = fair_price_krw - listing_price_krw
        diff_ratio = (diff_amount_krw / fair_price_krw) * 100
        is_alert_target = is_listing_alert_match(
            listing_price_krw,
            target_buy_price_krw,
            alert_price_direction,
        )
        if is_alert_target and not passes_price_bounds(
            listing_price_krw,
            alert_price_direction,
            min_price_krw=min_price_krw,
            max_price_krw=max_price_krw,
        ):
            is_alert_target = False

        listing = {
            "title": title,
            "body_text": description,
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
            risk_result=risk_result,
            body_text=description,
        )
        connection.commit()

        telegram_sent = False
        message = "알림 대상 아님"
        if is_alert_target:
            message_parts = ["알림 대상"]
            risk_level = risk_result.get("risk_level")
            if risk_level in {"medium", "high", "exclude"}:
                message_parts.append("주의 필요")
            if risk_level == "exclude":
                message_parts.append("제외급 위험")
            if risk_result.get("is_exchange_post"):
                message_parts.append("교환글")
            message = " - ".join(message_parts)
            delivery_policy = resolve_user_alert_delivery_policy(user_id)
            policy_enabled = bool(delivery_policy.get("enabled"))
            user_chat_id = delivery_policy.get("telegram_chat_id")
            allow_global_fallback = bool(delivery_policy.get("allow_global_fallback"))

            if policy_enabled:
                if user_chat_id is None and not allow_global_fallback:
                    print(
                        f"[analysis_service] telegram skipped: missing telegram_chat_id for user_id={user_id}"
                    )
                else:
                    telegram_sent = send_telegram_alert(
                        _build_telegram_message(
                            title=title,
                            listing_price_krw=listing_price_krw,
                            fair_price_krw=fair_price_krw,
                            diff_ratio=diff_ratio,
                            url=url,
                            risk_result=risk_result,
                            screen_inch_defaulted=parsed_spec.get("screen_inch_defaulted", False),
                        ),
                        chat_id=user_chat_id,
                        allow_global_fallback=allow_global_fallback,
                    )
            else:
                print(f"[analysis_service] telegram skipped: alerts disabled for user_id={user_id}")

        return {
            "ok": True,
            "status": "success",
            "user_id": user_id,
            "url": url,
            "title": title,
            "self_check_fields": self_check_fields,
            "parse_success": True,
            "product_type": parsed_spec["product_type"],
            "chip": parsed_spec["chip"],
            "screen_inch": parsed_spec["screen_inch"],
            "screen_inch_defaulted": parsed_spec.get("screen_inch_defaulted"),
            "ram_gb": parsed_spec["ram_gb"],
            "ssd_gb": parsed_spec["ssd_gb"],
            "confidence_score": parsed_spec.get("confidence_score"),
            "unit_valid": parsed_spec.get("unit_valid"),
            "unit_validation_reason": parsed_spec.get("unit_validation_reason"),
            "missing_fields": parsed_spec.get("missing_fields", []),
            "detected_patterns": parsed_spec.get("detected_patterns", {}),
            "detected_conflicts": parsed_spec.get("detected_conflicts", []),
            "risk_detected": risk_result.get("risk_detected", False),
            "risk_level": risk_result.get("risk_level", "none"),
            "risk_score": risk_result.get("risk_score", 0),
            "risk_keywords": risk_result.get("risk_keywords", []),
            "risk_categories": risk_result.get("risk_categories", {}),
            "is_exchange_post": risk_result.get("is_exchange_post", False),
            "exchange_strength": risk_result.get("exchange_strength", "none"),
            "exchange_keywords": risk_result.get("exchange_keywords", []),
            "trade_type": risk_result.get("trade_type", "sale"),
            "body_text": description,
            "listing_price_krw": listing_price_krw,
            "fair_price_krw": fair_price_krw,
            "target_buy_price_krw": target_buy_price_krw,
            "diff_amount_krw": diff_amount_krw,
            "diff_ratio": round(diff_ratio, 1),
            "alert_drop_rate_percent": alert_drop_rate_percent,
            "alert_price_direction": alert_price_direction,
            "min_price_krw": min_price_krw,
            "max_price_krw": max_price_krw,
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
