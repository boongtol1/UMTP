import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


MODEL_VERSION_UNKNOWN = "unknown"
LOW_LABEL = "LOW"
MEDIUM_LABEL = "MEDIUM"
HIGH_LABEL = "HIGH"

_MODEL_ARTIFACT = None
_MODEL_LOAD_FAILED = False


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_model_path() -> str:
    return os.path.join(_project_root(), "models", "fraud_probability", "current.joblib")


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    text = _normalize_optional_text(value)
    if text is None:
        return 0
    lowered = text.lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return 1
    if lowered in {"0", "false", "no", "n", "off"}:
        return 0
    parsed = _safe_int(value)
    return 1 if parsed else 0


def _risk_keyword_count(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return 0
        if isinstance(decoded, list):
            return len(decoded)
    return 0


def probability_to_label(probability: Optional[float]) -> Optional[str]:
    if probability is None:
        return None
    if probability >= 0.65:
        return HIGH_LABEL
    if probability >= 0.25:
        return MEDIUM_LABEL
    return LOW_LABEL


def _load_model_artifact() -> Optional[Dict[str, Any]]:
    global _MODEL_ARTIFACT, _MODEL_LOAD_FAILED
    if _MODEL_ARTIFACT is not None:
        return _MODEL_ARTIFACT
    if _MODEL_LOAD_FAILED:
        return None

    model_path = os.getenv("FRAUD_PROBABILITY_MODEL_PATH") or _default_model_path()
    if not os.path.exists(model_path):
        _MODEL_LOAD_FAILED = True
        return None

    try:
        import joblib

        _MODEL_ARTIFACT = joblib.load(model_path)
        return _MODEL_ARTIFACT
    except Exception:
        _MODEL_LOAD_FAILED = True
        return None


def _fetch_first_search_result(cursor, product_id: str) -> Dict[str, Any]:
    cursor.execute(
        """
        SELECT
          id,
          product_id,
          title,
          price,
          sort_date,
          seller_store_seq,
          seller_store_name,
          seller_profile_image_url,
          seller_review_count,
          fetched_at
        FROM search_results
        WHERE CAST(product_id AS CHAR) = %s
        ORDER BY fetched_at ASC, id ASC
        LIMIT 1
        """,
        (product_id,),
    )
    return cursor.fetchone() or {}


def _fetch_latest_activity(cursor, *, store_id: str, feature_time: Any) -> Dict[str, Any]:
    if feature_time is None:
        return {}
    cursor.execute(
        """
        SELECT
          posts_last_1h,
          posts_last_6h,
          posts_last_24h,
          posts_last_7d,
          visible_product_count,
          has_default_profile_image,
          review_count,
          safe_trade_count,
          trust_score,
          reliability_score,
          activity_score,
          notified_score,
          visit_today_count,
          visit_total_count
        FROM fraud_store_activity_snapshots
        WHERE store_id = %s
          AND checked_at <= DATE_ADD(%s, INTERVAL 30 MINUTE)
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (store_id, feature_time),
    )
    return cursor.fetchone() or {}


def _fetch_latest_profile(cursor, *, store_id: str, feature_time: Any) -> Dict[str, Any]:
    if feature_time is None:
        return {}
    cursor.execute(
        """
        SELECT
          review_count AS profile_review_count,
          safe_trade_count AS profile_safe_trade_count,
          trust_score AS profile_trust_score,
          reliability_score AS profile_reliability_score,
          activity_score AS profile_activity_score,
          notified_score AS profile_notified_score,
          visit_today_count AS profile_visit_today_count,
          visit_total_count AS profile_visit_total_count,
          is_official_account AS profile_is_official_account
        FROM fraud_store_profile_field_snapshots
        WHERE store_id = %s
          AND checked_at <= DATE_ADD(%s, INTERVAL 30 MINUTE)
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (store_id, feature_time),
    )
    return cursor.fetchone() or {}


def _feature_value(key: str, value: Any) -> Any:
    if key in {"risk_level", "trade_type"}:
        return _normalize_optional_text(value) or "unknown"
    parsed = _safe_float(value)
    if parsed is None:
        return -1.0
    return parsed


def _build_features(
    *,
    search_result: Dict[str, Any],
    activity: Dict[str, Any],
    profile: Dict[str, Any],
    alert_context: Dict[str, Any],
) -> Dict[str, Any]:
    title = _normalize_optional_text(search_result.get("title")) or ""
    sort_date = search_result.get("sort_date")
    sort_hour = getattr(sort_date, "hour", None)
    sort_dayofweek = None
    if hasattr(sort_date, "isoweekday"):
        sort_dayofweek = sort_date.isoweekday() % 7 + 1

    raw_features = {
        "price_krw": search_result.get("price") or alert_context.get("price_krw"),
        "title_len": len(title),
        "sort_hour": sort_hour,
        "sort_dayofweek": sort_dayofweek,
        "has_profile_image": 1 if _normalize_optional_text(search_result.get("seller_profile_image_url")) else 0,
        "store_name_len": len(_normalize_optional_text(search_result.get("seller_store_name")) or ""),
        "seller_review_count": search_result.get("seller_review_count"),
        "has_activity_snapshot": 1 if activity else 0,
        "posts_last_1h": activity.get("posts_last_1h"),
        "posts_last_6h": activity.get("posts_last_6h"),
        "posts_last_24h": activity.get("posts_last_24h"),
        "posts_last_7d": activity.get("posts_last_7d"),
        "visible_product_count": activity.get("visible_product_count"),
        "has_default_profile_image": activity.get("has_default_profile_image"),
        "activity_review_count": activity.get("review_count"),
        "safe_trade_count": activity.get("safe_trade_count"),
        "trust_score": activity.get("trust_score"),
        "reliability_score": activity.get("reliability_score"),
        "activity_score": activity.get("activity_score"),
        "notified_score": activity.get("notified_score"),
        "visit_today_count": activity.get("visit_today_count"),
        "visit_total_count": activity.get("visit_total_count"),
        "has_profile_snapshot": 1 if profile else 0,
        "profile_review_count": profile.get("profile_review_count"),
        "profile_safe_trade_count": profile.get("profile_safe_trade_count"),
        "profile_trust_score": profile.get("profile_trust_score"),
        "profile_reliability_score": profile.get("profile_reliability_score"),
        "profile_activity_score": profile.get("profile_activity_score"),
        "profile_notified_score": profile.get("profile_notified_score"),
        "profile_visit_today_count": profile.get("profile_visit_today_count"),
        "profile_visit_total_count": profile.get("profile_visit_total_count"),
        "profile_is_official_account": profile.get("profile_is_official_account"),
        "drop_rate_percent": alert_context.get("drop_rate_percent"),
        "risk_score": alert_context.get("risk_score"),
        "risk_level": alert_context.get("risk_level"),
        "trade_type": alert_context.get("trade_type"),
        "is_exchange_post": _safe_bool_int(alert_context.get("is_exchange_post")),
        "risk_keyword_count": _risk_keyword_count(alert_context.get("risk_keywords_json")),
    }
    return {key: _feature_value(key, value) for key, value in raw_features.items()}


def score_alert_fraud_probability(
    cursor,
    *,
    product_id: Any,
    store_id: Any = None,
    alert_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    artifact = _load_model_artifact()
    if not artifact or "model" not in artifact:
        return {}

    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_product_id is None:
        return {}

    alert_context = alert_context or {}
    try:
        search_result = _fetch_first_search_result(cursor, normalized_product_id)
        normalized_store_id = _normalize_optional_text(store_id)
        if normalized_store_id is None:
            normalized_store_id = _normalize_optional_text(search_result.get("seller_store_seq"))

        activity = {}
        profile = {}
        feature_time = search_result.get("fetched_at")
        if normalized_store_id is not None:
            activity = _fetch_latest_activity(
                cursor,
                store_id=normalized_store_id,
                feature_time=feature_time,
            )
            profile = _fetch_latest_profile(
                cursor,
                store_id=normalized_store_id,
                feature_time=feature_time,
            )

        features = _build_features(
            search_result=search_result,
            activity=activity,
            profile=profile,
            alert_context=alert_context,
        )
        probability = float(artifact["model"].predict_proba([features])[0][1])
    except Exception:
        return {}

    return {
        "fraud_probability": probability,
        "fraud_probability_label": probability_to_label(probability),
        "fraud_model_version": _normalize_optional_text(artifact.get("model_version")) or MODEL_VERSION_UNKNOWN,
        "fraud_scored_at": _utc_now_naive(),
    }

