import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from src.db import get_connection


DEFAULT_SOURCE = "joongna"

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
    "contacted_at",
    "seller_response_at",
    "seller_answer_text",
    "negotiable",
    "seller_tone",
    "seller_location",
    "suspicious_points",
    "confirmed_price_krw",
    "decision_at",
    "decision_result",
    "decision_reason",
    "target_purchase_price_krw",
    "expected_sale_price_krw",
    "expected_net_profit_krw",
    "expected_sale_duration_days",
    "purchased_at",
    "purchase_price_krw",
    "purchase_method",
    "purchase_location",
    "transport_cost_krw",
    "shipping_cost_krw",
    "cleaned_at",
    "photo_taken_at",
    "payment_method",
    "serial_number",
    "model_number",
    "applecare_status",
    "cpu_core_count",
    "gpu_core_count",
    "activation_lock_off",
    "mdm_lock_none",
    "battery_health_percent",
    "battery_cycle_count",
    "battery_condition",
    "truetone_ok",
    "display_condition",
    "keyboard_condition",
    "trackpad_condition",
    "speaker_condition",
    "camera_condition",
    "wifi_bluetooth_ok",
    "exterior_grade",
    "included_items",
    "repair_suspected",
    "inspection_notes",
    "current_stage",
    "final_result_notes",
}

RESALE_PATCH_FIELDS = {
    "resale_title",
    "resale_body_text",
    "resale_photo_count",
    "resale_listing_price_krw",
    "minimum_accept_price_krw",
    "resale_platform",
    "resale_strategy_notes",
    "resale_listing_created_at",
    "resale_url",
    "resale_product_id",
    "initial_resale_price_krw",
    "upload_time_slot",
    "view_count",
    "favorite_count",
    "inquiry_count",
    "first_inquiry_at",
    "negotiation_count",
    "price_drop_count",
    "price_drop_history",
    "buyer_questions",
    "common_objections",
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


def _fetch_latest_alert_event(cursor, *, user_id: str, source: str, product_id: str) -> dict[str, Any]:
    base = """
        SELECT *
        FROM alert_events
        WHERE source = %s
          AND product_id = %s
          AND (%s IS NULL OR user_id = %s)
    """
    query = _safe_order_query(
        base,
        [
            "COALESCE(sort_date, analyzed_at, created_at) DESC, id DESC",
            "created_at DESC, id DESC",
            "id DESC",
        ],
    )
    return _safe_fetchone(cursor, query, (source, product_id, user_id, user_id)) or {}


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


def _fetch_latest_listing_analysis(cursor, *, source: str, product_id: str) -> dict[str, Any]:
    joined = _safe_fetchone(
        cursor,
        """
        SELECT lar.*, aj.source AS analysis_source, aj.product_id AS analysis_product_id, aj.created_at AS analysis_job_created_at
        FROM listing_analysis_results lar
        INNER JOIN analysis_jobs aj ON aj.id = lar.analysis_job_id
        WHERE aj.source = %s
          AND aj.product_id = %s
        ORDER BY COALESCE(lar.created_at, aj.created_at) DESC, lar.id DESC
        LIMIT 1
        """,
        (source, product_id),
    )
    if joined:
        return joined

    direct = _safe_fetchone(
        cursor,
        """
        SELECT *
        FROM listing_analysis_results
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (),
    )
    return direct or {}


def _first_non_blank(*values: Any) -> Any:
    for value in values:
        if not _is_blank(value):
            return value
    return None


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

    return {
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
        "seller_nickname": _normalize_optional_text(row.get("seller_store_name")),
        "seller_shop_id": _normalize_optional_text(row.get("seller_store_seq")),
        "watch_rule_id": _normalize_optional_int(row.get("watch_rule_id")),
        "analysis_job_id": _normalize_optional_int(row.get("analysis_job_id")),
    }


def _build_analysis_job_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    return {
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
    }


def _build_seen_product_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    image_urls = None
    image_url = _normalize_optional_text(row.get("image_url"))
    if image_url:
        image_urls = _normalize_json_text([image_url])

    return {
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
    }


def _build_search_result_mapping(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    if not row:
        return {}

    return {
        "source": source,
        "product_id": _normalize_optional_text(row.get("product_id")),
        "url": _normalize_optional_text(row.get("url")),
        "title": _normalize_optional_text(row.get("title")),
        "listing_price_krw": _normalize_optional_int(_first_non_blank(row.get("price_krw"), row.get("price"))),
        "seller_nickname": _normalize_optional_text(_first_non_blank(row.get("seller_nickname"), row.get("seller_store_name"))),
        "seller_shop_id": _normalize_optional_text(_first_non_blank(row.get("seller_shop_id"), row.get("seller_store_seq"))),
        "seller_location": _normalize_optional_text(row.get("seller_location")),
        "image_urls": _normalize_json_text(_first_non_blank(row.get("image_urls"), row.get("image_url"))),
        "body_text": _normalize_optional_text(row.get("body_text")),
        "discovered_at": _normalize_optional_datetime(_first_non_blank(row.get("created_at"), row.get("fetched_at"))),
    }


def _build_listing_analysis_mapping(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}

    return {
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
    alert_event = _build_alert_mapping(_fetch_latest_alert_event(cursor, user_id=user_id, source=source, product_id=product_id))
    analysis_job = _build_analysis_job_mapping(_fetch_latest_analysis_job(cursor, user_id=user_id, source=source, product_id=product_id))
    seen_product = _build_seen_product_mapping(_fetch_latest_seen_product(cursor, product_id=product_id))
    search_result = _build_search_result_mapping(_fetch_latest_search_result(cursor, product_id=product_id), source=source)
    listing_analysis = _build_listing_analysis_mapping(_fetch_latest_listing_analysis(cursor, source=source, product_id=product_id))

    merged_updates = _merge_by_priority(
        user_values=user_values or {},
        existing_row=row,
        source_candidates=[
            alert_event,
            analysis_job,
            seen_product,
            search_result,
            listing_analysis,
        ],
        writable_columns=writable_columns,
    )

    row_id = _normalize_optional_int(row.get("id"))
    if row_id is None:
        return row

    updates_to_apply = _filter_writable_updates(merged_updates, writable_columns)
    _apply_updates(cursor, row_id=row_id, updates=updates_to_apply)
    return _load_row_detail(cursor, row_id)


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

        user_values = {
            "user_id": normalized_user_id,
            "source": normalized_source,
            "product_id": normalized_product_id,
        }

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

        return {
            "ok": True,
            "id": row_id,
            "source": normalized_source,
            "product_id": normalized_product_id,
            "current_stage": hydrated_row.get("current_stage"),
            "row": hydrated_row,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


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
