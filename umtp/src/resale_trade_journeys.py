import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from src.db import get_connection
from src.spec_parser import parse_listing_text


DEFAULT_SOURCE = "joongna"

DROPPED_RESALE_JOURNEY_COLUMNS = {
    "gross_profit_krw",
    "net_profit_krw",
    "roi_percent",
    "url_digest",
    "listing_created_at",
    "discovered_at",
    "seller_shop_id",
    "purchase_contact_record",
    "purchase_conversation_text",
    "response_time_minutes",
    "money_sent_at",
    "money_received_at",
    "purchase_account_number",
    "cpu_core_count",
    "gpu_core_count",
    "applecare_status",
    "minimum_accept_price_krw",
    "resale_listing_created_at",
    "resale_product_id",
    "initial_resale_price_krw",
    "resale_contact_record",
    "resale_conversation_text",
    "resale_account_number",
    "final_shipping_cost_krw",
    "platform_fee_krw",
    "refund_or_claim",
    "expected_profit_krw",
    "risk_score",
    "reason_tags",
    "purchase_speed_minutes",
    "sale_duration_hours",
    "total_holding_time_hours",
    "profit_per_day_krw",
    "final_result_notes",
}

STAGE_DISCOVERED = "DISCOVERED"
STAGE_INSPECTED = "INSPECTED"
STAGE_RESALE_LISTED = "RESALE_LISTED"
STAGE_SOLD = "SOLD"

DATETIME_FIELDS = {
    "listing_created_at",
    "discovered_at",
    "contacted_at",
    "seller_response_at",
    "decision_at",
    "purchased_at",
    "cleaned_at",
    "photo_taken_at",
    "money_sent_at",
    "money_received_at",
    "resale_listing_created_at",
    "first_inquiry_at",
    "sold_at",
}
INT_FIELDS = {
    "listing_price_krw",
    "screen_inch",
    "ram_gb",
    "ssd_gb",
    "fair_price_krw",
    "expected_profit_krw",
    "risk_score",
    "confirmed_price_krw",
    "target_purchase_price_krw",
    "expected_sale_price_krw",
    "expected_net_profit_krw",
    "expected_sale_duration_days",
    "cpu_core_count",
    "gpu_core_count",
    "purchase_price_krw",
    "transport_cost_krw",
    "shipping_cost_krw",
    "total_cost_krw",
    "battery_health_percent",
    "battery_cycle_count",
    "resale_photo_count",
    "resale_listing_price_krw",
    "minimum_accept_price_krw",
    "initial_resale_price_krw",
    "view_count",
    "favorite_count",
    "inquiry_count",
    "negotiation_count",
    "price_drop_count",
    "sale_price_krw",
    "final_shipping_cost_krw",
    "platform_fee_krw",
    "gross_profit_krw",
    "net_profit_krw",
    "purchase_speed_minutes",
    "sale_duration_hours",
    "total_holding_time_hours",
    "profit_per_day_krw",
    "watch_rule_id",
    "analysis_job_id",
}
DECIMAL_FIELDS = {
    "discount_rate_percent",
    "roi_percent",
}
BOOL_FIELDS = {
    "negotiable",
    "activation_lock_off",
    "mdm_lock_none",
    "truetone_ok",
    "wifi_bluetooth_ok",
    "repair_suspected",
}
JSON_TEXT_FIELDS = {
    "image_urls",
    "reason_tags",
    "suspicious_points",
    "included_items",
    "price_drop_history",
    "buyer_questions",
    "common_objections",
}

# 정확 확인 정보는 자동 하이드레이션 대상에서 제외하고 수동 입력으로만 관리한다.
MANUAL_VERIFICATION_FIELDS = {
    "serial_number",
    "model_number",
    "cpu_core_count",
    "gpu_core_count",
    "battery_cycle_count",
    "battery_health_percent",
    "applecare_status",
    "activation_lock_off",
    "mdm_lock_none",
}

IDENTITY_FIELDS = {"user_id", "source", "product_id", "url"}

AUTO_HYDRATE_FIELDS = {
    "source",
    "product_id",
    "url",
    "title",
    "listing_created_at",
    "discovered_at",
    "listing_price_krw",
    "seller_nickname",
    "seller_shop_id",
    "seller_location",
    "image_urls",
    "body_text",
    "product_type",
    "chip",
    "screen_inch",
    "ram_gb",
    "ssd_gb",
    "fair_price_krw",
    "discount_rate_percent",
    "expected_profit_krw",
    "risk_score",
    "reason_tags",
    "watch_rule_id",
    "analysis_job_id",
}

PURCHASE_PATCH_FIELDS = {
    "purchase_contact_record",
    "purchase_conversation_text",
    "purchase_account_number",
    "contacted_at",
    "seller_response_at",
    "purchased_at",
    "purchase_price_krw",
    "purchase_method",
    "purchase_location",
    "transport_cost_krw",
    "shipping_cost_krw",
    "payment_method",
    "money_sent_at",
    "inspection_notes",
    "sale_platform",
    "serial_number",
    "model_number",
    "cpu_core_count",
    "gpu_core_count",
    "battery_cycle_count",
    "battery_health_percent",
    "applecare_status",
    "activation_lock_off",
    "mdm_lock_none",
    "current_stage",
    "final_result_notes",
}

RESALE_PATCH_FIELDS = {
    "resale_contact_record",
    "resale_conversation_text",
    "resale_account_number",
    "money_received_at",
    "resale_listing_price_krw",
    "minimum_accept_price_krw",
    "resale_platform",
    "resale_listing_created_at",
    "resale_url",
    "resale_product_id",
    "initial_resale_price_krw",
    "current_stage",
}

SOLD_PATCH_FIELDS = {
    "sold_at",
    "sale_price_krw",
    "buyer_nickname",
    "sale_method",
    "sale_location",
    "sale_platform",
    "final_shipping_cost_krw",
    "platform_fee_krw",
    "refund_or_claim",
    "final_result_notes",
}

BLOCKED_PATCH_FIELDS = {
    "id",
    "url_digest",
}

LEGACY_PURCHASE_UPSERT_FIELDS = PURCHASE_PATCH_FIELDS | RESALE_PATCH_FIELDS
LEGACY_RESALE_UPSERT_FIELDS = RESALE_PATCH_FIELDS | SOLD_PATCH_FIELDS
RESALE_RECORD_PATCH_FIELDS = RESALE_PATCH_FIELDS | SOLD_PATCH_FIELDS

TRADE_PREFILL_FIELDS = {
    "user_id",
    "source",
    "product_id",
    "current_stage",
    "url",
    "title",
    "listing_price_krw",
    "seller_nickname",
    "seller_location",
    "image_urls",
    "body_text",
    "product_type",
    "chip",
    "screen_inch",
    "ram_gb",
    "ssd_gb",
    "fair_price_krw",
    "discount_rate_percent",
}
TRADE_PREFILL_SPEC_FIELDS = {
    "product_type",
    "chip",
    "screen_inch",
    "ram_gb",
    "ssd_gb",
}
TRADE_PREFILL_STATE_FIELDS = {
    "url",
    "title",
    "listing_price_krw",
    "seller_nickname",
    "seller_location",
    "image_urls",
    "body_text",
}

for _field_set in (
    DATETIME_FIELDS,
    INT_FIELDS,
    DECIMAL_FIELDS,
    JSON_TEXT_FIELDS,
    MANUAL_VERIFICATION_FIELDS,
    AUTO_HYDRATE_FIELDS,
    PURCHASE_PATCH_FIELDS,
    RESALE_PATCH_FIELDS,
    SOLD_PATCH_FIELDS,
    LEGACY_PURCHASE_UPSERT_FIELDS,
    LEGACY_RESALE_UPSERT_FIELDS,
    RESALE_RECORD_PATCH_FIELDS,
):
    _field_set.difference_update(DROPPED_RESALE_JOURNEY_COLUMNS)
del _field_set


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _normalize_optional_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = _normalize_optional_text(value)
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


def _latest_datetime(*values: Any) -> Optional[datetime]:
    parsed_values = [
        parsed
        for parsed in (_normalize_optional_datetime(value) for value in values)
        if parsed is not None
    ]
    if not parsed_values:
        return None
    return max(parsed_values)


def _normalize_json_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return _normalize_optional_text(value)


def _normalize_source(value: Any) -> str:
    normalized = _normalize_optional_text(value)
    return normalized if normalized else DEFAULT_SOURCE


def _normalize_for_column(column: str, value: Any) -> Any:
    if column in DATETIME_FIELDS:
        return _normalize_optional_datetime(value)
    if column in INT_FIELDS:
        return _normalize_optional_int(value)
    if column in DECIMAL_FIELDS:
        return _normalize_optional_float(value)
    if column in BOOL_FIELDS:
        return _normalize_optional_bool(value)
    if column in JSON_TEXT_FIELDS:
        return _normalize_json_text(value)
    return _normalize_optional_text(value)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _extract_product_id_from_url(url: Optional[str]) -> Optional[str]:
    normalized_url = _normalize_optional_text(url)
    if normalized_url is None:
        return None

    match = re.search(r"/product/(\d+)", normalized_url)
    if not match:
        return None
    return _normalize_optional_text(match.group(1))


def _looks_like_url(value: Any) -> bool:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return False
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", normalized):
        return True
    return "/product/" in normalized or ("/" in normalized and "." in normalized.split("/", 1)[0])


def _normalize_reference_url(value: Any) -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    if _looks_like_url(normalized):
        return normalized
    return None


def _build_url_lookup_values(url: Optional[str]) -> list[str]:
    normalized = _normalize_optional_text(url)
    if normalized is None:
        return []

    values: list[str] = []
    base_without_query = re.split(r"[?#]", normalized, maxsplit=1)[0]
    for candidate in (
        normalized,
        normalized.rstrip("/"),
        base_without_query,
        base_without_query.rstrip("/"),
    ):
        cleaned = _normalize_optional_text(candidate)
        if cleaned is not None and cleaned not in values:
            values.append(cleaned)
    return values


def _infer_source_from_url(url: Optional[str]) -> str:
    normalized_url = (_normalize_optional_text(url) or "").lower()
    if "bunjang" in normalized_url:
        return "bunjang"
    if "daangn" in normalized_url or "karrot" in normalized_url:
        return "daangn"
    if "joongna" in normalized_url:
        return "joongna"
    return DEFAULT_SOURCE


def _safe_fetchone(cursor, query: str, params: tuple[Any, ...]) -> Optional[dict[str, Any]]:
    try:
        cursor.execute(query, params)
        row = cursor.fetchone()
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" in lowered or "doesn't exist" in lowered or "unknown table" in lowered:
            return None
        raise

    if not isinstance(row, dict):
        return None
    return row


def _safe_fetchall(cursor, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" in lowered or "doesn't exist" in lowered or "unknown table" in lowered:
            return []
        raise

    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _get_resale_columns(cursor) -> tuple[set[str], set[str]]:
    rows = _safe_fetchall(cursor, "SHOW COLUMNS FROM resale_trade_journeys", ())
    all_columns: set[str] = set()
    writable_columns: set[str] = set()
    for row in rows:
        name = _normalize_optional_text(row.get("Field"))
        if name is None:
            continue
        all_columns.add(name)
        extra = (_normalize_optional_text(row.get("Extra")) or "").lower()
        if "generated" not in extra:
            writable_columns.add(name)
    writable_columns.difference_update(DROPPED_RESALE_JOURNEY_COLUMNS)
    return all_columns, writable_columns


def _filter_writable_updates(updates: dict[str, Any], writable_columns: set[str]) -> dict[str, Any]:
    return {key: value for key, value in updates.items() if key in writable_columns}


def _prepare_sparse_updates(
    payload: dict[str, Any],
    allowed_fields: Optional[set[str]],
    writable_columns: set[str],
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    target_fields = allowed_fields if allowed_fields is not None else set(payload.keys())

    for field in target_fields:
        if field in BLOCKED_PATCH_FIELDS:
            continue
        if field not in payload:
            continue
        normalized = _normalize_for_column(field, payload.get(field))
        if normalized is None:
            continue
        updates[field] = normalized
    return _filter_writable_updates(updates, writable_columns)


def _fetch_journey_by_id(cursor, row_id: int, *, user_id: Optional[str] = None, for_update: bool = False) -> Optional[dict[str, Any]]:
    lock_sql = " FOR UPDATE" if for_update else ""
    if user_id is None:
        return _safe_fetchone(
            cursor,
            f"""
            SELECT *
            FROM resale_trade_journeys
            WHERE id = %s
            LIMIT 1{lock_sql}
            """,
            (row_id,),
        )

    return _safe_fetchone(
        cursor,
        f"""
        SELECT *
        FROM resale_trade_journeys
        WHERE id = %s
          AND user_id = %s
        LIMIT 1{lock_sql}
        """,
        (row_id, user_id),
    )


def _fetch_journey_by_key(
    cursor,
    *,
    user_id: str,
    source: str,
    product_id: str,
    for_update: bool = False,
) -> Optional[dict[str, Any]]:
    lock_sql = " FOR UPDATE" if for_update else ""
    return _safe_fetchone(
        cursor,
        f"""
        SELECT *
        FROM resale_trade_journeys
        WHERE user_id = %s
          AND source = %s
          AND product_id = %s
        ORDER BY id DESC
        LIMIT 1{lock_sql}
        """,
        (user_id, source, product_id),
    )


def _fetch_journey_by_product_id(
    cursor,
    *,
    user_id: str,
    product_id: str,
    for_update: bool = False,
) -> Optional[dict[str, Any]]:
    lock_sql = " FOR UPDATE" if for_update else ""
    return _safe_fetchone_with_order_fallback(
        cursor,
        f"""
        SELECT *
        FROM resale_trade_journeys
        WHERE user_id = %s
          AND product_id = %s
        """,
        (user_id, product_id),
        [
            "updated_at DESC, id DESC",
            "id DESC",
        ],
    )


def _insert_or_get_journey_id(cursor, *, user_id: str, source: str, product_id: str, writable_columns: set[str]) -> int:
    existing_row = _fetch_journey_by_key(
        cursor,
        user_id=user_id,
        source=source,
        product_id=product_id,
        for_update=True,
    )
    if existing_row:
        existing_id = _normalize_optional_int(existing_row.get("id"))
        if existing_id is not None and existing_id > 0:
            return existing_id

    insert_columns = ["user_id", "source", "product_id"]
    if "current_stage" in writable_columns:
        insert_columns.append("current_stage")
    placeholders = ", ".join(["%s"] * len(insert_columns))
    column_sql = ", ".join(insert_columns)

    values: list[Any] = [user_id, source, product_id]
    if "current_stage" in writable_columns:
        values.append(STAGE_DISCOVERED)

    update_sql = "id = LAST_INSERT_ID(id), updated_at = CURRENT_TIMESTAMP"

    cursor.execute(
        f"""
        INSERT INTO resale_trade_journeys ({column_sql})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {update_sql}
        """,
        tuple(values),
    )

    row_id = _normalize_optional_int(cursor.lastrowid)
    if row_id is None or row_id <= 0:
        row = _fetch_journey_by_key(
            cursor,
            user_id=user_id,
            source=source,
            product_id=product_id,
            for_update=True,
        )
        if not row:
            raise RuntimeError("journey_insert_failed")
        row_id = _normalize_optional_int(row.get("id"))
    if row_id is None or row_id <= 0:
        raise RuntimeError("journey_insert_failed")
    return row_id


def _safe_order_query(base_sql: str, order_candidates: list[str]) -> str:
    for order_clause in order_candidates:
        query = f"{base_sql} ORDER BY {order_clause} LIMIT 1"
        if query:
            return query
    return f"{base_sql} LIMIT 1"


def _safe_fetchone_with_order_fallback(
    cursor,
    base_sql: str,
    params: tuple[Any, ...],
    order_candidates: list[str],
) -> Optional[dict[str, Any]]:
    for order_clause in order_candidates:
        row = _safe_fetchone(
            cursor,
            f"{base_sql} ORDER BY {order_clause} LIMIT 1",
            params,
        )
        if row:
            return row
    return None


def _fetch_latest_alert_event_by_reference(
    cursor,
    *,
    user_id: Optional[str],
    source: Optional[str] = None,
    product_id: Optional[str] = None,
    url: Optional[str] = None,
) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_source = _normalize_optional_text(source)
    normalized_product_id = _normalize_optional_text(product_id)
    url_values = _build_url_lookup_values(url)

    query_specs: list[tuple[str, list[Any]]] = []
    if normalized_product_id is not None and normalized_source is not None:
        query_specs.append(
            (
                "source = %s AND product_id = %s",
                [normalized_source, normalized_product_id],
            )
        )
    if normalized_product_id is not None:
        query_specs.append(("product_id = %s", [normalized_product_id]))

    if url_values:
        placeholders = ", ".join(["%s"] * len(url_values))
        if normalized_source is not None:
            query_specs.append(
                (
                    f"source = %s AND TRIM(url) IN ({placeholders})",
                    [normalized_source, *url_values],
                )
            )
        query_specs.append((f"TRIM(url) IN ({placeholders})", list(url_values)))

    order_candidates = [
        "COALESCE(sort_date, analyzed_at, created_at) DESC, id DESC",
        "COALESCE(sort_date, created_at) DESC, id DESC",
        "created_at DESC, id DESC",
        "id DESC",
    ]
    for where_sql, params in query_specs:
        user_sql = ""
        if normalized_user_id is not None:
            user_sql = "AND user_id = %s"
            params = [*params, normalized_user_id]

        row = _safe_fetchone_with_order_fallback(
            cursor,
            f"""
            SELECT *
            FROM alert_events
            WHERE {where_sql}
              {user_sql}
            """,
            tuple(params),
            order_candidates,
        )
        if row:
            return row

    return {}


def _fetch_latest_alert_event(cursor, *, user_id: str, source: str, product_id: str) -> dict[str, Any]:
    return _fetch_latest_alert_event_by_reference(
        cursor,
        user_id=user_id,
        source=source,
        product_id=product_id,
    )


def _fetch_alert_event_by_id(cursor, *, user_id: str, alert_event_id: int) -> dict[str, Any]:
    row = _safe_fetchone(
        cursor,
        """
        SELECT *
        FROM alert_events
        WHERE id = %s
          AND (%s IS NULL OR user_id = %s)
        LIMIT 1
        """,
        (alert_event_id, user_id, user_id),
    )
    return row or {}


def _fetch_read_archive_event_by_id(cursor, *, user_id: str, read_archive_event_id: int) -> dict[str, Any]:
    row = _safe_fetchone(
        cursor,
        """
        SELECT *
        FROM alert_read_archive_events
        WHERE id = %s
          AND (%s IS NULL OR user_id = %s)
        LIMIT 1
        """,
        (read_archive_event_id, user_id, user_id),
    )
    return row or {}


def _fetch_latest_analysis_job(cursor, *, user_id: str, source: str, product_id: str) -> dict[str, Any]:
    base = """
        SELECT *
        FROM analysis_jobs
        WHERE source = %s
          AND product_id = %s
          AND (%s IS NULL OR user_id = %s)
    """
    query = _safe_order_query(
        base,
        [
            "COALESCE(sort_date, processed_at, started_at, created_at) DESC, id DESC",
            "created_at DESC, id DESC",
            "id DESC",
        ],
    )
    return _safe_fetchone(cursor, query, (source, product_id, user_id, user_id)) or {}


def _fetch_latest_seen_product(cursor, *, product_id: str) -> dict[str, Any]:
    numeric_product_id = _normalize_optional_int(product_id)
    if numeric_product_id is None:
        return {}

    base = """
        SELECT *
        FROM joongna_seen_products
        WHERE seq = %s
    """
    query = _safe_order_query(
        base,
        [
            "COALESCE(last_sort_date, sort_date, first_seen_at) DESC",
            "first_seen_at DESC",
        ],
    )
    return _safe_fetchone(cursor, query, (numeric_product_id,)) or {}


def _fetch_latest_search_result(cursor, *, product_id: str) -> dict[str, Any]:
    base = """
        SELECT *
        FROM search_results
        WHERE product_id = %s
    """
    query = _safe_order_query(
        base,
        [
            "COALESCE(sort_date, fetched_at, created_at) DESC, id DESC",
            "fetched_at DESC, id DESC",
            "id DESC",
        ],
    )
    return _safe_fetchone(cursor, query, (product_id,)) or {}


def _fetch_latest_listing_analysis(
    cursor,
    *,
    source: Optional[str] = None,
    product_id: str,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    normalized_source = _normalize_optional_text(source)
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_product_id is None:
        return {}

    where_parts = ["aj.product_id = %s"]
    params: list[Any] = [normalized_product_id]
    if normalized_source is not None:
        where_parts.append("aj.source = %s")
        params.append(normalized_source)
    if normalized_user_id is not None:
        where_parts.append("(%s IS NULL OR aj.user_id = %s)")
        params.extend([normalized_user_id, normalized_user_id])

    joined = _safe_fetchone_with_order_fallback(
        cursor,
        f"""
        SELECT lar.*, aj.source AS analysis_source, aj.product_id AS analysis_product_id,
               aj.created_at AS analysis_job_created_at
        FROM listing_analysis_results lar
        INNER JOIN analysis_jobs aj ON aj.id = lar.analysis_job_id
        WHERE {" AND ".join(where_parts)}
        """,
        tuple(params),
        [
            "COALESCE(lar.updated_at, lar.created_at, aj.updated_at, aj.created_at) DESC, lar.id DESC",
            "COALESCE(lar.created_at, aj.created_at) DESC, lar.id DESC",
            "lar.id DESC",
        ],
    )
    if joined:
        return joined

    direct = _safe_fetchone_with_order_fallback(
        cursor,
        """
        SELECT *
        FROM listing_analysis_results
        WHERE product_id = %s
        """,
        (normalized_product_id,),
        [
            "COALESCE(updated_at, created_at) DESC, id DESC",
            "created_at DESC, id DESC",
            "id DESC",
        ],
    )
    return direct or {}


def _fetch_latest_url_analysis_log(
    cursor,
    *,
    user_id: Optional[str],
    product_id: str,
) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_product_id is None:
        return {}

    like_values = [
        f"%/product/{normalized_product_id}%",
        f"%product/{normalized_product_id}%",
    ]
    where_sql = " OR ".join(["url LIKE %s"] * len(like_values))
    params: list[Any] = list(like_values)
    user_sql = ""
    if normalized_user_id is not None:
        user_sql = "AND user_id = %s"
        params.append(normalized_user_id)

    row = _safe_fetchone_with_order_fallback(
        cursor,
        f"""
        SELECT *
        FROM url_analysis_logs
        WHERE ({where_sql})
          {user_sql}
        """,
        tuple(params),
        [
            "COALESCE(updated_at, created_at) DESC, id DESC",
            "created_at DESC, id DESC",
            "id DESC",
        ],
    )
    return row or {}


def _first_non_blank(*values: Any) -> Any:
    for value in values:
        if not _is_blank(value):
            return value
    return None


def _filter_active_journey_values(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if key not in DROPPED_RESALE_JOURNEY_COLUMNS
    }


def _filter_trade_prefill_values(values: dict[str, Any]) -> dict[str, Any]:
    filtered: dict[str, Any] = {}
    for key, value in values.items():
        if key not in TRADE_PREFILL_FIELDS:
            continue
        if _is_blank(value):
            continue
        normalized = _normalize_for_column(key, value)
        if normalized is not None:
            filtered[key] = normalized
    return filtered


def _source_timestamp(row: dict[str, Any], *field_names: str) -> Optional[datetime]:
    return _latest_datetime(*(row.get(field_name) for field_name in field_names))


def _decode_json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None
    return None


def _extract_image_url_from_payload(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        for key in (
            "image_url",
            "imageUrl",
            "thumbnail_url",
            "thumbnailUrl",
            "thumbnail",
            "productImageUrl",
        ):
            image_url = _extract_image_url_from_payload(value.get(key))
            if image_url is not None:
                return image_url
        return None
    if isinstance(value, list):
        for item in value:
            image_url = _extract_image_url_from_payload(item)
            if image_url is not None:
                return image_url
        return None
    return _normalize_optional_text(value)


def _normalize_location_value(value: Any) -> Optional[str]:
    if isinstance(value, list):
        parts = [_normalize_optional_text(item) for item in value]
        parts = [part for part in parts if part]
        return ", ".join(parts) if parts else None
    return _normalize_optional_text(value)


def _build_alert_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    listing_price = _normalize_optional_int(row.get("price_krw"))
    fair_price = _normalize_optional_int(row.get("fair_price_krw"))
    target_price = _normalize_optional_int(row.get("target_price_krw"))

    expected_profit = None
    if target_price is not None:
        expected_profit = target_price
    elif fair_price is not None and listing_price is not None:
        expected_profit = fair_price - listing_price

    image_value = _first_non_blank(row.get("listing_image_url"), row.get("image_url"))
    image_urls = None
    if not _is_blank(image_value):
        image_urls = _normalize_json_text([_normalize_optional_text(image_value)])

    return _filter_active_journey_values({
        "source": _normalize_optional_text(row.get("source")),
        "product_id": _normalize_optional_text(row.get("product_id")),
        "url": _normalize_optional_text(row.get("url")),
        "title": _normalize_optional_text(row.get("title")),
        "listing_created_at": _normalize_optional_datetime(row.get("sort_date")),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("analyzed_at"), row.get("created_at"))),
        "listing_price_krw": listing_price,
        "product_type": _normalize_optional_text(row.get("product_type")),
        "chip": _normalize_optional_text(row.get("chip")),
        "screen_inch": _normalize_optional_int(row.get("screen_inch")),
        "ram_gb": _normalize_optional_int(row.get("ram_gb")),
        "ssd_gb": _normalize_optional_int(row.get("ssd_gb")),
        "fair_price_krw": fair_price,
        "discount_rate_percent": _normalize_optional_float(row.get("drop_rate_percent")),
        "expected_profit_krw": expected_profit,
        "risk_score": _normalize_optional_int(row.get("risk_score")),
        "reason_tags": _normalize_json_text(row.get("risk_keywords")),
        "body_text": _normalize_optional_text(_first_non_blank(row.get("body_text"), row.get("body_excerpt"))),
        "image_urls": image_urls,
        "seller_nickname": _normalize_optional_text(_first_non_blank(row.get("seller_nickname"), row.get("seller_store_name"))),
        "seller_shop_id": _normalize_optional_text(_first_non_blank(row.get("seller_shop_id"), row.get("seller_store_seq"))),
        "seller_location": _normalize_optional_text(row.get("seller_location")),
        "watch_rule_id": _normalize_optional_int(row.get("watch_rule_id")),
        "analysis_job_id": _normalize_optional_int(row.get("analysis_job_id")),
    })


def _build_read_archive_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    image_url = _normalize_optional_text(row.get("alert_listing_image_url"))
    image_urls = _normalize_json_text([image_url]) if image_url else None

    return _filter_active_journey_values({
        "source": _normalize_optional_text(row.get("alert_source")),
        "product_id": _normalize_optional_text(row.get("alert_product_id")),
        "url": _normalize_optional_text(row.get("alert_url")),
        "title": _normalize_optional_text(row.get("alert_title")),
        "listing_created_at": _normalize_optional_datetime(row.get("alert_sort_date")),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("alert_analyzed_at"), row.get("alert_created_at"), row.get("created_at"))),
        "listing_price_krw": _normalize_optional_int(row.get("alert_price_krw")),
        "product_type": _normalize_optional_text(row.get("alert_product_type")),
        "chip": _normalize_optional_text(row.get("alert_chip")),
        "screen_inch": _normalize_optional_int(row.get("alert_screen_inch")),
        "ram_gb": _normalize_optional_int(row.get("alert_ram_gb")),
        "ssd_gb": _normalize_optional_int(row.get("alert_ssd_gb")),
        "fair_price_krw": _normalize_optional_int(row.get("alert_fair_price_krw")),
        "discount_rate_percent": _normalize_optional_float(_first_non_blank(row.get("alert_drop_rate_percent"), row.get("alert_rule_drop_rate_percent"))),
        "risk_score": _normalize_optional_int(row.get("alert_risk_score")),
        "reason_tags": _normalize_json_text(row.get("alert_risk_keywords")),
        "body_text": _normalize_optional_text(_first_non_blank(row.get("alert_body_text"), row.get("alert_body_excerpt"))),
        "image_urls": image_urls,
    })


def _build_analysis_job_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    return _filter_active_journey_values({
        "source": _normalize_optional_text(row.get("source")),
        "product_id": _normalize_optional_text(row.get("product_id")),
        "url": _normalize_optional_text(row.get("url")),
        "title": _normalize_optional_text(row.get("title")),
        "listing_created_at": _normalize_optional_datetime(row.get("sort_date")),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("analyzed_at"), row.get("created_at"))),
        "listing_price_krw": _normalize_optional_int(row.get("price_krw")),
        "product_type": _normalize_optional_text(row.get("product_type")),
        "chip": _normalize_optional_text(row.get("chip")),
        "screen_inch": _normalize_optional_int(row.get("screen_inch")),
        "ram_gb": _normalize_optional_int(row.get("ram_gb")),
        "ssd_gb": _normalize_optional_int(row.get("ssd_gb")),
        "fair_price_krw": _normalize_optional_int(row.get("fair_price_krw")),
        "discount_rate_percent": _normalize_optional_float(row.get("drop_rate_percent")),
        "risk_score": _normalize_optional_int(row.get("risk_score")),
        "reason_tags": _normalize_json_text(row.get("risk_keywords")),
        "body_text": _normalize_optional_text(row.get("body_text")),
    })


def _build_url_analysis_log_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    return _filter_active_journey_values({
        "source": _normalize_optional_text(row.get("source")),
        "product_id": _extract_product_id_from_url(row.get("url")),
        "url": _normalize_optional_text(row.get("url")),
        "title": _normalize_optional_text(row.get("title")),
        "listing_price_krw": _normalize_optional_int(row.get("listing_price_krw")),
        "product_type": _normalize_optional_text(row.get("product_type")),
        "chip": _normalize_optional_text(row.get("chip")),
        "screen_inch": _normalize_optional_int(row.get("screen_inch")),
        "ram_gb": _normalize_optional_int(row.get("ram_gb")),
        "ssd_gb": _normalize_optional_int(row.get("ssd_gb")),
        "fair_price_krw": _normalize_optional_int(row.get("fair_price_krw")),
        "discount_rate_percent": _normalize_optional_float(row.get("diff_ratio")),
        "body_text": _normalize_optional_text(row.get("body_text")),
    })


def _build_seen_product_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    image_urls = None
    image_url = _normalize_optional_text(row.get("image_url"))
    if image_url:
        image_urls = _normalize_json_text([image_url])

    return _filter_active_journey_values({
        "source": DEFAULT_SOURCE,
        "product_id": _normalize_optional_text(row.get("seq")),
        "url": _normalize_optional_text(row.get("product_url")),
        "title": _normalize_optional_text(_first_non_blank(row.get("last_title"), row.get("title"))),
        "listing_created_at": _normalize_optional_datetime(_first_non_blank(row.get("last_sort_date"), row.get("sort_date"))),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("discovered_at"), row.get("created_at"), row.get("first_seen_at"))),
        "listing_price_krw": _normalize_optional_int(_first_non_blank(row.get("last_price_krw"), row.get("price_krw"), row.get("price"))),
        "seller_nickname": _normalize_optional_text(_first_non_blank(row.get("seller_nickname"), row.get("seller_store_name"))),
        "seller_shop_id": _normalize_optional_text(_first_non_blank(row.get("seller_shop_id"), row.get("seller_store_seq"))),
        "seller_location": _normalize_optional_text(row.get("seller_location")),
        "image_urls": image_urls,
        "body_text": _normalize_optional_text(row.get("body_text")),
    })


def _build_search_result_mapping(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    if not row:
        return {}

    raw_json = _decode_json_value(row.get("raw_json"))
    raw_image_url = _extract_image_url_from_payload(raw_json) if isinstance(raw_json, (dict, list)) else None
    raw_location = None
    if isinstance(raw_json, dict):
        raw_location = _normalize_location_value(
            _first_non_blank(
                raw_json.get("seller_location"),
                raw_json.get("location"),
                raw_json.get("location_name"),
                raw_json.get("locationName"),
                raw_json.get("location_names"),
                raw_json.get("locationNames"),
            )
        )

    return _filter_active_journey_values({
        "source": source,
        "product_id": _normalize_optional_text(row.get("product_id")),
        "url": _normalize_optional_text(row.get("url")),
        "title": _normalize_optional_text(row.get("title")),
        "listing_price_krw": _normalize_optional_int(_first_non_blank(row.get("price_krw"), row.get("price"))),
        "seller_nickname": _normalize_optional_text(_first_non_blank(row.get("seller_nickname"), row.get("seller_store_name"))),
        "seller_shop_id": _normalize_optional_text(_first_non_blank(row.get("seller_shop_id"), row.get("seller_store_seq"))),
        "seller_location": _normalize_optional_text(row.get("seller_location")) or raw_location,
        "image_urls": _normalize_json_text(_first_non_blank(row.get("image_urls"), row.get("image_url"), raw_image_url)),
        "body_text": _normalize_optional_text(row.get("body_text")),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("created_at"), row.get("fetched_at"))),
    })


def _build_listing_analysis_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    return _filter_active_journey_values({
        "product_type": _normalize_optional_text(row.get("product_type")),
        "chip": _normalize_optional_text(row.get("chip")),
        "screen_inch": _normalize_optional_int(row.get("screen_inch")),
        "ram_gb": _normalize_optional_int(row.get("ram_gb")),
        "ssd_gb": _normalize_optional_int(row.get("ssd_gb")),
        "fair_price_krw": _normalize_optional_int(row.get("fair_price_krw")),
        "listing_price_krw": _normalize_optional_int(row.get("listing_price_krw")),
        "discount_rate_percent": _normalize_optional_float(_first_non_blank(row.get("discount_rate_percent"), row.get("diff_ratio"))),
        "expected_profit_krw": _normalize_optional_int(_first_non_blank(row.get("expected_profit_krw"), row.get("diff_amount_krw"))),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("analyzed_at"), row.get("created_at"))),
        "body_text": _normalize_optional_text(row.get("body_text")),
    })


def _parse_spec_from_prefill_text(row: dict[str, Any]) -> dict[str, Any]:
    if all(not _is_blank(row.get(field)) for field in TRADE_PREFILL_SPEC_FIELDS):
        return {}

    title = _normalize_optional_text(row.get("title"))
    body_text = _normalize_optional_text(row.get("body_text"))
    parsing_title = title or body_text
    if parsing_title is None:
        return {}

    try:
        parsed = parse_listing_text(parsing_title, body_text=body_text)
    except Exception:
        return {}

    parsed_values: dict[str, Any] = {}
    for field in TRADE_PREFILL_SPEC_FIELDS:
        if not _is_blank(row.get(field)):
            continue
        parsed_value = parsed.get(field)
        if _is_blank(parsed_value):
            continue
        normalized = _normalize_for_column(field, parsed_value)
        if normalized is not None:
            parsed_values[field] = normalized
    return parsed_values


def _apply_non_blank_values(target: dict[str, Any], values: dict[str, Any]) -> None:
    for field, value in _filter_trade_prefill_values(values).items():
        if _is_blank(target.get(field)):
            target[field] = value


def _fill_prefill_blanks_from_seed(row: dict[str, Any], seed_values: Optional[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(row)
    for field, value in _filter_trade_prefill_values(dict(seed_values or {})).items():
        if _is_blank(merged.get(field)):
            merged[field] = value
    return merged


def _build_trade_prefill_from_source_rows(
    *,
    user_id: str,
    product_id: str,
    alert_row: dict[str, Any],
    listing_analysis_row: dict[str, Any],
    url_analysis_row: dict[str, Any],
    seen_product_row: dict[str, Any],
    search_result_row: dict[str, Any],
) -> dict[str, Any]:
    alert_values = _build_alert_mapping(alert_row)
    listing_values = _build_listing_analysis_mapping(listing_analysis_row)
    url_values = _build_url_analysis_log_mapping(url_analysis_row)
    seen_values = _build_seen_product_mapping(seen_product_row)
    search_values = _build_search_result_mapping(search_result_row, source=DEFAULT_SOURCE)

    source_candidates = [
        ("alert_events", alert_row, alert_values, _source_timestamp(alert_row, "sort_date", "analyzed_at", "created_at")),
        (
            "listing_analysis_results",
            listing_analysis_row,
            listing_values,
            _source_timestamp(listing_analysis_row, "updated_at", "created_at", "analysis_job_created_at"),
        ),
        ("url_analysis_logs", url_analysis_row, url_values, _source_timestamp(url_analysis_row, "updated_at", "created_at")),
        (
            "joongna_seen_products",
            seen_product_row,
            seen_values,
            _source_timestamp(seen_product_row, "last_sort_date", "updated_at", "last_seen_at", "first_seen_at"),
        ),
        ("search_results", search_result_row, search_values, _source_timestamp(search_result_row, "sort_date", "fetched_at", "created_at")),
    ]
    used_sources = [name for name, raw_row, _values, _timestamp in source_candidates if raw_row]
    if not used_sources:
        return {
            "ok": False,
            "reason": "not_found",
            "message": "기존 DB 기록 없음",
            "user_id": user_id,
            "product_id": product_id,
            "row": {
                "user_id": user_id,
                "source": DEFAULT_SOURCE,
                "product_id": product_id,
                "current_stage": STAGE_DISCOVERED,
            },
            "sources": [],
        }

    resolved_source = (
        _normalize_optional_text(
            _first_non_blank(
                alert_values.get("source"),
                listing_analysis_row.get("analysis_source"),
                url_values.get("source"),
                search_values.get("source"),
                seen_values.get("source"),
            )
        )
        or DEFAULT_SOURCE
    )
    row: dict[str, Any] = {
        "user_id": user_id,
        "source": resolved_source,
        "product_id": product_id,
    }

    for _name, _raw_row, values, _timestamp in source_candidates:
        _apply_non_blank_values(row, values)

    latest_state_values: dict[str, tuple[Optional[datetime], int, Any]] = {}
    for priority_index, (_name, _raw_row, values, timestamp) in enumerate(source_candidates):
        for field in TRADE_PREFILL_STATE_FIELDS:
            value = values.get(field)
            if _is_blank(value):
                continue
            current = latest_state_values.get(field)
            current_timestamp = current[0] if current else None
            should_replace = current is None
            if not should_replace and timestamp is not None:
                if current_timestamp is None or timestamp > current_timestamp:
                    should_replace = True
                elif timestamp == current_timestamp and priority_index < current[1]:
                    should_replace = True
            if should_replace:
                latest_state_values[field] = (timestamp, priority_index, value)

    for field, (_timestamp, _priority_index, value) in latest_state_values.items():
        normalized = _normalize_for_column(field, value)
        if normalized is not None:
            row[field] = normalized

    for field in TRADE_PREFILL_SPEC_FIELDS:
        value = listing_values.get(field)
        if not _is_blank(value):
            normalized = _normalize_for_column(field, value)
            if normalized is not None:
                row[field] = normalized

    row.update(_parse_spec_from_prefill_text(row))
    row["user_id"] = user_id
    row["source"] = _normalize_optional_text(row.get("source")) or DEFAULT_SOURCE
    row["product_id"] = product_id
    row["current_stage"] = STAGE_DISCOVERED

    return {
        "ok": True,
        "existing": False,
        "trade_journey_id": None,
        "id": None,
        "source": row.get("source"),
        "product_id": product_id,
        "current_stage": STAGE_DISCOVERED,
        "row": _filter_trade_prefill_values(row),
        "sources": used_sources,
    }


def _build_trade_prefill_from_existing_db_with_cursor(
    cursor,
    *,
    product_id: str,
    user_id: str,
    source: Optional[str] = None,
) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")
    if normalized_product_id is None:
        raise ValueError("invalid_product_id")

    normalized_source = _normalize_optional_text(source) or DEFAULT_SOURCE
    alert_row = _fetch_latest_alert_event_by_reference(
        cursor,
        user_id=normalized_user_id,
        source=normalized_source,
        product_id=normalized_product_id,
    )
    if alert_row:
        normalized_source = _normalize_optional_text(alert_row.get("source")) or normalized_source

    listing_analysis_row = _fetch_latest_listing_analysis(
        cursor,
        source=normalized_source,
        product_id=normalized_product_id,
        user_id=normalized_user_id,
    )
    url_analysis_row = _fetch_latest_url_analysis_log(
        cursor,
        user_id=normalized_user_id,
        product_id=normalized_product_id,
    )
    seen_product_row = _fetch_latest_seen_product(cursor, product_id=normalized_product_id)
    search_result_row = _fetch_latest_search_result(cursor, product_id=normalized_product_id)

    return _build_trade_prefill_from_source_rows(
        user_id=normalized_user_id,
        product_id=normalized_product_id,
        alert_row=alert_row,
        listing_analysis_row=listing_analysis_row,
        url_analysis_row=url_analysis_row,
        seen_product_row=seen_product_row,
        search_result_row=search_result_row,
    )


def build_trade_prefill_from_existing_db(product_id, user_id):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")
    if normalized_product_id is None:
        raise ValueError("invalid_product_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        return _build_trade_prefill_from_existing_db_with_cursor(
            cursor,
            product_id=normalized_product_id,
            user_id=normalized_user_id,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def build_trade_prefill_from_input(*, user_id: str, input_value: str) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    source, product_id, seed_values = _build_basic_start_reference(
        user_id=normalized_user_id,
        reference=input_value,
    )
    if product_id is None:
        return {"ok": False, "reason": "invalid_product_id"}

    result = build_trade_prefill_from_existing_db(product_id, normalized_user_id)
    if not result.get("ok"):
        row = _fill_prefill_blanks_from_seed(dict(result.get("row") or {}), seed_values)
        row["user_id"] = normalized_user_id
        row["source"] = _normalize_optional_text(row.get("source")) or source
        row["product_id"] = product_id
        row["current_stage"] = row.get("current_stage") or STAGE_DISCOVERED
        result = {**result, "source": row.get("source"), "product_id": product_id, "row": row}
        return result

    row = _fill_prefill_blanks_from_seed(dict(result.get("row") or {}), seed_values)
    row["user_id"] = normalized_user_id
    row["source"] = _normalize_optional_text(row.get("source")) or source
    row["product_id"] = product_id
    row["current_stage"] = row.get("current_stage") or STAGE_DISCOVERED
    return {
        **result,
        "source": row.get("source"),
        "product_id": product_id,
        "current_stage": row.get("current_stage"),
        "row": _filter_trade_prefill_values(row),
    }


def _merge_by_priority(
    *,
    user_values: dict[str, Any],
    existing_row: dict[str, Any],
    source_candidates: list[dict[str, Any]],
    writable_columns: set[str],
) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    for field in AUTO_HYDRATE_FIELDS:
        if field not in writable_columns:
            continue

        user_value = user_values.get(field)
        if not _is_blank(user_value):
            normalized_user = _normalize_for_column(field, user_value)
            if normalized_user is not None and normalized_user != existing_row.get(field):
                updates[field] = normalized_user
            continue

        existing_value = existing_row.get(field)
        if not _is_blank(existing_value):
            continue

        for candidate in source_candidates:
            candidate_value = candidate.get(field)
            if _is_blank(candidate_value):
                continue
            normalized_candidate = _normalize_for_column(field, candidate_value)
            if normalized_candidate is None:
                continue
            updates[field] = normalized_candidate
            break

    resolved_fair = _normalize_optional_int(
        updates.get("fair_price_krw") if "fair_price_krw" in updates else existing_row.get("fair_price_krw")
    )
    resolved_listing = _normalize_optional_int(
        updates.get("listing_price_krw") if "listing_price_krw" in updates else existing_row.get("listing_price_krw")
    )

    if (
        "discount_rate_percent" in writable_columns
        and _is_blank(existing_row.get("discount_rate_percent"))
        and "discount_rate_percent" not in updates
        and resolved_fair is not None
        and resolved_fair > 0
        and resolved_listing is not None
    ):
        updates["discount_rate_percent"] = round(((resolved_fair - resolved_listing) / resolved_fair) * 100.0, 2)

    if (
        "expected_profit_krw" in writable_columns
        and _is_blank(existing_row.get("expected_profit_krw"))
        and "expected_profit_krw" not in updates
        and resolved_fair is not None
        and resolved_listing is not None
    ):
        updates["expected_profit_krw"] = resolved_fair - resolved_listing

    return updates


def _apply_updates(cursor, *, row_id: int, updates: dict[str, Any]):
    if not updates:
        return
    assignments = ", ".join([f"{column} = %s" for column in updates.keys()])
    values = tuple(updates.values()) + (row_id,)
    cursor.execute(f"UPDATE resale_trade_journeys SET {assignments} WHERE id = %s", values)


def _load_row_detail(cursor, row_id: int) -> dict[str, Any]:
    row = _safe_fetchone(
        cursor,
        """
        SELECT *
        FROM resale_trade_journeys
        WHERE id = %s
        LIMIT 1
        """,
        (row_id,),
    )
    return row or {"id": row_id}


def _derive_stage_after_purchase(row: dict[str, Any], payload_updates: dict[str, Any]) -> Optional[str]:
    manual_stage = _normalize_optional_text(payload_updates.get("current_stage"))
    if manual_stage:
        return manual_stage

    inspection_keys = {
        "purchased_at",
        "purchase_price_krw",
        "battery_health_percent",
        "battery_cycle_count",
        "exterior_grade",
        "included_items",
        "inspection_notes",
        "truetone_ok",
        "purchase_method",
        "purchase_location",
        "transport_cost_krw",
        "shipping_cost_krw",
        "payment_method",
        "serial_number",
        "model_number",
        "applecare_status",
        "activation_lock_off",
        "mdm_lock_none",
        "battery_condition",
        "display_condition",
        "keyboard_condition",
        "trackpad_condition",
        "speaker_condition",
        "camera_condition",
        "wifi_bluetooth_ok",
        "repair_suspected",
        "cpu_core_count",
        "gpu_core_count",
    }

    if any(field in payload_updates for field in inspection_keys):
        return STAGE_INSPECTED

    current_stage = _normalize_optional_text(row.get("current_stage"))
    return current_stage or STAGE_DISCOVERED


def _derive_stage_after_resale_or_sold(row: dict[str, Any], payload_updates: Optional[dict[str, Any]] = None) -> str:
    manual_stage = _normalize_optional_text((payload_updates or {}).get("current_stage"))
    if manual_stage:
        return manual_stage

    sale_price = _normalize_optional_int(row.get("sale_price_krw"))
    sold_at = _normalize_optional_datetime(row.get("sold_at"))
    if sale_price is not None or sold_at is not None:
        return STAGE_SOLD

    has_resale_listing = any(
        not _is_blank(row.get(field))
        for field in (
            "resale_listing_price_krw",
            "resale_platform",
            "resale_url",
            "resale_listing_created_at",
        )
    )
    if has_resale_listing:
        return STAGE_RESALE_LISTED

    current_stage = _normalize_optional_text(row.get("current_stage"))
    return current_stage or STAGE_DISCOVERED


def _build_purchase_calculated_updates(row: dict[str, Any], writable_columns: set[str]) -> dict[str, Any]:
    calculated: dict[str, Any] = {}

    fair_price = _normalize_optional_int(row.get("fair_price_krw"))
    purchase_price = _normalize_optional_int(row.get("purchase_price_krw"))
    total_cost = _normalize_optional_int(row.get("total_cost_krw"))

    if fair_price is not None and fair_price > 0 and purchase_price is not None and "discount_rate_percent" in writable_columns:
        calculated["discount_rate_percent"] = round(((fair_price - purchase_price) / fair_price) * 100.0, 2)

    if fair_price is not None and total_cost is not None and "expected_profit_krw" in writable_columns:
        calculated["expected_profit_krw"] = fair_price - total_cost

    return calculated


def _build_sold_calculated_updates(row: dict[str, Any], writable_columns: set[str]) -> dict[str, Any]:
    calculated: dict[str, Any] = {}

    sale_price = _normalize_optional_int(row.get("sale_price_krw"))
    purchase_price = _normalize_optional_int(row.get("purchase_price_krw"))
    total_cost = _normalize_optional_int(row.get("total_cost_krw"))
    final_shipping = _normalize_optional_int(row.get("final_shipping_cost_krw")) or 0
    platform_fee = _normalize_optional_int(row.get("platform_fee_krw")) or 0

    if sale_price is not None and purchase_price is not None and "gross_profit_krw" in writable_columns:
        calculated["gross_profit_krw"] = sale_price - purchase_price

    if sale_price is not None and total_cost is not None and "net_profit_krw" in writable_columns:
        calculated["net_profit_krw"] = sale_price - total_cost - final_shipping - platform_fee

    if total_cost is not None and total_cost > 0 and sale_price is not None and "roi_percent" in writable_columns:
        net = sale_price - total_cost - final_shipping - platform_fee
        calculated["roi_percent"] = round((net / total_cost) * 100.0, 2)

    resale_created_at = _normalize_optional_datetime(row.get("resale_listing_created_at"))
    sold_at = _normalize_optional_datetime(row.get("sold_at"))
    purchased_at = _normalize_optional_datetime(row.get("purchased_at"))

    if resale_created_at and sold_at and "sale_duration_hours" in writable_columns:
        calculated["sale_duration_hours"] = int((sold_at - resale_created_at).total_seconds() // 3600)

    if purchased_at and sold_at and "total_holding_time_hours" in writable_columns:
        holding_hours = int((sold_at - purchased_at).total_seconds() // 3600)
        calculated["total_holding_time_hours"] = holding_hours
        net_profit = _normalize_optional_int(_first_non_blank(calculated.get("net_profit_krw"), row.get("net_profit_krw")))
        if net_profit is not None and holding_hours > 0 and "profit_per_day_krw" in writable_columns:
            calculated["profit_per_day_krw"] = int(round(net_profit / (holding_hours / 24.0), 0))

    return calculated


def _normalize_identity(*, user_id: str, source: Any, product_id: Any) -> tuple[str, str, str]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    normalized_source = _normalize_source(source)

    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_product_id is None:
        raise ValueError("invalid_product_id")

    return normalized_user_id, normalized_source, normalized_product_id


def _build_basic_start_reference(
    *,
    user_id: str,
    reference: str,
    source_hint: Optional[str] = None,
) -> tuple[str, Optional[str], dict[str, Any]]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_reference = _normalize_optional_text(reference)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")
    if normalized_reference is None:
        raise ValueError("invalid_url")

    reference_url = _normalize_reference_url(normalized_reference)
    product_id = _extract_product_id_from_url(normalized_reference)
    if product_id is None and reference_url is None:
        product_id = normalized_reference

    source = _normalize_optional_text(source_hint) or _infer_source_from_url(reference_url)
    seed_values = {"source": source}
    if product_id is not None:
        seed_values["product_id"] = product_id
    if reference_url is not None:
        seed_values["url"] = reference_url
    return source, product_id, seed_values


def _resolve_start_reference_from_alerts(
    cursor,
    *,
    user_id: str,
    reference: str,
    source_hint: Optional[str] = None,
) -> tuple[str, str, dict[str, Any]]:
    source, product_id, seed_values = _build_basic_start_reference(
        user_id=user_id,
        reference=reference,
        source_hint=source_hint,
    )
    reference_url = _normalize_reference_url(reference)

    alert_row = _fetch_latest_alert_event_by_reference(
        cursor,
        user_id=user_id,
        source=source,
        product_id=product_id,
        url=reference_url,
    )
    alert_values = _build_alert_mapping(alert_row)
    if not alert_values:
        if product_id is None:
            raise ValueError("invalid_product_id")
        return source, product_id, seed_values

    resolved_url = _normalize_optional_text(
        _first_non_blank(
            alert_values.get("url"),
            seed_values.get("url"),
            reference_url,
        )
    )
    resolved_source = (
        _normalize_optional_text(alert_values.get("source"))
        or source
        or _infer_source_from_url(resolved_url)
    )
    resolved_product_id = (
        _normalize_optional_text(alert_values.get("product_id"))
        or product_id
        or _extract_product_id_from_url(resolved_url)
    )
    if resolved_product_id is None:
        raise ValueError("invalid_product_id")

    resolved_seed_values = {**seed_values, **alert_values}
    resolved_seed_values["source"] = resolved_source
    resolved_seed_values["product_id"] = resolved_product_id
    if resolved_url is not None:
        resolved_seed_values["url"] = resolved_url

    return resolved_source, resolved_product_id, resolved_seed_values


def _hydrate_row_by_product(
    cursor,
    *,
    row: dict[str, Any],
    user_id: str,
    source: str,
    product_id: str,
    user_values: Optional[dict[str, Any]],
    writable_columns: set[str],
) -> dict[str, Any]:
    prefill_result = _build_trade_prefill_from_existing_db_with_cursor(
        cursor,
        product_id=product_id,
        user_id=user_id,
        source=source,
    )
    prefill_candidate = dict(prefill_result.get("row") or {}) if prefill_result.get("ok") else {}

    merged_updates = _merge_by_priority(
        user_values=user_values or {},
        existing_row=row,
        source_candidates=[prefill_candidate],
        writable_columns=writable_columns,
    )

    row_id = _normalize_optional_int(row.get("id"))
    if row_id is None:
        return row

    updates_to_apply = _filter_writable_updates(merged_updates, writable_columns)
    _apply_updates(cursor, row_id=row_id, updates=updates_to_apply)
    return _load_row_detail(cursor, row_id)


def _build_prefill_row_by_product(
    cursor,
    *,
    user_id: str,
    source: str,
    product_id: str,
    seed_values: Optional[dict[str, Any]] = None,
    prefill_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    base_row: dict[str, Any] = {
        "id": None,
        "user_id": user_id,
        "source": source,
        "product_id": product_id,
        "current_stage": STAGE_DISCOVERED,
    }
    prefill_row = dict(base_row)
    resolved_prefill_result = prefill_result
    if resolved_prefill_result is None:
        resolved_prefill_result = _build_trade_prefill_from_existing_db_with_cursor(
            cursor,
            product_id=product_id,
            user_id=user_id,
            source=source,
        )
    if resolved_prefill_result.get("ok"):
        prefill_row.update(_filter_trade_prefill_values(dict(resolved_prefill_result.get("row") or {})))

    prefill_row = _fill_prefill_blanks_from_seed(prefill_row, seed_values)
    prefill_row["source"] = _normalize_optional_text(prefill_row.get("source")) or source
    prefill_row["product_id"] = product_id
    prefill_row["user_id"] = user_id
    if _is_blank(prefill_row.get("current_stage")):
        prefill_row["current_stage"] = STAGE_DISCOVERED
    return prefill_row


def hydrate_resale_trade_journey_by_product(
    user_id: str,
    source: str,
    product_id: str,
    *,
    row_id: Optional[int] = None,
    user_values: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    normalized_user_id, normalized_source, normalized_product_id = _normalize_identity(
        user_id=user_id,
        source=source,
        product_id=product_id,
    )

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _, writable_columns = _get_resale_columns(cursor)

        if row_id is not None:
            row = _fetch_journey_by_id(cursor, row_id, user_id=normalized_user_id, for_update=True)
        else:
            row = _fetch_journey_by_key(
                cursor,
                user_id=normalized_user_id,
                source=normalized_source,
                product_id=normalized_product_id,
                for_update=True,
            )

        if not row:
            return {"ok": False, "reason": "not_found"}

        hydrated_row = _hydrate_row_by_product(
            cursor,
            row=row,
            user_id=normalized_user_id,
            source=normalized_source,
            product_id=normalized_product_id,
            user_values=user_values,
            writable_columns=writable_columns,
        )

        connection.commit()
        return {
            "ok": True,
            "id": hydrated_row.get("id"),
            "source": hydrated_row.get("source"),
            "product_id": hydrated_row.get("product_id"),
            "current_stage": hydrated_row.get("current_stage"),
            "row": hydrated_row,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def create_or_hydrate_resale_trade_journey_from_product(
    *,
    user_id: str,
    source: str,
    product_id: str,
    seed_values: Optional[dict[str, Any]] = None,
    include_existing: bool = False,
) -> dict[str, Any]:
    normalized_user_id, normalized_source, normalized_product_id = _normalize_identity(
        user_id=user_id,
        source=source,
        product_id=product_id,
    )

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        _, writable_columns = _get_resale_columns(cursor)

        row = _fetch_journey_by_key(
            cursor,
            user_id=normalized_user_id,
            source=normalized_source,
            product_id=normalized_product_id,
            for_update=True,
        )
        existing_row_id = _normalize_optional_int((row or {}).get("id"))
        was_existing = existing_row_id is not None and existing_row_id > 0

        if was_existing:
            row_id = existing_row_id
        else:
            row_id = _insert_or_get_journey_id(
                cursor,
                user_id=normalized_user_id,
                source=normalized_source,
                product_id=normalized_product_id,
                writable_columns=writable_columns,
            )
            row = _fetch_journey_by_id(cursor, row_id, user_id=normalized_user_id, for_update=True)

        if not row:
            raise RuntimeError("journey_not_found_after_upsert")

        user_values: dict[str, Any] = {}
        if isinstance(seed_values, dict):
            user_values.update(seed_values)
        user_values.update(
            {
            "user_id": normalized_user_id,
            "source": normalized_source,
            "product_id": normalized_product_id,
            }
        )

        hydrated_row = _hydrate_row_by_product(
            cursor,
            row=row,
            user_id=normalized_user_id,
            source=normalized_source,
            product_id=normalized_product_id,
            user_values=user_values,
            writable_columns=writable_columns,
        )

        if "current_stage" in writable_columns and _is_blank(hydrated_row.get("current_stage")):
            _apply_updates(cursor, row_id=row_id, updates={"current_stage": STAGE_DISCOVERED})
            hydrated_row = _load_row_detail(cursor, row_id)

        connection.commit()

        result = {
            "ok": True,
            "id": row_id,
            "source": normalized_source,
            "product_id": normalized_product_id,
            "current_stage": hydrated_row.get("current_stage"),
            "row": hydrated_row,
        }
        if include_existing:
            result["existing"] = was_existing
            result["trade_journey_id"] = row_id
        return result
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def start_or_prefill_resale_trade_journey_from_product(
    *,
    user_id: str,
    source: str,
    product_id: str,
    seed_values: Optional[dict[str, Any]] = None,
    allow_empty_prefill: bool = True,
) -> dict[str, Any]:
    normalized_user_id, normalized_source, normalized_product_id = _normalize_identity(
        user_id=user_id,
        source=source,
        product_id=product_id,
    )

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _, writable_columns = _get_resale_columns(cursor)

        existing_row = _fetch_journey_by_key(
            cursor,
            user_id=normalized_user_id,
            source=normalized_source,
            product_id=normalized_product_id,
            for_update=True,
        )
        if not existing_row:
            existing_row = _fetch_journey_by_product_id(
                cursor,
                user_id=normalized_user_id,
                product_id=normalized_product_id,
                for_update=True,
            )
        existing_row_id = _normalize_optional_int((existing_row or {}).get("id"))

        if existing_row_id is not None and existing_row_id > 0:
            resolved_source = _normalize_optional_text(existing_row.get("source")) or normalized_source
            resolved_product_id = _normalize_optional_text(existing_row.get("product_id")) or normalized_product_id
            existing_seed_values = dict(seed_values or {})
            existing_seed_values["source"] = resolved_source
            existing_seed_values["product_id"] = resolved_product_id
            hydrated_row = _hydrate_row_by_product(
                cursor,
                row=existing_row,
                user_id=normalized_user_id,
                source=resolved_source,
                product_id=resolved_product_id,
                user_values=existing_seed_values,
                writable_columns=writable_columns,
            )
            connection.commit()
            return {
                "ok": True,
                "existing": True,
                "trade_journey_id": existing_row_id,
                "id": existing_row_id,
                "source": hydrated_row.get("source") or resolved_source,
                "product_id": hydrated_row.get("product_id") or resolved_product_id,
                "current_stage": hydrated_row.get("current_stage"),
                "row": hydrated_row,
            }

        prefill_result = _build_trade_prefill_from_existing_db_with_cursor(
            cursor,
            product_id=normalized_product_id,
            user_id=normalized_user_id,
            source=normalized_source,
        )
        if not allow_empty_prefill and not prefill_result.get("ok"):
            row = _fill_prefill_blanks_from_seed(dict(prefill_result.get("row") or {}), seed_values)
            row["user_id"] = normalized_user_id
            row["source"] = _normalize_optional_text(row.get("source")) or normalized_source
            row["product_id"] = normalized_product_id
            row["current_stage"] = row.get("current_stage") or STAGE_DISCOVERED
            return {
                **prefill_result,
                "source": row.get("source"),
                "product_id": normalized_product_id,
                "current_stage": row.get("current_stage"),
                "row": _filter_trade_prefill_values(row),
            }

        prefill_row = _build_prefill_row_by_product(
            cursor,
            user_id=normalized_user_id,
            source=normalized_source,
            product_id=normalized_product_id,
            seed_values=seed_values,
            prefill_result=prefill_result,
        )
        return {
            "ok": True,
            "existing": False,
            "trade_journey_id": None,
            "id": None,
            "source": prefill_row.get("source") or normalized_source,
            "product_id": normalized_product_id,
            "current_stage": prefill_row.get("current_stage"),
            "row": prefill_row,
            "sources": prefill_result.get("sources", []),
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def start_resale_trade_journey_from_url(*, user_id: str, url: str) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_reference = _normalize_optional_text(url)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")
    if normalized_reference is None:
        raise ValueError("invalid_url")

    source, product_id, seed_values = _build_basic_start_reference(
        user_id=normalized_user_id,
        reference=normalized_reference,
    )
    if product_id is None:
        return {"ok": False, "reason": "invalid_product_id"}

    prefill_result = build_trade_prefill_from_input(
        user_id=normalized_user_id,
        input_value=normalized_reference,
    )
    if prefill_result.get("ok"):
        prefill_row = dict(prefill_result.get("row") or {})
        source = _normalize_optional_text(prefill_row.get("source")) or _normalize_optional_text(prefill_result.get("source")) or source
        seed_values = _fill_prefill_blanks_from_seed(prefill_row, seed_values)

    result = start_or_prefill_resale_trade_journey_from_product(
        user_id=normalized_user_id,
        source=source,
        product_id=product_id,
        seed_values=seed_values,
        allow_empty_prefill=bool(prefill_result.get("ok")),
    )
    return result


def start_resale_trade_journey_from_alert(*, user_id: str, alert_event_id: int) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_alert_event_id = _normalize_optional_int(alert_event_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")
    if normalized_alert_event_id is None or normalized_alert_event_id <= 0:
        raise ValueError("invalid_alert_event_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        alert_row = _fetch_alert_event_by_id(
            cursor,
            user_id=normalized_user_id,
            alert_event_id=normalized_alert_event_id,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if not alert_row:
        return {"ok": False, "reason": "not_found"}

    seed_values = _build_alert_mapping(alert_row)
    resolved_url = _normalize_optional_text(_first_non_blank(seed_values.get("url"), alert_row.get("url")))
    source = _normalize_optional_text(seed_values.get("source")) or _infer_source_from_url(resolved_url)
    product_id = _normalize_optional_text(seed_values.get("product_id")) or _extract_product_id_from_url(resolved_url)
    if product_id is None:
        return {"ok": False, "reason": "invalid_product_id"}

    prefill_result = build_trade_prefill_from_existing_db(product_id, normalized_user_id)
    if prefill_result.get("ok"):
        prefill_row = dict(prefill_result.get("row") or {})
        source = _normalize_optional_text(prefill_row.get("source")) or _normalize_optional_text(prefill_result.get("source")) or source
        seed_values = _fill_prefill_blanks_from_seed(prefill_row, seed_values)

    if resolved_url is not None:
        seed_values["url"] = resolved_url
    seed_values["source"] = source
    seed_values["product_id"] = product_id

    result = start_or_prefill_resale_trade_journey_from_product(
        user_id=normalized_user_id,
        source=source,
        product_id=product_id,
        seed_values=seed_values,
        allow_empty_prefill=True,
    )
    return result


def start_resale_trade_journey_from_read_archive(*, user_id: str, read_archive_event_id: int) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_archive_id = _normalize_optional_int(read_archive_event_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")
    if normalized_archive_id is None or normalized_archive_id <= 0:
        raise ValueError("invalid_read_archive_event_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        archive_row = _fetch_read_archive_event_by_id(
            cursor,
            user_id=normalized_user_id,
            read_archive_event_id=normalized_archive_id,
        )
        alert_row: dict[str, Any] = {}
        archive_alert_id = _normalize_optional_int((archive_row or {}).get("alert_event_id"))
        if archive_alert_id is not None and archive_alert_id > 0:
            alert_row = _fetch_alert_event_by_id(
                cursor,
                user_id=normalized_user_id,
                alert_event_id=archive_alert_id,
            )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if not archive_row:
        return {"ok": False, "reason": "not_found"}

    alert_seed_values = _build_alert_mapping(alert_row)
    archive_seed_values = _build_read_archive_mapping(archive_row)
    seed_values = {**alert_seed_values, **archive_seed_values}

    resolved_url = _normalize_optional_text(
        _first_non_blank(
            seed_values.get("url"),
            archive_row.get("alert_url"),
            (alert_row or {}).get("url"),
        )
    )
    source = (
        _normalize_optional_text(seed_values.get("source"))
        or _infer_source_from_url(resolved_url)
    )
    product_id = (
        _normalize_optional_text(seed_values.get("product_id"))
        or _extract_product_id_from_url(resolved_url)
    )
    if product_id is None:
        return {"ok": False, "reason": "invalid_product_id"}

    prefill_result = build_trade_prefill_from_existing_db(product_id, normalized_user_id)
    if prefill_result.get("ok"):
        prefill_row = dict(prefill_result.get("row") or {})
        source = _normalize_optional_text(prefill_row.get("source")) or _normalize_optional_text(prefill_result.get("source")) or source
        seed_values = _fill_prefill_blanks_from_seed(prefill_row, seed_values)

    if resolved_url is not None:
        seed_values["url"] = resolved_url
    seed_values["source"] = source
    seed_values["product_id"] = product_id

    result = start_or_prefill_resale_trade_journey_from_product(
        user_id=normalized_user_id,
        source=source,
        product_id=product_id,
        seed_values=seed_values,
        allow_empty_prefill=True,
    )
    return result


def patch_resale_trade_journey_purchase(*, user_id: str, journey_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _, writable_columns = _get_resale_columns(cursor)

        row = _fetch_journey_by_id(cursor, journey_id, user_id=normalized_user_id, for_update=True)
        if not row:
            return {"ok": False, "reason": "not_found"}

        sparse_updates = _prepare_sparse_updates(
            updates or {},
            PURCHASE_PATCH_FIELDS,
            writable_columns,
        )
        _apply_updates(cursor, row_id=journey_id, updates=sparse_updates)

        row_after_update = _load_row_detail(cursor, journey_id)
        source = _normalize_optional_text(row_after_update.get("source"))
        product_id = _normalize_optional_text(row_after_update.get("product_id"))

        if source and product_id:
            row_after_update = _hydrate_row_by_product(
                cursor,
                row=row_after_update,
                user_id=normalized_user_id,
                source=source,
                product_id=product_id,
                user_values={},
                writable_columns=writable_columns,
            )

        calculated_updates = _build_purchase_calculated_updates(row_after_update, writable_columns)

        next_stage = _derive_stage_after_purchase(row_after_update, sparse_updates)
        if "current_stage" in writable_columns and next_stage:
            calculated_updates["current_stage"] = next_stage

        _apply_updates(cursor, row_id=journey_id, updates=_filter_writable_updates(calculated_updates, writable_columns))

        connection.commit()

        final_row = _load_row_detail(cursor, journey_id)
        return {
            "ok": True,
            "id": journey_id,
            "source": final_row.get("source"),
            "product_id": final_row.get("product_id"),
            "current_stage": final_row.get("current_stage"),
            "row": final_row,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _patch_resale_or_sold(*, user_id: str, journey_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        _, writable_columns = _get_resale_columns(cursor)

        row = _fetch_journey_by_id(cursor, journey_id, user_id=normalized_user_id, for_update=True)
        if not row:
            return {"ok": False, "reason": "not_found"}

        sparse_updates = _prepare_sparse_updates(
            updates or {},
            RESALE_RECORD_PATCH_FIELDS,
            writable_columns,
        )
        _apply_updates(cursor, row_id=journey_id, updates=sparse_updates)

        row_after_update = _load_row_detail(cursor, journey_id)
        source = _normalize_optional_text(row_after_update.get("source"))
        product_id = _normalize_optional_text(row_after_update.get("product_id"))

        if source and product_id:
            row_after_update = _hydrate_row_by_product(
                cursor,
                row=row_after_update,
                user_id=normalized_user_id,
                source=source,
                product_id=product_id,
                user_values={},
                writable_columns=writable_columns,
            )

        calculated_updates = _build_sold_calculated_updates(row_after_update, writable_columns)
        if "current_stage" in writable_columns:
            calculated_updates["current_stage"] = _derive_stage_after_resale_or_sold(
                row_after_update,
                sparse_updates,
            )

        _apply_updates(cursor, row_id=journey_id, updates=_filter_writable_updates(calculated_updates, writable_columns))

        connection.commit()

        final_row = _load_row_detail(cursor, journey_id)
        return {
            "ok": True,
            "id": journey_id,
            "source": final_row.get("source"),
            "product_id": final_row.get("product_id"),
            "current_stage": final_row.get("current_stage"),
            "row": final_row,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def patch_resale_trade_journey_resale(*, user_id: str, journey_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    return _patch_resale_or_sold(
        user_id=user_id,
        journey_id=journey_id,
        updates=updates,
    )


def patch_resale_trade_journey_sold(*, user_id: str, journey_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    return _patch_resale_or_sold(
        user_id=user_id,
        journey_id=journey_id,
        updates=updates,
    )


def list_completed_resale_trade_journeys(*, user_id: str, limit: int = 200) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    safe_limit = 200 if limit <= 0 else min(limit, 1000)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        rows = _safe_fetchall(
            cursor,
            """
            SELECT *
            FROM resale_trade_journeys
            WHERE user_id = %s
              AND current_stage = %s
            ORDER BY COALESCE(sold_at, updated_at) DESC, id DESC
            LIMIT %s
            """,
            (normalized_user_id, STAGE_SOLD, safe_limit),
        )
        return {"ok": True, "items": rows}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def list_purchased_resale_trade_journeys(*, user_id: str, limit: int = 200) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    safe_limit = 200 if limit <= 0 else min(limit, 1000)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        rows = _safe_fetchall(
            cursor,
            """
            SELECT *
            FROM resale_trade_journeys
            WHERE user_id = %s
              AND purchased_at IS NOT NULL
              AND (current_stage IS NULL OR current_stage <> %s)
            ORDER BY COALESCE(purchased_at, updated_at) DESC, id DESC
            LIMIT %s
            """,
            (normalized_user_id, STAGE_SOLD, safe_limit),
        )
        return {"ok": True, "items": rows}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def delete_completed_resale_trade_journeys(*, user_id: str, journey_ids: Optional[list[int]] = None, delete_all: bool = False) -> dict[str, Any]:
    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is None:
        raise ValueError("invalid_user_id")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if delete_all:
            cursor.execute(
                """
                DELETE FROM resale_trade_journeys
                WHERE user_id = %s
                  AND current_stage = %s
                """,
                (normalized_user_id, STAGE_SOLD),
            )
            deleted = cursor.rowcount or 0
        else:
            normalized_ids = sorted({int(value) for value in (journey_ids or []) if _normalize_optional_int(value) is not None})
            if not normalized_ids:
                return {"ok": True, "deleted_count": 0}

            placeholders = ", ".join(["%s"] * len(normalized_ids))
            params: list[Any] = [normalized_user_id, STAGE_SOLD, *normalized_ids]
            cursor.execute(
                f"""
                DELETE FROM resale_trade_journeys
                WHERE user_id = %s
                  AND current_stage = %s
                  AND id IN ({placeholders})
                """,
                tuple(params),
            )
            deleted = cursor.rowcount or 0

        connection.commit()
        return {"ok": True, "deleted_count": int(deleted)}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ------------------------------
# Backward-compatible wrappers
# ------------------------------

def _legacy_prepare_identity(payload: dict[str, Any]) -> tuple[str, str, str]:
    source = _normalize_source(payload.get("source"))

    product_id = _normalize_optional_text(payload.get("product_id"))
    if product_id is None:
        product_id = _extract_product_id_from_url(_normalize_optional_text(payload.get("url")))

    user_id = _normalize_optional_text(payload.get("user_id"))

    if user_id is None:
        raise ValueError("invalid_user_id")
    if product_id is None:
        raise ValueError("invalid_product_id")

    return user_id, source, product_id


def upsert_resale_trade_after_purchase(**payload):
    user_id, source, product_id = _legacy_prepare_identity(payload)
    created = create_or_hydrate_resale_trade_journey_from_product(
        user_id=user_id,
        source=source,
        product_id=product_id,
    )
    if not created.get("ok"):
        return created

    row_id = _normalize_optional_int(created.get("id"))
    if row_id is None:
        return {"ok": False, "reason": "journey_create_failed"}

    updates = {
        key: value
        for key, value in payload.items()
        if key in LEGACY_PURCHASE_UPSERT_FIELDS
    }

    return patch_resale_trade_journey_purchase(
        user_id=user_id,
        journey_id=row_id,
        updates=updates,
    )


def upsert_resale_trade_after_resale(**payload):
    user_id, source, product_id = _legacy_prepare_identity(payload)
    created = create_or_hydrate_resale_trade_journey_from_product(
        user_id=user_id,
        source=source,
        product_id=product_id,
    )
    if not created.get("ok"):
        return created

    row_id = _normalize_optional_int(created.get("id"))
    if row_id is None:
        return {"ok": False, "reason": "journey_create_failed"}

    resale_updates = {
        key: value
        for key, value in payload.items()
        if key in RESALE_PATCH_FIELDS
    }
    sold_updates = {
        key: value
        for key, value in payload.items()
        if key in SOLD_PATCH_FIELDS
    }

    if resale_updates:
        patch_resale_trade_journey_resale(
            user_id=user_id,
            journey_id=row_id,
            updates=resale_updates,
        )

    if sold_updates:
        return patch_resale_trade_journey_sold(
            user_id=user_id,
            journey_id=row_id,
            updates=sold_updates,
        )

    return patch_resale_trade_journey_resale(
        user_id=user_id,
        journey_id=row_id,
        updates={},
    )
