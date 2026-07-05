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
