import json
import os
import re
from hashlib import sha256
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

STORE_MY_STORE_URL_TEMPLATE = "https://main-api.joongna.com/v2/my-store/{store_id}"
STORE_MY_STORE_REQUEST_TIMEOUT_SECONDS = 10
STORE_MY_STORE_HEADERS = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0",
}

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
    "페이지를 찾을 수 없습니다",
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


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_bool_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    normalized = _safe_text(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return 1
    if lowered in {"0", "false", "no", "n", "off"}:
        return 0
    parsed = _safe_int(value)
    if parsed is None:
        return None
    return 1 if parsed != 0 else 0


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


def _normalize_store_name(name: Any) -> Optional[str]:
    normalized = _safe_text(name)
    if normalized is None:
        return None
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    return collapsed or None


def _sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _build_store_name_fingerprint(store_id: str, store_name: str) -> str:
    normalized_name = _normalize_store_name(store_name) or ""
    return _sha256_hex(f"{store_id}|{normalized_name}")


def _build_profile_fingerprint(store_id: str, profile: Dict[str, Any]) -> str:
    normalized_name = _normalize_store_name(profile.get("store_name")) or ""
    tokens = [
        store_id,
        normalized_name,
        _safe_text(profile.get("profile_image_url")) or "",
        str(_safe_int(profile.get("review_count")) or ""),
        str(_safe_int(profile.get("reliability_score")) or ""),
        str(_safe_int(profile.get("activity_score")) or ""),
        str(_safe_int(profile.get("trust_score")) or ""),
        str(_safe_int(profile.get("safe_trade_count")) or ""),
        str(_safe_int(profile.get("store_level_number")) or ""),
    ]
    return _sha256_hex("|".join(tokens))


def _snapshot_datetime_key(value: Any) -> Optional[str]:
    parsed = _safe_datetime(value)
    if parsed is None:
        return None
    return parsed.isoformat(sep=" ", timespec="seconds")


def _snapshot_text_hash(value: Any) -> Optional[str]:
    text = _safe_text(value)
    if text is None:
        return None
    return _sha256_hex(text)


def _snapshot_fingerprint(payload: Dict[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return _sha256_hex(normalized)


def _is_unknown_column_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "unknown column" in lowered


def _is_missing_table_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "unknown table" in lowered or "doesn't exist" in lowered


def _is_schema_missing_error(exc: Exception) -> bool:
    return _is_unknown_column_error(exc) or _is_missing_table_error(exc)


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
        "product_snapshot_candidate_count": 0,
        "product_snapshots_upserted": 0,
        "profile_field_snapshots_inserted": 0,
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


def _fetch_recent_product_snapshot_candidates(
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
                CAST(sr.product_id AS CHAR) AS product_id,
                CAST(sr.seller_store_seq AS CHAR) AS store_id,
                sr.fetched_at AS observed_at,
                sr.sort_date AS sort_date,
                sr.price AS price_krw,
                sr.title AS title,
                sr.url AS url,
                sr.raw_json AS raw_payload_json,
                'search_results' AS source
            FROM search_results sr
            LEFT JOIN search_queries sq
              ON sq.id = sr.search_query_id
            WHERE sr.seller_store_seq IS NOT NULL
              AND sr.product_id IS NOT NULL
              AND CHAR_LENGTH(TRIM(CAST(sr.product_id AS CHAR))) > 0
              AND sr.sort_date IS NOT NULL
              AND sr.fetched_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)
              AND (sq.source IS NULL OR sq.source = 'joongna')
            ORDER BY sr.fetched_at ASC, sr.id ASC
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
                CAST(sr.product_id AS CHAR) AS product_id,
                CAST(sr.seller_store_seq AS CHAR) AS store_id,
                sr.fetched_at AS observed_at,
                sr.sort_date AS sort_date,
                sr.price AS price_krw,
                sr.title AS title,
                sr.url AS url,
                sr.raw_json AS raw_payload_json,
                'search_results' AS source
            FROM search_results sr
            WHERE sr.seller_store_seq IS NOT NULL
              AND sr.product_id IS NOT NULL
              AND CHAR_LENGTH(TRIM(CAST(sr.product_id AS CHAR))) > 0
              AND sr.sort_date IS NOT NULL
              AND sr.fetched_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)
            ORDER BY sr.fetched_at ASC, sr.id ASC
            LIMIT %s
            """,
            (lookback_days, safe_limit),
        )
    rows = cursor.fetchall() or []

    snapshot_candidates: List[Dict[str, Any]] = []
    for row in rows:
        product_id = _safe_text(row.get("product_id"))
        store_id = _normalize_store_id(row.get("store_id"))
        sort_date = _safe_datetime(row.get("sort_date"))
        observed_at = _safe_datetime(row.get("observed_at")) or _utc_now_naive()
        if product_id is None or store_id is None or sort_date is None:
            continue

        snapshot_candidates.append(
            {
                "product_id": product_id,
                "store_id": store_id,
                "observed_at": observed_at,
                "sort_date": sort_date,
                "price_krw": _safe_int(row.get("price_krw")),
                "title": _safe_text(row.get("title")),
                "url": _safe_text(row.get("url")),
                "source": _safe_text(row.get("source")) or "search_results",
                "raw_payload_json": row.get("raw_payload_json"),
            }
        )
    return snapshot_candidates


def _serialize_raw_payload_json(raw_payload: Any) -> Optional[str]:
    if raw_payload is None:
        return None

    if isinstance(raw_payload, str):
        cleaned = raw_payload.strip()
        if not cleaned:
            return None
        try:
            parsed = json.loads(cleaned)
            return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
        except Exception:
            return cleaned

    try:
        return json.dumps(raw_payload, ensure_ascii=False, sort_keys=True)
    except Exception:
        return _safe_text(raw_payload)


def _parse_raw_payload_json(raw_payload: Any) -> Optional[Any]:
    if raw_payload is None:
        return None
    if isinstance(raw_payload, (dict, list)):
        return raw_payload
    raw_text = _safe_text(raw_payload)
    if raw_text is None:
        return None
    try:
        return json.loads(raw_text)
    except Exception:
        return None


def _extract_body_text_from_payload(raw_payload: Any) -> Optional[str]:
    payload = _parse_raw_payload_json(raw_payload)
    if not isinstance(payload, dict):
        return None

    for key in ("body", "content", "description", "desc", "productDescription", "productDesc", "text"):
        parsed = _safe_text(payload.get(key))
        if parsed is not None:
            return parsed

    nested_data = payload.get("data")
    if isinstance(nested_data, dict):
        for key in ("body", "content", "description", "desc", "productDescription", "productDesc", "text"):
            parsed = _safe_text(nested_data.get(key))
            if parsed is not None:
                return parsed
    return None


def _build_product_state_fingerprint(
    *,
    product_id: str,
    price_krw: Optional[int],
    sort_date: Optional[datetime],
    title_hash: Optional[str],
    content_hash: Optional[str],
) -> str:
    sort_date_key = sort_date.isoformat(sep=" ", timespec="seconds") if sort_date is not None else ""
    return _sha256_hex(
        "|".join(
            [
                product_id,
                str(price_krw) if price_krw is not None else "",
                sort_date_key,
                title_hash or "",
                content_hash or "",
            ]
        )
    )


def _normalize_product_snapshot_row(candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    product_id = _safe_text(candidate.get("product_id"))
    store_id = _normalize_store_id(candidate.get("store_id"))
    observed_at = _safe_datetime(candidate.get("observed_at")) or _utc_now_naive()
    sort_date = _safe_datetime(candidate.get("sort_date"))
    if product_id is None or store_id is None:
        return None

    title = _safe_text(candidate.get("title"))
    raw_payload_json_text = _serialize_raw_payload_json(candidate.get("raw_payload_json"))
    body_text = _extract_body_text_from_payload(candidate.get("raw_payload_json"))
    title_hash = _sha256_hex(title) if title is not None else None
    body_hash = _sha256_hex(body_text) if body_text is not None else None
    content_source = body_text if body_text is not None else raw_payload_json_text
    content_hash = _sha256_hex(content_source) if content_source is not None else None
    fingerprint = _build_product_state_fingerprint(
        product_id=product_id,
        price_krw=_safe_int(candidate.get("price_krw")),
        sort_date=sort_date,
        title_hash=title_hash,
        content_hash=content_hash,
    )

    return {
        "product_id": product_id,
        "store_id": store_id,
        "observed_at": observed_at,
        "sort_date": sort_date,
        "price_krw": _safe_int(candidate.get("price_krw")),
        "title": title,
        "body_hash": body_hash,
        "title_hash": title_hash,
        "content_hash": content_hash,
        "source": _safe_text(candidate.get("source")) or "search_results",
        "url": _safe_text(candidate.get("url")),
        "raw_payload_json": raw_payload_json_text,
        "fingerprint": fingerprint,
    }


def _fetch_latest_product_snapshot(cursor, *, product_id: str) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            id,
            product_id,
            store_id,
            observed_at,
            sort_date,
            price_krw,
            title_hash,
            body_hash,
            content_hash
        FROM fraud_product_snapshots
        WHERE product_id = %s
        ORDER BY observed_at DESC, id DESC
        LIMIT 1
        """,
        (product_id,),
    )
    row = cursor.fetchone() or {}
    if not row or not isinstance(row, dict):
        return None
    return row


def _product_snapshot_fingerprint_from_row(row: Dict[str, Any]) -> str:
    product_id = _safe_text(row.get("product_id")) or ""
    return _build_product_state_fingerprint(
        product_id=product_id,
        price_krw=_safe_int(row.get("price_krw")),
        sort_date=_safe_datetime(row.get("sort_date")),
        title_hash=_safe_text(row.get("title_hash")),
        content_hash=_safe_text(row.get("content_hash")),
    )


def _resolve_snapshot_reason(
    *,
    previous_snapshot: Optional[Dict[str, Any]],
    current_snapshot: Dict[str, Any],
) -> str:
    if previous_snapshot is None:
        return "first_seen"

    previous_price = _safe_int(previous_snapshot.get("price_krw"))
    current_price = _safe_int(current_snapshot.get("price_krw"))
    if previous_price != current_price:
        return "price_changed"

    previous_content_hash = _safe_text(previous_snapshot.get("content_hash"))
    current_content_hash = _safe_text(current_snapshot.get("content_hash"))
    if previous_content_hash != current_content_hash:
        return "content_changed"

    previous_body_hash = _safe_text(previous_snapshot.get("body_hash"))
    current_body_hash = _safe_text(current_snapshot.get("body_hash"))
    if previous_body_hash != current_body_hash:
        return "body_changed"

    previous_title_hash = _safe_text(previous_snapshot.get("title_hash"))
    current_title_hash = _safe_text(current_snapshot.get("title_hash"))
    if previous_title_hash != current_title_hash:
        return "title_changed"

    previous_sort_date = _safe_datetime(previous_snapshot.get("sort_date"))
    current_sort_date = _safe_datetime(current_snapshot.get("sort_date"))
    if previous_sort_date != current_sort_date:
        return "sort_date_changed"
    return "periodic"


def _insert_product_snapshot(cursor, *, snapshot_row: Dict[str, Any], snapshot_reason: str) -> None:
    cursor.execute(
        """
        INSERT INTO fraud_product_snapshots (
            product_id,
            store_id,
            observed_at,
            sort_date,
            price_krw,
            title,
            body_hash,
            title_hash,
            content_hash,
            source,
            url,
            snapshot_reason,
            raw_payload_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            snapshot_row.get("product_id"),
            snapshot_row.get("store_id"),
            snapshot_row.get("observed_at"),
            snapshot_row.get("sort_date"),
            _safe_int(snapshot_row.get("price_krw")),
            _safe_text(snapshot_row.get("title")),
            _safe_text(snapshot_row.get("body_hash")),
            _safe_text(snapshot_row.get("title_hash")),
            _safe_text(snapshot_row.get("content_hash")),
            _safe_text(snapshot_row.get("source")),
            _safe_text(snapshot_row.get("url")),
            snapshot_reason,
            snapshot_row.get("raw_payload_json"),
        ),
    )


def _upsert_product_state_snapshots(cursor, snapshot_candidates: List[Dict[str, Any]]) -> int:
    if not snapshot_candidates:
        return 0

    normalized_candidates = []
    for candidate in snapshot_candidates:
        normalized = _normalize_product_snapshot_row(candidate)
        if normalized is not None:
            normalized_candidates.append(normalized)

    normalized_candidates.sort(
        key=lambda row: (
            _safe_datetime(row.get("observed_at")) or datetime.min,
            _safe_text(row.get("product_id")) or "",
        )
    )

    inserted_count = 0
    latest_snapshot_cache: Dict[str, Optional[Dict[str, Any]]] = {}
    for normalized in normalized_candidates:
        product_id = normalized["product_id"]
        observed_at = _safe_datetime(normalized.get("observed_at")) or _utc_now_naive()

        previous_snapshot = latest_snapshot_cache.get(product_id)
        previous_observed_at = (
            _safe_datetime(previous_snapshot.get("observed_at"))
            if previous_snapshot is not None
            else None
        )
        if product_id not in latest_snapshot_cache or (
            previous_observed_at is not None and previous_observed_at > observed_at
        ):
            try:
                previous_snapshot = _fetch_latest_product_snapshot_before(
                    cursor,
                    product_id=product_id,
                    observed_at=observed_at,
                )
            except Exception as exc:
                if _is_schema_missing_error(exc):
                    return inserted_count
                raise
            latest_snapshot_cache[product_id] = previous_snapshot

        if previous_snapshot is not None:
            previous_fingerprint = _product_snapshot_fingerprint_from_row(previous_snapshot)
            if previous_fingerprint == normalized.get("fingerprint"):
                continue

        snapshot_reason = _resolve_snapshot_reason(
            previous_snapshot=previous_snapshot,
            current_snapshot=normalized,
        )
        try:
            _insert_product_snapshot(cursor, snapshot_row=normalized, snapshot_reason=snapshot_reason)
        except Exception as exc:
            if _is_schema_missing_error(exc):
                return inserted_count
            raise
        inserted_count += 1
        latest_snapshot_cache[product_id] = normalized
    return inserted_count


def _fetch_latest_product_snapshot_before(
    cursor,
    *,
    product_id: str,
    observed_at: datetime,
) -> Optional[Dict[str, Any]]:
    """
    학습용 예시 SQL:
    - 상점 정지 이전 상품 스냅샷 이력:
      SELECT fps.*
      FROM fraud_product_snapshots fps
      JOIN fraud_training_label_candidates fl
        ON fl.product_id = fps.product_id
      WHERE fl.label = 1
        AND fps.observed_at <= fl.first_inactive_at
      ORDER BY fps.product_id, fps.observed_at DESC;

    - 특정 시점 직전 1건:
      SELECT *
      FROM fraud_product_snapshots
      WHERE product_id = ?
        AND observed_at <= ?
      ORDER BY observed_at DESC
      LIMIT 1;
    """
    cursor.execute(
        """
        SELECT
            id,
            product_id,
            store_id,
            observed_at,
            sort_date,
            price_krw,
            title,
            body_hash,
            title_hash,
            content_hash,
            source,
            url,
            snapshot_reason
        FROM fraud_product_snapshots
        WHERE product_id = %s
          AND observed_at <= %s
        ORDER BY observed_at DESC, id DESC
        LIMIT 1
        """,
        (product_id, observed_at),
    )
    row = cursor.fetchone() or {}
    if not row or not isinstance(row, dict):
        return None
    return row


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


def _extract_meta_from_json(payload: Any) -> Tuple[Optional[int], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return None, None
    return _safe_int(meta.get("code")), _safe_text(meta.get("message"))


def _extract_my_store_profile(store_id: str, payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    profile_image_url = _safe_text(data.get("profileImageUrl")) or _safe_text(data.get("storeImgUrl"))
    store_name = _normalize_store_name(data.get("storeName")) or _normalize_store_name(data.get("nickName"))
    return {
        "store_id": store_id,
        "store_name": store_name,
        "store_name_fingerprint": _build_store_name_fingerprint(store_id, store_name) if store_name else None,
        "profile_image_url": profile_image_url,
        "has_default_profile_image": 1 if "default/profile_" in (profile_image_url or "").lower() else 0,
        "store_level": _safe_text(data.get("storeLevel")),
        "store_level_number": _safe_int(data.get("storeLevelNumber")),
        "review_count": _safe_int(data.get("reviewCount")),
        "reliability_score": _safe_int(data.get("reliabilityScore")),
        "activity_score": _safe_int(data.get("activityScore")),
        "notified_score": _safe_int(data.get("notifiedScore")),
        "safe_trade_count": _safe_int(data.get("safeTradeCount")),
        "trust_score": _safe_int(data.get("trustScore")),
        "chat_response_ratio": _safe_text(data.get("chatResponseRatio")),
        "chat_response_time": _safe_int(data.get("chatResponseTime")),
        "chat_response_time_text": _safe_text(data.get("chatResponseTimeText")),
        "visit_today_count": _safe_int(data.get("visitTodayCount")),
        "visit_total_count": _safe_int(data.get("visitTotalCount")),
        "store_grade": _safe_float(data.get("storeGrade")),
        "user_type": _safe_int(data.get("userType")),
        "partner_center_seller_yn": _safe_bool_int(data.get("partnerCenterSellerYn")),
        "is_official_account": _safe_bool_int(data.get("isOfficialAccount")),
        "store_desc": _safe_text(data.get("storeDesc")) or _safe_text(data.get("storeAbout")),
        "raw_json": data,
    }


def _summarize_my_store_response(
    *,
    url: str,
    status_code: int,
    meta_code: Optional[int],
    meta_message: Optional[str],
    payload: Any,
) -> Dict[str, Any]:
    if isinstance(payload, dict):
        data = payload.get("data")
    else:
        data = None
    snippet_obj = payload if isinstance(payload, (dict, list)) else {"value": _safe_text(payload)}
    snippet_text = ""
    try:
        snippet_text = json.dumps(snippet_obj, ensure_ascii=False)[:240]
    except Exception:
        snippet_text = _safe_text(snippet_obj) or ""
    return {
        "my_store_url": url,
        "http_status": status_code,
        "meta_code": meta_code,
        "meta_message": meta_message,
        "has_data_object": isinstance(data, dict),
        "data_keys": sorted(list(data.keys())) if isinstance(data, dict) else [],
        "payload_excerpt": snippet_text,
    }


def _classify_store_status_from_my_store(
    *,
    status_code: int,
    meta_code: Optional[int],
    meta_message: Optional[str],
    profile: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    lowered_message = (meta_message or "").lower()
    if status_code in (404, 410):
        return STATUS_DELETED, f"http_{status_code}"
    if meta_code == 0 and isinstance(profile, dict):
        return STATUS_ACTIVE, "my_store_success"
    if meta_code == 400999 or "이용제한" in (meta_message or "") or "restricted" in lowered_message:
        return STATUS_SUSPENDED, "my_store_suspended_message"
    return STATUS_UNKNOWN, "my_store_unknown"


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


def _extract_rsc_value(body_text: str, key: str) -> Any:
    pattern = rf'"{re.escape(key)}"\s*:\s*(null|true|false|-?\d+(?:\.\d+)?|"(?:\\.|[^"\\])*")'
    match = re.search(pattern, body_text)
    if match is None:
        return None
    token = match.group(1)
    if token == "null":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if token.startswith('"') and token.endswith('"'):
        try:
            return json.loads(token)
        except Exception:
            return token[1:-1]
    if "." in token:
        try:
            return float(token)
        except Exception:
            return None
    try:
        return int(token)
    except Exception:
        return None


def _extract_profile_from_rsc_body(store_id: str, body_text: str) -> Optional[Dict[str, Any]]:
    if not body_text:
        return None

    store_name = _normalize_store_name(_extract_rsc_value(body_text, "storeName")) or _normalize_store_name(
        _extract_rsc_value(body_text, "nickName")
    )
    profile_image_url = _safe_text(_extract_rsc_value(body_text, "profileImageUrl")) or _safe_text(
        _extract_rsc_value(body_text, "storeImgUrl")
    )
    extracted_profile = {
        "store_id": store_id,
        "store_name": store_name,
        "store_name_fingerprint": _build_store_name_fingerprint(store_id, store_name) if store_name else None,
        "profile_image_url": profile_image_url,
        "has_default_profile_image": 1 if "default/profile_" in (profile_image_url or "").lower() else 0,
        "store_level": _safe_text(_extract_rsc_value(body_text, "storeLevel")),
        "store_level_number": _safe_int(_extract_rsc_value(body_text, "storeLevelNumber")),
        "review_count": _safe_int(_extract_rsc_value(body_text, "reviewCount")),
        "reliability_score": _safe_int(_extract_rsc_value(body_text, "reliabilityScore")),
        "activity_score": _safe_int(_extract_rsc_value(body_text, "activityScore")),
        "notified_score": _safe_int(_extract_rsc_value(body_text, "notifiedScore")),
        "safe_trade_count": _safe_int(_extract_rsc_value(body_text, "safeTradeCount")),
        "trust_score": _safe_int(_extract_rsc_value(body_text, "trustScore")),
        "chat_response_ratio": _safe_text(_extract_rsc_value(body_text, "chatResponseRatio")),
        "chat_response_time": _safe_int(_extract_rsc_value(body_text, "chatResponseTime")),
        "chat_response_time_text": _safe_text(_extract_rsc_value(body_text, "chatResponseTimeText")),
        "visit_today_count": _safe_int(_extract_rsc_value(body_text, "visitTodayCount")),
        "visit_total_count": _safe_int(_extract_rsc_value(body_text, "visitTotalCount")),
        "store_grade": _safe_float(_extract_rsc_value(body_text, "storeGrade")),
        "user_type": _safe_int(_extract_rsc_value(body_text, "userType")),
        "partner_center_seller_yn": _safe_bool_int(_extract_rsc_value(body_text, "partnerCenterSellerYn")),
        "is_official_account": _safe_bool_int(_extract_rsc_value(body_text, "isOfficialAccount")),
        "store_desc": _safe_text(_extract_rsc_value(body_text, "storeDesc"))
        or _safe_text(_extract_rsc_value(body_text, "storeAbout")),
        "raw_json": {
            "source": "store_rsc",
            "storeLevel": _extract_rsc_value(body_text, "storeLevel"),
            "storeLevelNumber": _extract_rsc_value(body_text, "storeLevelNumber"),
            "reviewCount": _extract_rsc_value(body_text, "reviewCount"),
            "reliabilityScore": _extract_rsc_value(body_text, "reliabilityScore"),
            "activityScore": _extract_rsc_value(body_text, "activityScore"),
            "notifiedScore": _extract_rsc_value(body_text, "notifiedScore"),
            "safeTradeCount": _extract_rsc_value(body_text, "safeTradeCount"),
            "trustScore": _extract_rsc_value(body_text, "trustScore"),
            "visitTodayCount": _extract_rsc_value(body_text, "visitTodayCount"),
            "visitTotalCount": _extract_rsc_value(body_text, "visitTotalCount"),
            "isOfficialAccount": _extract_rsc_value(body_text, "isOfficialAccount"),
        },
    }

    # 최소한 하나 이상의 핵심 필드가 있어야 profile 로 인정한다.
    has_core_field = any(
        extracted_profile.get(key) is not None
        for key in (
            "store_name",
            "trust_score",
            "review_count",
            "store_level",
            "store_level_number",
            "safe_trade_count",
            "reliability_score",
            "activity_score",
            "notified_score",
            "visit_today_count",
            "visit_total_count",
            "is_official_account",
        )
    )
    if not has_core_field:
        return None
    return extracted_profile


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
            "source": "my_store_api",
            "http_status": None,
            "meta_code": None,
            "meta_message": "invalid_store_id",
            "raw_snippet": "invalid_store_id",
            "profile": None,
        }

    my_store_url = STORE_MY_STORE_URL_TEMPLATE.format(store_id=normalized_store_id)
    my_store_summary: Dict[str, Any] = {}
    my_store_status = STATUS_UNKNOWN
    my_store_reason = "my_store_unknown"
    my_store_http_status: Optional[int] = None
    my_store_meta_code: Optional[int] = None
    my_store_meta_message: Optional[str] = None
    my_store_profile: Optional[Dict[str, Any]] = None

    try:
        my_store_response = requests.get(
            my_store_url,
            headers=STORE_MY_STORE_HEADERS,
            timeout=STORE_MY_STORE_REQUEST_TIMEOUT_SECONDS,
        )
        my_store_http_status = int(my_store_response.status_code)
        my_store_payload = None
        try:
            my_store_payload = my_store_response.json()
        except Exception:
            my_store_payload = {"raw_text": _decode_response_body_text(my_store_response)[:240]}

        my_store_meta_code, my_store_meta_message = _extract_meta_from_json(my_store_payload)
        my_store_profile = _extract_my_store_profile(normalized_store_id, my_store_payload)
        my_store_status, my_store_reason = _classify_store_status_from_my_store(
            status_code=my_store_http_status,
            meta_code=my_store_meta_code,
            meta_message=my_store_meta_message,
            profile=my_store_profile,
        )
        my_store_summary = _summarize_my_store_response(
            url=my_store_url,
            status_code=my_store_http_status,
            meta_code=my_store_meta_code,
            meta_message=my_store_meta_message,
            payload=my_store_payload,
        )
    except Exception as exc:
        my_store_status = STATUS_ERROR
        my_store_reason = _safe_text(exc) or "my_store_error"
        my_store_summary = {
            "my_store_url": my_store_url,
            "exception_type": type(exc).__name__,
            "error_message": _safe_text(exc),
        }

    if my_store_status in {STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_DELETED}:
        return {
            "checked_at": checked_at,
            "status": my_store_status,
            "is_active": 1 if my_store_status == STATUS_ACTIVE else 0,
            "raw_status_text": my_store_reason,
            "raw_response_json": my_store_summary,
            "error_message": None if my_store_status != STATUS_ERROR else my_store_reason,
            "source": "my_store_api",
            "http_status": my_store_http_status,
            "meta_code": my_store_meta_code,
            "meta_message": my_store_meta_message,
            "raw_snippet": _safe_text((my_store_summary or {}).get("payload_excerpt")),
            "profile": my_store_profile,
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
        rsc_profile = _extract_profile_from_rsc_body(normalized_store_id, body_text) if status == STATUS_ACTIVE else None
        merged_profile = my_store_profile if isinstance(my_store_profile, dict) else rsc_profile
        merged_summary = {
            "my_store": my_store_summary,
            "rsc": summary,
            "rsc_profile_detected": bool(isinstance(rsc_profile, dict)),
        }
        final_status = status
        final_marker = marker
        if my_store_status == STATUS_ERROR and status == STATUS_UNKNOWN:
            final_status = STATUS_ERROR
            final_marker = my_store_reason
        return {
            "checked_at": checked_at,
            "status": final_status,
            "is_active": 1 if final_status == STATUS_ACTIVE else 0,
            "raw_status_text": final_marker,
            "raw_response_json": merged_summary,
            "error_message": my_store_reason if final_status == STATUS_ERROR else None,
            "source": "store_rsc",
            "http_status": status_code,
            "meta_code": my_store_meta_code,
            "meta_message": my_store_meta_message,
            "raw_snippet": _safe_text(summary.get("body_excerpt")),
            "profile": merged_profile,
        }
    except Exception as exc:
        message = str(exc)
        return {
            "checked_at": checked_at,
            "status": STATUS_ERROR,
            "is_active": 0,
            "raw_status_text": message,
            "raw_response_json": {
                "my_store": my_store_summary,
                "rsc_url": rsc_url,
                "exception_type": type(exc).__name__,
            },
            "error_message": message,
            "source": "store_rsc",
            "http_status": None,
            "meta_code": my_store_meta_code,
            "meta_message": my_store_meta_message,
            "raw_snippet": None,
            "profile": my_store_profile,
        }


def _store_status_snapshot_fingerprint_from_row(row: Dict[str, Any]) -> str:
    return _snapshot_fingerprint(
        {
            "store_seq": _safe_int(row.get("store_seq")),
            "status": _safe_text(row.get("status")),
            "status_reason": _safe_text(row.get("status_reason")),
            "source": _safe_text(row.get("source")),
            "is_active": _safe_int(row.get("is_active")),
            "http_status": _safe_int(row.get("http_status")),
            "meta_code": _safe_int(row.get("meta_code")),
            "meta_message": _safe_text(row.get("meta_message")),
            "raw_status_text_hash": _snapshot_text_hash(row.get("raw_status_text")),
            "raw_snippet_hash": _snapshot_text_hash(row.get("raw_snippet")),
            "first_seen_product_id": _safe_text(row.get("first_seen_product_id")),
            "first_seen_sort_date": _snapshot_datetime_key(row.get("first_seen_sort_date")),
            "error_message_hash": _snapshot_text_hash(row.get("error_message")),
        }
    )


def _fetch_latest_store_status_snapshot_before(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            id,
            store_id,
            store_seq,
            checked_at,
            status,
            status_reason,
            source,
            is_active,
            http_status,
            meta_code,
            meta_message,
            raw_status_text,
            raw_snippet,
            first_seen_product_id,
            first_seen_sort_date,
            error_message
        FROM fraud_store_status_snapshots
        WHERE store_id = %s
          AND checked_at <= %s
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (store_id, checked_at),
    )
    row = cursor.fetchone() or {}
    if not row or not isinstance(row, dict):
        return None
    return row


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
    source: Optional[str] = None,
    http_status: Optional[int] = None,
    meta_code: Optional[int] = None,
    meta_message: Optional[str] = None,
    raw_snippet: Optional[str] = None,
):
    raw_json_text = None
    if raw_response_json is not None:
        try:
            raw_json_text = json.dumps(raw_response_json, ensure_ascii=False)
        except Exception:
            raw_json_text = None

    candidate_row = {
        "store_seq": _safe_int(store_id),
        "status": status,
        "status_reason": raw_status_text,
        "source": source,
        "is_active": is_active,
        "http_status": http_status,
        "meta_code": meta_code,
        "meta_message": meta_message,
        "raw_status_text": raw_status_text,
        "raw_snippet": raw_snippet,
        "first_seen_product_id": first_seen_product_id,
        "first_seen_sort_date": first_seen_sort_date,
        "error_message": error_message,
    }

    try:
        previous_snapshot = _fetch_latest_store_status_snapshot_before(
            cursor,
            store_id=store_id,
            checked_at=checked_at,
        )
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise
        previous_snapshot = None

    if previous_snapshot is not None:
        previous_fingerprint = _store_status_snapshot_fingerprint_from_row(previous_snapshot)
        current_fingerprint = _store_status_snapshot_fingerprint_from_row(candidate_row)
        if previous_fingerprint == current_fingerprint:
            return

    try:
        cursor.execute(
            """
            INSERT INTO fraud_store_status_snapshots (
                store_id,
                store_seq,
                checked_at,
                status,
                status_reason,
                source,
                is_active,
                http_status,
                meta_code,
                meta_message,
                raw_status_text,
                raw_snippet,
                raw_response_json,
                first_seen_product_id,
                first_seen_sort_date,
                error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                store_id,
                _safe_int(store_id),
                checked_at,
                status,
                raw_status_text,
                source,
                is_active,
                http_status,
                meta_code,
                meta_message,
                raw_status_text,
                raw_snippet,
                raw_json_text,
                first_seen_product_id,
                first_seen_sort_date,
                error_message,
            ),
        )
        return
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

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


def _fetch_joongna_store_profile_row(cursor, store_seq: int) -> Dict[str, Any]:
    try:
        cursor.execute(
            """
            SELECT store_seq, store_name, store_name_fingerprint
            FROM joongna_store_profiles
            WHERE store_seq = %s
            LIMIT 1
            """,
            (store_seq,),
        )
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise
        try:
            cursor.execute(
                """
                SELECT store_seq, store_name
                FROM joongna_store_profiles
                WHERE store_seq = %s
                LIMIT 1
                """,
                (store_seq,),
            )
        except Exception as fallback_exc:
            if _is_schema_missing_error(fallback_exc):
                return {}
            raise
    row = cursor.fetchone() or {}
    if not isinstance(row, dict):
        return {}
    return row


def _insert_store_name_change(
    cursor,
    *,
    store_seq: int,
    old_name: Optional[str],
    new_name: str,
    old_fingerprint: Optional[str],
    new_fingerprint: str,
    changed_at: datetime,
    source: str,
):
    try:
        cursor.execute(
            """
            INSERT INTO joongna_store_name_changes (
                store_seq,
                old_name,
                new_name,
                old_fingerprint,
                new_fingerprint,
                changed_at,
                source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                store_seq,
                old_name,
                new_name,
                old_fingerprint,
                new_fingerprint,
                changed_at,
                source,
            ),
        )
    except Exception as exc:
        if _is_schema_missing_error(exc):
            return
        raise


def _upsert_joongna_store_profile_snapshot(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    profile: Dict[str, Any],
    status: str,
    status_reason: Optional[str],
    source: str,
):
    store_seq = _safe_int(store_id)
    if store_seq is None:
        return

    normalized_store_name = _normalize_store_name(profile.get("store_name"))
    store_name_fingerprint = (
        _build_store_name_fingerprint(store_id, normalized_store_name)
        if normalized_store_name is not None
        else None
    )
    profile_fingerprint = _build_profile_fingerprint(
        store_id,
        {
            "store_name": normalized_store_name,
            "profile_image_url": profile.get("profile_image_url"),
            "review_count": profile.get("review_count"),
            "reliability_score": profile.get("reliability_score"),
            "activity_score": profile.get("activity_score"),
            "trust_score": profile.get("trust_score"),
            "safe_trade_count": profile.get("safe_trade_count"),
            "store_level_number": profile.get("store_level_number"),
        },
    )

    existing_row = _fetch_joongna_store_profile_row(cursor, store_seq)
    old_name = _normalize_store_name(existing_row.get("store_name"))
    old_fingerprint = _safe_text(existing_row.get("store_name_fingerprint"))
    if normalized_store_name is not None and (
        old_fingerprint != store_name_fingerprint
        or (old_fingerprint is None and old_name != normalized_store_name)
    ):
        _insert_store_name_change(
            cursor,
            store_seq=store_seq,
            old_name=old_name,
            new_name=normalized_store_name,
            old_fingerprint=old_fingerprint,
            new_fingerprint=store_name_fingerprint,
            changed_at=checked_at,
            source=source,
        )

    try:
        cursor.execute(
            """
            INSERT INTO joongna_store_profiles (
                store_seq,
                store_name,
                store_name_fingerprint,
                profile_fingerprint,
                profile_image_url,
                store_level,
                store_level_number,
                review_count,
                reliability_score,
                activity_score,
                notified_score,
                safe_trade_count,
                trust_score,
                chat_response_ratio,
                chat_response_time,
                chat_response_time_text,
                visit_today_count,
                visit_total_count,
                store_grade,
                user_type,
                partner_center_seller_yn,
                is_official_account,
                store_desc,
                fetch_status,
                error_message,
                last_status,
                last_status_reason,
                last_status_checked_at,
                last_seen_at,
                last_fetched_at,
                next_retry_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, 'success', NULL, %s, %s, %s, %s, %s, NULL
            )
            ON DUPLICATE KEY UPDATE
                store_name = VALUES(store_name),
                store_name_fingerprint = VALUES(store_name_fingerprint),
                profile_fingerprint = VALUES(profile_fingerprint),
                profile_image_url = VALUES(profile_image_url),
                store_level = VALUES(store_level),
                store_level_number = VALUES(store_level_number),
                review_count = VALUES(review_count),
                reliability_score = VALUES(reliability_score),
                activity_score = VALUES(activity_score),
                notified_score = VALUES(notified_score),
                safe_trade_count = VALUES(safe_trade_count),
                trust_score = VALUES(trust_score),
                chat_response_ratio = VALUES(chat_response_ratio),
                chat_response_time = VALUES(chat_response_time),
                chat_response_time_text = VALUES(chat_response_time_text),
                visit_today_count = VALUES(visit_today_count),
                visit_total_count = VALUES(visit_total_count),
                store_grade = VALUES(store_grade),
                user_type = VALUES(user_type),
                partner_center_seller_yn = VALUES(partner_center_seller_yn),
                is_official_account = VALUES(is_official_account),
                store_desc = VALUES(store_desc),
                fetch_status = 'success',
                error_message = NULL,
                last_status = VALUES(last_status),
                last_status_reason = VALUES(last_status_reason),
                last_status_checked_at = VALUES(last_status_checked_at),
                last_seen_at = VALUES(last_seen_at),
                last_fetched_at = VALUES(last_fetched_at),
                next_retry_at = NULL
            """,
            (
                store_seq,
                normalized_store_name,
                store_name_fingerprint,
                profile_fingerprint,
                _safe_text(profile.get("profile_image_url")),
                _safe_text(profile.get("store_level")),
                _safe_int(profile.get("store_level_number")),
                _safe_int(profile.get("review_count")),
                _safe_int(profile.get("reliability_score")),
                _safe_int(profile.get("activity_score")),
                _safe_int(profile.get("notified_score")),
                _safe_int(profile.get("safe_trade_count")),
                _safe_int(profile.get("trust_score")),
                _safe_text(profile.get("chat_response_ratio")),
                _safe_int(profile.get("chat_response_time")),
                _safe_text(profile.get("chat_response_time_text")),
                _safe_int(profile.get("visit_today_count")),
                _safe_int(profile.get("visit_total_count")),
                _safe_float(profile.get("store_grade")),
                _safe_int(profile.get("user_type")),
                _safe_bool_int(profile.get("partner_center_seller_yn")),
                _safe_bool_int(profile.get("is_official_account")),
                _safe_text(profile.get("store_desc")),
                status,
                _safe_text(status_reason),
                checked_at,
                checked_at,
                checked_at,
            ),
        )
        return
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

    try:
        cursor.execute(
            """
            INSERT INTO joongna_store_profiles (
                store_seq,
                store_name,
                fetch_status,
                error_message,
                last_fetched_at,
                next_retry_at
            )
            VALUES (%s, %s, 'success', NULL, %s, NULL)
            ON DUPLICATE KEY UPDATE
                store_name = VALUES(store_name),
                fetch_status = 'success',
                error_message = NULL,
                last_fetched_at = VALUES(last_fetched_at),
                next_retry_at = NULL
            """,
            (
                store_seq,
                normalized_store_name,
                checked_at,
            ),
        )
    except Exception as fallback_exc:
        if _is_schema_missing_error(fallback_exc):
            return
        raise


def _upsert_joongna_store_profile_status(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    status: str,
    status_reason: Optional[str],
    error_message: Optional[str],
):
    store_seq = _safe_int(store_id)
    if store_seq is None:
        return
    try:
        cursor.execute(
            """
            INSERT INTO joongna_store_profiles (
                store_seq,
                store_name,
                fetch_status,
                error_message,
                last_status,
                last_status_reason,
                last_status_checked_at,
                last_seen_at,
                last_fetched_at,
                next_retry_at
            )
            VALUES (%s, NULL, 'success', %s, %s, %s, %s, %s, %s, NULL)
            ON DUPLICATE KEY UPDATE
                fetch_status = VALUES(fetch_status),
                error_message = VALUES(error_message),
                last_status = VALUES(last_status),
                last_status_reason = VALUES(last_status_reason),
                last_status_checked_at = VALUES(last_status_checked_at),
                last_seen_at = VALUES(last_seen_at),
                last_fetched_at = VALUES(last_fetched_at),
                next_retry_at = NULL
            """,
            (
                store_seq,
                _safe_text(error_message),
                status,
                _safe_text(status_reason),
                checked_at,
                checked_at,
                checked_at,
            ),
        )
    except Exception as exc:
        if _is_schema_missing_error(exc):
            return
        raise


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


def _store_activity_snapshot_fingerprint_from_row(row: Dict[str, Any]) -> str:
    return _snapshot_fingerprint(
        {
            "store_seq": _safe_int(row.get("store_seq")),
            "posts_last_1h": _safe_int(row.get("posts_last_1h")) or 0,
            "posts_last_6h": _safe_int(row.get("posts_last_6h")) or 0,
            "posts_last_24h": _safe_int(row.get("posts_last_24h")) or 0,
            "posts_last_7d": _safe_int(row.get("posts_last_7d")) or 0,
            "visible_product_count": _safe_int(row.get("visible_product_count")),
            "store_name_fingerprint": _safe_text(row.get("store_name_fingerprint")),
            "profile_fingerprint": _safe_text(row.get("profile_fingerprint")),
            "profile_image_url_hash": _snapshot_text_hash(row.get("profile_image_url")),
            "has_default_profile_image": _safe_int(row.get("has_default_profile_image")),
            "store_level": _safe_text(row.get("store_level")),
            "store_level_number": _safe_int(row.get("store_level_number")),
            "review_count": _safe_int(row.get("review_count")),
            "reliability_score": _safe_int(row.get("reliability_score")),
            "activity_score": _safe_int(row.get("activity_score")),
            "notified_score": _safe_int(row.get("notified_score")),
            "safe_trade_count": _safe_int(row.get("safe_trade_count")),
            "trust_score": _safe_int(row.get("trust_score")),
            "chat_response_ratio": _safe_text(row.get("chat_response_ratio")),
            "chat_response_time": _safe_int(row.get("chat_response_time")),
            "chat_response_time_text": _safe_text(row.get("chat_response_time_text")),
            "visit_today_count": _safe_int(row.get("visit_today_count")),
            "visit_total_count": _safe_int(row.get("visit_total_count")),
            "store_grade": _safe_float(row.get("store_grade")),
            "user_type": _safe_int(row.get("user_type")),
            "partner_center_seller_yn": _safe_bool_int(row.get("partner_center_seller_yn")),
            "is_official_account": _safe_bool_int(row.get("is_official_account")),
            "store_desc_hash": _snapshot_text_hash(row.get("store_desc")),
            "first_seen_product_id": _safe_text(row.get("first_seen_product_id")),
            "first_seen_sort_date": _snapshot_datetime_key(row.get("first_seen_sort_date")),
        }
    )


def _fetch_latest_store_activity_snapshot_before(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            id,
            store_id,
            store_seq,
            checked_at,
            posts_last_1h,
            posts_last_6h,
            posts_last_24h,
            posts_last_7d,
            visible_product_count,
            store_name_fingerprint,
            profile_fingerprint,
            profile_image_url,
            has_default_profile_image,
            store_level,
            store_level_number,
            review_count,
            reliability_score,
            activity_score,
            notified_score,
            safe_trade_count,
            trust_score,
            chat_response_ratio,
            chat_response_time,
            chat_response_time_text,
            visit_today_count,
            visit_total_count,
            store_grade,
            user_type,
            partner_center_seller_yn,
            is_official_account,
            store_desc,
            first_seen_product_id,
            first_seen_sort_date
        FROM fraud_store_activity_snapshots
        WHERE store_id = %s
          AND checked_at <= %s
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (store_id, checked_at),
    )
    row = cursor.fetchone() or {}
    if not row or not isinstance(row, dict):
        return None
    return row


def _insert_activity_snapshot(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    activity: Dict[str, int],
    first_seen_product_id: Optional[str],
    first_seen_sort_date: Optional[datetime],
    profile: Optional[Dict[str, Any]] = None,
):
    normalized_store_name = _normalize_store_name((profile or {}).get("store_name"))
    store_name_fingerprint = (
        _build_store_name_fingerprint(store_id, normalized_store_name)
        if normalized_store_name is not None
        else None
    )
    profile_fingerprint = (
        _build_profile_fingerprint(store_id, profile)
        if isinstance(profile, dict)
        else None
    )
    store_desc = _safe_text((profile or {}).get("store_desc"))
    raw_json_text = None
    if isinstance(profile, dict):
        try:
            raw_json_text = json.dumps(profile.get("raw_json"), ensure_ascii=False)
        except Exception:
            raw_json_text = None

    candidate_row = {
        "store_seq": _safe_int(store_id),
        "posts_last_1h": int(activity.get("posts_last_1h") or 0),
        "posts_last_6h": int(activity.get("posts_last_6h") or 0),
        "posts_last_24h": int(activity.get("posts_last_24h") or 0),
        "posts_last_7d": int(activity.get("posts_last_7d") or 0),
        "visible_product_count": _safe_int(activity.get("visible_product_count")),
        "store_name_fingerprint": store_name_fingerprint,
        "profile_fingerprint": profile_fingerprint,
        "profile_image_url": _safe_text((profile or {}).get("profile_image_url")),
        "has_default_profile_image": _safe_int((profile or {}).get("has_default_profile_image")),
        "store_level": _safe_text((profile or {}).get("store_level")),
        "store_level_number": _safe_int((profile or {}).get("store_level_number")),
        "review_count": _safe_int((profile or {}).get("review_count")),
        "reliability_score": _safe_int((profile or {}).get("reliability_score")),
        "activity_score": _safe_int((profile or {}).get("activity_score")),
        "notified_score": _safe_int((profile or {}).get("notified_score")),
        "safe_trade_count": _safe_int((profile or {}).get("safe_trade_count")),
        "trust_score": _safe_int((profile or {}).get("trust_score")),
        "chat_response_ratio": _safe_text((profile or {}).get("chat_response_ratio")),
        "chat_response_time": _safe_int((profile or {}).get("chat_response_time")),
        "chat_response_time_text": _safe_text((profile or {}).get("chat_response_time_text")),
        "visit_today_count": _safe_int((profile or {}).get("visit_today_count")),
        "visit_total_count": _safe_int((profile or {}).get("visit_total_count")),
        "store_grade": _safe_float((profile or {}).get("store_grade")),
        "user_type": _safe_int((profile or {}).get("user_type")),
        "partner_center_seller_yn": _safe_bool_int((profile or {}).get("partner_center_seller_yn")),
        "is_official_account": _safe_bool_int((profile or {}).get("is_official_account")),
        "store_desc": store_desc,
        "first_seen_product_id": first_seen_product_id,
        "first_seen_sort_date": first_seen_sort_date,
    }

    try:
        previous_snapshot = _fetch_latest_store_activity_snapshot_before(
            cursor,
            store_id=store_id,
            checked_at=checked_at,
        )
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise
        previous_snapshot = None

    if previous_snapshot is not None:
        previous_fingerprint = _store_activity_snapshot_fingerprint_from_row(previous_snapshot)
        current_fingerprint = _store_activity_snapshot_fingerprint_from_row(candidate_row)
        if previous_fingerprint == current_fingerprint:
            return False

    try:
        cursor.execute(
            """
            INSERT INTO fraud_store_activity_snapshots (
                store_id,
                store_seq,
                checked_at,
                observed_at,
                posts_last_1h,
                posts_last_6h,
                posts_last_24h,
                posts_last_7d,
                visible_product_count,
                store_name,
                store_name_fingerprint,
                profile_fingerprint,
                profile_image_url,
                has_default_profile_image,
                store_level,
                store_level_number,
                review_count,
                reliability_score,
                activity_score,
                notified_score,
                safe_trade_count,
                trust_score,
                chat_response_ratio,
                chat_response_time,
                chat_response_time_text,
                visit_today_count,
                visit_total_count,
                store_grade,
                user_type,
                partner_center_seller_yn,
                is_official_account,
                store_desc,
                store_desc_length,
                raw_json,
                first_seen_product_id,
                first_seen_sort_date
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                store_id,
                _safe_int(store_id),
                checked_at,
                checked_at,
                int(activity.get("posts_last_1h") or 0),
                int(activity.get("posts_last_6h") or 0),
                int(activity.get("posts_last_24h") or 0),
                int(activity.get("posts_last_7d") or 0),
                _safe_int(activity.get("visible_product_count")),
                normalized_store_name,
                store_name_fingerprint,
                profile_fingerprint,
                _safe_text((profile or {}).get("profile_image_url")),
                _safe_int((profile or {}).get("has_default_profile_image")),
                _safe_text((profile or {}).get("store_level")),
                _safe_int((profile or {}).get("store_level_number")),
                _safe_int((profile or {}).get("review_count")),
                _safe_int((profile or {}).get("reliability_score")),
                _safe_int((profile or {}).get("activity_score")),
                _safe_int((profile or {}).get("notified_score")),
                _safe_int((profile or {}).get("safe_trade_count")),
                _safe_int((profile or {}).get("trust_score")),
                _safe_text((profile or {}).get("chat_response_ratio")),
                _safe_int((profile or {}).get("chat_response_time")),
                _safe_text((profile or {}).get("chat_response_time_text")),
                _safe_int((profile or {}).get("visit_today_count")),
                _safe_int((profile or {}).get("visit_total_count")),
                _safe_float((profile or {}).get("store_grade")),
                _safe_int((profile or {}).get("user_type")),
                _safe_bool_int((profile or {}).get("partner_center_seller_yn")),
                _safe_bool_int((profile or {}).get("is_official_account")),
                store_desc,
                len(store_desc) if store_desc is not None else None,
                raw_json_text,
                first_seen_product_id,
                first_seen_sort_date,
            ),
        )
        return True
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

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
    return True


def _store_profile_field_snapshot_fingerprint_from_row(row: Dict[str, Any]) -> str:
    return _snapshot_fingerprint(
        {
            "store_seq": _safe_int(row.get("store_seq")),
            "status": _safe_text(row.get("status")),
            "source": _safe_text(row.get("source")),
            "trust_score": _safe_int(row.get("trust_score")),
            "review_count": _safe_int(row.get("review_count")),
            "store_level": _safe_text(row.get("store_level")),
            "store_level_number": _safe_int(row.get("store_level_number")),
            "safe_trade_count": _safe_int(row.get("safe_trade_count")),
            "reliability_score": _safe_int(row.get("reliability_score")),
            "activity_score": _safe_int(row.get("activity_score")),
            "notified_score": _safe_int(row.get("notified_score")),
            "visit_today_count": _safe_int(row.get("visit_today_count")),
            "visit_total_count": _safe_int(row.get("visit_total_count")),
            "is_official_account": _safe_bool_int(row.get("is_official_account")),
        }
    )


def _fetch_latest_store_profile_field_snapshot_before(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            id,
            store_id,
            store_seq,
            checked_at,
            status,
            source,
            trust_score,
            review_count,
            store_level,
            store_level_number,
            safe_trade_count,
            reliability_score,
            activity_score,
            notified_score,
            visit_today_count,
            visit_total_count,
            is_official_account
        FROM fraud_store_profile_field_snapshots
        WHERE store_id = %s
          AND checked_at <= %s
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (store_id, checked_at),
    )
    row = cursor.fetchone() or {}
    if not row or not isinstance(row, dict):
        return None
    return row


def _insert_store_profile_field_snapshot(
    cursor,
    *,
    store_id: str,
    checked_at: datetime,
    status: str,
    source: Optional[str],
    profile: Dict[str, Any],
) -> bool:
    raw_profile_json_text = None
    try:
        raw_profile_json_text = json.dumps(profile.get("raw_json"), ensure_ascii=False)
    except Exception:
        raw_profile_json_text = None

    candidate_row = {
        "store_seq": _safe_int(store_id),
        "status": status,
        "source": source,
        "trust_score": _safe_int(profile.get("trust_score")),
        "review_count": _safe_int(profile.get("review_count")),
        "store_level": _safe_text(profile.get("store_level")),
        "store_level_number": _safe_int(profile.get("store_level_number")),
        "safe_trade_count": _safe_int(profile.get("safe_trade_count")),
        "reliability_score": _safe_int(profile.get("reliability_score")),
        "activity_score": _safe_int(profile.get("activity_score")),
        "notified_score": _safe_int(profile.get("notified_score")),
        "visit_today_count": _safe_int(profile.get("visit_today_count")),
        "visit_total_count": _safe_int(profile.get("visit_total_count")),
        "is_official_account": _safe_bool_int(profile.get("is_official_account")),
    }

    try:
        previous_snapshot = _fetch_latest_store_profile_field_snapshot_before(
            cursor,
            store_id=store_id,
            checked_at=checked_at,
        )
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise
        previous_snapshot = None

    if previous_snapshot is not None:
        previous_fingerprint = _store_profile_field_snapshot_fingerprint_from_row(previous_snapshot)
        current_fingerprint = _store_profile_field_snapshot_fingerprint_from_row(candidate_row)
        if previous_fingerprint == current_fingerprint:
            return False

    try:
        cursor.execute(
            """
            INSERT INTO fraud_store_profile_field_snapshots (
                store_id,
                store_seq,
                checked_at,
                status,
                source,
                trust_score,
                review_count,
                store_level,
                store_level_number,
                safe_trade_count,
                reliability_score,
                activity_score,
                notified_score,
                visit_today_count,
                visit_total_count,
                is_official_account,
                raw_profile_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                store_id,
                _safe_int(store_id),
                checked_at,
                status,
                source,
                _safe_int(profile.get("trust_score")),
                _safe_int(profile.get("review_count")),
                _safe_text(profile.get("store_level")),
                _safe_int(profile.get("store_level_number")),
                _safe_int(profile.get("safe_trade_count")),
                _safe_int(profile.get("reliability_score")),
                _safe_int(profile.get("activity_score")),
                _safe_int(profile.get("notified_score")),
                _safe_int(profile.get("visit_today_count")),
                _safe_int(profile.get("visit_total_count")),
                _safe_bool_int(profile.get("is_official_account")),
                raw_profile_json_text,
            ),
        )
        return True
    except Exception as exc:
        if _is_schema_missing_error(exc):
            return False
        raise


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


def ensure_store_snapshots_for_fraud_scoring(
    cursor,
    *,
    store_id: Any,
    first_seen_product_id: Optional[str] = None,
    first_seen_sort_date: Optional[datetime] = None,
    lookback_days: Optional[int] = None,
) -> Dict[str, Any]:
    normalized_store_id = _normalize_store_id(store_id)
    if normalized_store_id is None:
        return {
            "ok": False,
            "reason": "invalid_store_id",
            "status": STATUS_ERROR,
            "profile_available": False,
            "profile_field_snapshot_inserted": False,
            "activity_snapshot_inserted": False,
        }

    normalized_lookback_days = max(int(lookback_days or DEFAULT_LOOKBACK_DAYS), 1)
    checked_at = _utc_now_naive()
    probe = _probe_store_status(normalized_store_id)
    normalized_status = (_safe_text(probe.get("status")) or STATUS_UNKNOWN).lower()
    probe_checked_at = probe.get("checked_at") or checked_at
    profile = probe.get("profile")

    _insert_status_snapshot(
        cursor,
        store_id=normalized_store_id,
        checked_at=probe_checked_at,
        status=normalized_status,
        is_active=int(probe.get("is_active") or 0),
        raw_status_text=_safe_text(probe.get("raw_status_text")),
        raw_response_json=probe.get("raw_response_json"),
        first_seen_product_id=_safe_text(first_seen_product_id),
        first_seen_sort_date=_safe_datetime(first_seen_sort_date),
        error_message=_safe_text(probe.get("error_message")),
        source=_safe_text(probe.get("source")),
        http_status=_safe_int(probe.get("http_status")),
        meta_code=_safe_int(probe.get("meta_code")),
        meta_message=_safe_text(probe.get("meta_message")),
        raw_snippet=_safe_text(probe.get("raw_snippet")),
    )

    if isinstance(profile, dict):
        _upsert_joongna_store_profile_snapshot(
            cursor,
            store_id=normalized_store_id,
            checked_at=probe_checked_at,
            profile=profile,
            status=normalized_status,
            status_reason=_safe_text(probe.get("raw_status_text")),
            source=_safe_text(probe.get("source")) or "my_store_api",
        )
    else:
        _upsert_joongna_store_profile_status(
            cursor,
            store_id=normalized_store_id,
            checked_at=probe_checked_at,
            status=normalized_status,
            status_reason=_safe_text(probe.get("raw_status_text")),
            error_message=_safe_text(probe.get("error_message")),
        )

    profile_field_snapshot_inserted = False
    activity_snapshot_inserted = False
    if normalized_status == STATUS_ACTIVE and isinstance(profile, dict):
        profile_field_snapshot_inserted = _insert_store_profile_field_snapshot(
            cursor,
            store_id=normalized_store_id,
            checked_at=probe_checked_at,
            status=normalized_status,
            source=_safe_text(probe.get("source")),
            profile=profile,
        )
        activity = _compute_activity_snapshot_from_db(
            cursor,
            store_id=normalized_store_id,
            checked_at=probe_checked_at,
            lookback_days=normalized_lookback_days,
        )
        activity_snapshot_inserted = _insert_activity_snapshot(
            cursor,
            store_id=normalized_store_id,
            checked_at=probe_checked_at,
            activity=activity,
            first_seen_product_id=_safe_text(first_seen_product_id),
            first_seen_sort_date=_safe_datetime(first_seen_sort_date),
            profile=profile,
        )

    return {
        "ok": True,
        "store_id": normalized_store_id,
        "checked_at": probe_checked_at,
        "status": normalized_status,
        "profile_available": isinstance(profile, dict),
        "profile_field_snapshot_inserted": bool(profile_field_snapshot_inserted),
        "activity_snapshot_inserted": bool(activity_snapshot_inserted),
        "source": _safe_text(probe.get("source")),
    }


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

        product_snapshot_candidates = _fetch_recent_product_snapshot_candidates(
            cursor,
            lookback_days=stats["lookback_days"],
            limit=listing_candidate_limit,
        )
        stats["product_snapshot_candidate_count"] = len(product_snapshot_candidates)
        if product_snapshot_candidates:
            stats["product_snapshots_upserted"] = _upsert_product_state_snapshots(
                cursor,
                product_snapshot_candidates,
            )

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
                ensure_result = ensure_store_snapshots_for_fraud_scoring(
                    cursor,
                    store_id=store_id,
                    first_seen_product_id=_safe_text(target.get("first_seen_product_id")),
                    first_seen_sort_date=_safe_datetime(target.get("first_seen_sort_date")),
                    lookback_days=stats["lookback_days"],
                )
                normalized_status = _safe_text(ensure_result.get("status")) or STATUS_UNKNOWN
                if ensure_result.get("profile_field_snapshot_inserted"):
                    stats["profile_field_snapshots_inserted"] += 1
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
                        source="worker",
                        raw_snippet=_safe_text(exc),
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
