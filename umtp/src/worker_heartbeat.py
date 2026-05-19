import json
import logging
from datetime import datetime, timezone

try:
    from src.db import get_connection
except ModuleNotFoundError:
    from db import get_connection


logger = logging.getLogger("umtp.worker_heartbeat")
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 60
_LAST_HEARTBEAT_AT = {}


def _normalize_text(value, *, default=None, max_length=None):
    if value is None:
        text = default
    else:
        text = str(value).strip()
        if not text:
            text = default

    if text is None:
        return None
    if max_length is not None:
        return text[:max_length]
    return text


def _normalize_interval_seconds(value):
    try:
        interval_seconds = int(value)
    except (TypeError, ValueError):
        interval_seconds = DEFAULT_HEARTBEAT_INTERVAL_SECONDS
    if interval_seconds <= 0:
        return DEFAULT_HEARTBEAT_INTERVAL_SECONDS
    return interval_seconds


def _utc_now():
    return datetime.now(timezone.utc)


def _is_due(worker_name, *, interval_seconds):
    now = _utc_now()
    last_seen_at = _LAST_HEARTBEAT_AT.get(worker_name)
    if last_seen_at is None:
        return True

    elapsed_seconds = (now - last_seen_at).total_seconds()
    return elapsed_seconds >= interval_seconds


def _mark_sent(worker_name):
    _LAST_HEARTBEAT_AT[worker_name] = _utc_now()


def _build_stats_payload(stats):
    if not isinstance(stats, dict):
        return "{}"

    payload = {}
    for key, value in stats.items():
        if key == "results":
            continue
        payload[key] = value

    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return "{}"


def write_worker_heartbeat(
    worker_name,
    *,
    status="ok",
    detail=None,
    stats=None,
    min_interval_seconds=DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    force=False,
):
    normalized_worker_name = _normalize_text(worker_name, default="unknown_worker", max_length=100)
    normalized_status = _normalize_text(status, default="ok", max_length=30)
    normalized_detail = _normalize_text(detail, default=None, max_length=255)
    interval_seconds = _normalize_interval_seconds(min_interval_seconds)

    if not force and not _is_due(normalized_worker_name, interval_seconds=interval_seconds):
        return {"ok": True, "skipped": True, "worker_name": normalized_worker_name}

    stats_json = _build_stats_payload(stats)
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO worker_heartbeats (
                worker_name,
                last_heartbeat_at,
                last_status,
                last_detail,
                last_stats_json,
                created_at,
                updated_at
            )
            VALUES (
                %s, CURRENT_TIMESTAMP, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON DUPLICATE KEY UPDATE
                last_heartbeat_at = CURRENT_TIMESTAMP,
                last_status = VALUES(last_status),
                last_detail = VALUES(last_detail),
                last_stats_json = VALUES(last_stats_json),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                normalized_worker_name,
                normalized_status,
                normalized_detail,
                stats_json,
            ),
        )
        connection.commit()
        _mark_sent(normalized_worker_name)
        return {"ok": True, "skipped": False, "worker_name": normalized_worker_name}
    except Exception as exc:
        print(
            f"[heartbeat] worker={normalized_worker_name} heartbeat 기록 실패: {exc}"
        )
        logger.warning(
            "[heartbeat] worker=%s heartbeat write failed: %s",
            normalized_worker_name,
            exc,
        )
        return {"ok": False, "skipped": False, "worker_name": normalized_worker_name, "reason": str(exc)}
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None and connection.is_connected():
            try:
                connection.close()
            except Exception:
                pass
