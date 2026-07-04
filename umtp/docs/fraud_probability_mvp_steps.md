# Fraud Probability MVP Steps

작성일: 2026-07-04

이 문서는 `feature/fraud-probability-mvp` 브랜치에 남긴 1-8단계 구현 기록이다.

## 1. 확정 라벨 조회

원천 테이블은 `fraud_training_label_candidates`다. 학습에는 `label IS NOT NULL`만 사용한다.

현재 확인값:

| label | reason | count |
|---:|---|---:|
| 0 | `store_active_after_14d` | 890 |
| 1 | `store_inactive_within_7d` | 636 |

학습 row는 총 1,526개다.

## 2. 최초 검색 관측 row 연결

`search_results`는 같은 `product_id`가 여러 번 관측될 수 있으므로 `fetched_at ASC, id ASC` 기준 첫 row만 사용한다.

검증 결과:

| 항목 | count |
|---|---:|
| labeled_total | 1,526 |
| joined_search_result | 1,526 |
| missing_search_result | 0 |

## 3. 판매자 스냅샷 연결

판매자 정보는 아래 테이블에서 붙인다.

- `fraud_store_activity_snapshots`
- `fraud_store_profile_field_snapshots`

미래 정보 누수를 막기 위해 `checked_at <= first_search_result.fetched_at + 30분`인 최신 row만 사용한다.

검증 결과:

| 항목 | count |
|---|---:|
| activity snapshot 연결 | 829 |
| activity snapshot 누락 | 697 |
| profile snapshot 연결 | 824 |
| profile snapshot 누락 | 702 |

누락은 정상이다. 모델 입력에서는 빈 값을 `-1.0`으로 채우고, `has_activity_snapshot`, `has_profile_snapshot` 플래그를 별도로 둔다.

## 4. Feature Row 생성

재현 명령:

```bash
cd /Users/boongtol_pro/Desktop/UMTP/umtp
python src/fraud_probability_features.py
```

생성 파일:

```text
data/fraud_probability/training_features.csv
```

현재 파일은 header 1줄 + 학습 row 1,526줄이다.

## 5. Logistic Regression 학습

모델은 `DictVectorizer + LogisticRegression(class_weight="balanced") + CalibratedClassifierCV`를 사용한다.

재현 명령:

```bash
cd /Users/boongtol_pro/Desktop/UMTP/umtp
python src/train_fraud_probability_model.py
```

## 6. 모델 저장

생성 파일:

```text
models/fraud_probability/current.joblib
models/fraud_probability/current_metrics.json
```

현재 metric:

| metric | value |
|---|---:|
| average_precision | 0.9308 |
| roc_auc | 0.7455 |
| brier_score | 0.2875 |

`brier_score`는 아직 거칠기 때문에 10단계 알림 억제 전에는 확률 분포를 더 관찰한다.

## 7. 알림 생성 시 확률 계산

`src/fraud_probability_service.py`가 `current.joblib`을 lazy load하고, `product_id` 기준으로 검색/판매자 snapshot feature를 다시 만들어 확률을 계산한다.

모델이 없거나 Python 환경에 `joblib/scikit-learn`이 없으면 빈 결과를 반환하고, 알림 생성은 계속된다.

## 8. `alert_events`에 저장

DB migration:

```bash
mysql -u <DB_USER> -p < sql/add_fraud_probability_columns.sql
```

추가 컬럼:

- `fraud_probability`
- `fraud_probability_label`
- `fraud_model_version`
- `fraud_scored_at`

`src/listing_analysis_pipeline.py`는 alert insert 전에 확률을 계산하고 위 컬럼에 저장한다.

## 9. 앱 / Telegram / FCM 표시

`src/notification_worker.py`는 `alert_events`의 fraud 컬럼을 읽어 `/alerts` 응답 item에 포함한다.

추가 응답 필드:

- `fraud_probability`
- `fraud_probability_label`
- `formatted_fraud_probability_label`
- `fraud_probability_text`
- `fraud_model_version`
- `fraud_scored_at`

Telegram 메시지에는 `사기 가능성` row를 추가했다.

FCM data payload에는 아래 값을 추가했다.

- `fraud_probability`
- `fraud_probability_label`
- `fraud_probability_text`

Android 앱은 `AlertItem`에 fraud 필드를 추가하고, 일반 알림 상세와 읽음 보관함 상세에 `사기 가능성`을 표시한다. FCM foreground 수신 시에도 push 본문에 `사기 가능성` 문구를 붙인다.

## 다음 단계

10단계에서 1주일 정도 확률 분포와 false positive를 관찰한 뒤 알림 억제 정책을 적용한다.
