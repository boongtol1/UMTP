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
