def _normalize_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_chip(value):
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.upper()


def _normalize_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _matches_field(rule_value, parsed_value):
    if rule_value is None:
        return True
    return rule_value == parsed_value


def matches_watch_rule(parsed_spec, watch_rule):
    if not isinstance(watch_rule, dict):
        return False

    parsed_spec = parsed_spec if isinstance(parsed_spec, dict) else {}

    rule_product_type = _normalize_text(watch_rule.get("product_type"))
    rule_chip = _normalize_chip(watch_rule.get("chip"))
    rule_screen_inch = _normalize_int(watch_rule.get("screen_inch"))
    rule_ram_gb = _normalize_int(watch_rule.get("ram_gb"))
    rule_ssd_gb = _normalize_int(watch_rule.get("ssd_gb"))

    parsed_product_type = _normalize_text(parsed_spec.get("product_type"))
    parsed_chip = _normalize_chip(parsed_spec.get("chip"))
    parsed_screen_inch = _normalize_int(parsed_spec.get("screen_inch"))
    parsed_ram_gb = _normalize_int(parsed_spec.get("ram_gb"))
    parsed_ssd_gb = _normalize_int(parsed_spec.get("ssd_gb"))

    if not _matches_field(rule_product_type, parsed_product_type):
        return False
    if not _matches_field(rule_chip, parsed_chip):
        return False
    if not _matches_field(rule_screen_inch, parsed_screen_inch):
        return False
    if not _matches_field(rule_ram_gb, parsed_ram_gb):
        return False
    if not _matches_field(rule_ssd_gb, parsed_ssd_gb):
        return False

    return True
