# UMTP 1차 MVP

UMTP 프로젝트의 가장 간단한 1차 MVP입니다.  
MySQL에 공정가를 저장하고, Python에서 가짜 매물을 분석한 뒤 결과를 DB에 저장합니다.

## 1) 설치 방법

```bash
pip install -r requirements.txt
```

## 2) 환경변수 설정

`.env.example` 파일을 `.env`로 복사한 뒤, 실제 DB 접속 정보를 입력하세요.

```bash
cp .env.example .env
```

`.env.example` 내용:

```env
DB_HOST=your_db_host
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=UMTP_RB
```

## 3) 테이블 생성 방법

아래 SQL을 실행해서 DB/테이블을 생성하세요.

```bash
mysql -u <DB_USER> -p < sql/init_mvp_tables.sql
```

`sql/init_mvp_tables.sql`은 다음을 수행합니다.
- `mac_fair_prices` 테이블 생성
- `listing_analysis_results` 테이블 생성
- MacBook Air M1 13인치 8GB RAM 256GB SSD 공정가 550000원 upsert(중복 방지)

## 4) 실행 방법

```bash
python src/run_fake_umtp.py
```

예상 출력:

```text
공정가: 550000원
매물가: 440000원
차이금액: 110000원
차이비율: 20.0%
결과: 알림 대상
DB 저장 완료
```

## 5) 주의사항

`.env`에는 실제 DB 비밀번호 등 민감 정보가 들어갑니다.  
`.env` 파일은 절대 git에 올리지 마세요.

---

# UMTP 2차 MVP

2차 MVP에서는 가짜 매물 고정값 대신, 사용자가 터미널에서 매물 제목/가격을 직접 입력합니다.  
입력값을 바탕으로 DB에 저장된 공정가와 비교 분석하고, 결과를 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

## 1) 실행 방법

```bash
python src/run_manual_umtp.py
```

실행 후 아래처럼 입력합니다.

```text
매물 제목 입력: 맥북에어 M1 8GB 256GB 급처
매물 가격 입력: 430000
```

## 2) 동작 규칙

고정 제품 정보:
- `product_type`: `MacBook Air`
- `chip`: `M1`
- `screen_inch`: `13`
- `ram_gb`: `8`
- `ssd_gb`: `256`
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율이 `20` 이상이면 알림 대상
- 분석 결과 저장: `listing_analysis_results`

## 3) 예상 출력

```text
공정가: 550000원
매물가: 430000원
차이금액: 120000원
차이비율: 21.8%
결과: 알림 대상
DB 저장 완료
```

---

## UMTP MVP Progress

- 0.1: 고정 가짜 매물 분석
- 0.2: 터미널 입력 매물 분석
- 0.3: 매물 제목 스펙 자동 추출 후 분석 (진행 중)

0.3 실행 명령:

```bash
python src/run_title_parse_umtp.py
```

현재 단계는 매물 제목에서 스펙 추출 성공/실패 항목 확인까지 구현되었습니다.
