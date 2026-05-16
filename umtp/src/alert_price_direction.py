from decimal import Decimal, ROUND_HALF_UP


BELOW_OR_EQUAL = "BELOW_OR_EQUAL"
ABOVE_OR_EQUAL = "ABOVE_OR_EQUAL"
ALERT_PRICE_DIRECTIONS = frozenset({BELOW_OR_EQUAL, ABOVE_OR_EQUAL})
DEFAULT_ALERT_PRICE_DIRECTION = BELOW_OR_EQUAL

MIN_ALERT_DROP_RATE_PERCENT = -100.0
MAX_ALERT_DROP_RATE_PERCENT = 100.0


def normalize_alert_price_direction(value):
    if not isinstance(value, str):
        return DEFAULT_ALERT_PRICE_DIRECTION
    normalized = value.strip().upper()
    if normalized in ALERT_PRICE_DIRECTIONS:
        return normalized
    return DEFAULT_ALERT_PRICE_DIRECTION


def is_valid_alert_price_direction(value):
    if not isinstance(value, str):
        return False
    return value.strip().upper() in ALERT_PRICE_DIRECTIONS


def is_valid_alert_drop_rate_percent(value):
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return False
    return MIN_ALERT_DROP_RATE_PERCENT <= normalized <= MAX_ALERT_DROP_RATE_PERCENT


def compute_target_buy_price_krw(fair_price_krw, alert_drop_rate_percent):
    try:
        normalized_fair_price = int(fair_price_krw)
        normalized_drop_rate = Decimal(str(alert_drop_rate_percent))
    except (TypeError, ValueError):
        return None

    if normalized_fair_price <= 0:
        return None

    multiplier = Decimal("1") - (normalized_drop_rate / Decimal("100"))
    target = (Decimal(normalized_fair_price) * multiplier).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    return int(target)


def is_listing_alert_match(listing_price_krw, target_buy_price_krw, alert_price_direction):
    try:
        normalized_listing_price = int(listing_price_krw)
        normalized_target_price = int(target_buy_price_krw)
    except (TypeError, ValueError):
        return False

    normalized_direction = normalize_alert_price_direction(alert_price_direction)
    if normalized_direction == ABOVE_OR_EQUAL:
        return normalized_listing_price >= normalized_target_price

    return normalized_listing_price <= normalized_target_price
