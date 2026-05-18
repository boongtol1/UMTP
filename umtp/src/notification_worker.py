import os
import json

from dotenv import load_dotenv

try:
    from src.alert_price_direction import ABOVE_OR_EQUAL, BELOW_OR_EQUAL, normalize_alert_price_direction
    from src.db import get_connection
    from src.push_token_service import (
        deactivate_user_push_token,
        list_active_user_push_tokens,
        mark_user_push_token_sent,
    )
    from src.telegram_notifier import send_telegram_alert
    from src.user_alert_settings import resolve_user_alert_delivery_policy
except ModuleNotFoundError:
    from alert_price_direction import ABOVE_OR_EQUAL, BELOW_OR_EQUAL, normalize_alert_price_direction
    from db import get_connection
    from push_token_service import (
        deactivate_user_push_token,
        list_active_user_push_tokens,
        mark_user_push_token_sent,
    )
    from telegram_notifier import send_telegram_alert
    from user_alert_settings import resolve_user_alert_delivery_policy

try:  # pragma: no cover - optional runtime dependency
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception:  # pragma: no cover
    firebase_admin = None
    credentials = None
    messaging = None


_FIREBASE_INIT_ATTEMPTED = False
_FIREBASE_INIT_ERROR = None


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_required_text(value, field_name):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ValueError(f"invalid_{field_name}")
    return normalized


def _normalize_optional_int(value, field_name):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field_name}") from exc


def _safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_bool(value):
    if value is None:
        return None
    return bool(value)


def _safe_json_loads(value, *, fallback):
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    if isinstance(decoded, type(fallback)):
        return decoded
    return fallback


def _parse_risk_keywords(value):
    keywords = _safe_json_loads(value, fallback=[])
    if isinstance(keywords, list):
        return [str(item) for item in keywords if isinstance(item, (str, int, float))]
    return []


def _build_alert_condition_label(alert_price_direction):
    if normalize_alert_price_direction(alert_price_direction) == ABOVE_OR_EQUAL:
        return "이 가격 이상이면 알림"
    return "이 가격 이하이면 알림"


def _build_formatted_risk_label(risk_level):
    normalized = _normalize_optional_text(risk_level)
    if normalized is None:
        return "정보 없음"
    normalized_upper = normalized.upper()
    if normalized_upper == "LOW":
        return "낮음"
    if normalized_upper == "MEDIUM":
        return "주의"
    if normalized_upper in {"HIGH", "EXCLUDE"}:
        return "위험"
    if normalized_upper == "NONE":
        return "낮음"
    return normalized


def _build_trade_type_flags(*, is_exchange_post, trade_type, risk_level):
    normalized_trade_type = (_normalize_optional_text(trade_type) or "").lower()
    normalized_risk_level = (_normalize_optional_text(risk_level) or "").upper()

    is_exchange = bool(is_exchange_post) or normalized_trade_type in {"exchange", "trade"}
    is_free = normalized_trade_type in {"free", "giveaway", "donation", "share"}
    is_suspicious = normalized_risk_level in {"HIGH", "EXCLUDE"}

    return {
        "is_exchange": is_exchange,
        "is_free": is_free,
        "is_suspicious": is_suspicious,
    }


def _build_body_excerpt(value, *, max_len=500):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len].rstrip()}..."


def _fetch_latest_log_details(cursor, *, user_id, url):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_url = _normalize_optional_text(url)
    if normalized_user_id is None or normalized_url is None:
        return {}

    try:
        cursor.execute(
            """
            SELECT
                source,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                confidence_score,
                risk_level,
                risk_score,
                risk_keywords,
                is_exchange_post,
                trade_type,
                body_text,
                created_at
            FROM url_analysis_logs
            WHERE user_id = %s
              AND url = %s
              AND status = 'success'
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized_user_id, normalized_url),
        )
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" not in lowered_exc and "doesn't exist" not in lowered_exc:
            raise
        try:
            cursor.execute(
                """
                SELECT
                source,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                NULL AS body_text,
                created_at
            FROM url_analysis_logs
                WHERE user_id = %s
                  AND url = %s
                  AND status = 'success'
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_user_id, normalized_url),
            )
        except Exception:
            return {}

    row = cursor.fetchone()
    if not row:
        return {}
    return row


def _fetch_alert_rows(cursor, *, normalized_user_id, normalized_limit):
    try:
        cursor.execute(
            """
            SELECT
                id,
                user_id,
                watch_rule_id,
                analysis_job_id,
                product_id,
                source,
                url,
                title,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                price_krw,
                fair_price_krw,
                target_price_krw,
                drop_rate_percent,
                alert_drop_rate_percent,
                alert_price_direction,
                risk_level,
                risk_score,
                risk_keywords,
                is_exchange_post,
                trade_type,
                body_excerpt,
                body_text,
                analyzed_at,
                trigger_reason,
                message,
                status,
                send_attempts,
                error_message,
                created_at,
                sent_at,
                updated_at
            FROM alert_events
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (normalized_user_id, normalized_limit),
        )
        return cursor.fetchall() or [], True
    except Exception as exc:
        lowered_exc = str(exc).lower()
        if "unknown column" not in lowered_exc:
            raise
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    watch_rule_id,
                    analysis_job_id,
                    product_id,
                    source,
                    url,
                    title,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    price_krw,
                    fair_price_krw,
                    target_price_krw,
                    drop_rate_percent,
                    alert_drop_rate_percent,
                    alert_price_direction,
                    risk_level,
                    risk_score,
                    risk_keywords,
                    is_exchange_post,
                    trade_type,
                    body_excerpt,
                    NULL AS body_text,
                    analyzed_at,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (normalized_user_id, normalized_limit),
            )
            return cursor.fetchall() or [], True
        except Exception as detail_exc:
            if "unknown column" not in str(detail_exc).lower():
                raise

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                NULL AS watch_rule_id,
                analysis_job_id,
                product_id,
                url,
                title,
                price_krw,
                fair_price_krw,
                target_price_krw,
                drop_rate_percent,
                trigger_reason,
                message,
                status,
                send_attempts,
                error_message,
                created_at,
                sent_at,
                updated_at
            FROM alert_events
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (normalized_user_id, normalized_limit),
        )
        return cursor.fetchall() or [], False


def _normalize_limit(limit):
    normalized = _normalize_optional_int(limit, "limit")
    if normalized is None:
        return 20
    if normalized <= 0:
        raise ValueError("invalid_limit")
    return min(normalized, 200)


def _normalize_alert_id(alert_id):
    normalized = _normalize_optional_int(alert_id, "alert_id")
    if normalized is None or normalized <= 0:
        raise ValueError("invalid_alert_id")
    return normalized


def _telegram_configured():
    load_dotenv()
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    return bool(bot_token)


def _fcm_configured():
    load_dotenv()
    has_json = bool((os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip())
    has_file = bool((os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE") or "").strip())
    has_google_cred_file = bool((os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip())
    return has_json or has_file or has_google_cred_file


def _ensure_firebase_initialized():
    global _FIREBASE_INIT_ATTEMPTED, _FIREBASE_INIT_ERROR

    if _FIREBASE_INIT_ATTEMPTED:
        return _FIREBASE_INIT_ERROR is None, _FIREBASE_INIT_ERROR

    _FIREBASE_INIT_ATTEMPTED = True

    if firebase_admin is None or credentials is None:
        _FIREBASE_INIT_ERROR = "firebase_admin_not_installed"
        return False, _FIREBASE_INIT_ERROR

    try:
        if firebase_admin._apps:
            _FIREBASE_INIT_ERROR = None
            return True, None
    except Exception:
        pass

    load_dotenv()
    credential_json = _normalize_optional_text(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
    credential_file = _normalize_optional_text(os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE"))
    project_id = _normalize_optional_text(os.getenv("FIREBASE_PROJECT_ID"))

    options = {}
    if project_id is not None:
        options["projectId"] = project_id

    try:
        if credential_json is not None:
            credential_obj = credentials.Certificate(json.loads(credential_json))
            firebase_admin.initialize_app(credential=credential_obj, options=options or None)
        elif credential_file is not None:
            credential_obj = credentials.Certificate(credential_file)
            firebase_admin.initialize_app(credential=credential_obj, options=options or None)
        else:
            firebase_admin.initialize_app(options=options or None)

        _FIREBASE_INIT_ERROR = None
        return True, None
    except Exception as exc:
        _FIREBASE_INIT_ERROR = str(exc)
        return False, _FIREBASE_INIT_ERROR


def _is_unregistered_push_token_error(error_text):
    lowered = (error_text or "").lower()
    return (
        "unregistered" in lowered
        or "registration token is not a valid fcm registration token" in lowered
        or "requested entity was not found" in lowered
        or "notfound" in lowered
    )


def _build_push_notification_payload(alert):
    title = _normalize_optional_text(alert.get("title")) or "UMTP 새 매물 알림"
    listing_price_krw = _safe_int(alert.get("price_krw"))
    risk_level = _normalize_optional_text(alert.get("risk_level"))
    risk_label = _build_formatted_risk_label(risk_level)

    body = _normalize_optional_text(alert.get("body_excerpt"))
    if body is None:
        body = _normalize_optional_text(alert.get("message"))
    if body is None:
        segments = []
        if listing_price_krw is not None:
            segments.append(f"{listing_price_krw:,}원")
        if risk_label != "정보 없음":
            segments.append(f"위험도 {risk_label}")
        body = " · ".join(segments) if segments else "새로운 매물이 등록되었습니다."

    data_payload = {
        "alert_id": str(_safe_int(alert.get("id")) or ""),
        "listing_title": title,
        "listing_price_krw": str(listing_price_krw) if listing_price_krw is not None else "",
        "risk_level": _normalize_optional_text(alert.get("risk_level")) or "",
        "product_id": _normalize_optional_text(alert.get("product_id")) or "",
        "url": _normalize_optional_text(alert.get("url")) or "",
        "trigger_reason": _normalize_optional_text(alert.get("trigger_reason")) or "",
    }
    data_payload = {key: value for key, value in data_payload.items() if isinstance(value, str)}
    return title, body, data_payload


def _send_fcm_to_user(user_id, alert):
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        return {"sent": 0, "failed": 0, "reason": "invalid_user_id", "attempted": 0}

    push_tokens = list_active_user_push_tokens(normalized_user_id, platform="android")
    if not push_tokens:
        return {"sent": 0, "failed": 0, "reason": "no_active_push_tokens", "attempted": 0}

    if not _fcm_configured():
        return {"sent": 0, "failed": 0, "reason": "fcm_credentials_missing", "attempted": 0}

    ready, init_error = _ensure_firebase_initialized()
    if not ready:
        return {"sent": 0, "failed": len(push_tokens), "reason": init_error or "firebase_init_failed", "attempted": len(push_tokens)}

    title, body, data_payload = _build_push_notification_payload(alert)
    sent_count = 0
    failed_count = 0

    for token_row in push_tokens:
        token_id = token_row.get("id")
        token = _normalize_optional_text(token_row.get("token"))
        if token is None:
            failed_count += 1
            continue

        try:
            message = messaging.Message(  # type: ignore[union-attr]
                token=token,
                notification=messaging.Notification(title=title, body=body),  # type: ignore[union-attr]
                data=data_payload,
            )
            messaging.send(message)  # type: ignore[union-attr]
            if token_id is not None:
                mark_user_push_token_sent(token_id)
            sent_count += 1
        except Exception as exc:
            failed_count += 1
            error_text = str(exc)
            if token_id is not None and _is_unregistered_push_token_error(error_text):
                deactivate_user_push_token(token_id, error_message=error_text)

    if sent_count > 0:
        return {"sent": sent_count, "failed": failed_count, "reason": "fcm_sent", "attempted": len(push_tokens)}
    return {"sent": 0, "failed": failed_count, "reason": "fcm_send_failed", "attempted": len(push_tokens)}


def _build_telegram_message(alert):
    message = _normalize_optional_text(alert.get("message"))
    if message:
        return message

    title = _normalize_optional_text(alert.get("title")) or "-"
    price_krw = _normalize_optional_int(alert.get("price_krw"), "price_krw") or 0
    fair_price_krw = _normalize_optional_int(alert.get("fair_price_krw"), "fair_price_krw") or 0
    drop_rate_percent = alert.get("drop_rate_percent")
    trigger_reason = _normalize_optional_text(alert.get("trigger_reason")) or "-"
    url = _normalize_optional_text(alert.get("url")) or "-"

    drop_text = "-"
    if drop_rate_percent is not None:
        try:
            drop_text = f"{float(drop_rate_percent):.2f}%"
        except (TypeError, ValueError):
            drop_text = str(drop_rate_percent)

    return (
        "[UMTP 알림]\n"
        f"{title}\n\n"
        f"현재가: {price_krw:,}원\n"
        f"공정가: {fair_price_krw:,}원\n"
        f"저평가율: {drop_text}\n"
        f"트리거: {trigger_reason}\n\n"
        "URL:\n"
        f"{url}"
    )


def get_pending_alert_events(limit=20):
    normalized_limit = _normalize_limit(limit)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    watch_rule_id,
                    analysis_job_id,
                    product_id,
                    url,
                    title,
                    price_krw,
                    fair_price_krw,
                    target_price_krw,
                    drop_rate_percent,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (normalized_limit,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    NULL AS watch_rule_id,
                    analysis_job_id,
                    product_id,
                    url,
                    title,
                    price_krw,
                    fair_price_krw,
                    target_price_krw,
                    drop_rate_percent,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (normalized_limit,),
            )
        return cursor.fetchall() or []
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _update_alert_event_status(alert_id, status, *, error_message=None, set_sent_at=False):
    normalized_alert_id = _normalize_alert_id(alert_id)
    normalized_status = _normalize_required_text(status, "status")
    normalized_error_message = _normalize_optional_text(error_message)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        if set_sent_at:
            cursor.execute(
                """
                UPDATE alert_events
                SET
                    status = %s,
                    error_message = %s,
                    sent_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_status, normalized_error_message, normalized_alert_id),
            )
        else:
            cursor.execute(
                """
                UPDATE alert_events
                SET
                    status = %s,
                    error_message = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (normalized_status, normalized_error_message, normalized_alert_id),
            )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_alert_event_sending(alert_id):
    normalized_alert_id = _normalize_alert_id(alert_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET
                status = 'sending',
                send_attempts = COALESCE(send_attempts, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'pending'
            """,
            (normalized_alert_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_alert_event_sent(alert_id):
    return _update_alert_event_status(alert_id, "sent", set_sent_at=True)


def mark_alert_event_app_only(alert_id):
    return _update_alert_event_status(alert_id, "app_only", set_sent_at=True)


def mark_alert_event_failed(alert_id, error_message):
    return _update_alert_event_status(alert_id, "failed", error_message=error_message, set_sent_at=False)


def send_alert_event(alert):
    if not isinstance(alert, dict):
        raise ValueError("invalid_alert")

    alert_id = _normalize_alert_id(alert.get("id"))
    user_id = _normalize_required_text(alert.get("user_id"), "user_id")
    delivery_policy = resolve_user_alert_delivery_policy(user_id)
    user_alert_enabled = bool(delivery_policy.get("enabled"))
    user_chat_id = _normalize_optional_text(delivery_policy.get("telegram_chat_id"))
    allow_global_fallback = bool(delivery_policy.get("allow_global_fallback"))

    if not user_alert_enabled:
        print(f"[notification_worker] delivery skipped: alerts disabled for user_id={user_id}")
        mark_alert_event_app_only(alert_id)
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "app_only",
            "reason": "alerts_disabled",
        }

    push_result = _send_fcm_to_user(user_id, alert)
    push_sent = int(push_result.get("sent", 0))
    push_attempted = int(push_result.get("attempted", 0))
    push_reason = _normalize_optional_text(push_result.get("reason"))

    telegram_status = "skipped"
    telegram_reason = None
    telegram_sent = False
    telegram_attempted = False

    telegram_ready = _telegram_configured()
    if not telegram_ready:
        telegram_reason = "telegram_bot_token_missing"
    elif user_chat_id is None and not allow_global_fallback:
        telegram_reason = "missing_telegram_chat_id"
    else:
        if user_chat_id is None and allow_global_fallback:
            print(
                f"[notification_worker] telegram fallback: using global chat id for user_id={user_id} "
                "(deprecated)"
            )

        telegram_attempted = True
        telegram_message = _build_telegram_message(alert)
        sent_ok = send_telegram_alert(
            telegram_message,
            chat_id=user_chat_id,
            allow_global_fallback=allow_global_fallback,
        )
        if sent_ok:
            telegram_status = "sent"
            telegram_reason = "telegram_sent"
            telegram_sent = True
        else:
            telegram_status = "failed"
            telegram_reason = "telegram_send_failed"

    if push_sent > 0 or telegram_sent:
        mark_alert_event_sent(alert_id)
        if push_sent > 0 and telegram_sent:
            reason = "push_and_telegram_sent"
        elif push_sent > 0:
            reason = "push_sent"
        else:
            reason = "telegram_sent"
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "sent",
            "reason": reason,
            "push_sent_count": push_sent,
            "push_reason": push_reason,
            "telegram_status": telegram_status,
            "telegram_reason": telegram_reason,
        }

    if push_attempted > 0 or telegram_attempted:
        failure_reason = telegram_reason or push_reason or "notification_send_failed"
        mark_alert_event_failed(alert_id, failure_reason)
        return {
            "ok": False,
            "alert_id": alert_id,
            "status": "failed",
            "reason": failure_reason,
            "push_sent_count": push_sent,
            "push_reason": push_reason,
            "telegram_status": telegram_status,
            "telegram_reason": telegram_reason,
        }

    mark_alert_event_app_only(alert_id)
    app_only_reason = telegram_reason or push_reason or "no_delivery_channel"
    return {
        "ok": True,
        "alert_id": alert_id,
        "status": "app_only",
        "reason": app_only_reason,
        "push_reason": push_reason,
        "telegram_reason": telegram_reason,
    }


def get_alert_event_by_id(alert_id):
    normalized_alert_id = _normalize_alert_id(alert_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    watch_rule_id,
                    analysis_job_id,
                    product_id,
                    url,
                    title,
                    price_krw,
                    fair_price_krw,
                    target_price_krw,
                    drop_rate_percent,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE id = %s
                LIMIT 1
                """,
                (normalized_alert_id,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    NULL AS watch_rule_id,
                    analysis_job_id,
                    product_id,
                    url,
                    title,
                    price_krw,
                    fair_price_krw,
                    target_price_krw,
                    drop_rate_percent,
                    trigger_reason,
                    message,
                    status,
                    send_attempts,
                    error_message,
                    created_at,
                    sent_at,
                    updated_at
                FROM alert_events
                WHERE id = %s
                LIMIT 1
                """,
                (normalized_alert_id,),
            )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def dispatch_alert_event_immediately(alert_id, *, fallback_alert=None):
    normalized_alert_id = _normalize_alert_id(alert_id)

    claimed = mark_alert_event_sending(normalized_alert_id)
    if not claimed:
        return {
            "ok": True,
            "alert_id": normalized_alert_id,
            "status": "skipped_not_pending",
            "reason": "not_pending",
        }

    alert_payload = None
    if isinstance(fallback_alert, dict):
        alert_payload = dict(fallback_alert)
        alert_payload["id"] = normalized_alert_id

    if not isinstance(alert_payload, dict):
        alert_payload = get_alert_event_by_id(normalized_alert_id)

    if not isinstance(alert_payload, dict):
        mark_alert_event_failed(normalized_alert_id, "alert_event_not_found_after_claim")
        return {
            "ok": False,
            "alert_id": normalized_alert_id,
            "status": "failed",
            "reason": "alert_event_not_found_after_claim",
        }

    try:
        return send_alert_event(alert_payload)
    except Exception as exc:
        mark_alert_event_failed(normalized_alert_id, str(exc))
        return {
            "ok": False,
            "alert_id": normalized_alert_id,
            "status": "failed",
            "reason": str(exc),
        }


def process_pending_alert_events(limit=20):
    pending_alerts = get_pending_alert_events(limit=limit)
    stats = {
        "fetched": len(pending_alerts),
        "sent": 0,
        "app_only": 0,
        "failed": 0,
        "results": [],
    }

    for alert in pending_alerts:
        alert_id = _normalize_alert_id(alert.get("id"))

        try:
            claimed = mark_alert_event_sending(alert_id)
            if not claimed:
                stats["results"].append(
                    {
                        "ok": True,
                        "alert_id": alert_id,
                        "status": "skipped_not_pending",
                    }
                )
                continue

            send_result = send_alert_event(alert)
            stats["results"].append(send_result)

            status = send_result.get("status")
            if status == "sent":
                stats["sent"] += 1
            elif status == "app_only":
                stats["app_only"] += 1
            else:
                stats["failed"] += 1
        except Exception as exc:
            try:
                mark_alert_event_failed(alert_id, str(exc))
            except Exception:
                pass
            stats["failed"] += 1
            stats["results"].append(
                {
                    "ok": False,
                    "alert_id": alert_id,
                    "status": "failed",
                    "reason": str(exc),
                }
            )

    return stats


def list_alert_events_for_user(user_id, limit=200):
    normalized_user_id = _normalize_required_text(user_id, "user_id")
    normalized_limit = _normalize_limit(limit)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        rows, has_detail_columns = _fetch_alert_rows(
            cursor,
            normalized_user_id=normalized_user_id,
            normalized_limit=normalized_limit,
        )

        items = []
        for row in rows:
            drop_rate_percent = _normalize_optional_float(row.get("drop_rate_percent"))
            alert_drop_rate_percent = _normalize_optional_float(row.get("alert_drop_rate_percent"))
            diff_ratio = drop_rate_percent

            alert_price_direction = normalize_alert_price_direction(row.get("alert_price_direction"))
            risk_keywords = _parse_risk_keywords(row.get("risk_keywords"))
            risk_level = _normalize_optional_text(row.get("risk_level"))
            risk_score = _safe_int(row.get("risk_score"))
            is_exchange_post = _normalize_optional_bool(row.get("is_exchange_post"))
            trade_type = _normalize_optional_text(row.get("trade_type"))
            source = _normalize_optional_text(row.get("source"))
            product_type = _normalize_optional_text(row.get("product_type"))
            chip = _normalize_optional_text(row.get("chip"))
            screen_inch = _safe_int(row.get("screen_inch"))
            ram_gb = _safe_int(row.get("ram_gb"))
            ssd_gb = _safe_int(row.get("ssd_gb"))
            body_text = _normalize_optional_text(row.get("body_text"))
            body_excerpt_source = row.get("body_excerpt")
            if body_excerpt_source is None:
                body_excerpt_source = body_text
            body_excerpt = _build_body_excerpt(body_excerpt_source)
            analyzed_at = row.get("analyzed_at") or row.get("created_at")
            confidence_score = _safe_int(row.get("confidence_score"))

            if not has_detail_columns:
                log_detail = _fetch_latest_log_details(
                    cursor,
                    user_id=row.get("user_id"),
                    url=row.get("url"),
                )
                source = source or _normalize_optional_text(log_detail.get("source"))
                product_type = product_type or _normalize_optional_text(log_detail.get("product_type"))
                chip = chip or _normalize_optional_text(log_detail.get("chip"))
                screen_inch = screen_inch or _safe_int(log_detail.get("screen_inch"))
                ram_gb = ram_gb or _safe_int(log_detail.get("ram_gb"))
                ssd_gb = ssd_gb or _safe_int(log_detail.get("ssd_gb"))
                risk_level = risk_level or _normalize_optional_text(log_detail.get("risk_level"))
                if risk_score is None:
                    risk_score = _safe_int(log_detail.get("risk_score"))
                if not risk_keywords:
                    risk_keywords = _parse_risk_keywords(log_detail.get("risk_keywords"))
                if is_exchange_post is None:
                    is_exchange_post = _normalize_optional_bool(log_detail.get("is_exchange_post"))
                if trade_type is None:
                    trade_type = _normalize_optional_text(log_detail.get("trade_type"))
                if body_text is None:
                    body_text = _normalize_optional_text(log_detail.get("body_text"))
                if body_excerpt is None:
                    body_excerpt = _build_body_excerpt(body_text)
                analyzed_at = analyzed_at or log_detail.get("created_at")
                if confidence_score is None:
                    confidence_score = _safe_int(log_detail.get("confidence_score"))

            trade_type_flags = _build_trade_type_flags(
                is_exchange_post=is_exchange_post,
                trade_type=trade_type,
                risk_level=risk_level,
            )
            risk_keywords_display = risk_keywords if risk_keywords else []

            items.append(
                {
                    "id": int(row.get("id")),
                    "user_id": row.get("user_id"),
                    "watch_rule_id": row.get("watch_rule_id"),
                    "analysis_job_id": row.get("analysis_job_id"),
                    "product_id": row.get("product_id"),
                    "source": source or "joongna",
                    "url": row.get("url"),
                    "product_url": row.get("url"),
                    "title": row.get("title"),
                    "product_type": product_type,
                    "chip": chip,
                    "screen_inch": screen_inch,
                    "ram_gb": ram_gb,
                    "ssd_gb": ssd_gb,
                    "price_krw": row.get("price_krw"),
                    "listing_price_krw": row.get("price_krw"),
                    "fair_price_krw": row.get("fair_price_krw"),
                    "user_market_price_krw": row.get("fair_price_krw"),
                    "target_price_krw": row.get("target_price_krw"),
                    "alert_target_price_krw": row.get("target_price_krw"),
                    "drop_rate_percent": diff_ratio,
                    "diff_ratio": diff_ratio,
                    "price_gap_percent": diff_ratio,
                    "alert_drop_rate_percent": alert_drop_rate_percent,
                    "alert_price_direction": alert_price_direction,
                    "alert_condition_label": _build_alert_condition_label(alert_price_direction),
                    "trigger_reason": row.get("trigger_reason"),
                    "message": row.get("message"),
                    "risk_level": risk_level,
                    "formatted_risk_label": _build_formatted_risk_label(risk_level),
                    "risk_score": risk_score,
                    "risk_keywords": risk_keywords_display,
                    "trade_type_flags": trade_type_flags,
                    "is_exchange_post": bool(is_exchange_post) if is_exchange_post is not None else False,
                    "trade_type": trade_type,
                    "body_excerpt": body_excerpt,
                    "body_text": body_text,
                    "analyzed_at": analyzed_at,
                    "confidence_score": confidence_score,
                    "status": row.get("status"),
                    "send_attempts": row.get("send_attempts"),
                    "error_message": row.get("error_message"),
                    "created_at": row.get("created_at"),
                    "sent_at": row.get("sent_at"),
                    "updated_at": row.get("updated_at"),
                    "is_alert_target": True,
                }
            )

        return items
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
