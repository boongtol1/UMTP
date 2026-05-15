REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")


def fetch_user_fair_price(cursor, user_id, parsed_spec):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id는 비어 있을 수 없습니다.")

    missing_fields = [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]
    if missing_fields:
        raise ValueError(f"스펙 누락: {', '.join(missing_fields)}")

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
                user_id.strip(),
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
                user_id.strip(),
                parsed_spec["product_type"],
                parsed_spec["chip"],
                parsed_spec["screen_inch"],
                parsed_spec["ram_gb"],
                parsed_spec["ssd_gb"],
            ),
        )
    row = cursor.fetchone()
    if not row:
        return None

    fair_price_krw = int(row[0])
    alert_drop_rate_percent = float(row[1])

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
    }
