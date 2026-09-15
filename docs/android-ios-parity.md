# Android → iOS 기능 동등성 작업

## 기준과 Git 보존

- 시작 2026-09-15, Android/iOS 기준 `da769c31ba4afdfa5d3b07ad9ecca2c39d7cbb04`.
- 시작 `main`에서 `feat/ios-android-parity` 생성. main과 origin/main은 같았고 기존 feature branch 관례에 따라 작업을 분리했다.
- remote `origin`: `https://github.com/boongtol1/UMTP.git` (fetch/push). push하지 않음.
- 시작 staged/unstaged 없음. 기존 untracked `umtp/sql/seed_silicon_macbook_pro_fair_prices.sql`은 MacBook Pro 시세 복구용 SQL로 보이나 작성자는 확인 불가. 사용자 변경으로 보존하며 stage/commit하지 않는다.
- 저장소 및 상위 경로에서 AGENTS.md/CLAUDE.md/CONTRIBUTING 없음. 각 프로젝트 README는 실제 코드와 대조했다.
- 기존 SwiftUI + ObservableObject/ViewModel + URLSession + UserDefaults 구조 유지. 기존 `umtp_user_id`, `umtp_ios_fallback_device_id`와 bundle ID 보존.

## 환경과 baseline

- Mac arm64, Xcode 26.6 (17F113), Swift 6.3.3, iOS 최소 17.0.
- project `ios/UMTP_IOS/UMTP_IOS.xcodeproj`, 앱 target/scheme `UMTP_IOS`. 기존 테스트 target 없음.
- iOS Debug baseline 성공: `xcodebuild -project ios/UMTP_IOS/UMTP_IOS.xcodeproj -scheme UMTP_IOS -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/umtp-parity.PKH6ia/baseline-ios CODE_SIGNING_ALLOWED=NO build`.
- Android baseline: Android Studio JBR 사용. 기존 산출물 hash 읽기에서 10분 이상 정지(스택/lsof 증거)하여 해당 실행만 종료하고 임시 build/cache 경로로 재실행. **Unit Test 19개·Debug APK 모두 성공**(33초). 기존 산출물 보존. 로그 `android-isolated-build.log`.
- Android 실행: adb 연결 기기 및 AVD/system image 없음. SDK system image 설치 시도는 미동의 라이선스로 중단됨. 라이선스 동의나 임의 기기 등록을 수행하지 않음.
- iOS 통합 1차: Swift actor 기본 인자 오류 발견 후 optional 주입으로 수정. 2차 **XCTest 39개 성공(실패 0)**, 실제 iPhone 17 Pro iOS 26.5 Simulator. 증거 `unit-tests-2.xcresult`, `unit-tests-2.log`. 구성: Core 7 / Alerts 11 / Settings 12 / Trade 9. UI 테스트는 별도로 진행 중.
- 원본 실행 증거 `/tmp/umtp-parity.PKH6ia/`. 최종 명령·결과 요약은 이 문서에 보존한다.

## 전체 조사와 기능 대응표

상세 기능 행의 Android 근거 파일/주요 심볼/진입/입력/기대 결과/예외는 다음 문서에 연결되어 있다. 아래 표는 같은 ID의 iOS 구현 및 검증 상태를 추적한다. 조사·구현·검증은 독립 상태이며 빌드 통과만으로 기능 검증을 완료하지 않는다.

- [Android 전체 화면·서비스·저장·진입점 조사 및 세부 기능 행](parity-android-inventory.md)
- [기존 iOS 전체 조사 및 실제 도달성](parity-ios-inventory.md)
- [API/백엔드 계약 및 사용·미사용 호출 대조](parity-api-contracts.md)

| 기능 ID | 이름/입력 → 기대 결과 | 기존 iOS와 차이·필요 변경 | 조사 | 구현 | 검증 | 방법·실제 결과·증거 | 관련 commit | 플랫폼 차이·외부 의존·미해결 |
|---|---|---|---|---|---|---|---|---|
| AUTH | ID 등록/로컬 세션 복원/재실행 → 같은 계정 | 등록 존재, 기존 식별자 보존 강화 필요; 서버 기기 조회 API 없음 | 완료 | 진행 | baseline만 | 등록 baseline build 성공 | — | 기존 ID/설정 보존; 자동 서버 기기조회는 Android에도 없음 |
| NAV | 탭·뒤로 → 알림/보관함/거래/설정 | 실제 루트는 placeholder; 기존 MainTabView 연결 | 완료 | 진행 | 미검증 | Simulator 예정 | — | NavigationStack |
| ALERT | 목록/상세/검토완료/새로고침 | 전체 stub; 서버 읽음·10초 폴링·상세 이식 | 완료 | 진행 | 미검증 | 계약·상태·UI 예정 | — | foreground만 주기 조회 |
| ARCHIVE | 제품/칩/화면·목록·선택/전체 삭제 | 없음; 서버 보관함·명시적 삭제 이식 | 완료 | 진행 | 미검증 | 계약·상태·UI 예정 | — | 서버 저장 |
| SETTINGS | 제품 트리/단일·일괄 조건/검색 새로고침 | stub; 가격·방향·경계·priority·검색어·부분 실패 | 완료 | 진행 | 미검증 | 수치·요청·상태·UI 예정 | — | 시스템 스펙 목록 API |
| TRADE | 자동채움/구매/재판매/기록·삭제 | 없음; Android 현재 2모드 UI·journey 전이 이식 | 완료 | 진행 | 미검증 | 계약·계산·상태·UI 예정 | — | 서버 prefill·매물 조회 |
| PUSH | 토큰 갱신/수신/알림 누름 → 해당 상세 | 없음; FCM/APNs client와 route 필요 | 완료 | 진행 | 미검증 | payload·routing·Simulator 예정 | — | 서버 android 필터와 Firebase iOS/APNs 설정 |

## 근거로 확인한 차이와 설계

- Android README의 30초/로컬읽음/샘플피드는 현재 코드와 다르다. 실제 폴링 10초, 서버 읽음, 명시적 검토완료이며 이를 따른다.
- Android MainActivity는 현재 4탭. 수동 URL 분석/WatchRuleSettingsScreen와 추천 키워드 별도 API 및 bulk 전용 API는 현재 진입/호출 없는 코드로 분리한다.
- Android 원시 응답/BODY 로그·일부 200 ok:false 성공 오판을 복제하지 않는다. API 오류 문구는 안전하게 고정하고 서버 메시지/주소/토큰을 노출하지 않는다.
- 인증은 기존 user_id/device_id 계약이다. 실제 존재하지 않는 Bearer 인증이나 로그아웃 서버 API를 만들지 않는다.
- 원격 푸시 차단: `umtp/src/notification_worker.py`가 `platform="android"`만 조회한다. iOS 등록만으로 발송 불가. 최소 서버 변경안과 외부 설정을 후속 기록하며 다른 iOS 작업을 진행한다.
- 실제 API 기능을 항상 성공/샘플 데이터로 대체하지 않는다. 테스트의 모의 응답은 테스트 전용 URLSession 주입으로 격리한다.

## 남은 작업 및 이어받기

- 주 에이전트: APIClient, 인증·세션, 앱 routing/push, Xcode 테스트 구조, 전체 통합/검증/commit.
- 설정 에이전트: UserFairPriceModels, SettingsAPI/ViewModel/View + SettingsParityTests.
- 알림 에이전트: AlertModels, AlertsAPI/ViewModel/Polling, Feed/Archive/Detail + AlertsParityTests.
- 거래 에이전트: ResaleTradeModels/API/ViewModel/View + TradeParityTests.
- 완료 상태는 구현·테스트 결과에 따라 기능별 세부 행으로 갱신할 것. 현재 전체 이식 완료 아님.

## 생성 commit

- `94623b7` — Android/iOS/API 전체 조사·baseline 기록.
- 공통 API/인증/테스트 구조 commit 준비: 39개 통합 Unit Test 통과. 추가 UI 및 푸시 검증 진행 중.
