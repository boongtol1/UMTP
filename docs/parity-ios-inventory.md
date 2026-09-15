# 기존 iOS 구현 조사 (변경 전 기준)

이 문서는 이식 전 iOS 상태를 고정해서 기록한다. 아래 “없음”, “현재”, “필요한 작업”은 별도 명시가 없으면 시작 기준이며 현재 앱의 누락을 뜻하지 않는다. 최신 구현·검증은 [기능 대응표](android-ios-parity.md)를 기준으로 한다. 현재 앱은 C15 commit 후 전체106개(단위86+UI20)를 실패0·skip0·exit0으로 통과했으며 로컬 구현·검증을 완료했다. 실서비스/APNs·서명된 실기기·Android 실행 검증은 별도다.

- 조사 기준 Android/iOS 공통 HEAD: `da769c31ba4afdfa5d3b07ad9ecca2c39d7cbb04`.
- 읽기 조사: iOS의 모든 Swift 20개 경로, Xcode project 전체 설정, README, Android MainActivity/등록/API/알림/푸시/저장 코드.
- 기존 사용자 변경: `umtp/sql/seed_silicon_macbook_pro_fair_prices.sql` untracked. 본 조사에서는 열거나 변경하지 않았다.
- 코드에서 확인한 사실이며, 이 문서 작성 담당은 빌드·실행을 수행하지 않았다. 빌드·실행 검증을 이 조사 완료와 혼동하면 안 된다.

## 1. 실제 구조와 진입점

이미 SwiftUI + Combine ObservableObject + URLSession 구조다. SwiftUI로 새로 전환할 필요가 없으며 기존 폴더 구분과 세션 등록 흐름을 확장할 수 있다.

```text
App/UMTPApp.swift (@main)
└─ ContentView (AppState 주입, 1회 restoreSession)
   ├─ isLoadingSession → ProgressView
   ├─ userId 있음 → MainPlaceholderView
   └─ userId 없음 → UserSetupView
      └─ UserSetupViewModel → UserAPI → APIClient POST /users/register
         └─ UserSessionService.saveUserId → AppState.completeLogin

MainTabView (현재 진입 경로 없음)
├─ AlertFeedView → AlertFeedViewModel → AlertPollingService (아무 요청도 하지 않음)
└─ SettingsView (준비 중 텍스트, 로그아웃 버튼)
```

`UMTP_IOSApp.swift`는 `import Foundation` 한 줄뿐이며 두 번째 앱 entrypoint가 아니다. 진짜 entrypoint는 `App/UMTPApp.swift:5`다. `MainTabView`, `AlertFeedView`, `SettingsView`는 파일이 있지만 `ContentView:12`가 placeholder를 호출하므로 실제 사용자가 도달하지 못한다. 이는 폐기된 기능이라는 증거가 아니라 Stage2에 연결하려고 만든 미완성 구조다. README도 이 상태를 정확히 설명한다.

## 2. Swift 파일·심볼 전수 목록

모든 상대 경로는 `ios/UMTP_IOS/UMTP_IOS/` 기준이다.

| 파일 | 주요 심볼 | 변경 전 실제 역할 / 상태 |
| --- | --- | --- |
| `App/UMTPApp.swift` | `UMTPApp.init`, `body` | AppState StateObject 생성, ContentView에 environmentObject 주입. 실제 앱 entrypoint |
| `App/AppState.swift` | `AppState.isLoggedIn`, `restoreSession`, `completeLogin`, `logout` | 공백 아닌 사용자 ID로 로그인 여부 판단. UserDefaults 복원. logout은 세션 삭제하나 앱 내 호출 없음 |
| `App/AppConfig.swift` | `AppConfig.apiBaseURL`, `requestTimeout` | `https://umtp.duckdns.org`, 10초. 외부 환경 override 없음 |
| `UMTP_IOSApp.swift` | 없음 | import만 있는 사용되지 않는 파일 |
| `ContentView.swift` | `ContentView.body` | .task 최초 1회 세션 복원. 이후 등록/placeholder 분기 |
| `Services/APIClient.swift` | `APIClient.init`, `postJSON`, `buildURL`, `APIClientError` | POST JSON만 지원. 2xx/HTTP 실패/네트워크/타임아웃/decoding 구분, response body의 reason/message 유실 |
| `Services/UserAPI.swift` | `UserAPIProtocol`, `RegisterUserResult`, `UserAPI.register`, `resolveDeviceId`, `UserAPIError`, DTO 2개 | 유일한 실제 서비스 호출. trim, 최소 2자, user_id/device_id/platform 전송. ok 확인. IDFV 우선, 없으면 UserDefaults UUID |
| `Services/UserSessionService.swift` | `saveUserId`, `loadUserId`, `clearUserId` | 기존 사용자 ID 영속 저장. shared singleton/private init으로 테스트 주입 제한 |
| `Services/AlertPollingService.swift` | `start`, `stop`, `isRunning` | bool만 바꾸는 stub. 타이머/Task/서버 호출 없음 |
| `ViewModels/UserSetupViewModel.swift` | `canSubmit`, `register` | 중복 등록 guard, errorMessage, isSubmitting, 저장 후 AppState 갱신. 실제 동작 |
| `ViewModels/AlertFeedViewModel.swift` | `alerts`, `onAppear`, `onDisappear` | 빈 배열 유지, polling stub start/stop. 네트워크 연결 없음 |
| `ViewModels/SettingsViewModel.swift` | `appVersion`, `refresh` | 항상 `Stage 1`. 실제 설정 없음 |
| `Views/UserSetupView.swift` | `UserSetupView.body` | 시작 문구, User ID 입력, 오류, 등록 버튼. submit 중 버튼만 비활성, 입력은 계속 가능 |
| `Views/MainPlaceholderView.swift` | `MainPlaceholderView.body` | 사용자 ID와 Stage2 예정 문구만 표시. 버튼/탭 없음 |
| `Views/MainTabView.swift` | `MainTabView.body` | 알림/설정 2탭 정의. 실제 entrypoint 없음 |
| `Views/AlertFeedView.swift` | `AlertFeedView.body` | 빈 상태 샘플 문구. 타이틀/message만 정의. 실사용 불가 |
| `Views/SettingsView.swift` | `SettingsView.body` | 준비 중, 로그인 상태, 조건 변경 후보 안내, 로그아웃 버튼. 실사용 불가 |
| `Models/AlertModels.swift` | `AlertItem` | id:String/title/message/createdAt 4개 필수 필드. 실제 서버 nullable/numeric/snake_case 계약에 맞지 않는 placeholder |
| `Models/UserFairPriceModels.swift` | `UserFairPriceItem` | id:String/symbol/fairPrice 3개. Mac 제품/RAM/SSD/rule 설정 계약과 불일치, 참조 없음 |
| `Models/UserModels.swift` | `UserInfo` | userId 한 개. 참조 없음 |

## 3. 기존 동작 보존 조건

### 사용자 ID / 기기 식별 / 세션

| 플랫폼 / 저장소 | 키 | 의미 | 보존 요구 |
| --- | --- | --- | --- |
| iOS UserDefaults | `umtp_user_id` | 현재 등록된 사용자 ID, trim해서 복원 | 키를 바꾸거나 앱 업데이트 때 삭제하지 않는다. 기존 사용자 ID로 모든 이식 API를 연결 |
| iOS UserDefaults | `umtp_ios_fallback_device_id` | IDFV를 얻지 못했을 때 만든 UUID | 계속 사용하거나 안전하게 읽어서 새 저장소로 승계. 다른 UUID를 무조건 생성하지 않는다 |
| Android `umtp_prefs` | `user_id` | 등록 사용자 | iOS 기존 키와 다르므로 Android 키 이름으로 iOS 데이터를 덮어쓰지 않는다 |
| Android `umtp_prefs` | `is_user_registered` | 등록 여부 | iOS는 userId 존재 여부를 사용 중. 서버 세션 token은 아님 |
| Android `umtp_prefs` | `fcm_token`, `push_token_registered` | FCM token과 서버 등록 성공 기억 | iOS에 대응 없음. 계정+token 단위 등록 상태가 필요 |

iOS APIClient와 Android UmtpApiService에는 bearer token/Authorization interceptor가 없다. 여기서 “로그인/세션”은 서버 user_id 및 device_id 등록과 로컬 복원이며, 존재하지 않는 OAuth/토큰 갱신 요구를 새로 만들어서는 안 된다. UserAPI가 `platform: ios`를 보낸다는 차이는 유지한다. iOS 로그아웃은 서버 삭제 API 호출 없이 로컬 ID만 삭제하는 기존 기능이고, placeholder 구조 때문에 사용자에게 도달하지 않았다.

### 등록 흐름의 실제 차이

- Android `UserSetupScreen`: 입력 label `User ID`, 안내 `사용자 ID를 입력해주세요.`, 버튼 `저장 및 시작`; submit 중 입력 비활성. iOS는 예시 placeholder, `등록`/`등록 중...` 버튼, 입력 활성.
- Android `registerUser`는 response.user_id가 null 또는 빈 문자열이면 입력 ID를 사용한다. iOS는 null일 때만 입력으로 fallback, 빈 문자열은 서버 응답 오류 처리.
- 두 앱 모두 trim 후 2자 이상을 요구하고 successful response 이후 저장한다. iOS의 기존 중복 제출 guard는 유지할 가치가 있다.
- iOS는 실패 JSON의 `message`, `reason`을 디코드하지만 안전한 등록 오류 외 구체적 오류 코드 mapping은 없다. Android의 `SafeErrorMessage.kt`처럼 원시 SQL/서버 내부 정보 없이 안전한 오류 의미를 보존해야 한다.
- iOS는 현재 IDFV를 얻으면 저장된 fallback UUID보다 우선한다. 영구 식별 정책을 바꿀 때 기존 식별값 변경 여부를 검토해야 한다. README의 Keychain TODO 자체가 현재 동작은 아니다.

## 4. Android 기능과 누락 대조

Android의 실제 앱 진입 경로는 `MainActivity.onCreate` → `MainTabScreen` 4탭이고 iOS 메인 placeholder 이후 모든 서비스 기능이 누락이다. 아래는 주 대응표 작성용 기능 묶음이다. Android 근거 경로의 prefix는 `android/app/src/main/java/com/boongtol/umtp_android/`다.

| 영역 | 실제 Android 근거·경로 | iOS 차이 | 필요한 작업 |
| --- | --- | --- | --- |
| 메인 이동 | `MainActivity.kt::MainTabScreen`, 알림/읽음 보관함/거래 입력/설정 | 2탭 stub마저 도달 불가 | 기존 MainTabView 4탭 연결. 기능 VM을 사용자 세션에 종속시키고 alert→거래 이동 공유 |
| 알림 갱신 | `ui/MacBookAirSettingsViewModel.kt::fetchAlerts/startAlertPolling`, onResume | 요청/로딩/오류/갱신 시각 없음 | GET alerts, 10초 foreground polling, 중복 요청 guard, 오류 시 이전 데이터 보존, 재시도 |
| 알림 목록·상세 | `ui/AlertFeedScreen.kt`, `network/AlertModels.kt` | title/message 외 모든 필드 없음 | 제품 이미지/링크/스펙/가격/조건/사기 V1·V2·V3/리스크/본문/시각/조건 변경 후보 전체 표시, 탐색/정렬/필터 |
| 읽음 처리 | `markAlertAsRead/markAllAlertsAsRead`, `markAlertEventReadWithFallback` | 없음 | 단건/전체 처리 및 PATCH 404/405/501만 POST 호환, 서버 성공 후 UI 반영 |
| 읽음 보관함 | `ui/ReadAlertArchiveScreen.kt`, `fetchReadGroupedAlerts/clearAllReadArchive/clearSelectedReadArchive` | 화면/모델/API 없음 | 제품별/칩별 group 탐색, 상세, 선택/전체 삭제, 확인/상태/거래 이동 |
| 거래 시작 | `ui/ResaleTradeInputScreen.kt`, `startTradeJourneyFromUrl/FromAlert/FromReadArchive` | 없음 | URL/상품 참조 및 alert/archive 출발, prefill/identity/fallback 처리 |
| 거래 수정 | `patchSelectedResaleJourneyPurchase/Resale`, `network/ResaleTradeModels.kt` | 없음 | 구매 후/되팔이 후 2모드 전체 입력, sparse update, 시각·금액 검증, 서버 반영. Sold callback은 선언만 있고 화면에서 호출하지 않음 |
| 거래 이력 | `loadResaleJourneyHistory/deleteSelectedCompletedResaleJourneys/deleteAllCompletedResaleJourneys` | 없음 | 구매 완료/판매 완료 목록, 선택 복원, 최대 200개, 완료 이력 삭제 |
| 설정 탐색 | `MainActivity.kt::SettingsNavigator/Screen`, ProductTypeList→ChipList→ScreenSizeList→RamSsdSettings | placeholder fairPrice 모델부터 불일치 | 제품/chip/screen/RAM/SSD 계층, Mac mini 화면크기 단계 생략, Android 순서 |
| 개별 감시 조건 | `MacBookAirSettingCard`, `upsertItem`, `AlertBoundMapper`, `FriendlyPriceText` | 없음 | 내 시세/목표가격/이상·이하/가격 bound/키워드/알림/후보알림/priority/금액 설명 및 서버 저장 |
| 일괄 조건 | `RamSsdSettingsScreen`, `bulkSet*`, `applyBulkUpsertFallback` | 없음 | 현재 chip/screen 또는 전체 제품 범위, enabled/notice/priority/drop rate/min/max/reset, 부분 실패 보고 |
| 조건 refresh | `refreshSettings/refreshSingleRuleSavedAt` | 없음 | 단순 재조회와 서버 규칙 saved_at 갱신 부작용 구분; 단건/전체 갱신 결과와 시각 |
| 추천 키워드 | `MacBookAirSettingCard`가 API03 응답의 `recommended_search_keyword` 표시 | 없음 | custom/effective/recommended 검색어 구분. 별도 `getRecommendedKeywords` API33은 선언만 존재 |
| 알림 권한·push | `MainActivity` POST_NOTIFICATIONS, `fcm/PushTokenManager`, `UMTPFirebaseMessagingService` | entitlement/delegate/SDK/권한/token/API 전부 없음 | iOS notification 허가 및 APNs/FCM 계약 확인, token 갱신/로그인/오류 재시도, foreground 처리 |
| 알림 클릭 이동 | `MainActivity.handleIntent/onNewIntent`, `initialTargetAlertId` | 없음 | cold/warm launch `alert_id` 큐를 유지하고 로그인 후 알림 탭/해당 항목 이동 |
| 외부 앱/복사 | Alert/Archive 화면 `ACTION_VIEW` 및 클립보드 복사 | 없음 | HTTP(S) 검증·Safari/openURL·클립보드·실패 안내. ACTION_SEND/공유 확장은 활성 기능이 아님 |
| 생명주기 | Android onResume 갱신, 10초 ViewModel coroutine | iOS scenePhase 관찰 없음 | active refresh/polling, inactive/background task 취소, 사용자 교체 시 이전 요청 결과 격리 |

Android `UmtpUrlAnalyzeScreen`/`WatchRuleSettingsScreen`는 `MainActivity`의 실제 탭 또는 `SettingsNavigator`에서 호출되지 않는다. 이 둘과 사용하지 않는 API 선언은 별도 Android call-site 조사로 활성 여부를 확정해야 하며, 존재하는 파일만 근거로 활성 메뉴로 추가하지 않는다. Android Manifest에는 MAIN/LAUNCHER만 있고 VIEW URL scheme/App Link intent-filter는 없다. 따라서 현재 active deep link는 push extra `alert_id`다. iOS Universal Link 지원을 Android의 기존 기능이라고 잘못 주장해서는 안 된다.

## 5. 네트워크와 데이터 기술 차이

- iOS: URLSession + JSONEncoder/Decoder, timeout request/resource 모두 10초, POST JSON 전용. Android: Retrofit/OkHttp, GET/POST/PATCH/query/path/body, boolean에 bool/0/1/yes/no/on/off 허용, 자체 DNS-over-HTTPS fallback. 실제 네트워크 설정값은 Android/환경 조사 문서에 상세 기록해야 한다.
- iOS 알림 id:String → Android id:Long, 필수 title/message/createdAt → nullable/snake_case timestamp. 기존 모델로 GET을 붙이면 decoding 실패한다. 활성 데이터와 맞게 모델 교체가 필요하며, 해당 placeholder 모델은 저장된 로컬 데이터가 없다.
- iOS UserFairPriceItem(symbol/fairPrice)은 Android 제품·스펙·사용자 rule 모델과 무관한 stub이다. 실제 서버 계약의 optional/default/override 상태를 모델에 반영해야 한다.
- iOS는 401/403을 세션 만료로 해석하거나 사용자 ID를 자동 삭제하는 현재 동작이 없다. 서버 인증 계약 증거 없이 네트워크 장애/권한 응답을 로그아웃으로 바꿔서는 안 된다.
- Android는 HTTP body/debug history raw body를 로그한다. iOS에 사용자 데이터/서버 상세 오류/토큰 로그를 그대로 이식할 필요가 없다.
- 로컬 DB/CoreData/SwiftData/cache repository/Keychain/파일 저장/설정 마이그레이션은 기존 iOS에 없다. URLSession 기본 캐시 외 별도 애플리케이션 캐시도 없다.

## 6. Xcode/테스트 조사

- 프로젝트: `ios/UMTP_IOS/UMTP_IOS.xcodeproj/project.pbxproj`.
- target `UMTP_IOS` 하나, 제품 유형 application. Unit/UI Test target 없음. `.xcscheme`, Package.swift, Podfile, XCTest source 없음.
- `PBXFileSystemSynchronizedRootGroup`를 사용하므로 앱 폴더 아래 새 Swift 소스는 자동 포함된다. `@main` 테스트 실행 파일을 앱 소스 폴더에 넣으면 안 된다.
- iOS deployment target 17.0; iPhone/iPad 지원; Swift language version 5.0; `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`, approachable concurrency 사용. 새 서비스/프로토콜/테스트의 actor-isolation을 확인해야 한다.
- Bundle ID `boongtol.UMTP-IOS`; signing automatic. 생성 Info.plist 사용. 현재 Push entitlement, associated domains, background modes, URL types 없음. 외부 Swift Package 의존성 없음.
- `APIClient`는 이미 URLSession 주입 가능하므로 URLProtocol transport double로 실제 JSON/HTTP/query/error 처리를 테스트할 수 있다. `UserAPIProtocol`도 등록 VM 테스트 주입점이다. UserSessionService는 기본 UserDefaults 인스턴스를 주입 가능하게 바꾸면 실제 사용자 데이터를 건드리지 않고 migration/세션 테스트 가능하다.
- 테스트 우선순위: 전체 contract JSON decoding, boolean/optional/null, 가격 bound·%/정렬/날짜, read HTTP fallback, bulk scope/부분 실패, sparse 거래 patch/입력 검증, 중복·취소·계정변경 상태, 세션 기존 키 복원.
- 실행/UI 확인 우선순위: 등록 화면/4탭/제품 계층/알림 상세/보관함 확인 dialog/거래 form·keyboard·history/빈·오류·재시도/foreground 복귀/알림 click.

## 7. 파일 충돌 없는 구현 분할 제안

1. 주 에이전트: `ContentView`, `MainTabView`, `AppState/UMTPApp`, `APIClient`, session/UserAPI, Xcode project/tests/scheme, 주요 문서와 Git. 공통 contract/access API naming을 먼저 공유한다.
2. 알림 묶음: `Models/AlertModels`, `Services/AlertAPI`(신규), `AlertPollingService`, `AlertFeedViewModel`, `Views/AlertFeedView`, 신규 ReadArchive/AlertDetail. alert→거래 callback과 pending alert ID 계약 공유.
3. 설정 묶음: `Models/UserFairPriceModels`, 신규 SettingsAPI, `SettingsViewModel`, `Views/SettingsView` 및 신규 계층/편집 뷰. 공통 client를 변경하지 않고 이미 합의한 메서드 사용.
4. 거래 묶음: 신규 TradeModels/TradeAPI/TradeViewModel/TradeViews. alert/archive 시작과 메인 탭 선택 callback 계약 공유.
5. 푸시 묶음: 앱 entrypoint/project를 주 에이전트가 소유한다면 신규 NotificationService/delegate 코드와 설정 제안을 별도로 전달. 서비스 백엔드와 FCM/APNs token 형식 확인 후 통합.

조사 기준의 iOS는 작은 Stage1 앱이었으므로 파일 동시 수정 충돌을 피하는 분할이 필요했다. 현재 구현도 SwiftUI/Combine/URLSession 및 기존 등록 흐름을 확장했다. 이 baseline 목록 자체를 구현·실행 검증 완료의 증거로 사용하지 않는다.
