import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


MODEL_VERSION_UNKNOWN = "unknown"
V1_MODEL_VERSION_KEY = "v1"
V2_MODEL_VERSION_KEY = "v2"
LOW_LABEL = "LOW"
MEDIUM_LABEL = "MEDIUM"
HIGH_LABEL = "HIGH"
TEXT_FEATURES = {"title_text", "body_text"}
SELLER_HISTORY_FEATURES = {
    "has_seller_history": 0,
    "seller_search_result_count_before": 0,
    "seller_search_result_count_7d": 0,
    "seller_seen_product_count_before": 0,
    "seller_seen_product_count_24h": 0,
    "seller_seen_product_count_7d": 0,
    "seller_history_age_hours": None,
    "seller_avg_price_7d": None,
    "seller_min_price_7d": None,
    "seller_max_price_7d": None,
    "seller_product_snapshot_count_before": 0,
    "seller_product_snapshot_count_7d": 0,
    "seller_price_change_count_7d": 0,
    "seller_content_change_count_7d": 0,
    "seller_alert_count_before": 0,
    "seller_alert_count_30d": 0,
    "seller_alert_product_count_30d": 0,
    "seller_store_name_change_count_before": 0,
    "seller_store_name_change_count_30d": 0,
}

_MODEL_ARTIFACT = None
_MODEL_LOAD_FAILED = False
_MODEL_ARTIFACT_BY_PATH = {}
_MODEL_LOAD_FAILED_PATHS = set()


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_model_path() -> str:
    return os.path.join(_project_root(), "models", "fraud_probability", "current.joblib")


def _default_v1_model_path() -> str:
    return os.path.join(_project_root(), "models", "fraud_probability", "fraud-logreg-v1.joblib")


def _default_v2_model_path() -> str:
    return os.path.join(_project_root(), "models", "fraud_probability", "fraud-logreg-tfidf-v2.joblib")


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


def _is_schema_missing_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "unknown column" in lowered or "doesn't exist" in lowered or "does not exist" in lowered


def probability_to_label(probability: Optional[float]) -> Optional[str]:
    if probability is None:
        return None
    if probability >= 0.65:
        return HIGH_LABEL
    if probability >= 0.25:
        return MEDIUM_LABEL
    return LOW_LABEL


def _resolve_model_path(model_path: Optional[str] = None) -> str:
    return model_path or os.getenv("FRAUD_PROBABILITY_MODEL_PATH") or _default_model_path()


def _load_model_artifact(model_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    global _MODEL_ARTIFACT, _MODEL_LOAD_FAILED
    resolved_model_path = os.path.abspath(_resolve_model_path(model_path))

    if model_path is None and _MODEL_ARTIFACT is not None:
        return _MODEL_ARTIFACT
    if model_path is None and _MODEL_LOAD_FAILED:
        return None
    if resolved_model_path in _MODEL_ARTIFACT_BY_PATH:
        return _MODEL_ARTIFACT_BY_PATH[resolved_model_path]
    if resolved_model_path in _MODEL_LOAD_FAILED_PATHS:
        return None

    if not os.path.exists(resolved_model_path):
        if model_path is None:
            _MODEL_LOAD_FAILED = True
        _MODEL_LOAD_FAILED_PATHS.add(resolved_model_path)
        return None

    try:
        project_root = _project_root()
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        import joblib

        artifact = joblib.load(resolved_model_path)
        _MODEL_ARTIFACT_BY_PATH[resolved_model_path] = artifact
        if model_path is None:
            _MODEL_ARTIFACT = artifact
        return artifact
    except Exception:
        if model_path is None:
            _MODEL_LOAD_FAILED = True
        _MODEL_LOAD_FAILED_PATHS.add(resolved_model_path)
        return None


def _load_v1_model_artifact() -> Optional[Dict[str, Any]]:
    return _load_model_artifact(
        os.getenv("FRAUD_PROBABILITY_V1_MODEL_PATH") or _default_v1_model_path()
    )


def _load_v2_model_artifact() -> Optional[Dict[str, Any]]:
    return _load_model_artifact(
        os.getenv("FRAUD_PROBABILITY_V2_MODEL_PATH") or _default_v2_model_path()
    )


def _fetch_first_search_result(cursor, product_id: str) -> Dict[str, Any]:
    try:
        cursor.execute(
            """
            SELECT
              id,
              product_id,
              title,
              body_text,
              price,
              sort_date,
              url,
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
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

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


def _seller_history_defaults() -> Dict[str, Any]:
    return dict(SELLER_HISTORY_FEATURES)


def _fetch_seller_history(cursor, *, store_id: str, product_id: str, feature_time: Any) -> Dict[str, Any]:
    if store_id is None or product_id is None or feature_time is None:
        return _seller_history_defaults()

    history = _seller_history_defaults()

    try:
        cursor.execute(
            """
            SELECT
              COUNT(id) AS seller_search_result_count_before,
              COUNT(
                CASE
                  WHEN fetched_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                    THEN id
                  ELSE NULL
                END
              ) AS seller_search_result_count_7d,
              COUNT(DISTINCT CAST(product_id AS CHAR)) AS seller_seen_product_count_before,
              COUNT(
                DISTINCT CASE
                  WHEN fetched_at >= DATE_SUB(%s, INTERVAL 24 HOUR)
                    THEN CAST(product_id AS CHAR)
                  ELSE NULL
                END
              ) AS seller_seen_product_count_24h,
              COUNT(
                DISTINCT CASE
                  WHEN fetched_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                    THEN CAST(product_id AS CHAR)
                  ELSE NULL
                END
              ) AS seller_seen_product_count_7d,
              TIMESTAMPDIFF(HOUR, MIN(fetched_at), %s) AS seller_history_age_hours,
              AVG(
                CASE
                  WHEN fetched_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                    THEN price
                  ELSE NULL
                END
              ) AS seller_avg_price_7d,
              MIN(
                CASE
                  WHEN fetched_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                    THEN price
                  ELSE NULL
                END
              ) AS seller_min_price_7d,
              MAX(
                CASE
                  WHEN fetched_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                    THEN price
                  ELSE NULL
                END
              ) AS seller_max_price_7d
            FROM search_results
            WHERE CAST(seller_store_seq AS CHAR) = %s
              AND CAST(product_id AS CHAR) <> %s
              AND fetched_at < %s
            """,
            (
                feature_time,
                feature_time,
                feature_time,
                feature_time,
                feature_time,
                feature_time,
                feature_time,
                store_id,
                product_id,
                feature_time,
            ),
        )
        history.update(cursor.fetchone() or {})
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

    try:
        cursor.execute(
            """
            SELECT
              COUNT(id) AS seller_product_snapshot_count_before,
              COUNT(
                CASE
                  WHEN observed_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                    THEN id
                  ELSE NULL
                END
              ) AS seller_product_snapshot_count_7d,
              COALESCE(SUM(
                CASE
                  WHEN observed_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                   AND snapshot_reason = 'price_changed'
                    THEN 1
                  ELSE 0
                END
              ), 0) AS seller_price_change_count_7d,
              COALESCE(SUM(
                CASE
                  WHEN observed_at >= DATE_SUB(%s, INTERVAL 7 DAY)
                   AND snapshot_reason = 'content_changed'
                    THEN 1
                  ELSE 0
                END
              ), 0) AS seller_content_change_count_7d
            FROM fraud_product_snapshots
            WHERE store_id = %s
              AND product_id <> %s
              AND observed_at < %s
            """,
            (
                feature_time,
                feature_time,
                feature_time,
                store_id,
                product_id,
                feature_time,
            ),
        )
        history.update(cursor.fetchone() or {})
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

    try:
        cursor.execute(
            """
            SELECT
              COUNT(id) AS seller_alert_count_before,
              COUNT(
                CASE
                  WHEN created_at >= DATE_SUB(%s, INTERVAL 30 DAY)
                    THEN id
                  ELSE NULL
                END
              ) AS seller_alert_count_30d,
              COUNT(
                DISTINCT CASE
                  WHEN created_at >= DATE_SUB(%s, INTERVAL 30 DAY)
                    THEN CAST(product_id AS CHAR)
                  ELSE NULL
                END
              ) AS seller_alert_product_count_30d
            FROM alert_events
            WHERE CAST(seller_store_seq AS CHAR) = %s
              AND (product_id IS NULL OR CAST(product_id AS CHAR) <> %s)
              AND created_at < %s
            """,
            (
                feature_time,
                feature_time,
                store_id,
                product_id,
                feature_time,
            ),
        )
        history.update(cursor.fetchone() or {})
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

    try:
        cursor.execute(
            """
            SELECT
              COUNT(id) AS seller_store_name_change_count_before,
              COUNT(
                CASE
                  WHEN changed_at >= DATE_SUB(%s, INTERVAL 30 DAY)
                    THEN id
                  ELSE NULL
                END
              ) AS seller_store_name_change_count_30d
            FROM joongna_store_name_changes
            WHERE CAST(store_seq AS CHAR) = %s
              AND changed_at < %s
            """,
            (
                feature_time,
                store_id,
                feature_time,
            ),
        )
        history.update(cursor.fetchone() or {})
    except Exception as exc:
        if not _is_schema_missing_error(exc):
            raise

    history["has_seller_history"] = 1 if any(
        _safe_float(history.get(key)) not in (None, 0.0)
        for key in (
            "seller_seen_product_count_before",
            "seller_product_snapshot_count_before",
            "seller_alert_count_before",
            "seller_store_name_change_count_before",
        )
    ) else 0
    return history


def _feature_value(key: str, value: Any) -> Any:
    if key in TEXT_FEATURES:
        return _normalize_optional_text(value) or ""
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
    seller_history: Dict[str, Any],
    alert_context: Dict[str, Any],
) -> Dict[str, Any]:
    search_title = _normalize_optional_text(search_result.get("title")) or ""
    title_text = _normalize_optional_text(alert_context.get("title")) or search_title
    body_text = (
        _normalize_optional_text(alert_context.get("body_text"))
        or _normalize_optional_text(alert_context.get("body_excerpt"))
        or _normalize_optional_text(search_result.get("body_text"))
        or ""
    )
    sort_date = search_result.get("sort_date")
    sort_hour = getattr(sort_date, "hour", None)
    sort_dayofweek = None
    if hasattr(sort_date, "isoweekday"):
        sort_dayofweek = sort_date.isoweekday() % 7 + 1

    raw_features = {
        "title_text": title_text,
        "body_text": body_text,
        "price_krw": search_result.get("price") or alert_context.get("price_krw"),
        "title_len": len(search_title or title_text),
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
        **_seller_history_defaults(),
        **(seller_history or {}),
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

    result = _score_alert_fraud_probability_with_artifact(
        cursor,
        artifact=artifact,
        product_id=product_id,
        store_id=store_id,
        alert_context=alert_context,
    )
    return result


def _build_alert_fraud_features(
    cursor,
    *,
    product_id: Any,
    store_id: Any = None,
    alert_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_product_id = _normalize_optional_text(product_id)
    if normalized_product_id is None:
        return {}

    alert_context = alert_context or {}
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

    return _build_features(
        search_result=search_result,
        activity=activity,
        profile=profile,
        seller_history=_fetch_seller_history(
            cursor,
            store_id=normalized_store_id,
            product_id=normalized_product_id,
            feature_time=feature_time,
        ),
        alert_context=alert_context,
    )


def _score_features_with_artifact(
    artifact: Optional[Dict[str, Any]],
    features: Dict[str, Any],
    *,
    scored_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    if not artifact or "model" not in artifact or not features:
        return {}

    probability = float(artifact["model"].predict_proba([features])[0][1])
    return {
        "fraud_probability": probability,
        "fraud_probability_label": probability_to_label(probability),
        "fraud_model_version": _normalize_optional_text(artifact.get("model_version")) or MODEL_VERSION_UNKNOWN,
        "fraud_scored_at": scored_at or _utc_now_naive(),
    }


def _score_alert_fraud_probability_with_artifact(
    cursor,
    *,
    artifact: Dict[str, Any],
    product_id: Any,
    store_id: Any = None,
    alert_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        features = _build_alert_fraud_features(
            cursor,
            product_id=product_id,
            store_id=store_id,
            alert_context=alert_context,
        )
        return _score_features_with_artifact(artifact, features)
    except Exception:
        return {}


def _add_versioned_score(
    result: Dict[str, Any],
    score: Dict[str, Any],
    *,
    version_key: str,
) -> None:
    result[f"fraud_probability_{version_key}"] = score.get("fraud_probability")
    result[f"fraud_probability_label_{version_key}"] = score.get("fraud_probability_label")
    result[f"fraud_model_version_{version_key}"] = score.get("fraud_model_version")
    result[f"fraud_scored_at_{version_key}"] = score.get("fraud_scored_at")


def score_alert_fraud_probability_comparison(
    cursor,
    *,
    product_id: Any,
    store_id: Any = None,
    alert_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score one alert with both the frozen v1 model and the current v2 model."""
    try:
        features = _build_alert_fraud_features(
            cursor,
            product_id=product_id,
            store_id=store_id,
            alert_context=alert_context,
        )
        if not features:
            return {}

        scored_at = _utc_now_naive()
        v1_score = _score_features_with_artifact(
            _load_v1_model_artifact(),
            features,
            scored_at=scored_at,
        )
        v2_score = _score_features_with_artifact(
            _load_v2_model_artifact(),
            features,
            scored_at=scored_at,
        )
    except Exception:
        return {}

    primary_score = v2_score or v1_score
    if not primary_score:
        return {}

    result = dict(primary_score)
    _add_versioned_score(result, v1_score, version_key=V1_MODEL_VERSION_KEY)
    _add_versioned_score(result, v2_score, version_key=V2_MODEL_VERSION_KEY)
    return result
