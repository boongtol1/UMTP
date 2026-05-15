from decimal import Decimal


REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT = 20.0


def _normalize_user_id(user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id는 비어 있을 수 없습니다.")
    return user_id.strip()


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


def _fetch_user_fair_price_row(cursor, user_id, parsed_spec):
    try:
        cursor.execute(
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
            (
                user_id,
                parsed_spec["product_type"],
                parsed_spec["chip"],
                parsed_spec["screen_inch"],
                parsed_spec["ram_gb"],
                parsed_spec["ssd_gb"],
            ),
        )
    return cursor.fetchone()


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

    fair_price_krw = int(row[0])
    alert_drop_rate_percent = _safe_float(row[1])

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "source": "user_fair_prices",
    }


def resolve_fair_price_for_user(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)

    user_row = _fetch_user_fair_price_row(cursor, normalized_user_id, parsed_spec)
    if user_row:
        return {
            "fair_price_krw": int(user_row[0]),
            "alert_drop_rate_percent": _safe_float(user_row[1]),
            "source": "user_fair_prices",
        }

    system_row = _fetch_system_fair_price_row(cursor, parsed_spec)
    if system_row:
        return {
            "fair_price_krw": int(system_row[0]),
            "alert_drop_rate_percent": DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT,
            "source": "mac_fair_prices",
        }

    return None
