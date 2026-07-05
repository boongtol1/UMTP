# Fraud Probability V2 Steps

작성일: 2026-07-05

이 문서는 `feature/fraud-probability-v2` 브랜치의 v2 확장 기록이다.

## 목표

v1의 숫자/스냅샷 기반 feature를 유지하면서 제목/본문 의미와 판매자 이력 패턴을 추가한다.

진행 순서:

1. `body_text` / `title_text` 학습 CSV에 넣기
2. `seller_history` feature SQL 추가
3. `train_fraud_probability_model.py`를 TF-IDF 포함 구조로 변경
4. `fraud_probability_service.py` 운영 feature도 동일하게 확장
5. v2 학습 후 metrics 비교
6. `current.joblib` 교체
7. 새 알림에서 v2 확률 표시

## 1. 제목/본문 학습 CSV

산출물:

```text
data/fraud_probability/training_features_v2_step1.csv
```

현재 상태:

| 항목 | 값 |
|---|---:|
| rows | 1,561 |
| columns | 43 |
| `title_text` filled | 1,561 / 1,561 |
| `body_text` filled | 1,521 / 1,561 |
| `body_text` missing | 40 |

`body_text`는 `alert_events`, `url_analysis_logs`, `listing_analysis_results`, `search_results` 등에서 순서대로 가져온다. DB에 본문이 없는 과거 row는 `src/backfill_fraud_training_body_text.py`로 가능한 범위까지 상세 페이지를 다시 읽어 채웠다.

## 2. Seller History Feature

산출물:

```text
data/fraud_probability/training_features_v2_step2.csv
```

현재 상태:

| 항목 | 값 |
|---|---:|
| rows | 1,561 |
| columns | 62 |
| step1 대비 추가 feature | 19 |

추가 feature:

- `has_seller_history`
- `seller_search_result_count_before`
- `seller_search_result_count_7d`
- `seller_seen_product_count_before`
- `seller_seen_product_count_24h`
- `seller_seen_product_count_7d`
- `seller_history_age_hours`
- `seller_avg_price_7d`
- `seller_min_price_7d`
- `seller_max_price_7d`
- `seller_product_snapshot_count_before`
- `seller_product_snapshot_count_7d`
- `seller_price_change_count_7d`
- `seller_content_change_count_7d`
- `seller_alert_count_before`
- `seller_alert_count_30d`
- `seller_alert_product_count_30d`
- `seller_store_name_change_count_before`
- `seller_store_name_change_count_30d`

사용 테이블:

- `search_results`
- `fraud_product_snapshots`
- `alert_events`
- `joongna_store_name_changes`

누수 방지 기준:

- 학습 row의 최초 검색 관측 시각인 `first_search_result.fetched_at`보다 과거인 이력만 사용한다.
- 현재 학습 대상 `product_id`는 seller history 집계에서 제외한다.
- 라벨 결과(`label`, `first_inactive_at`, `label_reason`)나 미래 비활성 상태는 seller history에 사용하지 않는다.

재현 명령:

```bash
cd /Users/boongtol_pro/Desktop/UMTP/umtp
python src/fraud_probability_features.py --output data/fraud_probability/training_features_v2_step2.csv
```

## 3. TF-IDF Logistic Regression 학습 스크립트

`src/train_fraud_probability_model.py`는 v2 기본 입력을 사용한다.

기본 입력:

```text
data/fraud_probability/training_features_v2_step2.csv
```

기본 산출물:

```text
models/fraud_probability/v2_candidate.joblib
models/fraud_probability/v2_candidate_metrics.json
```

아직 `current.joblib`은 덮어쓰지 않는다. `current.joblib` 교체는 metrics 비교 후 step6에서 진행한다.

모델 구조:

- `structured`: 숫자 feature + `risk_level`, `trade_type` 범주형 feature를 `DictVectorizer`로 변환
- `title_text`: `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))`
- `body_text`: `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))`
- classifier: `LogisticRegression(class_weight="balanced", solver="liblinear")`
- calibration: `CalibratedClassifierCV(method="sigmoid", cv=5)`

재현 명령:

```bash
cd /Users/boongtol_pro/Desktop/UMTP/umtp
python src/train_fraud_probability_model.py
```

운영 반영 전 임시 검증만 하려면 `/tmp` 등 별도 경로를 사용한다.

```bash
python src/train_fraud_probability_model.py \
  --model-output /tmp/fraud_probability_v2_candidate.joblib \
  --metrics-output /tmp/fraud_probability_v2_candidate_metrics.json
```

## 4. 운영 Feature 확장

`src/fraud_probability_service.py`가 알림 생성/발송 시점에도 v2 학습 feature와 같은 shape의 dict를 만든다.

추가 운영 feature:

- `title_text`
- `body_text`
- step2의 seller history feature 19개

연결 경로:

- `listing_analysis_pipeline.py`: 새 알림 생성 전 fraud score 계산 시 `title`, `body_excerpt`, `body_text` 전달
- `notification_worker.py`: 기존 알림 발송 직전 fraud score backfill 시 제목/본문 전달
- `backfill_fraud_probability_for_alerts.py`: 수동 backfill 시 제목/본문 전달
- `user_settings_service.py`: 조건 변경 후보 알림 생성 시 제목/본문 전달

주의:

- step4는 운영 feature 생성만 확장한다.
- `current.joblib` 교체는 아직 하지 않는다.
- v1 `current.joblib`은 추가 feature를 무시할 수 있어 기존 운영 점수 계산과 호환된다.

## 5. V2 Candidate 학습 및 Metrics 비교

산출물:

```text
models/fraud_probability/v2_candidate.joblib
models/fraud_probability/v2_candidate_metrics.json
models/fraud_probability/v2_metrics_comparison.json
```

비교 기준:

- v1 baseline: `models/fraud_probability/current.joblib`
- v2 candidate: `models/fraud_probability/v2_candidate.joblib`
- 아직 `current.joblib`은 교체하지 않는다.

주요 metrics:

| metric | v1 | v2 candidate | delta |
|---|---:|---:|---:|
| rows | 1,526 | 1,561 | +35 |
| positive | 636 | 651 | +15 |
| negative | 890 | 910 | +20 |
| average_precision | 0.9308 | 0.9471 | +0.0163 |
| roc_auc | 0.7455 | 0.8184 | +0.0729 |
| brier_score | 0.2875 | 0.2748 | -0.0128 |

threshold 비교:

| threshold | v1 flagged | v1 TP | v1 FP | v2 flagged | v2 TP | v2 FP |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 227 | 211 | 16 | 236 | 220 | 16 |
| 0.50 | 151 | 142 | 9 | 142 | 136 | 6 |
| 0.65 | 96 | 90 | 6 | 95 | 93 | 2 |
| 0.80 | 33 | 30 | 3 | 24 | 22 | 2 |

해석:

- v2는 ranking 지표인 `average_precision`, `roc_auc`가 모두 개선됐다.
- calibration 지표인 `brier_score`도 낮아졌다.
- `0.65` 기준에서는 flagged 수가 거의 같으면서 TP가 늘고 FP가 줄었다.
- step6에서 `current.joblib`을 v2 candidate로 교체할 근거가 충분하다.

검증:

```bash
python src/train_fraud_probability_model.py
FRAUD_PROBABILITY_MODEL_PATH=models/fraud_probability/v2_candidate.joblib \
  python - <<'PY'
from src.db import get_connection
from src.fraud_probability_service import score_alert_fraud_probability

conn = get_connection()
try:
    cur = conn.cursor(dictionary=True)
    print(score_alert_fraud_probability(
        cur,
        product_id="228109341",
        store_id="379066",
        alert_context={
            "title": "맥북 에어 m1 16GB",
            "body_text": "테스트 본문",
            "price_krw": 650000,
            "risk_level": "unknown",
            "trade_type": "unknown",
        },
    ))
finally:
    conn.close()
PY
```

## 6. Current Model 교체

v1 모델은 보존하고, 운영 기본 경로의 `current.*`를 v2 candidate로 교체했다.

보존된 v1 파일:

```text
models/fraud_probability/fraud-logreg-v1.joblib
models/fraud_probability/fraud-logreg-v1_metrics.json
```

운영 기본 모델:

```text
models/fraud_probability/current.joblib
models/fraud_probability/current_metrics.json
```

현재 `current.joblib`의 `model_version`:

```text
fraud-logreg-tfidf-v2
```

검증 명령:

```bash
cd /Users/boongtol_pro/Desktop/UMTP/umtp
python - <<'PY'
import joblib

artifact = joblib.load("models/fraud_probability/current.joblib")
print(artifact["model_version"])
PY
```

주의:

- 이미 떠 있는 worker/API process는 모델을 메모리에 cache할 수 있다.
- 새 알림에 v2 확률을 적용하려면 `notification_worker`, 앱/API 서버 등 fraud probability를 계산하는 process를 재시작한다.

## 7. 앱 Feed에서 V1/V2 비교 표시

새 알림 생성/발송 시 v1과 v2 모델을 둘 다 실행해서 비교 가능한 값을 저장한다.

보존된 모델 파일:

```text
models/fraud_probability/fraud-logreg-v1.joblib
models/fraud_probability/fraud-logreg-tfidf-v2.joblib
```

저장 방식:

- 기존 `fraud_probability`, `fraud_probability_label`, `fraud_model_version`, `fraud_scored_at`은 v2 대표값으로 유지한다.
- 비교용으로 아래 컬럼을 추가 저장한다.

```text
fraud_probability_v1
fraud_probability_label_v1
fraud_model_version_v1
fraud_scored_at_v1
fraud_probability_v2
fraud_probability_label_v2
fraud_model_version_v2
fraud_scored_at_v2
```

앱 feed 응답에는 아래 필드가 내려간다.

```text
fraud_probability_v1_text
fraud_probability_v2_text
fraud_probability_delta_v2_minus_v1
fraud_probability_delta_v2_minus_v1_text
fraud_probability_comparison_text
fraud_probability_comparison
```

예시:

```text
v1 주의 (31%) · v2 주의 (44%) · 차이 +13%p
```

주의:

- `fraud_probability`는 앱 기존 호환성을 위해 계속 v2 대표값으로 둔다.
- v1/v2 비교 계산은 같은 DB feature snapshot을 한 번 만든 뒤, 모델만 각각 실행한다.
- 새 컬럼 적용 후 worker/API process를 재시작해야 새 코드와 새 모델 cache가 반영된다.

최근 알림 backfill:

```bash
cd /Users/boongtol_pro/Desktop/UMTP/umtp
python src/backfill_fraud_probability_for_alerts.py --since-hours 12 --force --limit 500
```

2026-07-05 실행 결과:

```text
candidate_count: 21
scored_count: 21
updated_count: 21
skipped_count: 0
```
