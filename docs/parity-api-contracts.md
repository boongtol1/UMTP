# Android → iOS API 계약 조사

조사일: 2026-09-15. 기준은 작업 시작 시 저장소 코드이며 기준 SHA/브랜치와 구현·검증 상태의 최종 집계는 `android-ios-parity.md`를 따른다. 이 문서는 정적 계약 조사 결과이며 실제 서비스 요청/DB 검증을 수행했다는 의미가 아니다.

## 근거와 공통 계약

- Android API: `android/app/src/main/java/com/boongtol/umtp_android/network/UmtpApiService.kt`(34개 suspend 선언), DTO: 같은 디렉터리의 `*Models.kt`.
- 활성 호출/사용자 흐름: `ui/MacBookAirSettingsViewModel.kt`, `MainActivity.kt`, `ui/ResaleTradeInputScreen.kt`, `fcm/PushTokenManager.kt`.
- 서버 라우트: `umtp/src/api_server.py`, 구현: `user_settings_service.py`, `notification_worker.py`, `resale_trade_journeys.py`, `push_token_service.py`, `alert_price_direction.py`.
- 기존 iOS: `Services/UserAPI.swift`만 등록 API 연동. `AlertPollingService.start`는 상태 bool만 변경하고 실제 polling은 TODO. `Models/AlertModels.swift`(id/title/message/createdAt), `UserFairPriceModels.swift`(id/symbol/fairPrice)는 서버 형식과 불일치. 메인·설정은 Stage1 placeholder.
- Base URL은 Android `BuildConfig.UMTP_BASE_URL`, 기본 HTTPS DuckDNS. iOS 설정값은 `App/AppConfig.swift`. Android connect=15/read=30/write=30초. Android 시스템 DNS 실패 시 지정 호스트에 DoH fallback이 있지만 iOS URLSession은 시스템 DNS를 사용한다.
- 인증 헤더/JWT/access·refresh token/session expiry API는 없다. `user_id`를 body/query/path로 전송한다. 등록은 `user_id + device_id` 일치 검사이며 나머지 API는 등록 사용자 존재만 확인한다. iOS가 임의의 인증 토큰을 추가하거나 재등록으로 사용자 ID를 바꾸면 안 된다.
- 성공/실패는 HTTP 상태와 별도로 `{ok:true|false,message?,reason?}`를 확인해야 한다. 대부분 비즈니스 실패는 HTTP 200/ok:false, Pydantic 입력 오류는 HTTP 422. 내부 예외 문자열을 reason에 포함하는 서버 경로가 있어 원문을 사용자에게 그대로 노출하지 않는다.
- nullable 필드는 누락/null 가능. Android boolean adapter는 bool/0·1/"true"·"false"·"yes"·"no"·"y"·"n"·"on"·"off"를 지원한다. MySQL 결과 수치는 Int/Double/Decimal 직렬화 차이를 허용해야 한다. id는 64비트 정수 의미이며 iOS는 64비트 Int를 사용한다.
- 날짜는 서버 datetime JSON(ISO 8601)과 `yyyy-MM-dd HH:mm:ss` 문자열이 공존한다. 거래 입력은 시간대 없는 현지 시각을 그대로 서버로 보내며 UTC로 임의 재해석하지 않는다. 시간대가 있는 거래 입력은 서버에서 UTC naive로 변환한다. 저장 시각/정렬 시각은 서버가 결정한다.

## 전체 API 선언과 활성 여부

아래의 서버 근거 행 번호는 조사 당시 `api_server.py` 기준이다. 활성은 실제 Android 화면/서비스에서 호출 가능한지를 뜻한다.

| ID | Android 심볼 / HTTP 경로 | 입력 | 결과·예외·서버 근거 | 활성 / iOS 차이 |
|---|---|---|---|---|
| API01 | registerUser / POST users/register | user_id 1~100자, device_id 1~200자 | ok/user_id/action; user_device_mismatch, device_user_mismatch; :259, register_user :2311 | 활성 등록/복원. iOS 등록 존재, 2자 제한과 안전한 오류 필요 |
| API02 | getMacBookAirUnits / GET macbook-air-units | 없음 | units[{product_type,chip,screen_inch,ram_gb,ssd_gb}], :217 | 활성 설정 tree; iOS 없음 |
| API03 | getUserFairPrices / GET user-fair-prices | query user_id | 전체 유효 조합+system/user/effective 설정 items, :231 | 활성 설정; iOS 없음 |
| API04 | upsertUserFairPrice / POST user-fair-prices/upsert | 아래 설정 계약 | ok/immediate_poll_requested/missed_candidate_count, :340 | 활성 개별·모든 bulk 작업; iOS 없음 |
| API05 | bulkSetUserWatchRulesEnabled / PATCH user-watch-rules/bulk-enabled | user_id/enabled/product_type? | affected_count, :370 | 선언만. 실제 bulk는 API04 순차 호출 |
| API06 | bulkSetUserFairPricesDropRate / PATCH user-fair-prices/bulk-drop-rate | user_id/drop rate/product_type? | affected_count, :387 | 선언만. 실제 bulk는 API04 순차 호출 |
| API07 | resetUserFairPricesToSystemMarketPrices / POST user-fair-prices/reset-to-system-market-prices | user_id/product_type? | inserted_count/updated_count, :404 | 선언만. 실제 reset은 API04 순차 호출 |
| API08 | upsertResaleTradeAfterPurchase / POST resale-trades/after-purchase/upsert | user_id/source/product_id?·url?/updates | ok/id/current_stage/row, :449 | 활성 신규 prefill 저장; iOS 없음 |
| API09 | upsertResaleTradeAfterResale / POST resale-trades/after-resale/upsert | API08 동일 | ok/id/current_stage/row, :481 | 활성 신규 prefill 저장; iOS 없음 |
| API10 | createResaleTradeJourneyFromProduct / POST users/{user}/resale-trade-journeys/from-product | source/product_id | 실제 row 생성/hydrate, :513 | VM 메서드 있으나 MainActivity/화면 진입 없음 |
| API11 | startTradeJourneyFromUrl / POST trade-journeys/start-from-url | user_id/url(실제 URL 또는 숫자 product_id) | existing/id?·trade_journey_id?/row, :542 | 활성 거래 시작; iOS 없음 |
| API12 | getResaleTradePrefill / GET resale/prefill | query user_id/input | prefill row, :570 | 선언만 |
| API13 | startTradeJourneyFromAlert / POST trade-journeys/start-from-alert | user_id/alert_event_id>0 | existing/id?/row, :598 | 활성 알림 → 거래; iOS 없음 |
| API14 | startTradeJourneyFromReadArchive / POST trade-journeys/start-from-read-archive | user_id/read_archive_event_id>0 | existing/id?/row, :621 | 활성 보관함 → 거래; archive id 없으면 API13 fallback |
| API15 | patchResaleTradeJourneyPurchase / PATCH users/{user}/resale-trade-journeys/{id}/purchase | {updates:{변경 필드만}} | ok/id/row, not_found, :644 | 활성 기존 구매 저장; iOS 없음 |
| API16 | patchResaleTradeJourneyResale / PATCH users/{user}/resale-trade-journeys/{id}/resale | {updates:{변경 필드만}} | ok/id/row, :676 | 활성 기존 되팔이/판매 완료 저장; iOS 없음 |
| API17 | patchResaleTradeJourneySold / PATCH users/{user}/resale-trade-journeys/{id}/sold | {updates:{변경 필드만}} | API16과 같은 service handler, :701 | VM·callback 존재, 화면 callback 미호출 |
| API18 | getCompletedResaleTradeJourneys / GET users/{user}/resale-trade-journeys/completed | limit=200 | SOLD items, sold_at/updated_at DESC,id DESC, :726 | 활성 완료 내역; iOS 없음 |
| API19 | getPurchasedResaleTradeJourneys / GET users/{user}/resale-trade-journeys/purchased | limit=200 | purchased_at not null·SOLD 제외(KEEP 포함), :749 | 활성 구매 내역; iOS 없음 |
| API20 | deleteSelectedCompletedResaleTradeJourneys / PATCH users/{user}/resale-trade-journeys/completed/delete-selected | journey_ids:[Int] | deleted_count; 해당 user의 SOLD만 실제 DELETE, :772 | 활성 선택 삭제; iOS 없음 |
| API21 | deleteAllCompletedResaleTradeJourneys / PATCH users/{user}/resale-trade-journeys/completed/delete-all | body 없음 | deleted_count; 해당 user의 SOLD만 DELETE, :796 | 활성 전체 삭제; iOS 없음 |
| API22 | refreshUserRulesSavedAt / POST users/{user}/rules/refresh | body 없음 | refreshed_rule_count; 활성 규칙 saved_at 갱신, :819 | 활성 수동 새로고침; iOS 없음 |
| API23 | refreshSingleUserRuleSavedAt / POST users/{user}/rules/{rule}/refresh | rule id | rule_id; 해당 saved_at 갱신, :839 | 활성 규칙 카드 새로고침; iOS 없음 |
| API24 | registerPushToken / POST users/{user}/push-token | platform=android/token 20~1024자 | ok/message/reason, :299 | 활성 FCM; iOS 없음. provider 외부 제약 아래 참조 |
| API25 | getAlerts / GET alerts | user_id,is_read="0" | items, limit 기본/상한200, :908 | 활성 unread feed; iOS 없음 |
| API26 | markAlertEventRead / PATCH alert-events/{id}/read | query user_id | is_read/read_at/already_read, :928 | 활성 상세의 명시적 검토 완료; 단순 상세 열기는 읽음 아님; id 소유 사용자 검증 |
| API27 | markAlertEventReadPost / POST alert-events/{id}/read | API26 동일 | API26 동일 | API26 HTTP404/405 fallback |
| API28 | markAllAlertEventsRead / PATCH alert-events/read-all | query user_id | updated_count, :952 | 활성 모두 읽음; iOS 없음 |
| API29 | markAllAlertEventsReadPost / POST alert-events/read-all | API28 동일 | API28 동일 | API28 HTTP404/405 fallback |
| API30 | getGroupedReadAlerts / GET alert-events/read/grouped | query user_id | groups[chip][screen key]:[Alert], limit 기본500/상한1000, :1024 | 활성 읽음 보관함; iOS 없음 |
| API31 | clearAllReadArchive / PATCH alert-events/read/archive/clear-all | query user_id | cleared_count, :973 | 활성 보관함 비우기; 읽음/clear action log 보존 |
| API32 | clearSelectedReadArchive / PATCH alert-events/read/archive/clear-selected | query user_id,body alert_event_ids | requested/cleared/skipped/not_found_ids, :997 | 활성. archive row id와 alert_event id 구분 |
| API33 | getRecommendedKeywords / GET user-fair-prices/recommended-keywords | product_type/chip, ram_gb?·ssd_gb? | items:[String], :1061 | 선언만; 현재 설정은 서버 item의 추천어 활용 |
| API34 | analyzeUrl / POST analyze-url | user_id/url | status success/duplicate/failed와 분석 필드, :1090 | UmtpUrlAnalyzeScreen 존재, MainActivity에서 제외됨 |

실제 선언 수는 위 34개이며 PATCH→POST compatibility 메서드 두 쌍을 포함한다. 루트 parity 표는 이 목록으로 누락 검사를 수행한다.

## 설정 수치·저장 계약

- 식별자는 product_type + chip + screen_inch + ram_gb + ssd_gb. Mac mini의 screen_inch=0은 정상. 서버 `/macbook-air-units` 이름과 달리 MacBook Air/Pro/Mac mini 전체를 반환한다.
- fair_price_krw>0, drop rate -100...100, target=`ROUND_HALF_UP(fair * (1-rate/100))`. 예: 1,000,000 / -10 → 1,100,000원. 서버 effective target이 있으면 이를 우선 표시한다.
- 방향 BELOW_OR_EQUAL는 매물≤목표, min_price_krw 하한만 사용. ABOVE_OR_EQUAL는 매물≥목표, max_price_krw 상한만 사용. 반대 경계를 저장하지 않는다. 0은 유효 경계이고 빈 값/null과 구분한다.
- enabled=false, condition_change_candidate_notice_enabled=false 기본값. search_keyword는 null/빈 값이면 추천어로 해석. 서버 item의 custom/recommended/effective 검색어를 구분한다.
- priority FAST/NORMAL/LOW. worker 실제 기본 45/180/600초와 jitter; DTO poll_interval_seconds=60과 같은 개념으로 단순 치환하면 안 된다.
- 개별·bulk 저장은 saved_at/force_poll/last_poll_requested_at에 영향을 준다. 클라이언트 GET 재조회와 서버 규칙 POST refresh는 다른 동작이다.
- 실제 Android bulk는 product/chip/screen 필터 후 각 조합 API04 순차 upsert하며 다른 설정을 보존한다. 설정 on/off·drop rate·최소/최대·조건변경후보·priority·시스템시장가 reset을 포함한다. 서버 bulk endpoints를 직접 대체하면 scope/chip/screen과 보존 정책이 달라질 수 있다.
- 시세/규칙은 서버 저장; iOS 기존 UserDefaults user_id/기기 fallback key를 보존한다. 별도 로컬 DB/API 캐시는 Android에 없음.

## 알림·보관함 데이터

- 카드 row는 id/alert_event_id/read_archive_event_id를 별도 유지. 매물 URL은 product_url 우선/url fallback. 제목/메시지/이미지/제품 spec/market·target·gap·direction/위험도·trade flags/원문·요약/분석·발생·read 시각/trigger·refresh 정보를 포함한다.
- fraud_probability 기본/v1/v2/v3 각각 수치/label/text/model_version/scored_at 및 v2-v1·v3-v2 delta/comparison text가 있다. null을 0%로 표시하지 않는다. 원시 확률과 percent 표시를 구분한다.
- 서버 읽음 처리 뒤 unread feed에서 제거한다. 보관함 group은 chip→screen이지만 서로 다른 제품도 포함될 수 있어 원본 product_type을 카드에 유지한다.
- clear-selected는 `alert_event_ids`; 거래 시작 archive는 `read_archive_event_id`. 잘못된 id로 삭제/시작하지 않는다.
- 페이지 cursor/offset API가 없다. Android feed200/archive500/trade200 제한과 동일하게 설명하고 무한 pagination을 만들지 않는다.

## 거래 모델·흐름

- Android 화면은 5단계 wizard가 아닌 2모드(구매 후 기록/되팔이 후 기록)의 단일 스크롤이다. 정확 확인 정보, 자동채움 정보, 완료 목록, 구매 목록을 함께 노출한다.
- 새 URL/알림/보관함 start 성공은 `existing:false,id:null,row:{...}`일 수 있다. 저장 전 draft이며 반드시 row.id를 요구하면 신규 입력이 막힌다. 최초 저장은 legacy upsert, id가 있는 기록 수정은 PATCH를 사용한다.
- start 응답 row의 id/source/product_id/current_stage가 null일 경우 top-level id/trade_journey_id/source/product_id/current_stage로 보완한다. row 전체가 없으면 성공 표시하지 않는다.
- 자동채움: title/listing_price/seller/location/image_urls/body/spec/fair price/discount/metadata. image_urls는 JSON array/object 또는 JSON을 포함한 문자열/단일 URL 가능. 정확 확인(serial/model/battery/activation lock/MDM)은 자동 추정하지 않는다.
- 구매 입력: title, listing_price_krw, seller_nickname, body_text, fair_price_krw, seller_location, contacted_at, seller_response_at, purchased_at, purchase_method, purchase_location, purchase_price_krw, transport_cost_krw, shipping_cost_krw, payment_method, sale_platform, inspection_notes, current_stage 및 정확 확인 필드.
- 되팔이 입력: resale_platform, resale_url, resale_listing_price_krw, buyer_nickname, sale_method, sale_location, sold_at, sale_price_krw, current_stage 및 정확 확인 UI. 서버 resale whitelist에는 정확 확인이 포함되지 않아 Android의 되팔이 정확확인 변경은 유실된다. iOS는 정확확인 변경을 purchase PATCH에 별도 반영해야 동작을 완성할 수 있다.
- 수정은 sparse: 빈 입력/미변경은 생략하여 기존 값을 보존. Android는 잘못된 정수를 silently 생략하는 문제가 있으므로 iOS는 validation 오류로 안내해야 한다. bool은 true/false/미입력 삼상태다.
- 서버가 total_cost_krw(구매가+교통비+배송비)와 단계 DISCOVERED/INSPECTED/RESALE_LISTED/SOLD/KEEP을 계산한다. iOS는 서버 반환값으로 갱신한다.
- 완료 전체 삭제는 실제 데이터 삭제이며 Android는 확인 없이 호출한다. iOS는 대상·개수 확인 UI를 추가하여 우발 삭제를 줄인다. 완료 목록 조회 실패 상태에서 빈 목록과 혼동하지 않는다.

## 플랫폼/보안 차이와 필요한 외부 변경

1. 원격 푸시: `notification_worker.py:1970`은 활성 토큰을 platform="android"로 한정하고 :1993의 FCM Message에 AndroidConfig만 설정한다. iOS token을 `platform=ios`로 정상 등록해도 발송 대상이 되지 않는다. APNs raw token을 이 API의 FCM token으로 보내면 안 된다. 최소 서버 변경안은 android+ios FCM 토큰 조회 및 APNs alert/priority payload 구성. iOS Firebase 앱 설정 + APNs signing/key와 실제 기기 검증이 필요하다. Android로 platform을 위장하지 않는다.
2. 등록 API는 기기당 user_id 하나를 강제하므로 Android 기기에 묶인 기존 ID를 별도 iOS 기기에서 등록하면 거절된다. 이는 iOS 단독으로 해결 불가. 계정 이전/다중 기기 정책이 필요하면 별도 서버 계약이 필요하며 기존 매핑을 우회하거나 덮어쓰지 않는다.
3. 이후 API는 user_id 존재만 확인하고 디바이스/소유자 인증을 하지 않는 보안 부채가 있다. 현재 범위에서 임의 인증 설계나 backend 변경을 하지 않고, 클라이언트는 저장된 자신의 user_id만 사용한다. 서버 인증 도입은 별도 최소 설계가 필요하다.
4. Android `UmtpApiClient`의 BODY/거래 raw 응답 로깅과 VM 거래 입력 로그에는 개인정보가 포함될 수 있다. iOS에 복제하지 않는다. PushTokenResponse가 ok 없이 message만 파싱하는 것도 복제하지 않는다.
5. 앱 외 Notification Listener/URL scheme/Universal Links는 Android Manifest에 실제 활성 구현이 없으므로 README 대기 항목을 완료 기능으로 취급하지 않는다. 푸시 tap은 alert_id 및 url을 통해 알림 화면으로 이동하는 별도 흐름이다.

## 문서와 실제 코드 불일치

- Android README의 `읽음은 로컬`, `Mock 데이터 지원`, `카드 클릭은 브라우저 바로 연결`은 현재 서버 read/archive·상세 흐름과 맞지 않는다. 현재 코드 우선.
- Android README 수동 분석은 메인 제외라고 명시하며 코드도 미연결. WatchRuleSettingsScreen/WatchRuleUpsert/RequestPollNow DTO는 사용 안 되는 과거 구현이다.
- backend README 초반 `사용자는 product_id를 직접 입력하지 않는다`와 달리 현재 Android·서버 모두 URL 또는 product_id 입력을 허용한다.
- backend README 과거 버전 `FCM 미구현`, `가짜 알림`은 최신 1.10 worker 경로와 맞지 않는다. 버전별 이력이며 현재 앱 명세가 아니다.
- iOS README Stage1 placeholder 설명은 시작 기준 구현과 일치한다.

## 구현 담당 참고 / 검증 대상

공통 APIClient GET/POST/PATCH·query encoding·HTTP/ok 실패·취소·안전 메시지, 유연한 bool/숫자/nullable DTO → 등록 키 보존 → 알림/read/archive → 설정 sparse/full request → 거래 draft→upsert→PATCH 및 삼상태/날짜·금액 validation 순으로 구현 가능하다. 테스트는 mocked URLProtocol로 실제 URL/method/body·HTTP200 ok:false·422·timeout/취소·누락 row·nullable id·부동/문자 수치·삼상태 bool·sparse 보존·삭제 범위를 검증하고 실제 서비스/푸시 성공과 구분한다.
