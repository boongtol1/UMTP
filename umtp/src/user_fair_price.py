from decimal import Decimal

from src.alert_price_direction import (
    DEFAULT_ALERT_PRICE_DIRECTION,
    compute_target_buy_price_krw,
    normalize_alert_price_direction,
)


REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT = 20.0


def _normalize_user_id(user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id는 비어 있을 수 없습니다.")
    return user_id.strip()


def _normalize_watch_rule_id(watch_rule_id):
    if watch_rule_id is None:
        raise ValueError("watch_rule_id는 비어 있을 수 없습니다.")
    try:
        normalized = int(watch_rule_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("watch_rule_id는 양의 정수여야 합니다.") from exc
    if normalized <= 0:
        raise ValueError("watch_rule_id는 양의 정수여야 합니다.")
    return normalized


def _require_spec_fields(parsed_spec):
    missing_fields = [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]
    if missing_fields:
        raise ValueError(f"스펙 누락: {', '.join(missing_fields)}")


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _safe_int(value):
    if value is None:
        return None
    return int(value)


def _normalize_optional_row_user_id(value):
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_alert_price_row(row):
    if row is None:
        return None

    if isinstance(row, dict):
        fair_price_krw = _safe_int(row.get("fair_price_krw"))
        alert_drop_rate_percent = _safe_float(row.get("alert_drop_rate_percent"))
        target_buy_price_krw = _safe_int(row.get("target_buy_price_krw"))
        alert_price_direction = normalize_alert_price_direction(row.get("alert_price_direction"))
        min_price_krw = _safe_int(row.get("min_price_krw"))
        max_price_krw = _safe_int(row.get("max_price_krw"))
    else:
        row_values = tuple(row)
        fair_price_krw = _safe_int(row_values[0]) if len(row_values) > 0 else None
        alert_drop_rate_percent = _safe_float(row_values[1]) if len(row_values) > 1 else None
        target_buy_price_krw = _safe_int(row_values[2]) if len(row_values) > 2 else None
        raw_direction = row_values[3] if len(row_values) > 3 else DEFAULT_ALERT_PRICE_DIRECTION
        alert_price_direction = normalize_alert_price_direction(raw_direction)
        min_price_krw = _safe_int(row_values[4]) if len(row_values) > 4 else None
        max_price_krw = _safe_int(row_values[5]) if len(row_values) > 5 else None

    if target_buy_price_krw is None:
        target_buy_price_krw = compute_target_buy_price_krw(fair_price_krw, alert_drop_rate_percent)

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "target_buy_price_krw": target_buy_price_krw,
        "alert_price_direction": alert_price_direction,
        "min_price_krw": min_price_krw,
        "max_price_krw": max_price_krw,
    }


def _fetch_user_fair_price_row(cursor, user_id, parsed_spec):
    query_params = (
        user_id,
        parsed_spec["product_type"],
        parsed_spec["chip"],
        parsed_spec["screen_inch"],
        parsed_spec["ram_gb"],
        parsed_spec["ssd_gb"],
    )

    queries = (
        """
        SELECT
            fair_price_krw,
            alert_drop_rate_percent,
            target_buy_price_krw,
            alert_price_direction,
            min_price_krw,
            max_price_krw
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
          AND enabled = TRUE
        LIMIT 1
        """,
        """
        SELECT
            fair_price_krw,
            alert_drop_rate_percent,
            target_buy_price_krw,
            alert_price_direction,
            min_price_krw,
            max_price_krw
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent, target_buy_price_krw, alert_price_direction
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
          AND enabled = TRUE
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent, target_buy_price_krw, alert_price_direction
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
          AND enabled = TRUE
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
    )

    unknown_column_exc = None
    for query in queries:
        try:
            cursor.execute(query, query_params)
            return cursor.fetchone()
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            unknown_column_exc = exc
            continue

    if unknown_column_exc is not None:
        raise unknown_column_exc
    return None


def _fetch_user_fair_price_rule_row(cursor, watch_rule_id):
    queries = (
        """
        SELECT
            user_id,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            alert_drop_rate_percent,
            target_buy_price_krw,
            alert_price_direction,
            min_price_krw,
            max_price_krw,
            enabled
        FROM user_fair_prices
        WHERE id = %s
        LIMIT 1
        """,
        """
        SELECT
            user_id,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            alert_drop_rate_percent,
            target_buy_price_krw,
            alert_price_direction,
            NULL AS min_price_krw,
            NULL AS max_price_krw,
            enabled
        FROM user_fair_prices
        WHERE id = %s
        LIMIT 1
        """,
        """
        SELECT
            user_id,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            alert_drop_rate_percent,
            target_buy_price_krw,
            alert_price_direction,
            NULL AS min_price_krw,
            NULL AS max_price_krw,
            1 AS enabled
        FROM user_fair_prices
        WHERE id = %s
        LIMIT 1
        """,
        """
        SELECT
            user_id,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            alert_drop_rate_percent,
            NULL AS target_buy_price_krw,
            %s AS alert_price_direction,
            NULL AS min_price_krw,
            NULL AS max_price_krw,
            1 AS enabled
        FROM user_fair_prices
        WHERE id = %s
        LIMIT 1
        """,
    )

    unknown_column_exc = None
    for query in queries:
        try:
            if "%s AS alert_price_direction" in query:
                cursor.execute(query, (DEFAULT_ALERT_PRICE_DIRECTION, watch_rule_id))
            else:
                cursor.execute(query, (watch_rule_id,))
            return cursor.fetchone()
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            unknown_column_exc = exc
            continue

    if unknown_column_exc is not None:
        raise unknown_column_exc
    return None


def _normalize_user_fair_price_rule_row(row):
    if row is None:
        return None

    if isinstance(row, dict):
        return {
            "user_id": _normalize_optional_row_user_id(row.get("user_id")),
            "product_type": row.get("product_type"),
            "chip": row.get("chip"),
            "screen_inch": _safe_int(row.get("screen_inch")),
            "ram_gb": _safe_int(row.get("ram_gb")),
            "ssd_gb": _safe_int(row.get("ssd_gb")),
            "fair_price_krw": _safe_int(row.get("fair_price_krw")),
            "alert_drop_rate_percent": _safe_float(row.get("alert_drop_rate_percent")),
            "target_buy_price_krw": _safe_int(row.get("target_buy_price_krw")),
            "alert_price_direction": normalize_alert_price_direction(row.get("alert_price_direction")),
            "min_price_krw": _safe_int(row.get("min_price_krw")),
            "max_price_krw": _safe_int(row.get("max_price_krw")),
            "enabled": row.get("enabled"),
        }

    row_values = tuple(row)
    return {
        "user_id": _normalize_optional_row_user_id(row_values[0]) if len(row_values) > 0 else None,
        "product_type": row_values[1] if len(row_values) > 1 else None,
        "chip": row_values[2] if len(row_values) > 2 else None,
        "screen_inch": _safe_int(row_values[3]) if len(row_values) > 3 else None,
        "ram_gb": _safe_int(row_values[4]) if len(row_values) > 4 else None,
        "ssd_gb": _safe_int(row_values[5]) if len(row_values) > 5 else None,
        "fair_price_krw": _safe_int(row_values[6]) if len(row_values) > 6 else None,
        "alert_drop_rate_percent": _safe_float(row_values[7]) if len(row_values) > 7 else None,
        "target_buy_price_krw": _safe_int(row_values[8]) if len(row_values) > 8 else None,
        "alert_price_direction": normalize_alert_price_direction(row_values[9] if len(row_values) > 9 else None),
        "min_price_krw": _safe_int(row_values[10]) if len(row_values) > 10 else None,
        "max_price_krw": _safe_int(row_values[11]) if len(row_values) > 11 else None,
        "enabled": row_values[12] if len(row_values) > 12 else True,
    }


def _is_watch_rule_spec_match(rule_row, parsed_spec):
    return (
        rule_row.get("product_type") == parsed_spec.get("product_type")
        and rule_row.get("chip") == parsed_spec.get("chip")
        and rule_row.get("screen_inch") == parsed_spec.get("screen_inch")
        and rule_row.get("ram_gb") == parsed_spec.get("ram_gb")
        and rule_row.get("ssd_gb") == parsed_spec.get("ssd_gb")
    )


def _has_enabled_user_target(cursor, user_id, parsed_spec):
    try:
        cursor.execute(
            """
            SELECT 1
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
              AND enabled = TRUE
            LIMIT 1
            """,
            (
                user_id,
                parsed_spec["product_type"],
                parsed_spec["chip"],
                parsed_spec["screen_inch"],
                parsed_spec["ram_gb"],
                parsed_spec["ssd_gb"],
            ),
        )
    except Exception as exc:
        if "unknown column" not in str(exc).lower() or "enabled" not in str(exc).lower():
            raise
        cursor.execute(
            """
            SELECT 1
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
            LIMIT 1
            """,
            (
                user_id,
                parsed_spec["product_type"],
                parsed_spec["chip"],
                parsed_spec["screen_inch"],
                parsed_spec["ram_gb"],
                parsed_spec["ssd_gb"],
            ),
        )

    return cursor.fetchone() is not None


def _fetch_system_fair_price_row(cursor, parsed_spec):
    cursor.execute(
        """
        SELECT fair_price_krw
        FROM mac_fair_prices
        WHERE product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
        (
            parsed_spec["product_type"],
            parsed_spec["chip"],
            parsed_spec["screen_inch"],
            parsed_spec["ram_gb"],
            parsed_spec["ssd_gb"],
        ),
    )
    return cursor.fetchone()


def fetch_user_fair_price(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)

    row = _fetch_user_fair_price_row(cursor, normalized_user_id, parsed_spec)
    if not row:
        return None

    normalized_row = _normalize_alert_price_row(row)
    fair_price_krw = normalized_row.get("fair_price_krw")
    alert_drop_rate_percent = normalized_row.get("alert_drop_rate_percent")
    target_buy_price_krw = normalized_row.get("target_buy_price_krw")
    alert_price_direction = normalized_row.get("alert_price_direction")

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "target_buy_price_krw": target_buy_price_krw,
        "alert_price_direction": alert_price_direction,
        "min_price_krw": normalized_row.get("min_price_krw"),
        "max_price_krw": normalized_row.get("max_price_krw"),
        "source": "user_fair_prices",
    }


def is_user_fair_price_target_enabled(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)
    return _has_enabled_user_target(cursor, normalized_user_id, parsed_spec)


def resolve_fair_price_for_user(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)

    if not _has_enabled_user_target(cursor, normalized_user_id, parsed_spec):
        return None

    user_row = _fetch_user_fair_price_row(cursor, normalized_user_id, parsed_spec)
    if user_row:
        normalized_row = _normalize_alert_price_row(user_row)
        return {
            "fair_price_krw": normalized_row.get("fair_price_krw"),
            "alert_drop_rate_percent": normalized_row.get("alert_drop_rate_percent"),
            "target_buy_price_krw": normalized_row.get("target_buy_price_krw"),
            "alert_price_direction": normalized_row.get("alert_price_direction"),
            "min_price_krw": normalized_row.get("min_price_krw"),
            "max_price_krw": normalized_row.get("max_price_krw"),
            "source": "user_fair_prices",
        }

    system_row = _fetch_system_fair_price_row(cursor, parsed_spec)
    if system_row:
        fair_price_krw = int(system_row[0])
        alert_drop_rate_percent = DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT
        return {
            "fair_price_krw": fair_price_krw,
            "alert_drop_rate_percent": alert_drop_rate_percent,
            "target_buy_price_krw": compute_target_buy_price_krw(
                fair_price_krw,
                alert_drop_rate_percent,
            ),
            "alert_price_direction": DEFAULT_ALERT_PRICE_DIRECTION,
            "min_price_krw": None,
            "max_price_krw": None,
            "source": "mac_fair_prices",
        }

    return None


def resolve_fair_price_for_watch_rule(cursor, user_id, watch_rule_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    normalized_watch_rule_id = _normalize_watch_rule_id(watch_rule_id)
    _require_spec_fields(parsed_spec)

    rule_row = _fetch_user_fair_price_rule_row(cursor, normalized_watch_rule_id)
    if not rule_row:
        return None

    normalized_rule = _normalize_user_fair_price_rule_row(rule_row)
    if normalized_rule is None:
        return None

    if normalized_rule.get("user_id") != normalized_user_id:
        return None

    enabled = normalized_rule.get("enabled")
    if enabled is not None and not bool(enabled):
        return None

    if not _is_watch_rule_spec_match(normalized_rule, parsed_spec):
        return None

    normalized_price = _normalize_alert_price_row(
        {
            "fair_price_krw": normalized_rule.get("fair_price_krw"),
            "alert_drop_rate_percent": normalized_rule.get("alert_drop_rate_percent"),
            "target_buy_price_krw": normalized_rule.get("target_buy_price_krw"),
            "alert_price_direction": normalized_rule.get("alert_price_direction"),
            "min_price_krw": normalized_rule.get("min_price_krw"),
            "max_price_krw": normalized_rule.get("max_price_krw"),
        }
    )
    if normalized_price is None:
        return None

    fair_price_krw = normalized_price.get("fair_price_krw")
    alert_drop_rate_percent = normalized_price.get("alert_drop_rate_percent")
    if fair_price_krw is None or fair_price_krw <= 0 or alert_drop_rate_percent is None:
        return None

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "target_buy_price_krw": normalized_price.get("target_buy_price_krw"),
        "alert_price_direction": normalized_price.get("alert_price_direction"),
        "min_price_krw": normalized_price.get("min_price_krw"),
        "max_price_krw": normalized_price.get("max_price_krw"),
        "source": "watch_rule",
    }
