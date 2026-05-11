# UMTP 1차 MVP

UMTP 프로젝트의 가장 간단한 1차 MVP입니다.  
MySQL에 공정가를 저장하고, Python에서 가짜 매물을 분석한 뒤 결과를 DB에 저장합니다.

## UMTP MVP Progress

| Version | Summary | Run |
|---|---|---|
| 0.1 | 고정 가짜 매물 분석 | `python src/run_fake_umtp.py` |
| 0.2 | 터미널 입력 매물 분석 | `python src/run_manual_umtp.py` |
| 0.3 | 매물 제목 스펙 자동 추출 후 분석 | `python src/run_title_parse_umtp.py` |
| 0.4 | 여러 테스트 매물 일괄 분석 | `python src/run_batch_umtp.py` |
| 0.5 | CSV 매물 목록 일괄 분석 | `python src/run_csv_umtp.py` |
| 0.6 | 크롤링 결과 형태의 JSON 매물 일괄 분석 | `python src/run_json_umtp.py` |
| 0.7 | URL만 입력하는 실제 중고나라 매물 HTML 파싱 분석 | `python src/run_url_parse_umtp.py` |
| 0.8 | Android 알림 URL 수신 + 사용자 공정가 기준 분석 API | `uvicorn src.api_server:app --reload` |
| 0.9 | Telegram 알림 + 중복 URL 방지 + 분석 기록 안정화 | `uvicorn src.api_server:app --reload` |

- `data/sample_listings.csv`: 0.5에서 테스트 매물 목록을 읽는 CSV 입력 파일입니다.
- `data/sample_crawled_listings.json`: 0.6에서 크롤링 결과 형태의 테스트 매물 목록을 읽는 JSON 입력 파일입니다.
- 0.5는 아직 실제 중고나라 크롤링을 하지 않고 CSV 샘플 데이터 기반으로만 분석합니다.
- 0.6은 아직 실제 중고나라 크롤링을 하지 않고 JSON 샘플 데이터 기반으로만 분석합니다.
- 0.7은 아직 중고나라 전체 검색 크롤링을 하지 않고, 사용자가 입력한 실제 URL 1개만 `requests + BeautifulSoup`로 파싱합니다.
- 0.7 제목 추출: `twitter:title` meta 태그
- 0.7 본문 추출: `twitter:description` meta 태그
- 0.7 가격 추출: 지정된 class 토큰을 포함한 `span` 태그
- 향후에는 중고장터 키워드 알림에서 전달된 URL을 자동 분석하는 구조로 확장할 예정입니다.
- 0.8 초안: `sql/add_user_fair_prices.sql`로 사용자별 공정가 테이블을 추가합니다.
- `user_fair_prices`는 사용자별 공정가(`fair_price_krw`)와 알림 기준(`alert_drop_rate_percent`)을 관리합니다.
- 0.8 서비스 계층: `analysis_service.py`에서 URL 분석과 `ok/ reason` 실패 응답을 처리합니다.
- 0.8 알림은 `notifier.py`의 `print()` 기반 가짜 알림으로 처리합니다.
- 0.8은 Android Notification Listener 앱 자체를 구현하지 않고 `curl` 요청으로 URL 전달 상황을 흉내냅니다.
- 0.8은 실제 텔레그램 전송 대신 `notifier.py`의 `print()` 알림을 사용합니다.
- 0.9 초안: `sql/add_url_analysis_logs.sql`로 URL 분석 안정 로그 테이블을 추가합니다.
- 0.9 중복 정책: 같은 `user_id + url`이 `success/failed/duplicate`로 기록되면 재분석하지 않습니다.
- 0.9 분석 로그: `analysis_log.py`에서 `success/failed/duplicate`를 공통 저장합니다.
- 0.9 텔레그램 알림: `.env`의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 사용하며 미설정 시 서버는 종료되지 않습니다.
- 0.9 통합 응답: `status(success/duplicate/failed)`와 `telegram_sent`를 API 응답에 포함합니다.
- 텔레그램 실제 토큰/채팅 ID는 `.env`에만 넣고 Git에는 올리지 않습니다.

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

---

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

# UMTP 3차 MVP

3차 MVP에서는 사용자가 입력한 매물 제목에서 제품 스펙을 자동 추출한 뒤,  
DB 공정가와 비교 분석하고 결과를 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

## 1) 실행 방법

```bash
python src/run_title_parse_umtp.py
```

실행 후 아래처럼 입력합니다.

```text
매물 제목 입력: 맥북에어 M1 8GB 256GB 급처
매물 가격 입력: 430000
```

## 2) 동작 규칙

- 제목 파싱: `parse_listing_title(title)` 사용
- 지원 대상: `MacBook Air`, `M1`, `13인치`, `8GB/8기가`, `256GB/256기가`
- 스펙 추출 실패 시: 실패 항목 출력 후 종료
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율이 `20` 이상이면 알림 대상
- 분석 결과 저장: `listing_analysis_results`

## 3) 예상 출력

```text
추출된 스펙:
제품: MacBook Air
칩: M1
화면: 13인치
RAM: 8GB
SSD: 256GB

공정가: 550000원
매물가: 430000원
차이금액: 120000원
차이비율: 21.8%
결과: 알림 대상
DB 저장 완료
```

---

# UMTP 4차 MVP

4차 MVP에서는 여러 테스트 매물을 한 번에 분석합니다.  
각 매물 제목에서 스펙을 추출하고 DB 공정가와 비교해 알림 대상 여부를 판단한 뒤,  
성공 건은 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

## 1) 실행 방법

```bash
python src/run_batch_umtp.py
```

## 2) 동작 규칙

- 입력 데이터: `run_batch_umtp.py` 내부 테스트 매물 리스트(4건)
- 제목 파싱: `parse_listing_title(title)` 재사용
- 파싱 실패 또는 공정가 조회 실패 시:
  - `분석 실패: 현재 지원하지 않는 제품이거나 공정가가 없습니다.`
  - DB 저장하지 않음
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율이 `20` 이상이면 알림 대상
- 분석 결과 저장: `listing_analysis_results`
- 마지막 요약 출력:
  - 전체 매물 개수
  - DB 저장 성공 개수
  - 알림 대상 개수

## 3) 예상 출력

```text
[1] 맥북에어 M1 8GB 256GB 급처
공정가: 550000원
매물가: 430000원
차이금액: 120000원
차이비율: 21.8%
결과: 알림 대상
DB 저장 완료

[2] 맥북에어 M1 8GB 256GB 상태좋음
공정가: 550000원
매물가: 520000원
차이금액: 30000원
차이비율: 5.5%
결과: 알림 대상 아님
DB 저장 완료

[3] 맥북에어 M1 8기가 256기가 판매
공정가: 550000원
매물가: 450000원
차이금액: 100000원
차이비율: 18.2%
결과: 알림 대상 아님
DB 저장 완료

[4] 맥북프로 M2 16GB 512GB 판매
분석 실패: 현재 지원하지 않는 제품이거나 공정가가 없습니다.

요약:
전체 매물: 4개
DB 저장 성공: 3개
알림 대상: 1개
```

---

# UMTP 5차 MVP

5차 MVP에서는 CSV 파일에서 여러 매물 목록을 읽어 일괄 분석합니다.  
각 매물 제목에서 스펙을 추출하고 DB 공정가와 비교해 알림 대상 여부를 판단한 뒤,  
성공 건은 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

## 1) 실행 방법

```bash
python src/run_csv_umtp.py
```

## 2) 동작 규칙

- 입력 데이터: `data/sample_listings.csv`
- 제목 파싱: `parse_listing_title(title)` 재사용
- 스펙 추출 실패 시: 실패 사유 출력 후 DB 저장하지 않음
- 공정가 조회 실패 시: 실패 사유 출력 후 DB 저장하지 않음
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율이 `20` 이상이면 알림 대상
- 분석 결과 저장: `listing_analysis_results`
- 마지막 요약 출력:
  - 전체 CSV 행 개수
  - DB 저장 성공 개수
  - 알림 대상 개수
  - 실패 개수

## 3) 예상 출력

```text
[1] 맥북에어 M1 8GB 256GB 급처
공정가: 550000원
매물가: 430000원
차이금액: 120000원
차이비율: 21.8%
결과: 알림 대상
DB 저장 완료

[2] 맥북에어 M1 8GB 256GB 상태좋음
공정가: 550000원
매물가: 520000원
차이금액: 30000원
차이비율: 5.5%
결과: 알림 대상 아님
DB 저장 완료

[3] 맥북에어 M1 8기가 256기가 판매
공정가: 550000원
매물가: 450000원
차이금액: 100000원
차이비율: 18.2%
결과: 알림 대상 아님
DB 저장 완료

[4] 맥북프로 M2 16GB 512GB 판매
분석 실패: 제목 스펙 추출 실패 (제품, 칩, RAM, SSD 누락)
DB 저장 안 함

요약:
전체 CSV 행: 4개
DB 저장 성공: 3개
알림 대상: 1개
실패: 1개
```

---

# UMTP 6차 MVP

6차 MVP에서는 크롤링 결과 형태의 JSON 파일에서 여러 매물 목록을 읽어 일괄 분석합니다.  
아직 실제 중고나라 크롤링은 하지 않고, JSON 샘플 데이터 기반으로만 분석합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

## 1) 실행 방법

```bash
python src/run_json_umtp.py
```

## 2) 동작 규칙

- 입력 데이터: `data/sample_crawled_listings.json`
- JSON 파싱: Python 표준 라이브러리 `json` 모듈 사용
- JSON 루트 형식: 매물 dict들의 list
- 각 매물 필수 필드: `title`, `listing_price_krw`, `source`, `url`
- 제목 파싱: `parse_listing_title(title)` 재사용
- 스펙 추출 대상: `product_type`, `chip`, `screen_inch`, `ram_gb`, `ssd_gb`
- 스펙 추출 실패 시: 실패 사유 출력 후 DB 저장하지 않음
- 공정가 조회 실패 시: 실패 사유 출력 후 DB 저장하지 않음
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율이 `20` 이상이면 알림 대상
- 분석 결과 저장: `listing_analysis_results`
- 현재 `listing_analysis_results`에 `source`, `url` 컬럼이 없어 DB에는 저장하지 않음
- 각 매물마다 `source`, `url`을 함께 출력
- 마지막 요약 출력:
  - 전체 JSON 매물 개수
  - DB 저장 성공 개수
  - 알림 대상 개수
  - 실패 개수

## 3) 예상 출력

```text
[1] 맥북에어 M1 8GB 256GB 급처
출처: joongna
URL: https://example.com/listing/1
공정가: 550000원
매물가: 430000원
차이금액: 120000원
차이비율: 21.8%
결과: 알림 대상
DB 저장 완료

[2] 맥북에어 M1 8GB 256GB 상태좋음
출처: joongna
URL: https://example.com/listing/2
공정가: 550000원
매물가: 520000원
차이금액: 30000원
차이비율: 5.5%
결과: 알림 대상 아님
DB 저장 완료

[3] 맥북에어 M1 8기가 256기가 판매
출처: joongna
URL: https://example.com/listing/3
공정가: 550000원
매물가: 450000원
차이금액: 100000원
차이비율: 18.2%
결과: 알림 대상 아님
DB 저장 완료

[4] 맥북프로 M2 16GB 512GB 판매
출처: joongna
URL: https://example.com/listing/4
분석 실패: 제목 스펙 추출 실패 (제품, 칩, RAM, SSD 누락)
DB 저장 안 함

요약:
전체 JSON 매물: 4개
DB 저장 성공: 3개
알림 대상: 1개
실패: 1개
```

---

# UMTP 7차 MVP

7차 MVP에서는 사용자가 입력한 실제 중고나라 URL 1개에서 HTML을 읽고,  
제목/본문/가격을 자동 추출한 뒤 스펙 파싱까지 연결합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

## 1) 실행 방법

```bash
python src/run_url_parse_umtp.py
```

실행 후 아래처럼 URL만 입력합니다.

```text
매물 URL 입력: https://web.joongna.com/product/228451872
```

## 2) 동작 규칙

- 사용자 입력: URL 1개만 입력
- 0.7은 아직 중고나라 전체 검색 크롤링을 하지 않음
- HTML 요청: `requests.get(url)` + `User-Agent` + `timeout`
- HTML 파싱: `BeautifulSoup`
- 0.7 구현을 위해 의존성 `requests`, `beautifulsoup4`를 requirements에 추가
- 제목 추출: `meta name="twitter:title"`의 `content`
- 본문 추출: `meta name="twitter:description"`의 `content`
- 가격 추출: `whitespace-pre-line`, `text-32`, `font-bold`, `max-md:text-24` class 토큰을 모두 포함한 `span`
- 가격 변환: 숫자만 추출해 `int`로 변환 (`550,000원` -> `550000`)
- 가격 추출 실패 시: `가격 추출 실패` 메시지를 출력하고 DB 저장하지 않음
- 스펙 추출: `parse_listing_title(title + " " + description)` 재사용
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율 `20` 이상
- 분석 결과 저장: `listing_analysis_results`
- 출력 항목: 제목, 본문 일부, 가격, 스펙, 분석 결과, `source`, `url`

## 3) 예상 출력

```text
추출된 제목:
맥북 에어 M1 2020 8GB 실버

추출된 본문:
Apple Macbook Air M1 2020 8GB 램 256GB SSD 33.7cm 레티나 디스플레이 배터리 84% ...

추출된 가격:
550000원

추출된 스펙:
제품: MacBook Air
칩: M1
화면: 13인치
RAM: 8GB
SSD: 256GB

공정가: 550000원
매물가: 550000원
차이금액: 0원
차이비율: 0.0%
결과: 알림 대상 아님

출처: joongna
URL: https://web.joongna.com/product/228451872

DB 저장 완료
```

---

# UMTP 8차 MVP

8차 MVP에서는 Android Notification Listener 앱이 URL을 보낸다고 가정하고,  
URL 수신 API에서 사용자별 공정가 기준 분석을 수행합니다.

이번 단계는 Android 앱 자체를 구현하지 않고, `curl` 요청으로 URL 전달 상황을 흉내냅니다.  
실제 텔레그램 전송은 하지 않으며 `notifier.py`의 `print()` 알림으로 대체합니다.

## 1) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

## 2) 요청 예시(curl)

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "url": "https://web.joongna.com/product/228451872"
  }'
```

## 3) 동작 규칙

- 엔드포인트: `POST /analyze-url`
- 입력: `user_id`, `url`
- URL HTML 파싱: `listing_page_parser.py` 재사용
- 스펙 추출: `parse_listing_title(title + " " + description)` 재사용
- 사용자 공정가 조회: `user_fair_prices` (`fair_price_krw`, `alert_drop_rate_percent`)
- 분석 결과 저장: `listing_analysis_results`
- 알림 대상이면 `notifier.py`의 `send_alert(message)` 호출 (`print()` 기반)
- 실패 응답 형식: `{"ok": false, "reason": "..."}`
- 0.8 구현을 위해 `requirements.txt`에 `fastapi`, `uvicorn`을 추가

---

# UMTP 9차 MVP

9차 MVP에서는 Telegram 알림, 중복 URL 재분석 방지, 분석 로그 안정 저장을 추가합니다.

## 1) 추가 SQL 실행

```bash
mysql -u <DB_USER> -p < sql/add_url_analysis_logs.sql
```

## 2) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

## 3) .env 설정

`.env`에 아래 값을 설정합니다.

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

실제 비밀값은 `.env`에만 저장하고 Git에는 올리지 않습니다.

## 4) 테스트(curl)

테스트 URL:
`https://web.joongna.com/product/228436846`

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "url": "https://web.joongna.com/product/228436846"
  }'
```

## 5) 동작 규칙

- 같은 `user_id + url`이 `success/failed/duplicate`로 이미 기록되면 재분석하지 않습니다.
- 중복 요청은 `ok=true`, `status="duplicate"`, `message="이미 분석된 URL"`로 응답합니다.
- `url_analysis_logs`에 `success/failed/duplicate`를 모두 저장합니다.
- 알림 대상일 때만 Telegram Bot API `sendMessage`를 호출합니다.
- 텔레그램 설정이 없으면 서버는 죽지 않고 `텔레그램 설정 없음`을 출력합니다.

