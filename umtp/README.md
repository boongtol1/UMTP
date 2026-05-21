# UMTP

UMTP 프로젝트의 가장 간단한 1차 MVP입니다.  
MySQL에 공정가를 저장하고, Python에서 가짜 매물을 분석한 뒤 결과를 DB에 저장합니다.

## 문서 안내

- 처음 세팅은 `빠른 시작`부터 진행하세요.
- 현재 운영 기준(1.8 파이프라인)은 `UMTP 1.3~1.8 운영 MVP` 섹션의 SQL/실행/동작 규칙을 확인하세요.
- 과거 단계별 동작은 `버전별 상세 이력`에서 확인할 수 있습니다.

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
| 1.0 | 전체 MacBook Air 단위 제품 DB화 + rule-based 공정가 자동 생성 | `python src/seed_user_fair_prices.py` |
| 1.1 | 셀프검수 구조화 데이터 우선 파싱 + 숫자 기반 보조 파싱 | `uvicorn src.api_server:app --reload` |
| 1.2 | 위험 키워드 점수화 + 교환글 탐지 + 주의 알림 | `uvicorn src.api_server:app --reload` |
| 1.3 | 중고나라 Search API polling + 끌올/가격변경 감지 분석 | `python src/run_joongna_polling_umtp.py --once` |
| 1.4 | 사용자별 MacBook Air 공정가/차이비율 설정 API | `uvicorn src.api_server:app --reload` |
| 1.5 | user_fair_prices(enabled) 기반 polling 대상 설정 | `python src/run_joongna_polling_umtp.py --once` |
| 1.6 | 설정 저장 즉시 polling 요청(force_poll) | `python src/run_joongna_polling_umtp.py --once --user-id boongtol` |
| 1.7 | Android 사용자 지정 검색어 설정 | `uvicorn src.api_server:app --reload` |
| 1.8 | analysis_jobs + notification worker 기반 파이프라인 | `python src/run_analysis_worker_umtp.py --once` |
| 1.9 | Android 쉬운 감시 조건 UI | `cd ../android && ./gradlew :app:assembleDebug` |

## 주요 변경 요약

- `data/sample_listings.csv`: 0.5에서 테스트 매물 목록을 읽는 CSV 입력 파일입니다.
- `data/sample_crawled_listings.json`: 0.6에서 크롤링 결과 형태의 테스트 매물 목록을 읽는 JSON 입력 파일입니다.
- 0.5는 아직 실제 중고나라 크롤링을 하지 않고 CSV 샘플 데이터 기반으로만 분석합니다.
- 0.6은 아직 실제 중고나라 크롤링을 하지 않고 JSON 샘플 데이터 기반으로만 분석합니다.
- 0.7은 아직 중고나라 전체 검색 크롤링을 하지 않고, 사용자가 입력한 실제 URL 1개만 `requests + BeautifulSoup`로 파싱합니다.
- 0.7 제목 추출: `twitter:title` meta 태그
- 0.7 본문 추출: `twitter:description` meta 태그
- 0.7 가격 추출: 지정된 class 토큰을 포함한 `span` 태그
- 0.7 셀프검수(`dl/dt/dd`)가 있으면 모델명/램 용량/SSD용량/CPU종류/컬러를 스펙 파싱 재료로 추가합니다.
- 셀프검수 영역이 없는 매물은 기존처럼 제목+본문 기준으로 분석합니다.
- 향후에는 중고장터 키워드 알림에서 전달된 URL을 자동 분석하는 구조로 확장할 예정입니다.
- 0.8 초안: `sql/add_user_fair_prices.sql`로 사용자별 공정가 테이블을 추가합니다.
- `user_fair_prices`는 사용자별 공정가(`fair_price_krw`)와 알림 기준(`alert_drop_rate_percent`)을 관리합니다.
- `user_fair_prices.target_buy_price_krw`는 GENERATED STORED 컬럼이며 `ROUND(fair_price_krw * (1 - alert_drop_rate_percent / 100))`로 자동 계산됩니다.
- 예: 공정가 `1,000,000원`, 차이비율 `20.50%`이면 목표 구매가(`target_buy_price_krw`)는 `795,000원`입니다.
- `alert_drop_rate_percent`는 `-100.00% ~ 100.00%`를 허용합니다. 양수는 공정가보다 낮은 목표가, 음수는 공정가보다 높은 목표가를 의미합니다.
- `user_fair_prices.alert_price_direction` 기본값은 `BELOW_OR_EQUAL`이며, `ABOVE_OR_EQUAL`도 지원합니다.
- 알림 비교 규칙: `BELOW_OR_EQUAL`은 `listing_price_krw <= target_buy_price_krw`, `ABOVE_OR_EQUAL`은 `listing_price_krw >= target_buy_price_krw`입니다.
- `user_fair_prices.min_price_krw`/`max_price_krw`는 방향별 추가 경계값입니다. `BELOW_OR_EQUAL`에서는 `min_price_krw`만 사용(해당 값 미만 매물 제외), `ABOVE_OR_EQUAL`에서는 `max_price_krw`만 사용(해당 값 초과 매물 제외)합니다.
- 예: `BELOW_OR_EQUAL + min_price_krw=300000`이면 30만원 미만 매물은 제외됩니다.
- 예: `ABOVE_OR_EQUAL + max_price_krw=900000`이면 90만원 초과 매물은 제외됩니다.
- 예1: 공정가 `1,000,000원`, 차이비율 `20%` -> 목표가 `800,000원`, `BELOW_OR_EQUAL`이면 `800,000원 이하`만 알림입니다.
- 예2: 공정가 `1,000,000원`, 차이비율 `-10%` -> 목표가 `1,100,000원`, `ABOVE_OR_EQUAL`이면 `1,100,000원 이상`만 알림입니다.
- 알림 피드는 기존 필드를 유지하면서 상세 필드(제품 분류/시장가 기준/알림 조건/위험도/본문 요약/분석 시각/출처)를 추가 제공합니다.
- Android 가격 설정 화면은 개발자 용어 대신 사용자 친화 문구(`내가 생각한 시장가`, `시장가와의 차이(%)`, `알림 기준 가격`)를 사용합니다.
- Android 설정 화면은 새로고침 상태(`새로고침 중...`, `방금 새로고침됨`, 실패 메시지, 마지막 새로고침 시각)를 표시합니다.
- 설정 탭(칩/화면/RAM·SSD)에서도 수동 새로고침 액션을 제공하며, 네트워크 장애 시 크래시 없이 실패 상태/토스트 메시지를 표시합니다.
- 매물 본문 원문 저장용 `body_text` 컬럼을 `alert_events`, `listing_analysis_results`, `url_analysis_logs`에 추가했습니다. 신규/기존 환경 모두 `sql/migrate_body_text_fields.sql`로 반영할 수 있습니다.
- `/alerts` 및 `/analyze-url` 응답에 `body_text`를 포함하며, Android 알림 상세는 본문이 없으면 `본문 내용 없음`을 표시합니다.
- 알림 피드/텔레그램 문구를 동일 정책(사용자 친화 용어: `내가 생각한 시장가`, `시장가와의 차이`, `알림 기준 가격`)으로 맞췄고, 대표 이미지 URL이 있으면 Android 피드 카드와 Telegram 알림에 함께 표시합니다.
- 위험도 표시는 `낮음/주의/위험`으로 요약하며, 위험 키워드/교환 여부/본문 요약을 함께 제공합니다.
- `alert_events`에 읽음 상태 컬럼(`is_read`, `read_at`)을 추가했고, 기본 메인 피드는 안 읽은 알림(`is_read=0`)만 조회합니다.
- 알림 상세를 열면 자동 읽음 처리되며, 읽음 처리된 알림은 삭제되지 않고 읽음 보관함에서 `chip -> screen_inch -> alert list` 구조로 조회할 수 있습니다.
- 읽음/읽음보관함 동작 이력은 `alert_read_archive_events`에 액션 단위로 누적 기록합니다.
- 읽음 상세의 카드 요소(알림유형/제목/스펙/가격/위험도/위험키워드/교환·나눔·의심/특이사항/본문/시각 등)는 `alert_read_archive_events` 상세 컬럼과 `alert_payload_json`에도 함께 저장합니다.
- `PATCH /alert-events/{id}/read`, `PATCH /alert-events/read-all`, `GET /alert-events/read/grouped` API를 추가했습니다.
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
- 1.0 초안: `macbook_air_units.py`에 전체 실리콘 MacBook Air 유효 조합을 정의합니다.
- 1.0 rule-based 공정가는 실제 시세가 아닌 MVP용 임시 기준값입니다.
- 1.0 seed: `python src/seed_user_fair_prices.py`로 `user_fair_prices`를 일괄 생성/업데이트합니다.
- 1.0 SQL seed: `sql/seed_macbook_air_units.sql`로도 동일 기준값을 upsert할 수 있습니다.
- 1.0 파서 검증: MacBook Air 스펙 조합이 유효하지 않으면 `invalid_macbook_air_unit`으로 실패 처리합니다.
- 1.0 API 확장: `/analyze-url` 응답에 `unit_valid`, `unit_validation_reason`를 포함합니다.
- 1.1: HTML 전체 텍스트 대신 제목/본문/가격/셀프검수(`dl/dt/dd`) 구조화 영역만 파싱합니다.
- 1.1: 셀프검수 key-value를 우선 적용하고 부족한 값만 제목/본문 숫자 후보로 보완합니다.
- 1.1: `numeric_candidate_extractor.py`에서 화면(13/15), RAM(8/16/24/32), SSD(256/512/1024/2048/4096) 후보를 분리하고 `TB->GB`, `16/512` 축약표현을 파싱합니다.
- 1.1: `1/2/4` 단독 숫자는 SSD 후보로 보지 않고, `1TB/2TB/4TB`(또는 `t/테라`) 형태일 때만 SSD 후보로 변환합니다.
- 1.1: `spec_parser.py`는 `confidence_score`, `detected_patterns`, `detected_conflicts`를 반환하고 화면 크기 미검출 시 13인치 기본값을 사용합니다.
- spec parser 확장: 기존 `MacBook Air` 파싱은 유지하면서 `Mac mini`/`맥미니`/`맥 미니`/`macmini`를 제품 타입으로 인식합니다.
- `Mac mini` 파싱 시 `screen_inch`는 항상 `0`으로 설정되며, 화면 크기(13/15인치)가 명시된 경우 유효하지 않은 조합으로 실패 처리합니다.
- `Mac mini` 칩 파싱은 `M2 Pro`, `M4 Pro`를 `M2`, `M4`보다 먼저 검사해 오파싱을 방지합니다.
- `Mac mini` 유효 조합: `M1`, `M2`, `M2 Pro`, `M4`, `M4 Pro` + RAM/SSD 허용 조합 검증(`is_valid_silicon_unit`)을 적용합니다.
- 1.1: `/analyze-url` 응답/로그에 `confidence_score`, `screen_inch_defaulted`, `unit_valid`, `unit_validation_reason`를 포함합니다.
- 1.1: `sql/add_parser_confidence_columns.sql`로 `url_analysis_logs` 파서 신뢰도 컬럼을 안전하게 추가합니다.
- MySQL 환경에서 `ADD COLUMN IF NOT EXISTS` 사용이 제한되면 Workbench에서 컬럼 존재를 확인 후 수동 실행합니다.
- 1.2 초안: `risk_keywords.py`로 위험/교환 키워드 그룹을 카테고리 단위로 관리합니다.
- 1.2 초안: `risk_analyzer.py`에서 교환글/위험 키워드를 점수화(`none/low/medium/high/exclude`)합니다.
- 1.2 초안: `/analyze-url` 응답에 `risk_level`, `risk_score`, `risk_categories`, `trade_type`를 포함합니다.
- 1.2 초안: Telegram 알림 제목에 `[주의 필요]`, `[교환글]`, `[제외급 위험]` prefix를 조건부로 붙입니다.
- 1.2 초안: `sql/add_risk_exchange_columns.sql`로 `url_analysis_logs`에 위험/교환 로그 컬럼을 추가합니다.
- 1.3 초안: Android Notification Listener 없이도 서버에서 중고나라 Search API polling만으로 동작할 수 있습니다.
- 1.3 초안: `sql/create_joongna_seen_products.sql`로 `seq` 기준 중복 제거 테이블을 추가합니다.
- 1.3 초안: Search API 응답의 `url`은 이미지 URL로 저장하고, 실제 매물 URL은 `https://web.joongna.com/product/{seq}`로 생성합니다.
- 1.3 초안: 고정 기본 검색어 polling은 제거되었고, 앱에서 활성화된 사용자 설정 검색어만 대상으로 `joongna_seen_products` 상태 비교 후 신규/변경 매물만 기존 UMTP rule-based URL 분석 흐름으로 전달합니다.
- 1.3 진행 현황: 중고나라 끌올/가격변경 감지 구조를 추가했습니다.
- 1.4 초안: Android 앱에서 `POST /users/register`로 `user_id + device_id(Android ID)` 쌍이 모두 일치할 때만 로그인/등록됩니다.
- 1.4 초안: Android 앱에서 모델별 `enabled(on/off)`, 공정가, 차이비율 설정을 저장할 수 있습니다.
- 1.4 초안: 설정 저장은 맥미니 서버의 MySQL(`user_fair_prices`)에 즉시 반영됩니다.
- 1.4 초안: Telegram 기능은 삭제하지 않고 기존 동작을 그대로 유지합니다.
- 1.4 초안: 이번 패치는 FCM/앱 푸시 자체를 구현하지 않습니다.
- 1.4 초안: 이번 패치는 Android UI를 구현하지 않습니다.
- 1.5 진행 현황: `user_fair_prices(enabled)` 기반 polling 대상 설정 구조를 추가했습니다.
- 1.5 역할 분리 변경: 감시 조건 테이블(`user_watch_rules`)을 분리하지 않고 `user_fair_prices`에 검색어/폴링 상태 컬럼을 함께 사용합니다.
- 1.5 polling 규칙: `--search-word`가 있어도 DB due 대상(`enabled=true`, `last_poll_requested_at IS NOT NULL`) 안에 있는 검색어만 실행하며, due 대상이 없으면 polling은 스킵합니다.
- 1.6 진행 현황: 설정 저장 시 `force_poll=true`로 즉시 polling 요청하는 구조를 추가했습니다.
- 1.6 polling 규칙: `force_poll=true` 또는 `last_polled_at IS NULL`이면 즉시 검색하고, 검색 완료 후 `force_poll=false`와 `last_polled_at=NOW()`로 갱신합니다.
- 1.6 CLI 규칙: `--search-word` 수동 실행은 DB `force_poll` 요청 상태를 소비하지 않습니다.
- 1.7 진행 현황: Android 앱에서 검색어/공정가/알림기준을 설정에 직접 저장하고 `user_fair_prices(enabled)` 기반 polling 대상으로 즉시 반영할 수 있습니다.
- 1.7 백엔드 API: `GET /user-fair-prices/recommended-keywords`, `POST /user-fair-prices/upsert`.
- 1.7 polling 규칙: 검색어는 후보 수집용이며 최종 알림 대상은 스펙 파싱 결과 + 사용자 설정 공정가/알림기준으로 결정합니다.
- 1.8 진행 현황: polling은 감지된 매물을 `analysis_jobs`에 enqueue하고, analysis worker가 pending job을 처리해 `listing_analysis_results` 및 `alert_events`를 생성합니다.
- 1.8 polling 구조: 같은 `source + search_keyword`는 같은 polling cycle에서 외부 Search API를 1회만 호출하고, 결과를 저장한 뒤 여러 설정(`user_fair_prices`)은 저장 결과를 내부 매칭으로 공유합니다.
- 1.8 검색 캐시 구조: 공유 polling 결과는 `search_queries`(검색어 스코프) + `search_results`(조회 결과 스냅샷) 테이블에도 저장됩니다.
- 1.8 중고나라 판매자명 구조: Search API 응답에는 판매자 닉네임 필드가 직접 없고 `storeSeq`만 내려올 수 있습니다.
- 1.8 판매자 프로필 조회: `storeSeq`가 있으면 `GET https://main-api.joongna.com/v2/my-store/{storeSeq}`를 추가 호출해 `storeName`을 판매자 표시 이름으로 저장합니다.
- 1.8 장애 허용 정책: `my-store` 조회 실패는 전체 polling/analysis 실패로 처리하지 않고 seller 컬럼은 `NULL`로 저장하며 warning 로그만 남깁니다.
- 1.8 변경 감지 스킵 구조: `joongna_seen_products`의 이전 관측값과 현재 관측값을 비교해 `new/sort_date_changed/price_changed/title_changed/refresh_key_changed/body_maybe_changed`만 분석 큐로 보내고, `unchanged`는 분석을 스킵합니다.
- 1.8 lazy detail fetch 구조: analysis worker는 모든 매물의 상세본문을 조회하지 않고, `new/저가 후보/제목 파싱 실패/제품명만 있고 스펙 부족` 후보에만 상세조회(fetch_html)를 수행합니다.
- 1.8 알림 속도(priority) 구조: watch_rule(`user_fair_prices`)마다 `priority=FAST/NORMAL/LOW`를 저장하고, polling scheduler는 priority 기준 기본 주기(45/180/600초)에 ±20% jitter를 적용해 다음 조회 시점을 계산합니다.
- 1.8 변경 로그: polling 요약에 `fetched_count/new_count/changed_count/unchanged_skipped_count/analyzed_count/alert_created_count`를 함께 기록합니다.
- 1.8 알림 구조: notification worker가 `alert_events` pending을 읽어 Telegram 전송(`sent`) 또는 앱 피드 전용 상태(`app_only`)로 처리합니다.
- 1.8 운영 구조: polling은 enqueue 전용이며, analysis는 `run_analysis_worker_umtp.py`, Telegram 전송은 `run_notification_worker_umtp.py` 전용 worker로 처리합니다.
- identity 정책: `analysis_jobs`/`alert_events`의 중복 기준은 `(user_id, watch_rule_id, product_id, sort_date)`입니다.
- saved_at 정책: UMTP는 사용자가 저장한 시각(`saved_at`) 이후에 등록된 매물(`sort_date >= saved_at`)만 알림 후보로 봅니다.
- 재저장 정책: 같은 저장 조건에서 저장 버튼을 다시 누르면 `saved_at`이 현재 시각으로 갱신되고, 그 시점부터 새로 조회를 시작합니다.
- 새로고침 정책: 새로고침은 저장 조건의 `saved_at`을 현재 시각으로 갱신합니다. 전체 새로고침은 활성 규칙 전체를, 단일 새로고침은 선택한 규칙 하나만 갱신합니다. 새로고침 후 UMTP는 `sort_date >= saved_at` 인 매물만 정식 알림 후보로 봅니다.
- 조건 변경 참고 메시지 정책: 조건을 다시 저장할 때 이전 `saved_at`과 새 `saved_at` 사이에 등록된 매물 중 새 조건에는 맞지만 이전 조건에는 맞지 않았던 매물은 참고 메시지로 생성됩니다. 이 참고 메시지는 `alert_events.status='pending'`으로 저장되어 일반 알림 전송 루트(앱/텔레그램)로도 전달될 수 있습니다. 정식 알림 기준은 항상 `sort_date >= 현재 saved_at` 입니다.
- 참고 메시지 생성 시 `alert_events`/`url_analysis_logs`를 조회해 위험도·위험점수·위험키워드·교환여부·본문·분석시각을 가능한 범위에서 채워 일반 알림 카드와 유사한 정보 밀도를 유지합니다.
- 재알림 정책: 같은 `product_id`라도 `sort_date`가 바뀐(끌올/재등록) 경우 사용자/규칙 기준으로 재알림 가능합니다. 단, 같은 사용자/같은 규칙/같은 `product_id`/같은 `sort_date` 조합 알림은 한 번만 보냅니다.
- 마이그레이션: 기존 운영 DB는 `sql/migrate_realert_identity_sort_date.sql`을 실행해 `(user_id, watch_rule_id, product_id, sort_date)` 기준 unique key를 반영합니다.
- Telegram 발송 기준: 새 `alert_events` insert 성공 시 1회만 발송됩니다.
- 1.10 진행 현황: Android FCM 푸시를 위한 `POST /users/{user_id}/push-token` API와 `user_push_tokens` 저장소를 추가했습니다.
- 1.10 알림 전달 정책: notification worker는 사용자 활성 푸시 토큰이 있으면 FCM 푸시를 우선 시도하고, Telegram은 기존 정책대로 병행 처리합니다. 둘 다 실패하면 `failed`, 둘 다 전송 채널이 없으면 `app_only`로 남습니다.
- 1.9 진행 현황: Android 설정 화면에서 사용자는 차이비율을 직접 입력하지 않고 `내 기준 적정 가격`과 `내가 사고 싶은 가격`만 입력합니다.
- 1.9 자동 계산: 앱이 할인 정도를 읽기 전용 설명으로 표시하고, 최종 기준은 서버 응답 `alert_drop_rate_percent`를 사용합니다.
- 1.9 검색어 UX: 검색어를 직접 입력하거나 추천 검색어를 불러와 선택할 수 있습니다.
- 1.9 저장 동작: 저장 시 `user_fair_prices`에 반영되고 즉시 검색 요청(`force_poll`)이 걸리며, 설정 토글 자체가 감시 on/off 역할을 합니다.

## 빠른 시작

### 1) 설치 방법

```bash
pip install -r requirements.txt
```

### 2) 환경변수 설정

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
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
UMTP_ALLOW_GLOBAL_TELEGRAM_FALLBACK=false
FIREBASE_SERVICE_ACCOUNT_FILE=
FIREBASE_SERVICE_ACCOUNT_JSON=
FIREBASE_PROJECT_ID=
```

### 3) 테이블 생성 방법

아래 SQL을 실행해서 DB/테이블을 생성하세요.

```bash
mysql -u <DB_USER> -p < sql/init_mvp_tables.sql
```

`sql/init_mvp_tables.sql`은 다음을 수행합니다.
- `mac_fair_prices` 테이블 생성
- `listing_analysis_results` 테이블 생성
- MacBook Air M1 13인치 8GB RAM 256GB SSD 공정가 550000원 upsert(중복 방지)

### 4) 실행 방법

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

### 5) 주의사항

`.env`에는 실제 DB 비밀번호 등 민감 정보가 들어갑니다.  
`.env` 파일은 절대 git에 올리지 마세요.

---

## 버전별 상세 이력

### UMTP 2차 MVP

2차 MVP에서는 가짜 매물 고정값 대신, 사용자가 터미널에서 매물 제목/가격을 직접 입력합니다.  
입력값을 바탕으로 DB에 저장된 공정가와 비교 분석하고, 결과를 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

#### 1) 실행 방법

```bash
python src/run_manual_umtp.py
```

실행 후 아래처럼 입력합니다.

```text
매물 제목 입력: 맥북에어 M1 8GB 256GB 급처
매물 가격 입력: 430000
```

#### 2) 동작 규칙

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

#### 3) 예상 출력

```text
공정가: 550000원
매물가: 430000원
차이금액: 120000원
차이비율: 21.8%
결과: 알림 대상
DB 저장 완료
```

---

### UMTP 3차 MVP

3차 MVP에서는 사용자가 입력한 매물 제목에서 제품 스펙을 자동 추출한 뒤,  
DB 공정가와 비교 분석하고 결과를 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

#### 1) 실행 방법

```bash
python src/run_title_parse_umtp.py
```

실행 후 아래처럼 입력합니다.

```text
매물 제목 입력: 맥북에어 M1 8GB 256GB 급처
매물 가격 입력: 430000
```

#### 2) 동작 규칙

- 제목 파싱: `parse_listing_title(title)` 사용
- 지원 대상: `MacBook Air`, `M1`, `13인치`, `8GB/8기가`, `256GB/256기가`
- 스펙 추출 실패 시: 실패 항목 출력 후 종료
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율이 `20` 이상이면 알림 대상
- 분석 결과 저장: `listing_analysis_results`

#### 3) 예상 출력

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

### UMTP 4차 MVP

4차 MVP에서는 여러 테스트 매물을 한 번에 분석합니다.  
각 매물 제목에서 스펙을 추출하고 DB 공정가와 비교해 알림 대상 여부를 판단한 뒤,  
성공 건은 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

#### 1) 실행 방법

```bash
python src/run_batch_umtp.py
```

#### 2) 동작 규칙

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

#### 3) 예상 출력

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

### UMTP 5차 MVP

5차 MVP에서는 CSV 파일에서 여러 매물 목록을 읽어 일괄 분석합니다.  
각 매물 제목에서 스펙을 추출하고 DB 공정가와 비교해 알림 대상 여부를 판단한 뒤,  
성공 건은 `listing_analysis_results`에 저장합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

#### 1) 실행 방법

```bash
python src/run_csv_umtp.py
```

#### 2) 동작 규칙

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

#### 3) 예상 출력

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

### UMTP 6차 MVP

6차 MVP에서는 크롤링 결과 형태의 JSON 파일에서 여러 매물 목록을 읽어 일괄 분석합니다.  
아직 실제 중고나라 크롤링은 하지 않고, JSON 샘플 데이터 기반으로만 분석합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

#### 1) 실행 방법

```bash
python src/run_json_umtp.py
```

#### 2) 동작 규칙

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

#### 3) 예상 출력

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

### UMTP 7차 MVP

7차 MVP에서는 사용자가 입력한 실제 중고나라 URL 1개에서 HTML을 읽고,  
제목/본문/가격을 자동 추출한 뒤 스펙 파싱까지 연결합니다.

1차와 동일하게 설치/환경변수 설정/테이블 생성/주의사항을 적용합니다.

#### 1) 실행 방법

```bash
python src/run_url_parse_umtp.py
```

실행 후 아래처럼 URL만 입력합니다.

```text
매물 URL 입력: https://web.joongna.com/product/228451872
```

#### 2) 동작 규칙

- 사용자 입력: URL 1개만 입력
- 0.7은 아직 중고나라 전체 검색 크롤링을 하지 않음
- HTML 요청: `requests.get(url)` + `User-Agent` + `timeout`
- HTML 파싱: `BeautifulSoup`
- 0.7 구현을 위해 의존성 `requests`, `beautifulsoup4`를 requirements에 추가
- 제목 추출: `meta name="twitter:title"`의 `content`
- 본문 추출: `meta name="twitter:description"`의 `content`
- 가격 추출: `whitespace-pre-line`, `text-32`, `font-bold`, `max-md:text-24` class 토큰을 모두 포함한 `span`
- 셀프검수 추출(선택): `dl` 내부 `dt/dd`에서 모델명/램 용량/SSD용량/CPU종류/컬러를 우선 추출
- 셀프검수 영역이 없으면 기존처럼 `title + description`만으로 스펙 파싱
- 가격 변환: 숫자만 추출해 `int`로 변환 (`550,000원` -> `550000`)
- 가격 추출 실패 시: `가격 추출 실패` 메시지를 출력하고 DB 저장하지 않음
- 스펙 추출: `parse_listing_title(title + " " + description, self_check_fields=...)` 재사용
- 공정가 조회: `mac_fair_prices`
- 차이금액: `공정가 - 매물가`
- 차이비율: `(차이금액 / 공정가) * 100`
- 알림 기준: 차이비율 `20` 이상
- 분석 결과 저장: `listing_analysis_results`
- 출력 항목: 제목, 본문 일부, 가격, 스펙, 분석 결과, `source`, `url`

#### 3) 예상 출력

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

### UMTP 8차 MVP

8차 MVP에서는 Android Notification Listener 앱이 URL을 보낸다고 가정하고,  
URL 수신 API에서 사용자별 공정가 기준 분석을 수행합니다.

이번 단계는 Android 앱 자체를 구현하지 않고, `curl` 요청으로 URL 전달 상황을 흉내냅니다.  
실제 텔레그램 전송은 하지 않으며 `notifier.py`의 `print()` 알림으로 대체합니다.

#### 1) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

#### 2) 요청 예시(curl)

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "url": "https://web.joongna.com/product/228451872"
  }'
```

#### 3) 동작 규칙

- 엔드포인트: `POST /analyze-url`
- 입력: `user_id`, `url`
- URL HTML 파싱: `listing_page_parser.py` 재사용
- 스펙 추출: `parse_listing_title(title + " " + description, self_check_fields=...)` 재사용
- 사용자 공정가 조회: `user_fair_prices` (`fair_price_krw`, `alert_drop_rate_percent`)
- 분석 결과 저장: `listing_analysis_results`
- 알림 대상이면 `notifier.py`의 `send_alert(message)` 호출 (`print()` 기반)
- 실패 응답 형식: `{"ok": false, "reason": "..."}`
- 0.8 구현을 위해 `requirements.txt`에 `fastapi`, `uvicorn`을 추가

---

### UMTP 9차 MVP

9차 MVP에서는 Telegram 알림, 중복 URL 재분석 방지, 분석 로그 안정 저장을 추가합니다.

#### 1) 추가 SQL 실행

```bash
mysql -u <DB_USER> -p < sql/add_url_analysis_logs.sql
```

#### 2) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

#### 3) .env 설정

`.env`에 아래 값을 설정합니다.

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

실제 비밀값은 `.env`에만 저장하고 Git에는 올리지 않습니다.

#### 4) 테스트(curl)

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

#### 5) 동작 규칙

- 같은 `user_id + url`이 `success/failed/duplicate`로 이미 기록되면 재분석하지 않습니다.
- 중복 요청은 `ok=true`, `status="duplicate"`, `message="이미 분석된 URL"`로 응답합니다.
- `url_analysis_logs`에 `success/failed/duplicate`를 모두 저장합니다.
- 알림 대상일 때만 Telegram Bot API `sendMessage`를 호출합니다.
- 텔레그램 설정이 없으면 서버는 죽지 않고 `텔레그램 설정 없음`을 출력합니다.

---

### UMTP 1.0 MVP

1.0 MVP에서는 전체 실리콘 MacBook Air 유효 조합을 정의하고,  
rule-based 공정가를 `user_fair_prices`에 자동 반영하는 seed 흐름을 추가합니다.

#### 1) 실행 방법

```bash
python src/seed_user_fair_prices.py
```

#### 2) SQL seed 방법

```bash
mysql -u <DB_USER> -p < sql/seed_macbook_air_units.sql
```

#### 3) 동작 규칙

- `macbook_air_units.py`에서 유효 조합과 rule-based 공정가 계산을 관리합니다.
- 공정가는 실제 시세가 아닌 MVP용 임시 기준값입니다.
- `spec_parser.py`는 MacBook Air 스펙 파싱 후 유효 조합을 검증합니다.
- 유효하지 않은 조합은 `invalid_macbook_air_unit`으로 실패 처리됩니다.
- `/analyze-url` 요청 형식은 그대로 유지되며, 응답에 `unit_valid`, `unit_validation_reason`이 포함됩니다.

---

### UMTP 1.1 MVP

1.1 MVP에서는 HTML 전체 텍스트를 파싱하지 않고,  
제목/본문/가격/셀프검수 영역만 사용해 스펙을 추출합니다.

#### 1) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

#### 2) 요청 예시(curl)

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "url": "https://web.joongna.com/product/228436846"
  }'
```

#### 3) 추가 SQL 실행

```bash
mysql -u <DB_USER> -p < sql/add_parser_confidence_columns.sql
```

#### 4) 동작 규칙

- 셀프검수는 `dl/dt/dd` 구조를 key-value로 파싱해 `self_check_fields`로 저장합니다.
- `self_check_fields` 값(모델명/CPU종류/램 용량/SSD용량)을 제목/본문 파싱보다 우선합니다.
- 부족한 항목만 `numeric_candidate_extractor.py`로 제목+본문 숫자 후보를 보조 파싱합니다.
- 숫자 후보 분리 규칙: 화면 `13/15`, RAM `8/16/24/32`, SSD `256/512/1024/2048/4096`.
- `1/2/4`는 단독 숫자로 SSD 후보에 넣지 않고 `1TB/2TB/4TB`(`t/테라`)일 때만 `1024/2048/4096`으로 변환합니다.
- MacBook Air 제목/본문에 정확히 `기본형` 또는 `깡통` 표현이 있고 칩이 파싱되면, RAM/SSD 누락 시 최소 스펙 fallback을 적용합니다.
- 최소 스펙 fallback은 hardcoded 값이 아니라 `macbook_air_units.py`의 유효 조합 테이블에서 `chip + screen` 기준 최소 valid RAM/SSD를 계산해 사용합니다.
- RAM/SSD 숫자가 명시된 경우 명시값이 fallback보다 항상 우선합니다(누락된 필드만 fallback으로 보정).
- `screen_inch`를 찾지 못하면 13인치 기본값을 사용하고 `screen_inch_defaulted=true`로 반환합니다.
- `confidence_score`는 product/chip/ram/ssd/screen 추출 확실도를 0~100 점수로 반환합니다.
- `parse_success=false`이면 공정가 조회를 중단하고 `missing_fields`, `unit_validation_reason`를 응답에 포함합니다.
- MySQL 환경에서 `ADD COLUMN IF NOT EXISTS`가 제한되면 Workbench에서 컬럼 존재 확인 후 수동 실행합니다.

---

### UMTP 1.2 MVP

1.2 MVP에서는 위험 키워드 점수화와 교환글 탐지를 추가해  
API 응답/알림에 위험도를 함께 제공합니다.

#### 1) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

#### 2) 추가 SQL 실행

```bash
mysql -u <DB_USER> -p < sql/add_risk_exchange_columns.sql
```

#### 3) 동작 규칙

- 위험도는 `none / low / medium / high / exclude` 단계로 분류합니다.
- 제목+본문+셀프검수 value를 함께 검사해 위험/교환 키워드를 탐지합니다.
- 교환 강키워드(negation 없음) 또는 약키워드가 있으면 교환글로 판정합니다.
- 위험/교환이 있어도 공정가 비교 분석은 계속 수행합니다.
- Telegram 알림은 위험도에 따라 `[주의 필요]`, 교환글이면 `[교환글]`, 제외급이면 `[제외급 위험]` prefix를 붙입니다.
- MySQL 환경에서 `ADD COLUMN IF NOT EXISTS`가 제한되면 Workbench에서 컬럼 존재를 확인한 뒤 수동 실행합니다.

---

### UMTP 1.3~1.8 운영 MVP

1.3 MVP에서는 Android Notification Listener 없이,  
중고나라 Search API polling으로 새 매물을 감지해 기존 URL 분석 흐름으로 연결합니다.

#### 1) 추가 SQL 실행

```bash
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/create_joongna_seen_products.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/alter_joongna_seen_products_refresh_detection.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/alter_user_fair_prices_polling_keywords.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_user_fair_prices_search_keyword_format.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_target_buy_price_generated_column.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/create_analysis_jobs.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_analysis_jobs_lookup_indexes.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/create_or_alter_alert_events.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_alert_read_archive_events_log.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_alert_read_archive_events_detail_fields.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_user_push_tokens.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/alter_listing_analysis_results_pipeline.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_identity_user_product.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_joongna_sort_date_tracking.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_search_query_results_cache.sql
# heartbeat 롤백(066b3e5 제거) 시에만 실행
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_remove_worker_heartbeats.sql
```

적용 확인:

```sql
SHOW INDEX FROM analysis_jobs;

EXPLAIN
SELECT *
FROM analysis_jobs
WHERE user_id = 'boongtol'
  AND source = 'joongna'
  AND search_keyword = 'm2 맥북에어'
  AND created_at >= '2026-05-20 15:00:00'
  AND created_at < '2026-05-20 16:00:00';
```

#### 2) 실행 방법

```bash
python src/run_joongna_polling_umtp.py --once
python src/run_joongna_polling_umtp.py --interval 60
python src/run_analysis_worker_umtp.py --once
python src/run_analysis_worker_umtp.py --interval 5
python src/run_notification_worker_umtp.py --once
python src/run_notification_worker_umtp.py --interval 3
```

특정 검색어만 실행:

```bash
python src/run_joongna_polling_umtp.py --once --search-word m1맥북에어
```

#### 3) 동작 규칙

- 중고나라 Search API polling 기반으로 `m1~m5맥북에어` 검색 결과를 조회합니다.
- Search API `sort=RECENT_SORT` 응답의 `sortDate`를 수집합니다.
- polling 대상 선정은 `user_fair_prices(enabled=true AND last_poll_requested_at IS NOT NULL)`를 사용합니다.
- `enabled=true` 대상이 없으면 polling은 검색 자체를 실행하지 않고 스킵합니다.
- `DEFAULT_SEARCH_WORDS(m1~m5맥북에어)` + `test_user` fallback 검색은 제거되었습니다.
- analysis identity는 `(user_id, product_id)`입니다. 같은 사용자/같은 매물 enqueue가 반복되어도 `analysis_jobs`는 1개만 유지됩니다.
- alert identity는 `(user_id, product_id)`입니다. 같은 사용자/같은 매물은 `alert_events` 1개만 생성됩니다.
- 같은 `seq(product_id)`의 `sortDate`가 바뀌면 `sort_date_changed`로 판단하고 재분석 enqueue합니다.
- `sortDate` 변경 원인은 끌올/수정/재노출일 수 있으며, UMTP에서는 공통으로 "다시 최신순으로 올라온 매물"로 처리합니다.
- `productPositionNo`/rank 기반 끌올 추정은 사용하지 않습니다.
- Telegram 발송 기준은 job 완료가 아니라 `alert_events` 신규 insert 성공입니다.
- Telegram 발송은 `user_id`별 알림 토글(enabled=true)일 때만 허용됩니다.
- `users.telegram_chat_id`가 있으면 해당 사용자 채팅으로 발송하고, 없으면 앱 피드 상태만 갱신(`app_only`)합니다.
- 전역 `TELEGRAM_CHAT_ID` fallback은 deprecated이며 기본 비활성(`UMTP_ALLOW_GLOBAL_TELEGRAM_FALLBACK=false`)입니다.
- 공정가/알림 기준은 `user_fair_prices` override 우선, 없으면 `mac_fair_prices` fallback 순서입니다.
- 두 테이블 모두 기준값이 없으면 alert를 만들지 않고 `fair_price_missing`으로 처리합니다.
- 설정 저장 시 `enabled=true`이면 `force_poll=true`, `last_poll_requested_at=NOW()`, `last_polled_at=NULL`이 되어 즉시 due 대상이 됩니다.
- polling worker는 due 설정을 읽어 검색하며, 같은 검색어를 여러 사용자가 켜도 Search API는 검색어당 1회만 호출합니다.
- polling worker는 조회한 그룹 결과를 `search_queries`/`search_results`에도 저장해 후속 집계와 디버깅에 재사용할 수 있습니다.
- 참고 알림/놓친 후보 집계 성능을 위해 `analysis_jobs`에 `(user_id, source, search_keyword, created_at)` 및 `(user_id, source, search_keyword, product_id, created_at)` 조회 인덱스를 적용합니다.
- 알림 속도(priority)는 UI에 `빠름/보통/절전`으로 표시되며 내부값은 `FAST/NORMAL/LOW`를 사용합니다.
- priority별 기본 주기는 `FAST=45초`, `NORMAL=180초`, `LOW=600초`입니다.
- scheduler는 priority별 기본 주기에 jitter(±20%)를 적용해 실제 주기를 계산합니다. 예: `FAST 약 36~54초`, `NORMAL 약 144~216초`, `LOW 약 480~720초`.
- 운영 DB는 `sql/migrate_watch_rule_priority_polling.sql` 실행으로 `priority` 컬럼을 추가하고 기존 값을 `NORMAL`로 보정합니다.
- `POST /user-fair-prices/upsert`에서 `search_keyword`를 비우면 스펙 기반 기본 검색어(예: `m1맥북에어`)를 자동 생성합니다.
- `GET /user-fair-prices/recommended-keywords`로 Android 앱에서 추천 검색어를 받아 선택할 수 있습니다.
- polling worker는 `force_poll=true`인 설정을 우선 due로 처리하고, 검색 완료 후 `force_poll=false`, `last_polled_at=NOW()`로 갱신합니다.
- `joongna_seen_products`는 단순 중복 차단이 아니라 마지막 관측 상태 저장용으로 사용합니다.
- 같은 `product_id/seq`라도 가격/제목/`refresh_key`가 바뀌면 재분석합니다.
- 완전히 동일한 상태(`unchanged`)면 `last_seen_at`, `seen_count`만 갱신하고 중복 분석/중복 알림을 막습니다.
- analysis worker는 상세조회가 필요한 후보 매물에서만 상세페이지/본문을 조회하고, `unchanged`는 상세조회와 분석을 모두 스킵합니다.
- Search API 응답의 `url` 필드는 이미지 URL로 저장하며, 실제 매물 URL은 `https://web.joongna.com/product/{seq}`로 생성합니다.
- 같은 검색어를 쓰는 여러 설정/user는 검색 결과를 공유합니다.
- 재분석 이유는 `joongna_seen_products.last_change_reason`에서 확인합니다.
- CLI `--search-word` 실행은 `force_poll` 상태를 false로 바꾸지 않으며, DB 즉시요청 상태는 유지됩니다.
- 개별 API 실패/JSON 구조 변경/개별 매물 분석 실패가 있어도 polling 루프는 계속 동작합니다.
- `/alerts?user_id=...` API는 `alert_events`를 최신순(`created_at DESC`)으로 반환하며 Android 알림 피드에서 사용할 수 있습니다.
- `watch_rule_id` 컬럼은 deprecated 메타데이터로 유지하며 drop하지 않습니다.
- `user_watch_rules` fanout 기반 job 생성은 현재 구조에서 사용하지 않습니다.

#### 4) Docker 분리 실행 예시

```bash
docker build -t umtp .

docker run -d --name umtp-api --restart unless-stopped --env-file .env -p 8000:8000 umtp uvicorn src.api_server:app --host 0.0.0.0 --port 8000

docker run -d --name umtp-polling --restart unless-stopped --env-file .env umtp python src/run_joongna_polling_umtp.py --interval 60

docker run -d --name umtp-analysis --restart unless-stopped --env-file .env umtp python src/run_analysis_worker_umtp.py --interval 5

docker run -d --name umtp-notification --restart unless-stopped --env-file .env umtp python src/run_notification_worker_umtp.py --interval 3
```

로그 확인:

```bash
docker logs -f umtp-api
docker logs -f umtp-polling
docker logs -f umtp-analysis
docker logs -f umtp-notification
```

컨테이너 역할:
- `umtp-api`: Android/iOS API 서버(FastAPI)
- `umtp-polling`(market-watcher): 중고나라 polling + `analysis_jobs` enqueue 전용
- `umtp-analysis`(analysis-worker): `analysis_jobs` pending 처리 전용
- `umtp-notification`(notification-worker): `alert_events` pending Telegram/app 상태 처리 전용

#### 5) 검증 체크리스트

```bash
# 1) 중복 enqueue: 같은 product_id 반복 enqueue 시 analysis_jobs 1건 유지
python src/run_joongna_polling_umtp.py --once --search-word m1맥북에어

# 2) analysis worker 처리
python src/run_analysis_worker_umtp.py --once

# 3) notification worker 처리 (중복 Telegram 방지)
python src/run_notification_worker_umtp.py --once
```

검증 포인트:
- 같은 `user_id + product_id`를 여러 번 enqueue해도 `analysis_jobs`는 1개만 존재
- 같은 `user_id + product_id`는 `alert_events` 1개만 생성
- analysis worker 2개/notification worker 2개 동시 실행에서도 Telegram은 1회만 전송
- `enabled=false` 사용자 alert는 Telegram을 보내지 않고 `app_only`로 남음
- `users.telegram_chat_id`가 없는 사용자 alert는 Telegram을 보내지 않고 `app_only`로 남음
- 공정가 조회는 `user_fair_prices` override 우선
- override가 없으면 `mac_fair_prices` fallback 사용
- 둘 다 없으면 `fair_price_missing`으로 alert 미생성


---

### UMTP 1.4 MVP (설정 API 상세 참고)

1.4 MVP에서는 Android 앱이 사용자별 MacBook Air 설정을 서버 API로 저장/조회할 수 있도록,
`users` 등록 API와 `user_fair_prices` 기반 설정 API를 추가합니다.

#### 1) 추가 SQL 실행

```bash
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/create_users_table.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/add_users_device_id_column.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/drop_users_nickname_column.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/add_user_fair_price_settings_columns.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/alter_user_fair_prices_polling_keywords.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/migrate_user_fair_prices_search_keyword_format.sql
mysql -u <DB_USER> -p -h <DB_HOST> UMTP_RB < sql/add_user_settings_save_logs.sql
```

`sql/add_user_fair_price_settings_columns.sql`은 `enabled`, `updated_at` 컬럼 추가를 시도합니다.
`sql/alter_user_fair_prices_polling_keywords.sql`은 `search_keyword`, `poll_interval_seconds`, `force_poll`, `last_poll_requested_at`, `last_polled_at` 컬럼과 인덱스를 추가합니다.
`sql/migrate_user_fair_prices_search_keyword_format.sql`은 기존 기본 검색어를 `m1 맥북에어` / `m2pro 맥미니` 형태로 정규화(backfill)합니다.
MySQL 환경에서 `ADD COLUMN IF NOT EXISTS`가 제한되면, 컬럼 존재 여부를 먼저 확인한 뒤 수동 실행하세요.
`sql/add_users_device_id_column.sql`은 `users.device_id` 컬럼과 unique index를 안전하게 추가합니다.
`sql/drop_users_nickname_column.sql`은 users 테이블의 `nickname` 컬럼이 남아 있을 때만 삭제합니다.
`sql/add_user_settings_save_logs.sql`은 설정 저장 요청/응답/부분실패 정보를 추적하는 `user_settings_save_logs` 테이블을 생성합니다.

#### 2) 실행 방법

```bash
uvicorn src.api_server:app --reload
```

#### 3) API 테스트(curl)

MacBook Air unit 목록 조회:

```bash
curl http://127.0.0.1:8000/macbook-air-units
```

사용자 등록:

```bash
curl -X POST http://127.0.0.1:8000/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "boongtol",
    "device_id": "android-1234567890abcdef"
  }'
```

사용자별 설정 조회:

```bash
curl "http://127.0.0.1:8000/user-fair-prices?user_id=boongtol"
```

사용자별 설정 저장:

```bash
curl -X POST http://127.0.0.1:8000/user-fair-prices/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "boongtol",
    "product_type": "MacBook Air",
    "chip": "M1",
    "screen_inch": 13,
    "ram_gb": 8,
    "ssd_gb": 256,
    "fair_price_krw": 600000,
    "alert_drop_rate_percent": 15,
    "enabled": true,
    "search_keyword": "m1맥북에어",
    "poll_interval_seconds": 60
  }'
```

추천 검색어 조회:

```bash
curl "http://127.0.0.1:8000/user-fair-prices/recommended-keywords?product_type=MacBook%20Air&chip=M1&ram_gb=8&ssd_gb=256"
```

#### 4) 동작 규칙

- `GET /macbook-air-units`: 104개 MacBook Air 단위 조합을 `chip -> screen_inch -> ram_gb -> ssd_gb` 순으로 반환합니다.
- `GET /user-fair-prices`: 전체 단위 목록 기준으로 system/user/effective 값을 함께 반환합니다.
- 각 설정 항목은 `custom_search_keyword`, `recommended_search_keyword`, `effective_search_keyword`를 함께 반환합니다.
- user override가 없는 단위는 `enabled=false`를 기본값으로 반환합니다.
- `POST /users/register`: `device_id`가 이미 등록되어 있으면 저장된 기존 `user_id`로 로그인 처리합니다.
- `POST /user-fair-prices/upsert`: `user_id + product_type + chip + screen_inch + ram_gb + ssd_gb` 복합 키 기준 upsert를 수행합니다.
- `enabled=true` 저장 시 해당 설정 행이 즉시 polling 대상(`force_poll=true`)이 됩니다.
- 유효하지 않은 조합은 `invalid_macbook_air_unit`으로 거부합니다.
- 기존 `/analyze-url` 요청 형식은 변경하지 않습니다.
- polling 흐름과 Android Notification Listener 관련 내용은 이번 패치에서 크게 변경하지 않습니다.
