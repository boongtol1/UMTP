# Android 활성 기능 조사

조사 기준: `da769c31ba4afdfa5d3b07ad9ecca2c39d7cbb04`, 2026-09-15. 이 문서는 코드 조사 증거이며 기능 실행 성공을 의미하지 않는다. 통합 상태와 iOS 구현/검증/커밋은 `android-ios-parity.md`를 따른다.

## 조사 범위와 구조

- 저장소 내 AGENTS.md, CLAUDE.md, CONTRIBUTING.md 없음. `android/README.md`, Gradle, Manifest, 모든 main Kotlin 화면/서비스/모델/API, unit/instrumentation 테스트 목록 조사.
- Android: 단일 `MainActivity`, Compose 화면, `MacBookAirSettingsViewModel`의 StateFlow + Retrofit singleton. 별도 Repository, DI 컨테이너, Activity/Fragment, navigation graph, DB, Worker, BroadcastReceiver 없음.
- 이하 경로 약어 A = `android/app/src/main/java/com/boongtol/umtp_android/`. 서비스 호출 경로는 `A/network/UmtpApiService.kt`에 정의.
- README보다 코드 우선: README는 MacBook Air 위주/2탭, 읽음 상태 로컬 관리/Mock 지원이라고 설명하지만 실제는 Mac mini 포함 서버 units 트리/4탭/서버 읽음·보관함/거래 여정. 활성 화면에서 Mock fallback 없음.

## 활성 기능별 명세와 예외

| ID | 기능 / 진입 | 주요 근거·심볼 | 입력 및 기대 결과 | 예외·상태 |
|---|---|---|---|---|
| AUTH-01 | 최초 사용자 등록 | `A/MainActivity.kt:onCreate`, `ui/UserSetupScreen.kt`, `MacBookAirSettingsViewModel.registerUser` | trim ID 2자 이상 + ANDROID_ID → POST users/register; 서버 반환 user_id 우선 저장 후 메인 진입 | 중복 클릭 UI disabled, loading, ID/device 누락 설명, HTTP/서버 ok=false 실패; 암호/토큰 로그인·계정 편집·탈퇴 없음 |
| AUTH-02 | 재시작 세션 복구 | `user/UserPreferences.kt`, ViewModel init | `umtp_prefs/user_id` 읽어서 등록 생략; units/settings/alerts/archive 조회; FCM 등록 | 서버 읽기 실패가 저장 ID를 삭제하지 않음. 만료 토큰/refresh token 개념 없음 |
| NAV-01 | 4탭 및 뒤로 | `MainActivity.kt:MainTabScreen`, `SettingsNavigator`, `Screen` | 알림 / 읽음 보관함 / 거래 입력 / 설정; 설정 product→chip→inch→RAM/SSD; Mac mini는 inch 생략 | 다른 탭 Android Back→알림; 설정 하위 Back→상위. Compose remember UI는 탭 이탈/프로세스 종료 시 재생성될 수 있음 |
| ALERT-01 | 미읽음 피드 | `ui/AlertFeedScreen.kt`, VM `fetchAlerts/startAlertPolling` | GET alerts?user_id=&is_read=0; created_at 내림차순; 30초 polling 및 ON_RESUME; 수동 새로고침 시 시각/상태 | 빈 “알림이 없습니다.”; 중복 조회 억제; 실패 기존 목록 보존; 자동 실패는 조용함; 페이지네이션 없음 |
| ALERT-02 | 카드 전체 표시 | `AlertFeedScreen.kt:AlertCard`, resolve helpers | 사기 가능성, 이미지, 제목, 참고/내용변경/위험/조건 badges, 가격, 스펙, 기준가격, 차이%, 출처, URL 유무, 본문 요약, 시각, 상세 보기 | title→message→제목 없음; product_url→url; listing price→target; gap→diff_ratio→drop; fraud explicit text→probability/label; 0.25/0.65 경계; 후보/끌올 문구 |
| ALERT-03 | 상세 | `AlertFeedScreen.kt:AlertDetailScreen/buildAlertDetailRows` | 26 필드: 알림 유형/참고/출처/URL/이미지/제품/칩/인치/RAM/SSD/등록가격/시장가/기준가격/차이/설정차이/조건/사기/위험/점수/키워드/본문/등록·생성·분석 시각/거래유형/특이사항; 검토 완료·매물 열기 | 상세 진입만으로 읽음 변경하지 않음. “검토 완료” 서버 성공 후 목록 복귀·refresh |
| ALERT-04 | 선택·전체 읽음 | `AlertFeedScreen.kt`, VM `markAlertAsRead/markAllAlertsAsRead` | 선택모드/전체선택/해제/선택읽음 순차 호출; 전체읽음 endpoint; 성공 수·목록 갱신 | id>0만 선택; 실패도 다음 선택 진행; PATCH 404/405/501만 POST fallback; 실패 로컬 성공 처리 금지 |
| LINK-01 | 외부 매물/이미지·복사 | AlertFeed/ReadAlertArchive Screen | 카드 URL·이미지 URL 클립보드 복사 + toast; 상세 링크/이미지 및 매물 보러가기 ACTION_VIEW | URL 없으면 disabled. Android는 scheme 검사/ActivityNotFound 예외 누락 → iOS HTTP(S) 검증 및 실패 피드백 권장 |
| ARCHIVE-01 | 그룹 보관함/상세 | `ui/ReadAlertArchiveScreen.kt`, VM `fetchReadGroupedAlerts` | GET alert-events/read/grouped; chip→screen 그룹; M1..M5, 기타 last; screen 숫자 순; 가격/사기/스펙/읽음시각; 상세는 피드와 거의 같은 필드 | 빈 메시지·새로고침; 응답 순서 유지; 프로 칩 정렬은 기본 50(알려진 순서 차이) |
| ARCHIVE-02 | 선택·전체 비우기 | Screen + VM `clearSelectedReadArchive/clearAllReadArchive` | PATCH clear-selected `{alert_event_ids:[...]}` / clear-all; cleared/skipped 수 표시 후 refresh | 양수 중복제거; 실패 기존 보관함 보존. 원본 매물 삭제 의미 아님. Android는 확인 대화상자 없음 |
| TRADE-01 | URL/product_id 시작 | `ui/ResaleTradeInputScreen.kt`, VM `startTradeJourneyFromUrl/applyStartedTradeJourneyResponse` | POST trade-journeys/start-from-url `{user_id,url:trimInput}`; row 선택, 기존 기록 안내; top-level id/trade_journey_id/source/product_id/current_stage를 null row필드에 보강 | 빈 입력 오류; 중복 제출 차단; ok=true여도 row null 실패. 모의 자동채움 없음 |
| TRADE-02 | 알림/보관함 시작 | MainTabScreen callbacks, VM `startTradeJourneyFromAlert/startTradeJourneyFromReadArchive` | POST start-from-alert `{user_id,alert_event_id}` 또는 start-from-read-archive `{user_id,read_archive_event_id}`; 성공시 거래탭 선택 | archive id 없으면 alert_event_id→id fallback. 시작 실패시 기존 탭 유지 |
| TRADE-03 | 거래 자동채움/확인정보 | `ResaleTradeInputScreen.kt:buildJourneyValueMap/firstImageUrl/ExactVerificationInputSection` | DB row 원본 표시, 배열/객체/JSON문자열 image_urls 첫 이미지, 기본 스펙, 일련번호/모델번호/배터리 사이클·건강/활성화잠금·MDM true/false/미입력 | null/빈 객체 표시 없음; 데이터는 서버값 사용. Android base spec edit UI가 있으나 save 목록에 누락되는 버그 존재 |
| TRADE-04 | 구매후 기록 저장 | Screen `PURCHASE_INPUT_FIELDS/buildManualUpdates`, VM `patchSelectedResaleJourneyPurchase` | title/listing_price/seller_nickname/body/fair_price/seller_location/contacted_at/seller_response_at/purchased_at/purchase_method/location/price/transport/shipping/payment/sale_platform/inspection/current_stage + 정확확인; changed/nonblank sparse PATCH /users/{id}/resale-trade-journeys/{id}/purchase | 숫자 comma 제거, false/0 보존; id 없으나 product/url 있으면 after-purchase/upsert; 빈 칸은 삭제 아님. Android invalid number 조용히 생략 버그 이식 금지 |
| TRADE-05 | 재판매 기록 저장 | Screen `RESALE_INPUT_FIELDS`, VM `patchSelectedResaleJourneyResale` | resale_platform/url/listing_price, buyer_nickname, sale_method/location, sold_at, sale_price, current_stage + 정확확인; resale PATCH 또는 after-resale/upsert | 서버가 단계/계산 처리. onSubmitSold 콜백은 선언만 되고 UI에서 호출 안 됨; 별도 sold 버튼은 활성 기능 아님 |
| TRADE-06 | 구매/완료 내역·선택 | Screen history FlowRow, VM `loadResaleJourneyHistory` | GET completed + purchased limit=200; 단계(발견됨/구매점검/재판매등록/판매완료/KEEP), 제목/판매·구매 금액; 기록 선택 자동채움·다시 탭하여 해제 | 호출 순차; completed 네트워크 throw이면 purchased도 안 읽는 한계; 페이지네이션 없음; 이전 목록 유지 |
| TRADE-07 | 완료 내역 삭제 | VM `deleteSelectedCompletedResaleJourneys/deleteAllCompletedResaleJourneys` | PATCH completed/delete-selected `{journey_ids}` 또는 delete-all 후 내역 reload | Android 중복/확인·삭제된 selection 정리 부족 → iOS 개선 권장 |
| SETTINGS-01 | 카탈로그 트리 | `MainActivity.kt:SettingsNavigator`, ProductType/Chip/ScreenSize/RamSsdSettingsScreen | GET macbook-air-units + GET user-fair-prices; product Air→mini→other, chip M1/M2/M2 Pro/M3/M4/M4 Pro/M5→other; inch asc; 서버 RAM/SSD 조합 | Mac mini screen=0, bulk screen=null; empty refresh 재시도; 하드코딩 제품목록 아님 |
| SETTINGS-02 | 개별 시세/가격·방향 | `ui/MacBookAirSettingCard.kt`, `FriendlyPriceText.kt`, `AlertBoundMapper.kt`, VM `upsertItem` | 시스템/사용자 시장가·기준가격·차이%; fair,target,percentage 상호 계산 `(fair-target)/fair*100` 소수2자리 HALF_UP; percent 입력 기준 target 반올림; below/above | fair,target>0; min/max≥0; unknown direction→below. below는 min만, above는 max만 전달하여 반대 bound 해제; -% 지원 |
| SETTINGS-03 | 개별 검색/속도/알림/후보 | SettingCard, VM upsertItem, `WatchPriorityUi.kt` | custom/effective 초기 검색어 + 추천 검색어 표시; FAST 빠름/NORMAL 보통/LOW 절전; 알림 on/off, 조건변경후보 on/off; 저장 POST user-fair-prices/upsert, poll=60 | 공백 keyword=null(서버 추천); enabled이면 immediate_poll_requested별 메시지; 후보 최근7일은 분석확인시각→저장시각 기준 |
| SETTINGS-04 | 전체/개별 새로고침 | VM `refreshSettings/refreshSingleRuleSavedAt` | POST users/{id}/rules/refresh 또는 /rules/{rule}/refresh; 전체 units/settings/alerts/archive도 갱신; 마지막 HH:mm; 활성 override만 개별 enabled | **단순 조회가 아닌 saved_at 변경**: “지금부터 새로 올라오는 매물만 다시 조회합니다.”; 중복 억제/실패 표시 |
| SETTINGS-05 | bulk 범위·알림·후보·속도 | RamSsdSettingsScreen, VM bulk funcs / `applyBulkUpsertFallback` | 현재 chip/inch 또는 제품 전체; 확인 dialog; 해당 서버 settings 각 행 upsert 순차. enabled/candidate/priority만 변경하고 다른 값 유지 | has_override 표시 계산과 다르게 실제 bulk는 모든 scope settings 포함. 최초 error에서 중단(부분성공 가능); Android는 부분새로고침/명시 보고 부족 |
| SETTINGS-06 | bulk 차이/최소/최대 | 같은 근거 + resolveBulkPriceBoundsScopeState | -100..100, +/-; below 행에 최소/above 행에 최대, 동일 bounds면 기본표시; 각 확인 후 upsert | 적용방향 없으면 버튼 disabled; 서로 다른 bounds면 빈칸; Android opposite방향도 unchanged upsert하여 saved_at 바뀌는 문제 |
| SETTINGS-07 | 시스템 시장가 초기화 | VM resetFairPricesToSystem/resolveFallbackFairPrice | scope 전체 system_fair로 바꾸고 기존 방향/차이/bounds/keyword/priority/candidate/enabled 유지 | system fair null/≤0 건은 건너뜀; 전부 skip여도 성공 toast Android 버그; iOS 성공/skip 구분 권장 |
| PUSH-01 | 권한·토큰 | MainActivity, `fcm/PushTokenManager.kt`, UserPreferences | Android13+ POST_NOTIFICATIONS; FCM token fetch/rotation → POST users/{id}/push-token `{token,platform:android}`; 성공상태 보존 | 권한거부는 log만; 토큰달라지면 재등록; 실패 다음 앱 진입 재시도; Android는 response.ok 확인 없이 registered=true 버그 |
| PUSH-02 | 수신·알림클릭 | `fcm/UMTPFirebaseMessagingService.kt`, MainActivity.handleIntent, AlertFeed initialTargetAlertId | FCM data listing_title/price/fraud→high channel UMTP 매물알림; notification/data message 지원; alert_id PendingIntent; 알림탭 선택 후 id 일치 항목 상세 | 읽음/목록밖 ID는 찾지 못함; 늦은 목록에 매칭 재시도. 표준notification+data가 foreground 중복 notify 가능 |
| DATA-01 | 저장·복원·캐시 | UserPreferences, VM, Compose remember, coil AsyncImage | user_id/is_user_registered/fcm_token/push_token_registered만 명시적 영구키; 도메인데이터 서버 소유/메모리 목록; 이미지 라이브러리 기본 cache | Room/DataStore/파일도메인DB 없음. process 종료시 미저장 입력·탭·선택 복원 없음; 백업 allowBackup true 기본 sharedprefs 포함 |
| NET-01 | transport/계약·오류 | UmtpApiClient, SafeErrorMessage, all network models | 기본 HTTPS umtp.duckdns.org, BuildConfig UMTP_BASE_URL; Retrofit Gson Boolean 0/1/string yes/no/on/off 허용; user_id query/body/path, Authorization header 없음 | baseHost/*.duckdns.org system DNS 실패→Cloudflare/Google DoH 4s; 안전오류 URL/IP/키/path 숨김; 실패 데이터 보존·수동 재시도 |

## 제외/플랫폼/보안 차이

- `UmtpUrlAnalyzeScreen`는 파일내 정의만 존재하고 MainActivity 어느 경로에서도 호출하지 않음; README도 메인 제외 명시. analyze-url endpoint 이식을 필수 활성기능으로 계산하지 않음.
- `WatchRuleSettingsScreen`, `getRecommendedKeywords` API는 정의만 존재. 활성 SettingCard는 user-fair-prices 응답의 recommended_search_keyword를 표시한다. RequestPollNow/WatchRule 모델은 진입/API 사용 없음.
- bulk 전용 API 3개는 interface에 있으나 활성 ViewModel은 항상 개별 upsert fallback을 사용. iOS도 scope/full값 보존 위해 개별 upsert 필요.
- create-from-product, getResaleTradePrefill, legacy upsert public entry, loadCompleted wrapper는 MainActivity에서 호출하지 않음. after-purchase/after-resale API 자체는 활성 save의 id 없는 fallback에 사용됨.
- Manifest: launcher activity + FCM service만. NotificationListener, 외부 알림 읽기, 자동 URL 추출/전송, share extension/ACTION_SEND, URL Scheme/App Links, Widget, 검색 UI, camera/photos/location 권한, WorkManager, background service, feature flag 없음. README MVP-B..F는 미구현 미래 작업이다.
- iOS는 타 앱 알림읽기 대신 별도 구현할 대상 없음. Android 30초 polling도 앱 프로세스 메모리 scope일 뿐 OS guaranteed background job 아님. iOS foreground polling + resume refresh + remote push로 대응.
- Android `usesCleartextTraffic=true`, release에도 BODY logging/raw 거래응답 및 사용자 입력 로그를 남김. 이를 iOS에 복제하지 않는다. 백엔드 인증헤더 부재는 서비스 계약상 한계이며 임의 토큰 인증 추가로 기존 사용자 데이터 접근을 끊지 않는다.
- Android `upsertItem` savingKey는 product_type 빠짐(화면 비교키엔 포함) → 저장버튼 loading/중복 차단 실패. iOS는 전체 복합키를 사용한다.
- Android 카드 invalid 가격 누르면 아무피드백 없고 스펙 수정이 save에서 누락된다. 데이터손실/침묵실패 동등성으로 복제하지 않는다.

## 테스트 현황(코드 목록)

`FriendlyPriceTextTest`(ID label·숫자/반올림), `AlertBoundMapperTest`(방향별 bound), `WatchPriorityUiTest`(속도 정상화·request), `SafeErrorMessageTest`(민감정보·네트워크/JSON 구분), ExampleUnitTest 단순 덧셈, ExampleInstrumentedTest 앱 package 확인. UI flow/VM/API 통합 테스트는 기존 Android에 없음. 본 조사 에이전트는 빌드·실기기 실행을 하지 않았으며 루트 검증기록이 실제 실행 여부의 근거이다.
