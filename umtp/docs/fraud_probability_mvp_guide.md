# UMTP fraud probability MVP guide

작성일: 2026-07-04

## 목표

문제: 가격 조건에는 맞지만 사기 가능성이 높은 매물 알림이 너무 많이 온다.

목표: `UMTP_RB`에 이미 쌓인 중고나라 매물, 판매자, 사후 비활성 상태 데이터를 지도학습 라벨로 사용해서 `fraud_probability`를 예측하고, 그 값을 UMTP 앱/Telegram/FCM 알림에 표시한다. 1차는 표시만 하고, 2차에서 높은 확률의 알림을 앱 피드 전용 또는 낮은 우선순위로 보낸다.

## 현재 DB 상태

2026-07-04 기준 로컬 `UMTP_RB` 확인 결과:

| 테이블 | 행 수 | 역할 |
|---|---:|---|
| `listing_analysis_results` | 145,544 | 매물 분석 결과 |
| `analysis_jobs` | 145,530 | 분석 큐 |
| `alert_events` | 3,009 | 앱/Telegram/FCM 알림 원천 |
| `joongna_seen_products` | 3,265 | 검색 결과 중복/변경 감지 |
| `fraud_training_label_candidates` | 2,905 | 학습 라벨 후보 |
| `fraud_product_snapshots` | 20,570 | 상품 상태/가격/내용 스냅샷 |
| `fraud_store_status_snapshots` | 28,550 | 판매자 활성/비활성 상태 스냅샷 |
| `fraud_store_activity_snapshots` | 46,937 | 판매자 활동/프로필 스냅샷 |
| `fraud_store_profile_field_snapshots` | 33,231 | 판매자 신뢰도 필드 스냅샷 |

라벨 분포:

| label | reason | 행 수 | 의미 |
|---:|---|---:|---|
| 1 | `store_inactive_within_7d` | 636 | 등록 후 7일 안에 판매자 비활성/제재/삭제 감지 |
| 0 | `store_active_after_14d` | 890 | 등록 후 14일 뒤에도 판매자 활성 확인 |
| NULL | `pending_observation` | 1,085 | 아직 판정 대기 |
| NULL | `inactive_after_7d` | 294 | 비활성은 됐지만 사기 라벨 기준 밖 |

학습에 바로 쓸 수 있는 확정 라벨은 1,526건이다. 양성 비율이 약 41.7%라서 MVP 모델에는 충분하지만, 임계값은 반드시 알림 감소 효과 기준으로 고른다.

## 라벨 정책

현재 `fraud_store_monitor_service.py`는 이미 아래 정책으로 라벨을 만든다.

- `label = 1`: 매물 `listing_sort_date` 이후 7일 안에 판매자 상태가 `inactive`, `suspended`, `deleted` 중 하나가 됨.
- `label = 0`: 14일 뒤에도 판매자 상태가 `active`로 확인됨.
- `label = NULL`: 아직 시간이 부족하거나 애매한 케이스.

주의: 이 라벨은 "확정 사기"가 아니라 "사기 가능성이 높은 사후 패턴"이다. 앱 문구도 `사기 확률`보다는 `사기 의심 확률` 또는 `사기 가능성`이 안전하다.

## 누수 방지 원칙

모델이 실제 알림 시점에 몰랐던 정보를 배우면 운영에서 무너진다.

학습 피처는 `discovered_at` 또는 `listing_sort_date` 근처에 알 수 있었던 값만 사용한다.

사용 가능:

- `search_results`의 최초 관측 row: 제목, 가격, 판매자 store_seq/name, 리뷰 수, 프로필 이미지 URL, store level.
- `alert_events` 또는 분석 결과의 위험 키워드/위험 점수: 알림 생성 전에 분석한 값.
- `fraud_store_activity_snapshots`, `fraud_store_profile_field_snapshots`: `checked_at <= discovered_at + 30분` 정도로 제한한 최신 row.
- 같은 판매자의 과거 관측 통계: `listing_sort_date` 이전의 게시 빈도, 최근 제목/가격 변경 횟수.

사용 금지:

- `first_inactive_at`, `inactive_after_minutes`, `label_reason`.
- `fraud_store_status_snapshots`의 미래 비활성 상태.
- `joongna_store_profiles.last_status`처럼 현재 시점 상태를 그대로 쓰는 값. 과거 학습에서는 미래 정보가 섞일 수 있다.

## MVP 구조

1. `fraud_training_label_candidates`에서 확정 라벨만 가져온다.
2. `search_results` 최초 관측 row와 판매자/상품 스냅샷을 붙여 feature row를 만든다.
3. Python 학습 스크립트가 모델을 학습하고 `models/fraud_probability/current.joblib`에 저장한다.
4. 알림 생성 시 `fraud_probability_service`가 같은 feature를 만들어 점수를 계산한다.
5. `alert_events`에 확률/등급/모델 버전을 저장한다.
6. `/alerts`, Telegram 메시지, FCM data payload, Android `AlertItem`에 표시한다.
7. 충분히 검증되면 높은 사기 확률 알림은 push/Telegram을 줄이고 앱 피드에만 남긴다.

## 추천 DB 변경

MVP는 `alert_events`에 표시용 컬럼을 직접 추가하는 편이 가장 빠르다.

```sql
USE UMTP_RB;

ALTER TABLE alert_events
  ADD COLUMN fraud_probability DECIMAL(6,5) NULL AFTER risk_score,
  ADD COLUMN fraud_probability_label VARCHAR(20) NULL AFTER fraud_probability,
  ADD COLUMN fraud_model_version VARCHAR(100) NULL AFTER fraud_probability_label,
  ADD COLUMN fraud_scored_at DATETIME NULL AFTER fraud_model_version,
  ADD INDEX idx_alert_events_fraud_probability (fraud_probability);
```

운영 추적까지 하려면 별도 prediction 로그도 추가한다.

```sql
CREATE TABLE IF NOT EXISTS fraud_predictions (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  alert_event_id BIGINT UNSIGNED NULL,
  product_id VARCHAR(100) NULL,
  store_id VARCHAR(64) NULL,
  model_version VARCHAR(100) NOT NULL,
  fraud_probability DECIMAL(6,5) NOT NULL,
  fraud_probability_label VARCHAR(20) NOT NULL,
  feature_json JSON NULL,
  scored_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_fraud_predictions_alert_model (alert_event_id, model_version),
  KEY idx_fraud_predictions_product (product_id),
  KEY idx_fraud_predictions_store (store_id),
  KEY idx_fraud_predictions_probability (fraud_probability)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 학습 feature 초안

1차 feature는 적게 시작한다. 라벨이 1,526건이라 너무 많은 텍스트 feature를 넣으면 과적합된다.

| 그룹 | feature |
|---|---|
| 매물 | `price`, `title_len`, `sort_hour`, `sort_dayofweek`, `has_body`, `trigger_reason` |
| 가격 | `diff_ratio`, `price_to_fair_ratio`, `price_to_target_ratio` |
| 위험 룰 | `risk_score`, `risk_level`, `is_exchange_post`, `risk_keyword_count` |
| 판매자 프로필 | `seller_review_count`, `seller_store_level`, `has_profile_image`, `store_name_len` |
| 판매자 활동 | `posts_last_1h`, `posts_last_24h`, `posts_last_7d`, `visible_product_count` |
| 신뢰도 | `trust_score`, `safe_trade_count`, `reliability_score`, `activity_score` |
| 변경 패턴 | 최근 상품 스냅샷 수, 가격 변경 수, 제목 변경 수, 내용 변경 수 |

초기 모델은 텍스트 원문을 직접 넣지 말고 길이, 키워드 수, 룰 기반 위험 점수 정도만 쓴다.

## 학습 데이터 SQL 예시

아래 쿼리는 형태 예시다. 구현 시 `src/fraud_probability_training.py`에서 같은 로직을 Python으로 가져가도 된다.

```sql
WITH labeled AS (
  SELECT
    product_id,
    store_id,
    listing_sort_date,
    COALESCE(discovered_at, listing_sort_date) AS feature_time,
    label
  FROM fraud_training_label_candidates
  WHERE label IS NOT NULL
),
first_search_result AS (
  SELECT *
  FROM (
    SELECT
      sr.*,
      ROW_NUMBER() OVER (
        PARTITION BY sr.product_id
        ORDER BY sr.fetched_at ASC, sr.id ASC
      ) AS rn
    FROM search_results sr
    JOIN labeled l
      ON CAST(sr.product_id AS CHAR) = l.product_id
  ) ranked
  WHERE rn = 1
),
latest_activity AS (
  SELECT *
  FROM (
    SELECT
      l.product_id,
      fsa.posts_last_1h,
      fsa.posts_last_24h,
      fsa.posts_last_7d,
      fsa.visible_product_count,
      fsa.review_count,
      fsa.safe_trade_count,
      fsa.trust_score,
      fsa.reliability_score,
      fsa.activity_score,
      fsa.has_default_profile_image,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY fsa.checked_at DESC
      ) AS rn
    FROM labeled l
    LEFT JOIN fraud_store_activity_snapshots fsa
      ON fsa.store_id = l.store_id
     AND fsa.checked_at <= DATE_ADD(l.feature_time, INTERVAL 30 MINUTE)
  ) ranked
  WHERE rn = 1
),
latest_alert AS (
  SELECT *
  FROM (
    SELECT
      ae.*,
      ROW_NUMBER() OVER (
        PARTITION BY ae.product_id
        ORDER BY ae.created_at ASC, ae.id ASC
      ) AS rn
    FROM alert_events ae
    JOIN labeled l
      ON CAST(ae.product_id AS CHAR) = l.product_id
  ) ranked
  WHERE rn = 1
)
SELECT
  l.label,
  l.product_id,
  l.store_id,
  fsr.price,
  CHAR_LENGTH(COALESCE(fsr.title, '')) AS title_len,
  HOUR(fsr.sort_date) AS sort_hour,
  DAYOFWEEK(fsr.sort_date) AS sort_dayofweek,
  fsr.seller_review_count,
  CASE
    WHEN fsr.seller_profile_image_url IS NULL OR fsr.seller_profile_image_url = '' THEN 0
    ELSE 1
  END AS has_profile_image,
  CHAR_LENGTH(COALESCE(fsr.seller_store_name, '')) AS store_name_len,
  la.posts_last_1h,
  la.posts_last_24h,
  la.posts_last_7d,
  la.visible_product_count,
  la.review_count AS activity_review_count,
  la.safe_trade_count,
  la.trust_score,
  la.reliability_score,
  la.activity_score,
  la.has_default_profile_image,
  latest_alert.drop_rate_percent,
  latest_alert.risk_score,
  latest_alert.risk_level,
  latest_alert.is_exchange_post,
  JSON_LENGTH(latest_alert.risk_keywords) AS risk_keyword_count
FROM labeled l
JOIN first_search_result fsr
  ON CAST(fsr.product_id AS CHAR) = l.product_id
LEFT JOIN latest_activity la
  ON la.product_id = l.product_id
LEFT JOIN latest_alert
  ON CAST(latest_alert.product_id AS CHAR) = l.product_id;
```

## 모델 선택

추천 순서:

1. Baseline: `DummyClassifier(strategy="prior")`.
2. MVP: `LogisticRegression` + `SimpleImputer` + `OneHotEncoder`.
3. 개선: `HistGradientBoostingClassifier` + calibration.

현재 라벨 수에서는 Logistic Regression이 해석과 운영 안정성 면에서 좋다. 확률 품질이 중요하면 `CalibratedClassifierCV`를 붙인다.

추가 dependency:

```txt
scikit-learn
joblib
```

## 검증 기준

랜덤 split만 보지 말고 시간 기준 검증을 반드시 한다.

- 학습: 오래된 확정 라벨 70-80%.
- 검증: 그 이후 확정 라벨 20-30%.
- 별도 리포트: 최근 14일은 정상 라벨이 아직 부족하므로 pending 비율만 관찰.

볼 지표:

- PR-AUC: 양성 비율이 높고 임계값 운영이 중요해서 ROC-AUC보다 유용하다.
- Brier score/calibration: 확률 표시가 믿을 만한지 확인.
- threshold별 alert reduction simulation:
  - `p >= 0.65`를 push 제외하면 몇 건 줄어드는지.
  - 제외된 알림 중 실제 `label=0`이 얼마나 섞이는지.
  - `p < 0.25`를 정상 우선 알림으로 보내면 실제 사기 라벨이 얼마나 남는지.

## 확률 등급

초기 문구:

| 확률 | label | 표시 |
|---:|---|---|
| `< 0.25` | `LOW` | 사기 가능성 낮음 |
| `0.25 - 0.65` | `MEDIUM` | 사기 가능성 주의 |
| `>= 0.65` | `HIGH` | 사기 가능성 높음 |

운영 액션은 처음에는 표시만 한다. 1주일 관찰 후 아래처럼 줄인다.

| 등급 | 앱 피드 | FCM | Telegram |
|---|---|---|---|
| LOW | 표시 | 즉시 전송 | 즉시 전송 |
| MEDIUM | 표시 | 즉시 전송 | 즉시 전송, 제목에 `[주의]` |
| HIGH | 표시 | 기본 off 또는 낮은 priority | 즉시 전송 대신 요약/옵션화 |

## 백엔드 구현 순서

1. `sql/add_fraud_probability_columns.sql` 추가.
2. `requirements.txt`에 `scikit-learn`, `joblib` 추가.
3. `src/fraud_probability_features.py` 추가:
   - `build_training_rows(connection)`
   - `build_alert_candidate_features(connection, product_id, store_id, alert_context)`
4. `src/train_fraud_probability_model.py` 추가:
   - DB에서 라벨/feature 조회.
   - time split으로 검증.
   - `models/fraud_probability/current.joblib` 저장.
   - metric JSON 출력.
5. `src/fraud_probability_service.py` 추가:
   - 모델 lazy load.
   - 모델이 없거나 feature 생성 실패 시 `(None, None)` 반환.
   - `probability_to_label(prob)` 제공.
6. `src/listing_analysis_pipeline.py`의 `_create_alert_event_if_needed`에서 alert insert 전에 점수 계산.
7. `alert_events` insert column/value에 `fraud_probability`, `fraud_probability_label`, `fraud_model_version`, `fraud_scored_at` 추가.
8. `src/notification_worker.py`:
   - `_fetch_alert_rows` SELECT에 fraud 컬럼 추가.
   - `list_alert_events_for_user` item에 fraud 필드 추가.
   - `_build_telegram_message`에 `사기 가능성` row 추가.
   - `_build_push_notification_payload` data payload에 `fraud_probability`, `fraud_probability_label` 추가.
9. Android:
   - `network/AlertModels.kt`에 `fraud_probability`, `fraud_probability_label` 추가.
   - `AlertFeedScreen.kt` 상세 row에 `사기 가능성` 추가.
   - `UMTPFirebaseMessagingService.kt`에서 data payload를 읽어 push body에 `사기 가능성 높음` 같은 짧은 문구 추가.
10. 테스트:
   - feature 생성 SQL/함수 unit test.
   - 모델 없는 상태에서도 알림 생성이 실패하지 않는 테스트.
   - `/alerts` 응답에 fraud 필드가 포함되는 테스트.
   - Telegram 메시지에 fraud row가 들어가는 테스트.

## 운영 명령 예시

라벨/스냅샷 최신화:

```bash
cd umtp
python src/run_fraud_store_monitor_umtp.py --once
```

모델 학습:

```bash
cd umtp
python src/train_fraud_probability_model.py
```

백엔드 실행:

```bash
cd umtp
uvicorn src.api_server:app --reload
```

알림 worker:

```bash
cd umtp
python src/run_notification_worker_umtp.py --once
```

## 오늘 구현 범위 추천

오늘은 아래까지만 하면 성공이다.

1. `alert_events` fraud 컬럼 migration.
2. 학습 데이터 추출 함수와 Logistic Regression 학습 스크립트.
3. 알림 생성 시 확률 저장.
4. Telegram과 Android 상세 화면에 확률 표시.

알림 억제는 하루 이상 점수 분포를 보고 결정한다. 바로 막으면 좋은 매물까지 놓칠 수 있다.

