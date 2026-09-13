# Fraud Probability v3 (2026-09-13)

`fraud-logreg-tfidf-v3-20260913`은 2026-09-13 시점의 확정 라벨 4,015건으로 최종 학습한 운영 모델이다.

## 학습 데이터

- 정상 패턴(`store_active_after_14d`): 2,630건
- 사기 의심 패턴(`store_inactive_within_7d`): 1,385건
- 학습 입력: `data/fraud_probability/training_features_20260913_chronological.csv`
- 모델: `models/fraud_probability/fraud-logreg-tfidf-v3-20260913.joblib`

검증에서는 2026-08-16 이전 3,212건으로 모델을 학습하고 이후 최신 803건을 holdout으로 사용했다. 검증이 끝난 뒤 운영 모델은 4,015건 전체로 다시 학습했다.

| 최신 holdout 지표 | v2 | v3 |
|---|---:|---:|
| Average Precision | 0.6134 | 0.6991 |
| ROC-AUC | 0.7646 | 0.8292 |
| Brier score | 0.1945 | 0.1682 |
| 정확도(0.5 기준) | 0.6812 | 0.7472 |

상세 결과는 `models/fraud_probability/v3-20260913-comparison.json`에 기록한다.

## 운영 동작

- v1과 v2는 비교용으로 유지한다.
- v3를 대표 `fraud_probability`로 저장한다.
- API, FCM, Telegram에는 `v1 · v2 · v3 · v3-v2 차이` 형식의 비교 문구를 전달한다.
- 앱은 기존 `fraud_probability_text`와 v3 전용 응답 필드를 함께 받을 수 있다.

DB 적용:

```bash
mysql -u <DB_USER> -p < sql/add_fraud_probability_v3_columns.sql
```

기존 알림 재계산:

```bash
python src/backfill_fraud_probability_for_alerts.py --limit 200 --force
```

모델은 프로세스 안에서 캐시되므로 배포 후 analysis worker, notification worker, API process를 재시작해야 한다.
