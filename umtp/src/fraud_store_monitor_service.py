import json
import os
import re
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

try:
    from src.db import get_connection
except ModuleNotFoundError:
    from db import get_connection


FRAUD_STORE_MONITOR_ENABLED_ENV = "FRAUD_STORE_MONITOR_ENABLED"
FRAUD_STORE_MONITOR_INTERVAL_SECONDS_ENV = "FRAUD_STORE_MONITOR_INTERVAL_SECONDS"
FRAUD_STORE_MIN_CHECK_INTERVAL_MINUTES_ENV = "FRAUD_STORE_MIN_CHECK_INTERVAL_MINUTES"
FRAUD_STORE_LOOKBACK_DAYS_ENV = "FRAUD_STORE_LOOKBACK_DAYS"

DEFAULT_MONITOR_ENABLED = True
DEFAULT_MONITOR_INTERVAL_SECONDS = 600
DEFAULT_MIN_CHECK_INTERVAL_MINUTES = 30
DEFAULT_LOOKBACK_DAYS = 14
DEFAULT_LISTING_CANDIDATE_LIMIT = 10000
INACTIVE_LABEL_MAX_MINUTES = 7 * 24 * 60

STORE_RSC_URL_TEMPLATE = "https://web.joongna.com/store/{store_id}?_rsc=1"
STORE_PAGE_REFERER_TEMPLATE = "https://web.joongna.com/store/{store_id}"
STORE_RSC_REQUEST_TIMEOUT_SECONDS = 10
STORE_RSC_HEADERS = {
    "accept": "*/*",
    "rsc": "1",
    "user-agent": "Mozilla/5.0",
}

STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_SUSPENDED = "suspended"
STATUS_DELETED = "deleted"
STATUS_UNKNOWN = "unknown"
STATUS_ERROR = "error"
INACTIVE_STORE_STATUSES = {STATUS_INACTIVE, STATUS_SUSPENDED, STATUS_DELETED}

SUSPENDED_MARKERS = (
    "이용제한된 회원의 가게입니다",
    "이용제한된 회원",
    "이용제한",
    "이용 제한",
    "제한된 회원",
    "정지",
    "제재",
    "차단",
    "suspended",
    "restricted",
    "banned",
    "blocked",
)

DELETED_MARKERS = (
    "존재하지 않는 상점",
    "찾을 수 없는 상점",
    "삭제된 상점",
    "탈퇴한 회원",
    "존재하지 않는 회원",
    "not found",
    "deleted",
    "removed",
)

INACTIVE_MARKERS = (
    "비활성",
    "비공개",
    "휴면",
    "inactive",
    "private",
    "dormant",
)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _safe_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = _safe_text(value)
        if normalized is None:
            return None

        candidate = normalized.replace("Z", "+00:00")
        parsed = None
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            pass

        if parsed is None:
            for date_format in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
            ):
                try:
                    parsed = datetime.strptime(normalized, date_format)
                    break
                except ValueError:
                    continue

        if parsed is None:
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def _is_truthy_env(value: Any) -> bool:
    normalized = _safe_text(value)
    if normalized is None:
        return False
    return normalized.lower() in {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return _is_truthy_env(value)


def _env_int(name: str, default: int, minimum: int) -> int:
    parsed = _safe_int(os.getenv(name))
    if parsed is None:
        return default
    return max(parsed, minimum)


def _normalize_store_id(value: Any) -> Optional[str]:
    parsed = _safe_int(value)
    if parsed is not None and parsed > 0:
        return str(parsed)

    text = _safe_text(value)
    if text is None:
        return None
    return text


def get_fraud_store_monitor_config() -> Dict[str, Any]:
    return {
        "enabled": _env_bool(FRAUD_STORE_MONITOR_ENABLED_ENV, DEFAULT_MONITOR_ENABLED),
        "interval_seconds": _env_int(
            FRAUD_STORE_MONITOR_INTERVAL_SECONDS_ENV,
            DEFAULT_MONITOR_INTERVAL_SECONDS,
            1,
        ),
        "min_check_interval_minutes": _env_int(
            FRAUD_STORE_MIN_CHECK_INTERVAL_MINUTES_ENV,
            DEFAULT_MIN_CHECK_INTERVAL_MINUTES,
            1,
        ),
        "lookback_days": _env_int(FRAUD_STORE_LOOKBACK_DAYS_ENV, DEFAULT_LOOKBACK_DAYS, 1),
    }


def _build_stats(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "enabled": bool(config.get("enabled")),
        "interval_seconds": int(config.get("interval_seconds") or DEFAULT_MONITOR_INTERVAL_SECONDS),
        "min_check_interval_minutes": int(
            config.get("min_check_interval_minutes") or DEFAULT_MIN_CHECK_INTERVAL_MINUTES
        ),
        "lookback_days": int(config.get("lookback_days") or DEFAULT_LOOKBACK_DAYS),
        "candidate_listing_count": 0,
        "target_store_count": 0,
        "checked_count": 0,
        "skipped_count": 0,
        "active_count": 0,
        "inactive_count": 0,
        "error_count": 0,
        "unknown_count": 0,
        "label_candidates_upserted": 0,
        "label_rows_updated": 0,
        "store_errors": 0,
        "fatal_error": None,
    }


def _fetch_recent_listing_candidates(
    cursor,
    *,
    lookback_days: int,
    limit: int = DEFAULT_LISTING_CANDIDATE_LIMIT,
) -> List[Dict[str, Any]]:
    safe_limit = max(int(limit), 1)
    try:
        cursor.execute(
            """
            SELECT
                CAST(sr.seller_store_seq AS CHAR) AS store_id,
                CAST(sr.product_id AS CHAR) AS product_id,
                sr.sort_date AS listing_sort_date,
                MIN(sr.fetched_at) AS discovered_at
            FROM search_results sr
            LEFT JOIN search_queries sq
              ON sq.id = sr.search_query_id
            WHERE sr.seller_store_seq IS NOT NULL
              AND sr.product_id IS NOT NULL
              AND CHAR_LENGTH(TRIM(CAST(sr.product_id AS CHAR))) > 0
              AND sr.sort_date IS NOT NULL
              AND sr.sort_date >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)
              AND (sq.source IS NULL OR sq.source = 'joongna')
            GROUP BY sr.seller_store_seq, sr.product_id, sr.sort_date
            ORDER BY sr.sort_date DESC
            LIMIT %s
            """,
            (lookback_days, safe_limit),
        )
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" not in lowered and "doesn't exist" not in lowered:
            raise
        cursor.execute(
            """
            SELECT
                CAST(sr.seller_store_seq AS CHAR) AS store_id,
                CAST(sr.product_id AS CHAR) AS product_id,
                sr.sort_date AS listing_sort_date,
                MIN(sr.fetched_at) AS discovered_at
            FROM search_results sr
            WHERE sr.seller_store_seq IS NOT NULL
              AND sr.product_id IS NOT NULL
              AND CHAR_LENGTH(TRIM(CAST(sr.product_id AS CHAR))) > 0
              AND sr.sort_date IS NOT NULL
              AND sr.sort_date >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)
            GROUP BY sr.seller_store_seq, sr.product_id, sr.sort_date
            ORDER BY sr.sort_date DESC
            LIMIT %s
            """,
            (lookback_days, safe_limit),
        )
    rows = cursor.fetchall() or []

    candidates: List[Dict[str, Any]] = []
    for row in rows:
        store_id = _normalize_store_id(row.get("store_id"))
        product_id = _safe_text(row.get("product_id"))
        listing_sort_date = _safe_datetime(row.get("listing_sort_date"))
        if store_id is None or product_id is None or listing_sort_date is None:
            continue

        candidates.append(
            {
                "store_id": store_id,
                "product_id": product_id,
                "listing_sort_date": listing_sort_date,
                "discovered_at": _safe_datetime(row.get("discovered_at")),
            }
        )
    return candidates


def _build_store_targets(listing_candidates: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    dedup: Dict[str, Dict[str, Any]] = {}
    for candidate in listing_candidates:
        store_id = candidate.get("store_id")
        if not isinstance(store_id, str) or not store_id:
            continue
        if store_id in dedup:
            continue
        dedup[store_id] = {
            "store_id": store_id,
            "first_seen_product_id": candidate.get("product_id"),
            "first_seen_sort_date": candidate.get("listing_sort_date"),
        }
    return list(dedup.values())


def _chunked(values: List[str], chunk_size: int) -> Iterable[List[str]]:
    for start in range(0, len(values), chunk_size):
        yield values[start : start + chunk_size]


def _fetch_last_checked_map(cursor, store_ids: List[str]) -> Dict[str, datetime]:
    if not store_ids:
        return {}

    mapping: Dict[str, datetime] = {}
    for store_chunk in _chunked(store_ids, 500):
        placeholders = ", ".join(["%s"] * len(store_chunk))
        cursor.execute(
            f"""
            SELECT store_id, MAX(checked_at) AS last_checked_at
            FROM fraud_store_status_snapshots
            WHERE store_id IN ({placeholders})
            GROUP BY store_id
            """,
            tuple(store_chunk),
        )
        for row in cursor.fetchall() or []:
            store_id = _safe_text(row.get("store_id"))
            last_checked_at = _safe_datetime(row.get("last_checked_at"))
            if store_id and last_checked_at is not None:
                mapping[store_id] = last_checked_at
    return mapping


def _is_due_for_check(
    *,
    last_checked_at: Optional[datetime],
    checked_at: datetime,
    min_check_interval_minutes: int,
) -> bool:
    if last_checked_at is None:
        return True
    min_gap = timedelta(minutes=max(min_check_interval_minutes, 1))
    return (checked_at - last_checked_at) >= min_gap


def _find_marker(lowered_text: str, markers: Iterable[str]) -> Optional[str]:
    for marker in markers:
        lowered_marker = marker.lower()
        if lowered_marker in lowered_text:
            return marker
    return None


def _looks_like_active_store_info(body_text: str) -> bool:
    lowered = body_text.lower()
    if re.search(r'"storeseq"\s*:\s*\d+', lowered) and (
        '"storename"' in lowered
        or '"nickname"' in lowered
        or '"profileimageurl"' in lowered
        or '"reviewcount"' in lowered
    ):
        return True
    return False


def _classify_store_status_from_rsc(*, status_code: int, body_text: str) -> Tuple[str, str]:
    lowered = body_text.lower()

    if status_code in (404, 410):
        return STATUS_DELETED, f"http_{status_code}"

    # 우선순위: deleted > suspended > inactive > active > unknown > error
    deleted_marker = _find_marker(lowered, DELETED_MARKERS)
    if deleted_marker:
        return STATUS_DELETED, deleted_marker

    suspended_marker = _find_marker(lowered, SUSPENDED_MARKERS)
    if suspended_marker:
        return STATUS_SUSPENDED, suspended_marker

    inactive_marker = _find_marker(lowered, INACTIVE_MARKERS)
    if inactive_marker:
        return STATUS_INACTIVE, inactive_marker

    if _looks_like_active_store_info(body_text):
        return STATUS_ACTIVE, "store_info_detected"

    return STATUS_UNKNOWN, f"http_{status_code}_unknown"


def _summarize_rsc_response(
    *,
    url: str,
    status_code: int,
    body_text: str,
    marker: str,
    status: str,
) -> Dict[str, Any]:
    excerpt = body_text[:240] if body_text else ""
    return {
        "rsc_url": url,
        "http_status": status_code,
        "status": status,
        "detected_marker": marker,
        "response_size_bytes": len(body_text.encode("utf-8")) if body_text else 0,
        "contains_store_name_field": '"storeName"' in body_text,
        "contains_nick_name_field": '"nickName"' in body_text,
        "body_excerpt": excerpt,
    }


def _decode_response_body_text(response: Any) -> str:
    raw_content = getattr(response, "content", None)
    if isinstance(raw_content, (bytes, bytearray)):
        encodings = [
            "utf-8",
            _safe_text(getattr(response, "apparent_encoding", None)),
            _safe_text(getattr(response, "encoding", None)),
        ]
        for encoding in encodings:
            if not encoding:
                continue
            try:
                return raw_content.decode(encoding)
            except Exception:
                continue
        try:
            return raw_content.decode("utf-8", errors="replace")
        except Exception:
            pass

    text_value = getattr(response, "text", None)
    if isinstance(text_value, str):
        return text_value
    return ""


def _probe_store_status(store_id: str) -> Dict[str, Any]:
    checked_at = _utc_now_naive()
    normalized_store_id = _normalize_store_id(store_id)
    if normalized_store_id is None:
        return {
            "checked_at": checked_at,
            "status": STATUS_ERROR,
            "is_active": 0,
            "raw_status_text": "invalid_store_id",
            "raw_response_json": {"reason": "invalid_store_id"},
            "error_message": "invalid_store_id",
        }

    rsc_url = STORE_RSC_URL_TEMPLATE.format(store_id=normalized_store_id)
    headers = dict(STORE_RSC_HEADERS)
    headers["referer"] = STORE_PAGE_REFERER_TEMPLATE.format(store_id=normalized_store_id)

    try:
        response = requests.get(
            rsc_url,
            headers=headers,
            timeout=STORE_RSC_REQUEST_TIMEOUT_SECONDS,
        )
        status_code = int(response.status_code)
        body_text = _decode_response_body_text(response)
        status, marker = _classify_store_status_from_rsc(
            status_code=status_code,
            body_text=body_text,
        )
        summary = _summarize_rsc_response(
            url=rsc_url,
            status_code=status_code,
            body_text=body_text,
            marker=marker,
            status=status,
        )
        return {
            "checked_at": checked_at,
            "status": status,
            "is_active": 1 if status == STATUS_ACTIVE else 0,
            "raw_status_text": marker,
            "raw_response_json": summary,
            "error_message": None,
        }
    except Exception as exc:
        message = str(exc)
        return {
            "checked_at": checked_at,
            "status": STATUS_ERROR,
            "is_active": 0,
            "raw_status_text": message,
            "raw_response_json": {
                "rsc_url": rsc_url,
                "exception_type": type(exc).__name__,
            },
            "error_message": message,
        }


def _insert_status_snapshot(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    status: str,
    is_active: int,
    raw_status_text: Optional[str],
    raw_response_json: Any,
    first_seen_product_id: Optional[str],
    first_seen_sort_date: Optional[datetime],
    error_message: Optional[str],
):
    raw_json_text = None
    if raw_response_json is not None:
        try:
            raw_json_text = json.dumps(raw_response_json, ensure_ascii=False)
        except Exception:
            raw_json_text = None

    cursor.execute(
        """
        INSERT INTO fraud_store_status_snapshots (
            store_id,
            checked_at,
            status,
            is_active,
            raw_status_text,
            raw_response_json,
            first_seen_product_id,
            first_seen_sort_date,
            error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            store_id,
            checked_at,
            status,
            is_active,
            raw_status_text,
            raw_json_text,
            first_seen_product_id,
            first_seen_sort_date,
            error_message,
        ),
    )


def _compute_activity_snapshot_from_db(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    lookback_days: int,
) -> Dict[str, int]:
    lookback_from = checked_at - timedelta(days=max(lookback_days, 1))
    last_1h_from = checked_at - timedelta(hours=1)
    last_6h_from = checked_at - timedelta(hours=6)
    last_24h_from = checked_at - timedelta(hours=24)
    last_7d_from = checked_at - timedelta(days=7)

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN dedup.latest_sort_date >= %s THEN 1 ELSE 0 END), 0) AS posts_last_1h,
            COALESCE(SUM(CASE WHEN dedup.latest_sort_date >= %s THEN 1 ELSE 0 END), 0) AS posts_last_6h,
            COALESCE(SUM(CASE WHEN dedup.latest_sort_date >= %s THEN 1 ELSE 0 END), 0) AS posts_last_24h,
            COALESCE(SUM(CASE WHEN dedup.latest_sort_date >= %s THEN 1 ELSE 0 END), 0) AS posts_last_7d,
            COALESCE(COUNT(*), 0) AS visible_product_count
        FROM (
            SELECT
                CAST(sr.product_id AS CHAR) AS product_id,
                MAX(sr.sort_date) AS latest_sort_date
            FROM search_results sr
            WHERE sr.seller_store_seq = %s
              AND sr.sort_date IS NOT NULL
              AND sr.sort_date >= %s
            GROUP BY sr.product_id
        ) dedup
        """,
        (
            last_1h_from,
            last_6h_from,
            last_24h_from,
            last_7d_from,
            store_id,
            lookback_from,
        ),
    )
    row = cursor.fetchone() or {}
    return {
        "posts_last_1h": int(row.get("posts_last_1h") or 0),
        "posts_last_6h": int(row.get("posts_last_6h") or 0),
        "posts_last_24h": int(row.get("posts_last_24h") or 0),
        "posts_last_7d": int(row.get("posts_last_7d") or 0),
        "visible_product_count": int(row.get("visible_product_count") or 0),
    }


def _insert_activity_snapshot(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    activity: Dict[str, int],
    first_seen_product_id: Optional[str],
    first_seen_sort_date: Optional[datetime],
):
    cursor.execute(
        """
        INSERT INTO fraud_store_activity_snapshots (
            store_id,
            checked_at,
            posts_last_1h,
            posts_last_6h,
            posts_last_24h,
            posts_last_7d,
            visible_product_count,
            first_seen_product_id,
            first_seen_sort_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            store_id,
            checked_at,
            int(activity.get("posts_last_1h") or 0),
            int(activity.get("posts_last_6h") or 0),
            int(activity.get("posts_last_24h") or 0),
            int(activity.get("posts_last_7d") or 0),
            activity.get("visible_product_count"),
            first_seen_product_id,
            first_seen_sort_date,
        ),
    )


def _upsert_training_label_candidates(cursor, listing_candidates: List[Dict[str, Any]]) -> int:
    if not listing_candidates:
        return 0

    rows = []
    for candidate in listing_candidates:
        rows.append(
            (
                candidate.get("product_id"),
                candidate.get("store_id"),
                candidate.get("listing_sort_date"),
                candidate.get("discovered_at"),
            )
        )

    cursor.executemany(
        """
        INSERT INTO fraud_training_label_candidates (
            product_id,
            store_id,
            listing_sort_date,
            discovered_at
        )
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            store_id = VALUES(store_id),
            listing_sort_date = VALUES(listing_sort_date),
            discovered_at = COALESCE(fraud_training_label_candidates.discovered_at, VALUES(discovered_at))
        """,
        rows,
    )
    return len(rows)


def _first_time_on_or_after(sorted_times: List[datetime], threshold: datetime) -> Optional[datetime]:
    if not sorted_times:
        return None
    index = bisect_left(sorted_times, threshold)
    if index >= len(sorted_times):
        return None
    return sorted_times[index]


def _refresh_training_labels_for_candidates(
    cursor,
    *,
    listing_candidates: List[Dict[str, Any]],
) -> int:
    if not listing_candidates:
        return 0

    candidates_by_store: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in listing_candidates:
        store_id = candidate.get("store_id")
        listing_sort_date = candidate.get("listing_sort_date")
        if not isinstance(store_id, str) or not store_id:
            continue
        if not isinstance(listing_sort_date, datetime):
            continue
        candidates_by_store.setdefault(store_id, []).append(candidate)

    update_rows = []
    for store_id, store_candidates in candidates_by_store.items():
        min_sort_date = min(
            candidate["listing_sort_date"] for candidate in store_candidates if candidate.get("listing_sort_date")
        )
        cursor.execute(
            """
            SELECT checked_at, status
            FROM fraud_store_status_snapshots
            WHERE store_id = %s
              AND checked_at >= %s
            ORDER BY checked_at ASC
            """,
            (store_id, min_sort_date),
        )
        snapshot_rows = cursor.fetchall() or []

        inactive_times: List[datetime] = []
        active_times: List[datetime] = []
        for row in snapshot_rows:
            checked_at = _safe_datetime(row.get("checked_at"))
            status = _safe_text(row.get("status"))
            if checked_at is None or status is None:
                continue
            normalized_status = status.lower()
            if normalized_status == STATUS_ACTIVE:
                active_times.append(checked_at)
            if normalized_status in INACTIVE_STORE_STATUSES:
                inactive_times.append(checked_at)

        for candidate in store_candidates:
            product_id = candidate.get("product_id")
            listing_sort_date = candidate.get("listing_sort_date")
            if not isinstance(product_id, str) or not product_id:
                continue
            if not isinstance(listing_sort_date, datetime):
                continue

            first_inactive_at = _first_time_on_or_after(inactive_times, listing_sort_date)
            inactive_after_minutes: Optional[int] = None
            label: Optional[int] = None
            label_reason: str = "pending_observation"

            if first_inactive_at is not None:
                delta_minutes = int((first_inactive_at - listing_sort_date).total_seconds() // 60)
                inactive_after_minutes = max(delta_minutes, 0)
                if 0 <= inactive_after_minutes <= INACTIVE_LABEL_MAX_MINUTES:
                    label = 1
                    label_reason = "store_inactive_within_7d"
                else:
                    label = None
                    label_reason = "inactive_after_7d"
            else:
                stable_threshold = listing_sort_date + timedelta(days=14)
                active_after_threshold = _first_time_on_or_after(active_times, stable_threshold)
                if active_after_threshold is not None:
                    label = 0
                    label_reason = "store_active_after_14d"

            update_rows.append(
                (
                    first_inactive_at,
                    inactive_after_minutes,
                    label,
                    label_reason,
                    product_id,
                )
            )

    if not update_rows:
        return 0

    cursor.executemany(
        """
        UPDATE fraud_training_label_candidates
        SET
            first_inactive_at = %s,
            inactive_after_minutes = %s,
            label = %s,
            label_reason = %s
        WHERE product_id = %s
        """,
        update_rows,
    )
    return len(update_rows)


def run_fraud_store_monitor_once(
    *,
    min_check_interval_minutes: Optional[int] = None,
    lookback_days: Optional[int] = None,
    listing_candidate_limit: int = DEFAULT_LISTING_CANDIDATE_LIMIT,
    force_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    config = get_fraud_store_monitor_config()
    if force_enabled is not None:
        config["enabled"] = bool(force_enabled)
    if min_check_interval_minutes is not None:
        config["min_check_interval_minutes"] = max(int(min_check_interval_minutes), 1)
    if lookback_days is not None:
        config["lookback_days"] = max(int(lookback_days), 1)

    stats = _build_stats(config)
    if not stats["enabled"]:
        return stats

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        listing_candidates = _fetch_recent_listing_candidates(
            cursor,
            lookback_days=stats["lookback_days"],
            limit=listing_candidate_limit,
        )
        stats["candidate_listing_count"] = len(listing_candidates)

        if listing_candidates:
            stats["label_candidates_upserted"] = _upsert_training_label_candidates(cursor, listing_candidates)

        store_targets = _build_store_targets(listing_candidates)
        stats["target_store_count"] = len(store_targets)

        store_ids = [target["store_id"] for target in store_targets]
        last_checked_map = _fetch_last_checked_map(cursor, store_ids=store_ids)

        for target in store_targets:
            store_id = target["store_id"]
            checked_at = _utc_now_naive()
            last_checked_at = last_checked_map.get(store_id)
            if not _is_due_for_check(
                last_checked_at=last_checked_at,
                checked_at=checked_at,
                min_check_interval_minutes=stats["min_check_interval_minutes"],
            ):
                stats["skipped_count"] += 1
                continue

            try:
                probe = _probe_store_status(store_id)
                _insert_status_snapshot(
                    cursor,
                    store_id=store_id,
                    checked_at=probe.get("checked_at") or checked_at,
                    status=_safe_text(probe.get("status")) or STATUS_UNKNOWN,
                    is_active=int(probe.get("is_active") or 0),
                    raw_status_text=_safe_text(probe.get("raw_status_text")),
                    raw_response_json=probe.get("raw_response_json"),
                    first_seen_product_id=_safe_text(target.get("first_seen_product_id")),
                    first_seen_sort_date=_safe_datetime(target.get("first_seen_sort_date")),
                    error_message=_safe_text(probe.get("error_message")),
                )

                activity = _compute_activity_snapshot_from_db(
                    cursor,
                    store_id=store_id,
                    checked_at=probe.get("checked_at") or checked_at,
                    lookback_days=stats["lookback_days"],
                )
                _insert_activity_snapshot(
                    cursor,
                    store_id=store_id,
                    checked_at=probe.get("checked_at") or checked_at,
                    activity=activity,
                    first_seen_product_id=_safe_text(target.get("first_seen_product_id")),
                    first_seen_sort_date=_safe_datetime(target.get("first_seen_sort_date")),
                )

                normalized_status = (_safe_text(probe.get("status")) or STATUS_UNKNOWN).lower()
                if normalized_status == STATUS_ACTIVE:
                    stats["active_count"] += 1
                elif normalized_status in INACTIVE_STORE_STATUSES:
                    stats["inactive_count"] += 1
                elif normalized_status == STATUS_ERROR:
                    stats["error_count"] += 1
                else:
                    stats["unknown_count"] += 1

                stats["checked_count"] += 1
            except Exception as exc:
                stats["store_errors"] += 1
                stats["error_count"] += 1
                stats["checked_count"] += 1
                try:
                    _insert_status_snapshot(
                        cursor,
                        store_id=store_id,
                        checked_at=checked_at,
                        status=STATUS_ERROR,
                        is_active=0,
                        raw_status_text=_safe_text(exc),
                        raw_response_json={"exception_type": type(exc).__name__},
                        first_seen_product_id=_safe_text(target.get("first_seen_product_id")),
                        first_seen_sort_date=_safe_datetime(target.get("first_seen_sort_date")),
                        error_message=_safe_text(exc),
                    )
                except Exception:
                    pass

        if listing_candidates:
            stats["label_rows_updated"] = _refresh_training_labels_for_candidates(
                cursor,
                listing_candidates=listing_candidates,
            )

        connection.commit()
        return stats
    except Exception as exc:
        stats["fatal_error"] = str(exc)
        if connection is not None and connection.is_connected():
            connection.rollback()
        return stats
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
