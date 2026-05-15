import os

from dotenv import load_dotenv

try:
    from src.db import get_connection
    from src.telegram_notifier import send_telegram_alert
    from src.user_alert_settings import resolve_user_alert_delivery_policy
except ModuleNotFoundError:
    from db import get_connection
    from telegram_notifier import send_telegram_alert
    from user_alert_settings import resolve_user_alert_delivery_policy


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
        print(f"[notification_worker] telegram skipped: alerts disabled for user_id={user_id}")
        mark_alert_event_app_only(alert_id)
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "app_only",
            "reason": "alerts_disabled",
        }

    telegram_ready = _telegram_configured()

    if not telegram_ready:
        print(f"[notification_worker] telegram skipped: bot token missing for user_id={user_id}")
        mark_alert_event_app_only(alert_id)
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "app_only",
            "reason": "telegram_bot_token_missing",
        }

    if user_chat_id is None and not allow_global_fallback:
        print(f"[notification_worker] telegram skipped: missing telegram_chat_id for user_id={user_id}")
        mark_alert_event_app_only(alert_id)
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "app_only",
            "reason": "missing_telegram_chat_id",
        }

    if user_chat_id is None and allow_global_fallback:
        print(
            f"[notification_worker] telegram fallback: using global chat id for user_id={user_id} "
            "(deprecated)"
        )

    telegram_message = _build_telegram_message(alert)
    sent_ok = send_telegram_alert(
        telegram_message,
        chat_id=user_chat_id,
        allow_global_fallback=allow_global_fallback,
    )

    if sent_ok:
        mark_alert_event_sent(alert_id)
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "sent",
            "reason": "telegram_sent",
        }

    mark_alert_event_failed(alert_id, "telegram_send_failed")
    return {
        "ok": False,
        "alert_id": alert_id,
        "status": "failed",
        "reason": "telegram_send_failed",
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
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (normalized_user_id, normalized_limit),
        )
        rows = cursor.fetchall() or []

        items = []
        for row in rows:
            drop_rate_percent = row.get("drop_rate_percent")
            try:
                diff_ratio = float(drop_rate_percent) if drop_rate_percent is not None else None
            except (TypeError, ValueError):
                diff_ratio = None

            items.append(
                {
                    "id": int(row.get("id")),
                    "user_id": row.get("user_id"),
                    "watch_rule_id": row.get("watch_rule_id"),
                    "analysis_job_id": row.get("analysis_job_id"),
                    "product_id": row.get("product_id"),
                    "url": row.get("url"),
                    "product_url": row.get("url"),
                    "title": row.get("title"),
                    "price_krw": row.get("price_krw"),
                    "listing_price_krw": row.get("price_krw"),
                    "fair_price_krw": row.get("fair_price_krw"),
                    "target_price_krw": row.get("target_price_krw"),
                    "drop_rate_percent": diff_ratio,
                    "diff_ratio": diff_ratio,
                    "trigger_reason": row.get("trigger_reason"),
                    "message": row.get("message"),
                    "status": row.get("status"),
                    "send_attempts": row.get("send_attempts"),
                    "error_message": row.get("error_message"),
                    "created_at": row.get("created_at"),
                    "sent_at": row.get("sent_at"),
                    "updated_at": row.get("updated_at"),
                    "is_alert_target": True,
                    "risk_score": None,
                }
            )

        return items
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
