import argparse
import csv
import json
import os
import sys
from datetime import datetime
from typing import Any

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    roc_auc_score,
)
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.fraud_probability_model_pipeline import (
        CATEGORICAL_FEATURES,
        TEXT_FEATURES,
        extract_body_texts,
        extract_structured_feature_dicts,
        extract_title_texts,
        normalize_text,
    )
except ModuleNotFoundError:
    from fraud_probability_model_pipeline import (
        CATEGORICAL_FEATURES,
        TEXT_FEATURES,
        extract_body_texts,
        extract_structured_feature_dicts,
        extract_title_texts,
        normalize_text,
    )


DEFAULT_INPUT_PATH = os.path.join(
    "data",
    "fraud_probability",
    "training_features_v2_step2.csv",
)
DEFAULT_MODEL_PATH = os.path.join(
    "models",
    "fraud_probability",
    "v2_candidate.joblib",
)
DEFAULT_METRICS_PATH = os.path.join(
    "models",
    "fraud_probability",
    "v2_candidate_metrics.json",
)
MODEL_VERSION = "fraud-logreg-tfidf-v2"
SKIP_FEATURES = {"label", "product_id", "store_id"}
TITLE_TFIDF_CONFIG = {
    "analyzer": "char_wb",
    "ngram_range": (2, 5),
    "min_df": 2,
    "max_df": 0.95,
    "max_features": 800,
    "sublinear_tf": True,
}
BODY_TFIDF_CONFIG = {
    "analyzer": "char_wb",
    "ngram_range": (2, 5),
    "min_df": 2,
    "max_df": 0.95,
    "max_features": 2500,
    "sublinear_tf": True,
}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _load_rows(input_path: str):
    rows = []
    with open(input_path, newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            y_value = int(row["label"])
            features = {
                key: normalize_text(value) if key in TEXT_FEATURES else value
                for key, value in row.items()
                if key not in SKIP_FEATURES
            }
            rows.append((features, y_value, row["product_id"]))
    if not rows:
        raise RuntimeError("fraud probability training rows are empty")
    return rows


def _build_model_pipeline() -> Pipeline:
    structured_pipeline = Pipeline(
        [
            (
                "selector",
                FunctionTransformer(extract_structured_feature_dicts, validate=False),
            ),
            ("vectorizer", DictVectorizer(sparse=True)),
        ]
    )
    title_pipeline = Pipeline(
        [
            (
                "selector",
                FunctionTransformer(extract_title_texts, validate=False),
            ),
            ("tfidf", TfidfVectorizer(**TITLE_TFIDF_CONFIG)),
        ]
    )
    body_pipeline = Pipeline(
        [
            (
                "selector",
                FunctionTransformer(extract_body_texts, validate=False),
            ),
            ("tfidf", TfidfVectorizer(**BODY_TFIDF_CONFIG)),
        ]
    )

    return Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        ("structured", structured_pipeline),
                        ("title_text", title_pipeline),
                        ("body_text", body_pipeline),
                    ]
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="liblinear",
                ),
            ),
        ]
    )


def _feature_columns(rows):
    if not rows:
        return []
    keys = set()
    for features, _, _ in rows:
        keys.update(features.keys())
    return sorted(keys)


def _structured_feature_columns(rows):
    return [key for key in _feature_columns(rows) if key not in TEXT_FEATURES]


def train_model(
    input_path: str = DEFAULT_INPUT_PATH,
    model_path: str = DEFAULT_MODEL_PATH,
    metrics_path: str = DEFAULT_METRICS_PATH,
) -> dict:
    rows = _load_rows(input_path)
    split_index = int(len(rows) * 0.8)
    train_rows = rows[:split_index]
    test_rows = rows[split_index:]

    x_train = [item[0] for item in train_rows]
    y_train = [item[1] for item in train_rows]
    x_test = [item[0] for item in test_rows]
    y_test = [item[1] for item in test_rows]

    base_pipeline = _build_model_pipeline()
    model = CalibratedClassifierCV(base_pipeline, method="sigmoid", cv=5)
    model.fit(x_train, y_train)

    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = [1 if probability >= 0.5 else 0 for probability in probabilities]
    metrics = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "input_path": input_path,
        "row_count": len(rows),
        "train_count": len(train_rows),
        "test_count": len(test_rows),
        "positive_count": sum(y_value for _, y_value, _ in rows),
        "negative_count": len(rows) - sum(y_value for _, y_value, _ in rows),
        "feature_schema": {
            "structured_features": _structured_feature_columns(rows),
            "text_features": sorted(TEXT_FEATURES),
            "categorical_features": sorted(CATEGORICAL_FEATURES),
            "skip_features": sorted(SKIP_FEATURES),
            "title_tfidf": dict(TITLE_TFIDF_CONFIG),
            "body_tfidf": dict(BODY_TFIDF_CONFIG),
        },
        "average_precision": average_precision_score(y_test, probabilities),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "brier_score": brier_score_loss(y_test, probabilities),
        "classification_report_at_0_5": classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
        "thresholds": {},
    }

    for threshold in [0.25, 0.5, 0.65, 0.8]:
        flagged = [probability >= threshold for probability in probabilities]
        flagged_count = sum(flagged)
        metrics["thresholds"][str(threshold)] = {
            "flagged_count": flagged_count,
            "flagged_rate": flagged_count / len(probabilities),
            "true_positive_flagged": sum(
                1 for flag, y_value in zip(flagged, y_test) if flag and y_value == 1
            ),
            "false_positive_flagged": sum(
                1 for flag, y_value in zip(flagged, y_test) if flag and y_value == 0
            ),
        }

    artifact = {
        "model_version": metrics["model_version"],
        "trained_at": metrics["trained_at"],
        "model": model,
        "categorical_features": sorted(CATEGORICAL_FEATURES),
        "skip_features": sorted(SKIP_FEATURES),
        "text_features": sorted(TEXT_FEATURES),
        "structured_features": _structured_feature_columns(rows),
        "title_tfidf_config": dict(TITLE_TFIDF_CONFIG),
        "body_tfidf_config": dict(BODY_TFIDF_CONFIG),
    }

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(artifact, model_path)
    with open(metrics_path, "w", encoding="utf-8") as metrics_file:
        json.dump(_to_jsonable(metrics), metrics_file, ensure_ascii=False, indent=2)

    return _to_jsonable(
        {
            "model_path": model_path,
            "metrics_path": metrics_path,
            **metrics,
        }
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Train fraud probability model")
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH)
    parser.add_argument("--model-output", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--metrics-output", default=DEFAULT_METRICS_PATH)
    return parser.parse_args()


def main():
    args = parse_args()
    metrics = train_model(
        input_path=args.input,
        model_path=args.model_output,
        metrics_path=args.metrics_output,
    )
    print(f"saved model={metrics['model_path']}")
    print(f"saved metrics={metrics['metrics_path']}")
    print(f"rows={metrics['row_count']}")
    print(f"average_precision={metrics['average_precision']:.4f}")
    print(f"roc_auc={metrics['roc_auc']:.4f}")
    print(f"brier_score={metrics['brier_score']:.4f}")


if __name__ == "__main__":
    main()
