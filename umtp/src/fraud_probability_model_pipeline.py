from typing import Any, Optional


TEXT_FEATURES = {"title_text", "body_text"}
CATEGORICAL_FEATURES = {"risk_level", "trade_type"}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_optional_text(value: Any) -> Optional[str]:
    cleaned = normalize_text(value)
    return cleaned or None


def coerce_structured_value(key: str, value: Any) -> Any:
    if key in CATEGORICAL_FEATURES:
        return normalize_optional_text(value) or "unknown"

    if value is None or str(value).strip() == "":
        return -1.0

    try:
        return float(value)
    except ValueError:
        return -1.0


def extract_structured_feature_dicts(rows):
    return [
        {
            key: coerce_structured_value(key, value)
            for key, value in row.items()
            if key not in TEXT_FEATURES
        }
        for row in rows
    ]


def extract_title_texts(rows):
    return [normalize_text(row.get("title_text")) for row in rows]


def extract_body_texts(rows):
    return [normalize_text(row.get("body_text")) for row in rows]
