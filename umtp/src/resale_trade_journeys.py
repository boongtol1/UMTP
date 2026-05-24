import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

from src.db import get_connection


DEFAULT_SOURCE = "joongna"

STAGE_ORDER = {
    "DISCOVERED": 1,
    "AUTO_ANALYZED": 2,
    "CONTACTED": 3,
    "DECIDED": 4,
    "PURCHASED": 5,
    "INSPECTED": 6,
    "READY_FOR_RESALE": 7,
    "LISTED": 8,
    "LIVE_RESALE": 9,
    "FINALIZED": 10,
}

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
}
DECIMAL_FIELDS = {
    "discount_rate_percent",
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
TEXT_FIELDS = {
    "source",
    "product_id",
    "url",
    "title",
    "seller_nickname",
    "seller_shop_id",
    "seller_location",
    "body_text",
    "product_type",
    "chip",
    "color",
    "keyboard_layout",
    "seller_answer_text",
    "seller_tone",
    "decision_result",
    "decision_reason",
    "purchase_method",
    "purchase_location",
    "payment_method",
    "serial_number",
    "model_number",
    "applecare_status",
    "battery_condition",
    "display_condition",
    "keyboard_condition",
    "trackpad_condition",
    "speaker_condition",
    "camera_condition",
    "exterior_grade",
    "inspection_notes",
    "resale_title",
    "resale_body_text",
    "resale_platform",
    "resale_strategy_notes",
    "resale_url",
    "resale_product_id",
    "upload_time_slot",
    "buyer_nickname",
    "sale_method",
    "sale_location",
    "sale_platform",
    "refund_or_claim",
    "final_result_notes",
}

SEED_COLUMNS = [
    "user_id",
    "source",
    "product_id",
    "url",
    "title",
    "listing_created_at",
    "discovered_at",
    "listing_price_krw",
    "seller_nickname",
    "seller_shop_id",
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
    "current_stage",
]

PURCHASE_ALLOWED_FIELDS = {
    "contacted_at",
    "seller_response_at",
    "seller_answer_text",
    "negotiable",
    "seller_tone",
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
    "cleaned_at",
    "photo_taken_at",
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
}

SALE_ALLOWED_FIELDS = {
    "view_count",
    "favorite_count",
    "inquiry_count",
    "first_inquiry_at",
    "negotiation_count",
    "price_drop_count",
    "price_drop_history",
    "buyer_questions",
    "common_objections",
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
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
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


def _fetch_latest_analysis_job(cursor, *, source: str, product_id: Optional[str], url: Optional[str], user_id: Optional[str]):
    if product_id is None and url is None:
        return None

    if product_id is not None:
        return _safe_fetchone(
            cursor,
            """
            SELECT source, product_id, url, title, price_krw, sort_date, created_at
            FROM analysis_jobs
            WHERE source = %s
              AND product_id = %s
              AND (%s IS NULL OR user_id = %s)
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (source, product_id, user_id, user_id),
        )

    return _safe_fetchone(
        cursor,
        """
        SELECT source, product_id, url, title, price_krw, sort_date, created_at
        FROM analysis_jobs
        WHERE source = %s
          AND url = %s
          AND (%s IS NULL OR user_id = %s)
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (source, url, user_id, user_id),
    )


def _fetch_latest_search_result(cursor, *, product_id: Optional[str]):
    if product_id is None:
        return None

    return _safe_fetchone(
        cursor,
        """
        SELECT
            product_id,
            title,
            price,
            sort_date,
            url,
            seller_store_seq,
            seller_store_name,
            fetched_at
        FROM search_results
        WHERE product_id = %s
        ORDER BY fetched_at DESC, id DESC
        LIMIT 1
        """,
        (product_id,),
    )


def _fetch_latest_alert_event(cursor, *, source: str, product_id: Optional[str], url: Optional[str], user_id: Optional[str]):
    if product_id is None and url is None:
        return None

    if product_id is not None:
        return _safe_fetchone(
            cursor,
            """
            SELECT
                source,
                product_id,
                url,
                title,
                body_text,
                price_krw,
                fair_price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                risk_score,
                risk_keywords,
                seller_store_seq,
                seller_store_name,
                sort_date,
                created_at
            FROM alert_events
            WHERE source = %s
              AND product_id = %s
              AND (%s IS NULL OR user_id = %s)
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (source, product_id, user_id, user_id),
        )

    return _safe_fetchone(
        cursor,
        """
        SELECT
            source,
            product_id,
            url,
            title,
            body_text,
            price_krw,
            fair_price_krw,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            risk_score,
            risk_keywords,
            seller_store_seq,
            seller_store_name,
            sort_date,
            created_at
        FROM alert_events
        WHERE source = %s
          AND url = %s
          AND (%s IS NULL OR user_id = %s)
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (source, url, user_id, user_id),
    )


def _fetch_latest_listing_analysis(cursor, *, source: str, product_id: Optional[str], url: Optional[str]):
    if product_id is None and url is None:
        return None

    if product_id is not None:
        return _safe_fetchone(
            cursor,
            """
            SELECT
                lar.body_text,
                lar.product_type,
                lar.chip,
                lar.screen_inch,
                lar.ram_gb,
                lar.ssd_gb,
                lar.fair_price_krw,
                lar.listing_price_krw,
                lar.created_at
            FROM listing_analysis_results lar
            INNER JOIN analysis_jobs aj ON aj.id = lar.analysis_job_id
            WHERE aj.source = %s
              AND aj.product_id = %s
            ORDER BY lar.created_at DESC, lar.id DESC
            LIMIT 1
            """,
            (source, product_id),
        )

    return _safe_fetchone(
        cursor,
        """
        SELECT
            lar.body_text,
            lar.product_type,
            lar.chip,
            lar.screen_inch,
            lar.ram_gb,
            lar.ssd_gb,
            lar.fair_price_krw,
            lar.listing_price_krw,
            lar.created_at
        FROM listing_analysis_results lar
        INNER JOIN analysis_jobs aj ON aj.id = lar.analysis_job_id
        WHERE aj.source = %s
          AND aj.url = %s
        ORDER BY lar.created_at DESC, lar.id DESC
        LIMIT 1
        """,
        (source, url),
    )


def _fetch_latest_seen_product(cursor, *, product_id: Optional[str]):
    numeric_product_id = _normalize_optional_int(product_id)
    if numeric_product_id is None:
        return None

    row = _safe_fetchone(
        cursor,
        """
        SELECT
            seq,
            product_url,
            image_url,
            first_seen_at,
            last_sort_date,
            sort_date,
            last_title,
            title,
            last_price_krw,
            price
        FROM joongna_seen_products
        WHERE seq = %s
        LIMIT 1
        """,
        (numeric_product_id,),
    )
    if row is not None:
        return row

    return _safe_fetchone(
        cursor,
        """
        SELECT
            seq,
            product_url,
            image_url,
            first_seen_at,
            sort_date,
            title,
            price
        FROM joongna_seen_products
        WHERE seq = %s
        LIMIT 1
        """,
        (numeric_product_id,),
    )


def _build_seed_snapshot(cursor, *, source: str, product_id: Optional[str], url: Optional[str], user_id: Optional[str]):
    snapshot: dict[str, Any] = {
        "source": source,
        "product_id": product_id,
        "url": url,
    }

    analysis_job = _fetch_latest_analysis_job(
        cursor,
        source=source,
        product_id=product_id,
        url=url,
        user_id=user_id,
    ) or {}
    search_result = _fetch_latest_search_result(cursor, product_id=product_id) or {}
    alert_event = _fetch_latest_alert_event(
        cursor,
        source=source,
        product_id=product_id,
        url=url,
        user_id=user_id,
    ) or {}
    listing_result = _fetch_latest_listing_analysis(
        cursor,
        source=source,
        product_id=product_id,
        url=url,
    ) or {}
    seen_product = _fetch_latest_seen_product(cursor, product_id=product_id) or {}

    resolved_product_id = _normalize_optional_text(
        snapshot.get("product_id")
        or analysis_job.get("product_id")
        or search_result.get("product_id")
        or alert_event.get("product_id")
        or seen_product.get("seq")
        or _extract_product_id_from_url(snapshot.get("url"))
    )
    if resolved_product_id is not None:
        snapshot["product_id"] = resolved_product_id

    resolved_url = _normalize_optional_text(
        snapshot.get("url")
        or analysis_job.get("url")
        or search_result.get("url")
        or alert_event.get("url")
        or seen_product.get("product_url")
    )
    if resolved_url is None and resolved_product_id is not None and source == DEFAULT_SOURCE:
        resolved_url = f"https://web.joongna.com/product/{resolved_product_id}"
    snapshot["url"] = resolved_url

    snapshot["title"] = _normalize_optional_text(
        analysis_job.get("title")
        or search_result.get("title")
        or alert_event.get("title")
        or seen_product.get("last_title")
        or seen_product.get("title")
    )

    snapshot["listing_price_krw"] = _normalize_optional_int(
        search_result.get("price")
        or alert_event.get("price_krw")
        or analysis_job.get("price_krw")
        or listing_result.get("listing_price_krw")
        or seen_product.get("last_price_krw")
        or seen_product.get("price")
    )

    listing_created_at = (
        _normalize_optional_datetime(search_result.get("sort_date"))
        or _normalize_optional_datetime(alert_event.get("sort_date"))
        or _normalize_optional_datetime(analysis_job.get("sort_date"))
        or _normalize_optional_datetime(seen_product.get("last_sort_date"))
        or _normalize_optional_datetime(seen_product.get("sort_date"))
    )
    if listing_created_at is not None:
        snapshot["listing_created_at"] = listing_created_at

    discovered_at = (
        _normalize_optional_datetime(analysis_job.get("created_at"))
        or _normalize_optional_datetime(alert_event.get("created_at"))
        or _normalize_optional_datetime(search_result.get("fetched_at"))
        or _normalize_optional_datetime(seen_product.get("first_seen_at"))
        or datetime.utcnow().replace(microsecond=0)
    )
    snapshot["discovered_at"] = discovered_at

    seller_store_seq = _normalize_optional_text(
        search_result.get("seller_store_seq")
        or alert_event.get("seller_store_seq")
    )
    if seller_store_seq is not None:
        snapshot["seller_shop_id"] = seller_store_seq

    seller_name = _normalize_optional_text(
        search_result.get("seller_store_name")
        or alert_event.get("seller_store_name")
    )
    if seller_name is not None:
        snapshot["seller_nickname"] = seller_name

    image_url = _normalize_optional_text(seen_product.get("image_url"))
    if image_url is not None:
        snapshot["image_urls"] = _normalize_json_text([image_url])

    snapshot["body_text"] = _normalize_optional_text(
        alert_event.get("body_text")
        or listing_result.get("body_text")
    )

    snapshot["product_type"] = _normalize_optional_text(
        alert_event.get("product_type")
        or listing_result.get("product_type")
    )
    snapshot["chip"] = _normalize_optional_text(
        alert_event.get("chip")
        or listing_result.get("chip")
    )
    snapshot["screen_inch"] = _normalize_optional_int(
        alert_event.get("screen_inch")
        or listing_result.get("screen_inch")
    )
    snapshot["ram_gb"] = _normalize_optional_int(
        alert_event.get("ram_gb")
        or listing_result.get("ram_gb")
    )
    snapshot["ssd_gb"] = _normalize_optional_int(
        alert_event.get("ssd_gb")
        or listing_result.get("ssd_gb")
    )
    snapshot["fair_price_krw"] = _normalize_optional_int(
        alert_event.get("fair_price_krw")
        or listing_result.get("fair_price_krw")
    )

    risk_score = _normalize_optional_int(alert_event.get("risk_score"))
    if risk_score is not None:
        snapshot["risk_score"] = risk_score

    reason_tags = _normalize_json_text(alert_event.get("risk_keywords"))
    if reason_tags is not None:
        snapshot["reason_tags"] = reason_tags

    fair_price_krw = _normalize_optional_int(snapshot.get("fair_price_krw"))
    listing_price_krw = _normalize_optional_int(snapshot.get("listing_price_krw"))

    if fair_price_krw is not None and listing_price_krw is not None and fair_price_krw > 0:
        snapshot["discount_rate_percent"] = round(
            ((fair_price_krw - listing_price_krw) / fair_price_krw) * 100,
            2,
        )
        snapshot["expected_profit_krw"] = fair_price_krw - listing_price_krw

    snapshot["current_stage"] = (
        "AUTO_ANALYZED"
        if snapshot.get("product_type") and snapshot.get("fair_price_krw") is not None
        else "DISCOVERED"
    )

    return snapshot


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
    if column in TEXT_FIELDS:
        return _normalize_optional_text(value)
    return value


def _find_row(cursor, *, source: str, product_id: Optional[str], url: Optional[str]) -> Optional[dict[str, Any]]:
    if product_id is not None:
        row = _safe_fetchone(
            cursor,
            """
            SELECT id, current_stage, source, product_id, url
            FROM resale_trade_journeys
            WHERE source = %s
              AND product_id = %s
            LIMIT 1
            """,
            (source, product_id),
        )
        if row is not None:
            return row

    if url is None:
        return None

    return _safe_fetchone(
        cursor,
        """
        SELECT id, current_stage, source, product_id, url
        FROM resale_trade_journeys
        WHERE source = %s
          AND url = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (source, url),
    )


def _upsert_seed_row(cursor, seed: dict[str, Any]) -> dict[str, Any]:
    columns = [column for column in SEED_COLUMNS if seed.get(column) is not None]
    if not columns:
        columns = ["source"]
        seed = {"source": DEFAULT_SOURCE}

    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    update_sql = ", ".join([f"{column} = COALESCE(VALUES({column}), {column})" for column in columns])

    query = (
        f"INSERT INTO resale_trade_journeys ({column_sql}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_sql}"
    )
    values = tuple(seed.get(column) for column in columns)
    cursor.execute(query, values)

    row = _find_row(
        cursor,
        source=seed.get("source") or DEFAULT_SOURCE,
        product_id=_normalize_optional_text(seed.get("product_id")),
        url=_normalize_optional_text(seed.get("url")),
    )
    if row is None:
        raise RuntimeError("seed_row_not_found")

    return row


def _resolve_stage(existing_stage: Optional[str], candidate_stage: Optional[str]) -> Optional[str]:
    normalized_existing = _normalize_optional_text(existing_stage)
    normalized_candidate = _normalize_optional_text(candidate_stage)

    if normalized_candidate is None:
        return normalized_existing
    if normalized_existing is None:
        return normalized_candidate

    existing_rank = STAGE_ORDER.get(normalized_existing, 0)
    candidate_rank = STAGE_ORDER.get(normalized_candidate, 0)

    if candidate_rank >= existing_rank:
        return normalized_candidate
    return normalized_existing


def _derive_purchase_stage(update_values: dict[str, Any]) -> Optional[str]:
    if any(
        field in update_values
        for field in (
            "resale_listing_created_at",
            "resale_url",
            "resale_product_id",
            "initial_resale_price_krw",
        )
    ):
        return "LISTED"

    if any(
        field in update_values
        for field in (
            "cleaned_at",
            "photo_taken_at",
            "resale_title",
            "resale_listing_price_krw",
        )
    ):
        return "READY_FOR_RESALE"

    if any(
        field in update_values
        for field in (
            "serial_number",
            "model_number",
            "cpu_core_count",
            "gpu_core_count",
            "battery_health_percent",
            "display_condition",
            "repair_suspected",
        )
    ):
        return "INSPECTED"

    if any(
        field in update_values
        for field in (
            "purchased_at",
            "purchase_price_krw",
            "purchase_method",
            "purchase_location",
        )
    ):
        return "PURCHASED"

    if any(
        field in update_values
        for field in (
            "decision_at",
            "decision_result",
            "target_purchase_price_krw",
        )
    ):
        return "DECIDED"

    if any(
        field in update_values
        for field in (
            "contacted_at",
            "seller_response_at",
            "confirmed_price_krw",
        )
    ):
        return "CONTACTED"

    return None


def _derive_sale_stage(update_values: dict[str, Any]) -> Optional[str]:
    if any(
        field in update_values
        for field in (
            "sold_at",
            "sale_price_krw",
            "buyer_nickname",
            "sale_method",
            "final_shipping_cost_krw",
            "platform_fee_krw",
        )
    ):
        return "FINALIZED"

    if any(
        field in update_values
        for field in (
            "view_count",
            "favorite_count",
            "inquiry_count",
            "first_inquiry_at",
            "negotiation_count",
            "price_drop_count",
        )
    ):
        return "LIVE_RESALE"

    return None


def _build_update_values(payload: dict[str, Any], *, allowed_fields: set[str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for field in allowed_fields:
        if field not in payload:
            continue
        normalized = _normalize_for_column(field, payload.get(field))
        if normalized is None:
            continue
        updates[field] = normalized
    return updates


def _update_row_by_id(cursor, row_id: int, updates: dict[str, Any]):
    if not updates:
        return

    assignments = ", ".join([f"{column} = %s" for column in updates.keys()])
    query = f"UPDATE resale_trade_journeys SET {assignments} WHERE id = %s"
    values = tuple(updates.values()) + (row_id,)
    cursor.execute(query, values)


def _prepare_identity(payload: dict[str, Any]):
    source = _normalize_source(payload.get("source"))
    user_id = _normalize_optional_text(payload.get("user_id"))
    url = _normalize_optional_text(payload.get("url"))

    product_id = _normalize_optional_text(payload.get("product_id"))
    if product_id is None:
        product_id = _extract_product_id_from_url(url)

    if product_id is None and url is None:
        raise ValueError("invalid_identity")

    if url is None and product_id is not None and source == DEFAULT_SOURCE:
        url = f"https://web.joongna.com/product/{product_id}"

    return source, product_id, url, user_id


def _load_row_summary(cursor, row_id: int) -> dict[str, Any]:
    row = _safe_fetchone(
        cursor,
        """
        SELECT
            id,
            user_id,
            source,
            product_id,
            url,
            current_stage,
            purchased_at,
            sold_at,
            net_profit_krw,
            roi_percent,
            created_at,
            updated_at
        FROM resale_trade_journeys
        WHERE id = %s
        LIMIT 1
        """,
        (row_id,),
    )
    return row or {"id": row_id}


def _upsert_common(payload: dict[str, Any], *, allowed_fields: set[str], stage_deriver) -> dict[str, Any]:
    source, product_id, url, user_id = _prepare_identity(payload)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        seed = _build_seed_snapshot(
            cursor,
            source=source,
            product_id=product_id,
            url=url,
            user_id=user_id,
        )

        if user_id is not None:
            seed["user_id"] = user_id
        seed["source"] = source
        seed["product_id"] = product_id
        seed["url"] = url

        seeded_row = _upsert_seed_row(cursor, seed)
        row_id = int(seeded_row.get("id"))

        updates = _build_update_values(payload, allowed_fields=allowed_fields)
        updates["source"] = source
        if product_id is not None:
            updates["product_id"] = product_id
        if url is not None:
            updates["url"] = url
        if user_id is not None:
            updates["user_id"] = user_id

        candidate_stage = stage_deriver(updates)
        next_stage = _resolve_stage(seeded_row.get("current_stage"), candidate_stage)
        if next_stage is not None:
            updates["current_stage"] = next_stage

        _update_row_by_id(cursor, row_id=row_id, updates=updates)

        connection.commit()

        row_summary = _load_row_summary(cursor, row_id)
        return {
            "ok": True,
            "id": row_id,
            "source": source,
            "product_id": product_id,
            "url": url,
            "current_stage": row_summary.get("current_stage"),
            "row": row_summary,
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def upsert_resale_trade_after_purchase(**payload):
    return _upsert_common(
        payload,
        allowed_fields=PURCHASE_ALLOWED_FIELDS,
        stage_deriver=_derive_purchase_stage,
    )


def upsert_resale_trade_after_resale(**payload):
    return _upsert_common(
        payload,
        allowed_fields=SALE_ALLOWED_FIELDS,
        stage_deriver=_derive_sale_stage,
    )
