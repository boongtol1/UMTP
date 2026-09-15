# Android → iOS 기능 동등성 작업

## 현재 판정과 기록 기준

**활성 iOS 기능의 구현·연결과 최신 전체106개(단위86+UI20) 로컬 검증을 완료했다.** C15 commit 후 R-FINAL4는 실패0·skip0·exit0이며 UI 실행은620.650초였다. Android 활성28개 ID·기존 iOS 로그아웃 보존1개와 DNS 하위 NET-DNS를 아래30개 ID로 추적하며 마지막 독립 검토에서 추가 확정 누락은 없었다. C14 안내 수정·C15 cold-start 격리를 포함하고 최신 Simulator Release/서명 없는 기기용 컴파일도 통과했다. 이전 기대값/DNS 단위 실패와 중단 실행은 이력으로 보존한다. 실서비스 사용자 쓰기·원격 APNs·서명된 실기기·Android 실제 화면 비교·실제 iOS DNS 장애망은 별도 외부 검증으로 남으므로 모든 환경에서의 동등성까지 완료했다고 판정하지 않는다.

- Android 기준 commit: `da769c31ba4afdfa5d3b07ad9ecca2c39d7cbb04`.
- 기존 iOS 기준 commit: 위와 동일. 작업 branch: `feat/ios-android-parity`.
- 현재 앱 체크포인트: `974762970a1ba566356bf5db7131c34419cf7bc7`(C15), 생성 commit C1..C15. 메인/거래 UI는 C11, 설정 탐색/초안은 C12, 권한/외부 연동은 C13, 시장가 안내는 C14, Debug Simulator 전용 cold-start 격리/테스트는 C15에 반영됐다. 신규 앱 소스는 모두 커밋됐고 이후 소스 변경 없이 R-FINAL4 전체106개가 통과했다. 이 대응표·세 조사 문서·iOS README는 C16 최종 문서 묶음이다. 최종 문서 commit은 자기 hash를 본문에 추정하지 않고 완료 후 `git log -1`로 확인한다.
- 원본 조사: [Android 전체 진입점·활성 기능](parity-android-inventory.md), [변경 전 iOS 전체 파일·도달성](parity-ios-inventory.md), [Android 34개 API 선언·백엔드 계약](parity-api-contracts.md).
- 세 문서는 조사 증거다. 실제 실행 결과와 최신 구현 상태는 이 문서의 기능별 상태·검증 증거를 우선한다.

## Git 상태 보존과 저장소 관례

- 시작 branch는 `main`, 시작 HEAD는 위 기준 commit이며 `origin/main`과 같았다. 기존 feature branch 관례를 확인하고 이번 작업을 분리하려고 `feat/ios-android-parity`를 새로 만들었다.
- remote `origin` fetch/push: `https://github.com/boongtol1/UMTP.git`. remote push는 수행하지 않았다.
- 시작 staged/unstaged 변경 없음. 기존 untracked `umtp/sql/seed_silicon_macbook_pro_fair_prices.sql`은 MacBook Pro 시세 복구용 SQL로 추정되지만 작성자는 확인할 수 없다. 사용자 변경으로 보존하며 이번 stage/commit 대상에서 제외한다. stash/reset/restore로 제거하지 않았다.
- 저장소 및 상위 경로에 AGENTS.md/CLAUDE.md/CONTRIBUTING 없음. 루트 README는 없으며 Android·iOS·백엔드 README를 실제 코드와 대조했다.
- 기준 iOS는 이미 SwiftUI + Combine ObservableObject/ViewModel + URLSession + UserDefaults다. 프레임워크 전환이나 전체 재작성이 아니라 기존 계층과 컴포넌트를 확장했다.
- bundle ID `boongtol.UMTP-IOS`, 기존 저장키 `umtp_user_id`, `umtp_ios_fallback_device_id` 유지. IDFV/기존 fallback을 Keychain 기반 식별자로 승계하되 업데이트 시 기존 사용자의 기기 ID를 임의 교체하지 않는다.
- 각 주요 묶음은 관련 테스트와 diff를 확인한 뒤 필요한 파일만 stage한다. C3..C14는 각 commit의 독립 체크포인트 build를 통과했다. 추가 cold-start 격리/테스트는 R-COLD2 통과 후 C15로 커밋했고 최종 문서는 별도 커밋한다.

## 환경·실행 증거

- Mac arm64, Xcode 26.6 (17F113), Swift 6.3.3, 앱 최소 iOS 17.0.
- 실제 project: `ios/UMTP_IOS/UMTP_IOS.xcodeproj`, 앱 target/scheme `UMTP_IOS`. 기준에는 테스트 target이 없었고 이번 작업에서 Unit/UI Test target·공유 scheme을 추가했다.
- Android: `android/` Gradle 프로젝트, Android Studio JBR 사용. 실제 기기/AVD 없음.
- iOS 실기기: paired iPhone15Pro(iOS27.0)가 존재하며 developer mode는 enabled다. 설치된 Xcode는26.6뿐이다(`paired-device-final.json`/`.log`). 최신 직접 기기 빌드는 developer disk image 마운트 실패/목적지 timeout(exit70), 별도 generic signed build는 provisioning profile 부재로 실패했다. DDI 실패를 developer mode OFF로 해석하지 않는다. 서명 없는 기기용 컴파일만 성공했으며 설치/실행은 미검증이다.
- 백엔드: `umtp/src/api_server.py` 및 설정·알림·거래·push service를 읽기 조사했다. 백엔드 기능 변경이나 실서비스 사용자 데이터 쓰기를 검증 명목으로 수행하지 않았다.
- 재시작 전 실행 증거 디렉터리: `/tmp/umtp-parity.PKH6ia/`. **환경 재시작 후 이 디렉터리 전체가 없어져 기존 xcresult/log/첨부 자료를 현재 다시 열 수 없다.** 아래 과거 결과는 당시 실행과 대화 기록에서 확인한 이력이며, 원본 파일을 현재 보유한다는 뜻이 아니다. 자격정보·응답 원문을 문서에 복사하지 않는다.
- 재시작 후 빌드·로그·검증 자료의 보관 루트: `/Users/boongtol_air/Library/Developer/UMTPParity/20260915-resume/`. 패키지 캐시·기존 Simulator·loopback fixture를 복구하고 최신 코드를 다시 검증한다. 새 실행의 최종 결과가 확인되기 전에는 과거 성공을 새 실행 성공으로 기록하지 않는다.

아래 E-* 표의 파일명은 별도 명시가 없으면 **현재 없는 재시작 전 경로**를 가리킨다. E-UI-T3/E-U-T4/E-UI-T4/E-R1도 재시작 전 관찰 기록이며 원본 파일 재확인은 불가능하다.

| 증거 ID | 실제 실행 / 대상 | 결과 | 증거 위치·제한 |
|---|---|---|---|
| E-I0 | 변경 전 iOS Debug / generic iOS Simulator / signing 없음 | 성공 | `baseline-ios-build.log`, `baseline-registration.png`; 기능 동등성 통과를 뜻하지 않음 |
| E-A0 | 변경 전 Android 기본 build/cache 실행 | 중단 | `baseline-android.log`; 기존 산출물 hash 읽기에서 10분 이상 정지, stack/lsof로 확인 후 해당 실행만 종료 |
| E-A1 | 별도 임시 build/cache의 Android Debug APK + Unit Test | APK 성공, **19개 테스트 통과** | `android-isolated-build.log`, `android-build/app/reports/tests/testDebugUnitTest/`; 약33초, 기존 산출물 보존 |
| E-A-RUN | Android 기기/AVD 확인 및 SDK image 설치 시도 | 실행 미검증 | `android-image-install.log`; 기기·AVD·system image 없음, 라이선스 미동의로 설치 중단. 임의 동의하지 않음 |
| E-U2 | 통합 XCTest, iPhone 17 Pro / iOS 26.5 Simulator | **39개 통과 / 실패0** | `unit-tests-2.xcresult`, `unit-tests-2.log`; Core7 + Alerts11 + Settings12 + Trade9. 이후 추가 회귀 수정·추가 테스트·푸시는 이 결과에 포함되지 않음 |
| E-UI1 | 최초 XCUITest / 같은 Simulator / loopback fixture | **9개 중4개 통과·5개 실패, 전체 실패** | `ui-tests-1.xcresult`, `ui-tests-1.log`, `ui-attachments/`; 아래 상세 참조 |
| E-LIVE | 실제 서비스 GET `/health`, GET `/macbook-air-units` | 두 조회 성공 | units 응답 `live-units.json`, health는 주 에이전트 실행 기록. 등록/읽음/설정/거래/토큰 저장 등 다른 실서비스 계약은 미검증 |
| E-DNS-LIVE | macOS CLI에서 실제 AppConfig/APIClient/DNSRecovery 컴파일→최초DNS실패만 주입→실제native PrivacyContext설정→실제URLSession HTTPS health조회 | 성공: `health_ok=true attempts=2` | `NativeDNSHealthHarness.swift`, `native-dns-health.log`; 원URL/Host/TLS유지. 실제망DNS장애 재현·iOS실기기·선택된DoH resolver 확인이 아님. 시스템DNS설정/사용자API쓰기 없음 |
| E-PKG | Firebase iOS SDK resolve/clone 및 앱 컴파일 | 의존성 확보 후 Firebase 포함 Simulator 컴파일 성공 | `package-resolve.log`, `firebase-shallow.log`, `unit-tests-3.log`; 최초 source clone/SPM 60초 다운로드 timeout 뒤 공식 tag/SHA를 확인한 cache로 재시도. 원격 FCM/APNs 성공 증거는 아님 |
| E-U3 | Firebase 포함 통합 XCTest, 실제 iPhone 17 Pro / iOS 26.5 Simulator | **58개 중57개 통과·1개 실패, 전체 실패** | `unit-tests-3.xcresult`, `unit-tests-3.log`; Core7/Alerts12/Settings20/Push4 모두통과, Trade15 중14통과/1실패. 불가능한 ISO 날짜 자동보정 문제는 후속수정 후 E-U4에서 통과 |
| E-U4 | 날짜 수정 + DNS 복구 + Firebase 포함 통합 XCTest / 같은 실제 Simulator | **67개 모두 통과 / 실패0** | `unit-tests-4.xcresult`, `unit-tests-4.log`; Alerts12/Core7/DNS9/Push4/Settings20/Trade15. 날짜 자동보정 회귀 포함, 운영서비스/APNs 검증 아님 |
| E-UI2 | 후속 XCUITest 12개 / Simulator / loopback fixture | **10개 통과·2개 실패, 전체 실패** | `ui-tests-2.xcresult`, `ui-tests-2.log`; 알림기존4·등록1·push1·설정3·잘못된거래입력1 통과. 새draft교체확인1 및 수동구매저장1 실패. runner 재시작 뒤0tests 로그가 있어도 실패case와최종TEST FAILED를 기준으로 집계 |
| E-UI-T3 | `ui-targeted-3` / Simulator / loopback fixture | 인증 흐름 1개 통과, 초안 보호 테스트 실패 | 인증 실패 후 재시도→앱 재실행→로그아웃→기기 ID 보존 흐름 통과. 초안 교체 `.alert`는 표시됐으나 중첩 요소의 중복 접근성 ID로 조회 실패; 이후 `.firstMatch` 선택자로 수정 |
| E-U-T4 | `targeted-4`의 통합 단위 테스트 / Simulator | **67개 통과** | 재시작 전 관찰 결과. 이후 추가한 푸시 삭제 실패 처리 등 새 회귀는 당시 범위 밖이며 후속 R-UNIT-FINAL2 단위84개 및 최종 R-FINAL4 단위86개 결과와 구분 |
| E-UI-T4 | `targeted-4`의 대상 UI 테스트 / Simulator / loopback fixture | 초안 보호·전체 읽음/전체 비우기·잘못된 거래 확인정보 보존 통과, 보관함 선택 확인 실패, 마지막 수동 거래 결과 미상 | 보관함 선택은 `label.contains("선택됨")` 확인에서 실패. 마지막 수동 거래 실행의 최종 결과는 로그 소실로 확인할 수 없어 성공·실패 집계에서 제외 |
| E-R1 | `release-build-1` / Release / generic iOS Simulator | 성공 | 재시작 전 Release 빌드 관찰 결과. 최신 안내 수정 포함 빌드는 R-RELEASE2에서 별도 확인 |
| E-D1 | paired iPhone 15 Pro 대상 signed Debug build | 실패, 설치/실행 미검증 | `device-build-1.log`; `boongtol.UMTP-IOS` iOS App Development provisioning profile 없음. `-allowProvisioningUpdates`로 계정의 profile/기기를 임의 생성하지 않음 |
| E-C3 | C3 푸시 commit의 독립 detached 체크포인트 / Debug generic Simulator build | 성공 | `checkpoint-push.log`; 해당 commit까지의 소스만 빌드, 사용자 working tree의 후속 구현으로 성공을 보완하지 않음 |
| E-C4 | C4 DNS commit의 독립 detached 체크포인트 / 같은 build | 성공 | `checkpoint-dns.log`; 해당 commit까지의 누적 tree 기준 |
| E-C5 | C5 설정 commit의 독립 detached 체크포인트 / 같은 build | 성공 | `checkpoint-settings.log`; 해당 commit까지의 누적 tree 기준 |
| E-C6 | C6 알림/보관함 commit의 독립 detached 체크포인트 / 같은 build | 성공 | `checkpoint-alerts.log`; 해당 commit까지의 누적 tree 기준 |

E-UI1의 실제 결과:

- 통과: `ParityUITests.testRegistrationValidation`.
- 통과: `SettingsFlowUITests.testIndividualPriceDirectionAndBoundReachTheAPI`, `testMacMiniSkipsScreenSizeAndSupportsBackNavigation`, `testUnsavedPriceSurvivesTabRoundTripWithoutWritingServer`.
- 실패: AlertFlow의 명시적 읽음→보관함→거래, 미읽음→거래, 장애→복구 3개. 카드 제목을 StaticText로 찾았으나 실제는 Button인 locator 문제를 확인하여 접근성 ID/테스트를 수정했다. 후속 E-UI2에서 이3개와 실패한 거래시작 재시도1개가 통과했다.
- 실패: TradeFlow의 수동 prefill→구매저장→내역, 잘못된 확인정보 보존 2개. 후속 E-UI2에서 잘못된 확인정보 보존은 통과했으나 수동 구매 흐름은 `TradeFlowUITests.swift:126`의 키보드 표시 대기에서 실패했다. 당시 로그·화면 녹화·접근성 조사에서 빈 날짜 입력칸의 중앙을 눌러도 키보드가 표시되지 않는 것을 확인했다. 44pt 터치 영역과 `FocusState` 보완만으로 해결되지 않았으며 재시작 후 Form 행 구조를 수정한 R-SR2에서 수동 구매 흐름이 통과했다.
- 후속 E-U3에서 archive/alert 거래 시작 재시도, bulk draft 재조정, 서버 저장 성공 뒤 재조회 실패, 100% 가격차이/0원 목표값, 현재시각 UTC offset, push route/token 경쟁 등을 실행해 통과했다. 다만 `TradeParityTests.testServerSupportedDateOnlyAndISOTimeZoneInputs`가 `2026-02-30T14:20:00Z`를 ISO formatter가 자동보정하여 실패했다. strict 날짜/시간 component 검증과 회귀를 추가한 뒤 E-U4에서 통과했다.
- 날짜 수정/DNS 추가 후 E-U4의 단위 테스트 67개가 모두 통과했다. E-UI2에서 등록 1개·설정 3개·기존 알림 흐름 4개·Simulator 푸시 1개·잘못된 거래 입력 1개는 통과했다. 새 `testAlertTradeNavigationPreservesDraftUnlessReplacementConfirmed`는 “계속 작성” 선택 단계에서 실패했고, 수동 구매 1개는 키보드 표시 대기에서 실패했다. 총 12개 중 10개 통과·2개 실패이며 전체 UI 성공으로 보고하지 않는다.
- 이후 E-UI-T3에서는 인증 재시도·세션 복원·로그아웃·기기 ID 보존을 확인했다. 초안 교체 확인창의 중복 접근성 ID 조회를 `.firstMatch`로 수정한 뒤 E-UI-T4에서 초안 보호가 통과했다. E-UI-T4의 전체 읽음/보관함 전체 비우기와 잘못된 거래 확인정보 보존도 통과했으나, 보관함 선택 상태의 접근성 확인은 실패했고 마지막 수동 거래 결과는 알 수 없다.

### 2026-09-15 재시작 인계

- 과거 E-* 실행 결과와 원본 자료의 현재 부재를 함께 유지한다. 사라진 `/tmp` 로그·빌드·패키지 경로를 재사용 가능한 자료로 취급하지 않는다.
- 새 보관 루트에서 C14 안내 수정을 포함한 R-FINAL3 전체103개(단위84+UI19)·C14까지 독립 빌드를 확인했다. 같은 안내 수정을 포함한 Release/서명 없는 기기용 컴파일도 통과했으며 서명된 실행의 profile/DDI 차단은 별도 기록한다.
- R-FINAL 전체 UI19개 성공 후 레이아웃 수정 전 binary로 시작한 R-FINAL2는 중단했다. 수정 후 R-FINAL3 전체103개는 통과했고 새 안내 화면도 직접 확인했다. 추가 cold-start 격리 실행의 실패/재시도는 R-COLD1/R-COLD2로 분리하며 중단/실패 실행을 전체 성공으로 바꾸지 않는다.

### 재시작 후 검증·수정 기록

아래 경로는 모두 새 보관 루트 기준이며 현재 원본이 있다. 실패가 포함된 실행을 전체 성공으로 취급하지 않는다.

| 증거 ID | 실행 | 실제 결과 |
|---|---|---|
| R-TA1 | `trade-archive-1.log` / `.xcresult` | 거래 단위15개 통과, 보관함 선택/전체 처리 UI2개 통과, 잘못된 거래 입력 UI 통과, 수동 구매 날짜 키보드 대기 실패 |
| R-M2 | `manual-trade-2.log` / `.xcresult` | 하단 탭바 효과 영역을 피해 입력칸 전체를 노출한 뒤에도 수동 날짜 키보드 대기 실패 |
| R-M3 | `manual-trade-3.log` / `.xcresult` | **단위72개 모두 통과**(Core7/Alerts12/DNS9/Push9/Settings20/Trade15). UI는 날짜 키보드 대기와 알림 설정 앱 페이지 확인 2개 실패 |
| R-M4 | `manual-trade-4.log` / `.xcresult` | 시작 reference 입력의 실제 소프트웨어 키보드는 표시됨. 날짜 칸 포커스 실패는 전체 Simulator 키보드 비활성 문제가 아님 |
| R-M7 | `manual-trade-7.log` / `manual-trade-7.xcresult` | **단위77개 모두 통과**(Core7/Alerts12/DNS9/Push9/Settings20/Trade20). 수동 거래 UI는 `purchased_at` 키보드 표시 대기에서 실패. 후속 UI·코드 전체 통과가 아님 |
| R-C7 | `checkpoint-c7.log` | `4a4a4bd`만의 독립 detached tree Debug generic Simulator build 성공 |
| R-C8 | `checkpoint-c8.log` | `411fba8`만의 독립 detached tree Debug generic Simulator build 성공 |
| R-I1 | 후속 통합 UI 1차 실행·개별 관찰 | 당시 기록401 되팔이 수정은 통과. 선택 삭제의 잘못된 전체 확인창과 외부 링크 복귀 상태 확인은 실패, 권한 변경은 미검증이었다. 이 부분 관찰을 전체 실행 통과로 집계하지 않으며 이후 수정/통과는 R-M9/R-FINAL/R-PERM1에서 별도 기록 |
| R-A1 | `android-isolated-build-1.log`, `android-isolated-1.init.gradle`, `android-build-1/app/reports/tests/testDebugUnitTest/index.html` 및 test-results | 오프라인 JBR21·Gradle9.4.1 격리 실행 약49초: Debug APK 성공, 단위19개 통과·실패0·skip0. Android 소스와 기존 산출물은 변경하지 않음; Android 앱 실행 검증은 아님 |
| R-LIVE | 원본 HTTPS GET `/health`, `/macbook-air-units`; `live-health.json`, `live-units.json` | 두 조회 성공, health `ok=true`. paired iPhone15Pro도 다시 확인했으나 신규 서명/설치 또는 실서비스 사용자 데이터 쓰기는 수행하지 않음 |
| R-FD | `focus-diagnostic` 대상 UI 실행 | 설정3개 통과, 새 일괄 속도/최소/최대·개별 시장가·탐색 경로 보존 및 HTTP 쓰기 없음 검증 포함. 수동 구매 날짜 입력 UI는 실패 |
| R-M8 | `manual8` 대상 UI·개별 관찰 | 외부 링크 UI 전체 통과. 거래 선택 삭제의 확인창·API 범위·취소는 통과했으나 마지막 KEEP 행 조회 도우미의 과도한 하단 경계 조건으로 해당 테스트는 실패. 도우미 수정 후 R-M9에서 통과 |
| R-M9 | `manual-trade-9.log` / `.xcresult` | 선택/전체 완료 거래 삭제 UI 전체 통과: 각각 취소 시 쓰기 없음·선택 ID/전체 범위·구매/KEEP/다른 사용자 기록 보존. 날짜 입력과 알림 설정 페이지 확인은 실패 |
| R-M10 | `manual-trade-10.log` | 진단 코드의 명시적 self 캡처 누락 3곳으로 컴파일 실패; 수정 후 R-M11 실행. 테스트 성공으로 집계하지 않음 |
| R-M11 | `manual-trade-11.log` / `.xcresult` | **단위79개 모두 통과**(Core7/Alerts12/DNS9/Push9/Settings20/Trade22). 정확 확인만 변경한 KEEP 단계 보존·불필요 resale 호출 생략 회귀 포함. 날짜 입력 첫 글자 후 포커스 해제 및 Settings 알림 허용 스위치 변경 대기 실패 |
| R-C9 | `checkpoint-c9.log` | `ae839d9`만의 독립 detached tree Debug generic Simulator build 성공 |
| R-FOCUS | `focus-stack.log` / `.xcresult`, `focus-diagnostic-events.log` | 날짜 UI 실패의 실제 `resignFirstResponder` 호출자는 `UICollectionView._resignOrRebaseFirstResponderViewWithIndexPathMapping`→SwiftUI List batch update. 입력 컨트롤 교체/비활성화가 아니라 Form 행 재배치임을 확인; 후속 R-SR1/R-SR2에서 수정 검증 |
| R-SR1 | `stable-row-1` 대상 UI | 안정된 Form 행 구조 적용 후 수동 구매 UI 통과, 약57초. 진단 코드와 native 입력 대안을 포함한 중간 실행 |
| R-SR2 | `stable-row-2` 대상 UI | 진단/native 입력 대안을 제거한 SwiftUI 전용 구현으로 TradeFlow 2개 모두 통과, 약130초. 수동 입력→구매 저장→내역 및 잘못된 확인정보 보존 검증 |
| R-PERM1 | `permission-toggle-1` 대상 UI·화면 첨부 | 1개 통과, 37.145초·skip0. 실제 시스템 스위치 OFF→앱의 거부 안내→ON→앱의 허용 상태 갱신 확인. `permission-toggle-1-attachments`의 9개 첨부 manifest와 회색 OFF·앱 안내·녹색 ON/알림/사운드/배지 화면을 직접 확인. 공식 설정 링크의 루트 도착 후 Apps 수동 탐색은 플랫폼 차이로 유지 |
| R-FINAL | `integrated-final-1` | **UI19개 통과·실패0·skip0, 약623초**. Alert5/Archive2/Authentication1/ExternalLink1/Permission1/Parity1/Push1/Settings3/TradeFlow2/TradeHistory2. 단위는83통과/1실패여서 bundle 전체는 **102통과/1실패·전체 실패**. 실패는 APIClient가 먼저 던지는 `APIClientError.serverRejected` 대신 `TradeError.server`를 기대한 테스트 오류; 원래 ID PATCH/POST 없음/초안 보존 동작은 통과. 기대값만 고친 단위 재실행은 R-UNIT-FINAL2/R-UNIT-C10 |
| R-FINAL2 | `integrated-final-2` | 안내 레이아웃 수정 전 코드로 이미 컴파일된 실행이어서 약2분 후 SIGINT로 중단. exit73, `TEST INTERRUPTED`. 전체 성공 결과 없음 |
| R-FINAL3 | `integrated-final-3.log` / `integrated-final-3.xcresult` | **총103개(단위84+UI19) 통과·실패0·skip0, exit0**. UI 594.045초. C14 안내 레이아웃/높이·본문 회귀 포함. `integrated-final-3-attachments/DB69BA00-9111-4FE8-95DC-69A39F27DA66.png`에서 두 문장·두 줄 전체 표시와 잘림 없음을 직접 확인 |
| R-COLD1 | `cold-launch-1.log` / `.xcresult` | **전체88개 중86개 통과·2개 실패·skip0, exit65·전체 실패**. 단위86개 중84개 통과/2개 DNS 실패(5개 assertion), cold UI 18.449초·warm UI 14.909초 모두 통과. 특수 fixture의 HTTP 기본 URL을 기존 DNS 단위가 사용해 HTTPS 전용 복구가 실행되지 않은 테스트 격리 문제. 실제 알림 cold launch 성공과 전체 실행 실패를 구분 |
| R-COLD2 | `cold-launch-2.log` / `.xcresult` | **전체88개(단위86+Push UI2) 통과·실패0·skip0·exit0**, UI 33.543초. Core9/Alerts12/DNS9/Push9/Settings20/Trade27. DNS 단위 mock client 7곳에 명시적 `https://api.example.invalid`를 주입하여 앱 fixture 기본값과 분리했으며 주입 transport/DNS 설정으로 외부 DNS 접촉 없음 |
| R-FINAL4 | `integrated-final-4.log` / `integrated-final-4.xcresult` | **C15 commit 후 전체106개 통과·실패0·skip0·exit0**. 단위86(Core9/Alerts12/DNS9/Push9/Settings20/Trade27)+UI20(Alert5/Archive2/Authentication1/ExternalLink1/Permission1/Parity1/Push2/Settings3/TradeFlow2/TradeHistory2). UI620.650초. `integrated-final-4-attachments/` 내보내기 및 마지막 UI 실제 요청 `final-fixture-events.json` 보관; 이후 앱 소스 변경 없음 |
| R-FIXTURE-RELEASE | `ReleaseFixtureIsolation.swift`, `release-fixture-isolation.log` | 실제 AppConfig를 DEBUG 없이 macOS native swiftc로 컴파일하고 loopback `UMTP_TEST_BASE_URL`을 지정해도 production URL을 반환하는 precondition **통과**. iOS Release 실행 또는 physical 빌드의 실행 증거는 아님. cold preflight는 일반 빌드에서 false, 전용 빌드에서 true 확인 |
| R-UNIT-FINAL2 | `unit-final-2.log` / `unit-final-2.xcresult` | **단위84개 통과·실패0·skip0**, xcresult 확인. Core7/Alerts12/DNS9/Push9/Settings20/Trade27. UI 실행을 방해하지 않도록 새 iPhone17Pro/iOS26.5 Simulator `UMTP Parity Unit Verification`(`A94689BC-66A6-4A20-9321-7D7BCD83E34D`)와 별도 derived data `unit-final` 사용. 기존 기기를 변경하지 않았고 첫 실행 대비 오류 기대값만 수정; Release/기기용 컴파일/UI와 앱 소스는 동일 |
| R-C10 | `checkpoint-c10.log` | C10 `a0db410`만의 독립 detached tree Debug generic Simulator **BUILD SUCCEEDED** |
| R-C11 | `checkpoint-c11.log` | C11 `b04318e`만의 독립 detached tree Debug generic Simulator **BUILD SUCCEEDED** |
| R-C12 | `checkpoint-c12.log` | C12 `a5e791d`만의 독립 detached tree Debug generic Simulator **BUILD SUCCEEDED** |
| R-C13 | `checkpoint-c13.log` | C13 `8d5dd38`만의 독립 detached tree Debug generic Simulator **BUILD SUCCEEDED** |
| R-C14 | `checkpoint-c14.log` | C14 `37cd0cb`만의 독립 detached tree Debug generic Simulator **BUILD SUCCEEDED** |
| R-UNIT-C10 | `unit-post-c10.xcresult` | C10 commit 후 전체 작업 트리 단위 **84개 통과·실패0·skip0**, xcresult 확인. 독립 detached commit만의 테스트로 분류하지 않음 |
| R-RELEASE | `release-final` | 최신 generic iOS Simulator Release **BUILD SUCCEEDED** |
| R-DEVICE-COMPILE | `device-unsigned-final` | 별도 derived data의 generic iOS Debug 서명 없는 기기용 컴파일 **BUILD SUCCEEDED**. 서명된 기기 빌드·설치·실행이 아님 |
| R-RELEASE2 | `release-final-2.log` | 시장가 안내 레이아웃 수정 포함 generic iOS Simulator Release **BUILD SUCCEEDED** |
| R-DEVICE-COMPILE2 | `device-unsigned-final-2.log` | 같은 안내 수정 포함 generic iOS Debug 서명 없는 기기용 컴파일 **BUILD SUCCEEDED**. 실제 기기 설치/실행 아님 |
| R-RELEASE3 | `release-final-3.log` | C15 포함 기본 설정 generic iOS Simulator Release **BUILD SUCCEEDED·exit0**. 빌드 Info의 fixture URL/compilation conditions는 모두 빈 문자열 |
| R-DEVICE-COMPILE3 | `device-unsigned-final-3.log` | C15 포함 기본 설정 generic iOS Debug 서명 없는 기기용 컴파일 **BUILD SUCCEEDED·exit0**. fixture Info는 빈 문자열. 실제 기기 설치/실행 아님 |
| R-STATIC | 최신 파일/격리 점검 | fixture `py_compile`(별도 evidence pycache), Info.plist/project.pbxproj `plutil -lint`, diff 공백 검사 통과. Android/backend tracked 코드의 기준 대비 변경 없음·패턴 기반 iOS/docs 비밀정보 스캔 매치 없음. 검출되지 않은 비밀정보까지 없음을 보장하는 검사는 아님 |
| R-LIVE-FINAL | R-LIVE의 원본 HTTPS 응답 파일 재확인 | 보관된 `live-health.json`의 health `ok=true`, `live-units.json`의 catalog units161을 재확인. 새 네트워크 요청을 실행한 기록이 아니며 실제 사용자 데이터 쓰기는 수행하지 않음 |
| R-DEVICE-SIGNED | `device-signed-final.log` | paired iPhone15Pro 대상 새 signed build **실패(exit70)**. destination timeout과 `The developer disk image could not be mounted on this device.` 확인. 설치/실행 없음; 기존 profile 실패와 별개의 기기 준비 장애 |
| R-SIGNING | `device-signing-final.log` | developer disk image 문제와 분리한 generic iOS signed build도 **실패: provisioning profile 없음**. 서명/설치 권한을 임의 생성하지 않음 |

- C7 = `4a4a4bd fix(ios): persist failed push token cleanup across sessions`. 토큰 삭제 실패 marker를 영구 보존하고 다음 activation에서 재시도, 동시 삭제/fetch 순서 및 재등록 차단을 검증했다. Firebase 설정 없는 빌드의 OS 권한 조회/요청은 계속 허용하며 새 삭제 marker를 만들지 않는다. 관련 Push 단위9개가 R-M3에서 통과했다.
- iOS 26.5 Simulator에서 `UIApplication.openNotificationSettingsURLString`은 Settings 앱 자체는 열었으나 앱별 알림 페이지가 아닌 설정 루트에 도착했다. 원본 `manual-trade-3-attachments/C383CBE5-E0D3-45B2-A09A-302303016192.png`를 시각 확인했다. 공식 API 계약은 [Apple 문서](https://developer.apple.com/documentation/uikit/uiapplication/opennotificationsettingsurlstring)를 따르며 비공개 URL scheme을 도입하지 않는다. 앱의 수동 경로 안내와 열기 실패 처리를 보완했고, Apps→정확한 UMTP 앱→알림의 실제 스위치를 조작한 R-PERM1에서 거부/허용 복귀 갱신이 통과했다. 실기기나 원격 APNs 검증은 아니다.
- C8의 거래 수정: 새 초안에 명시적 단계가 있으면 같은 user/source/product의 ID를 빈 purchase upsert로 확보한 뒤 단계와 되팔이 필드를 단일 resale PATCH로 보낸다. 준비 성공 후 저장 결과가 확인되지 않으면 성공을 표시하지 않고 초안을 유지하며 재시도한다. 재판매 URL은 JSON 배열/객체를 허용하는 이미지 파서 대신 단일 HTTP(S) URL·host·공백 검사를 사용한다. 요청 순서·본문·실패/동일 ID 재시도·엄격한 URL 회귀를 포함한 Trade20이 R-M7에서 통과했다.
- 원인 증거: backend `resale_trade_journeys.py:2714`의 필드 분리 후 `:2725`에서 resale PATCH, `:2732`에서 sold PATCH 또는 `:2739`에서 빈 resale PATCH를 호출한다. 두 번째 호출에는 명시 단계가 없어 `:1717`의 단계 파생이 이를 덮는다. 실제 함수를 DB 대신 메모리 상태로 실행했을 때 `KEEP + sale_price_krw=300000`은 `KEEP→SOLD`, `KEEP + resale_platform=joongna`는 `KEEP→RESALE_LISTED`가 됐다. 동일 ID 재사용 근거는 `:654`의 기존 identity 조회와 `sql/create_resale_trade_journeys.sql:75`의 `UNIQUE(user_id, source, product_id)`다. 실서비스 쓰기는 하지 않았다.
- C12 설정 수정: 같은 사용자로 탭 복귀할 때 `NavigationStack` 경로를 유지하고 일괄 기본값은 첫 표시 때만 초기화한다. 실제 scope 변경/서버 aggregate 변경은 계속 반영한다. 일괄 속도·최소/최대·개별 시장가 보존과 쓰기 요청 부재를 포함한 Settings3 UI가 R-FINAL에서 통과했다.
- 추가 UI: `TradeHistoryUITests`의 선택 기록 되팔이 수정은 R-I1, 선택/전체 삭제·취소·구매/KEEP/다른 사용자 보존은 R-M9에서 통과했다. `ExternalLinkUITests`의 복사·Safari·복귀는 R-M8, `NotificationPermissionUITests`의 실제 시스템 권한 OFF/ON·앱 상태 갱신은 R-PERM1에서 통과했다.
- C9 거래 수정: 기존 KEEP 기록의 정확 확인 정보만 되팔이 모드에서 바꾸면 보조 purchase 저장 후 빈 resale PATCH를 생략한다. 다른 모드 초안·성공 안내·내역 갱신은 유지하고, 확인정보 변경 없는 명시적 빈 resale 저장은 기존 계약을 유지한다. 이 회귀 2개를 포함한 Trade22/단위79개가 R-M11에서 통과했다.
- 키보드 수정: 입력 필드와 날짜 보조 버튼을 안정된 단일 Form 행 컨테이너 안에 묶어 입력 중 List 행 재배치를 막았다. native 입력 대안이나 진단 후킹에 의존하지 않는 최종 SwiftUI 코드로 R-SR2 TradeFlow 2개가 통과했다. 진단 로그/입력 대안 코드는 제거했다.
- C10 거래 후속 수정: 삭제 응답은 count만 제공하므로 명시적으로 선택한 ID 수와 삭제 수가 정확히 같을 때만 해당 초안을 해제한다. 0건·부분 삭제·전체 삭제는 원래 양수 ID와 초안을 보존하고 저장 전 최신 기록 확인을 안내한다. 200개 제한 내역에서 보이지 않는 것만으로 삭제를 단정하지 않으며 후속 저장도 같은 ID의 PATCH여서 묵시적 재생성을 하지 않는다. `2026-09-15 14:20:00+09:00` 같은 공백 구분 시간대 입력도 허용하되 잘못된 날짜/시간 거부는 유지한다. R-FINAL의 오류 타입 기대값 1개를 수정한 뒤 회귀 5개를 포함한 Trade27/단위84개가 R-UNIT-FINAL2에서 모두 통과했다.
- cold 화면 검수: R-COLD1에서 통과한 cold UI의 `cold-launch-1-attachments/D3FE0286-AE6D-4928-AFD1-0067614FB377.png`(종료 후 홈/알림 없음)→`F5AE1B74-8E7A-4837-9C01-97303A7D3438.png`(현재 OS 배너)→`0805D921-3D10-4282-B29D-E7DEB283C31C.png`(alert101 상세)를 직접 확인했다. 같은 bundle의 DNS 단위 실패는 별개로 보존한다.
- 최종 화면 검수: R-FINAL 첨부에서 거래 날짜 키보드/전체 입력값·저장된301/450,000원·삭제 후 KEEP403/구매404 보존·알림 상세26개 정보와 위험 v1/v2/v3를 직접 확인했다. `integrated-final-1-attachments`의 파일명이 `5CDB`로 시작하는 PNG에서 시장가 안내만 말줄임으로 잘린 것을 발견해 `.fixedSize(horizontal: false, vertical: true)`와 접근성 ID를 추가했다. 기존 Settings UI에 높이>30·전체 본문·화면 첨부 검증을 더했고 C14로 커밋했다. R-FINAL3 전체103개가 통과했으며 `DB69BA00-9111-4FE8-95DC-69A39F27DA66.png`에서 두 문장·두 줄 전체 표시와 잘림 없음을 직접 확인했다.
- C15 이후 최종 화면도 직접 검수했다. `integrated-final-4-attachments/F40B3C61-79FB-4FBD-B47E-11F0DEE45669.png`는 시장가 안내 두 문장·두 줄 전체 표시, `5D1F5ABA-A0CE-4400-B334-AEF758E9AE09.png`는 완료 목록 비움 후 구매404/KEEP403 보존, `6F6B227A-2A0C-4EA0-9023-5633534B885A.png`는 cold 알림 tap 후 alert101 상세를 확인하는 증거다.
- 실행 정리: `final-fixture-events.json` 보관 후 이번 작업이 시작한 loopback fixture 프로세스 PID26285만 TERM으로 종료했다. 이 서버 프로세스의 exit143은 정상 정리이며 R-FINAL4 테스트 exit0과 별개다. 기존 사용자 서버는 없었고 Simulator·로그·xcresult·빌드 산출물은 보존했다. 문서5개 외 추가 수정 없이 기존 untracked SQL만 제외/보존한 상태로 최종 문서 commit에 인계했다.

테스트 격리: [loopback fixture](../ios/UMTP_IOS/TestsSupport/parity_server.py)는 `127.0.0.1:18765` 메모리 상태만 사용한다. `POST /__reset`, `GET /__events`, 장애 주입 `POST /__fail`로 실제 앱 요청의 method/query/body와 상태를 검증한다. DEBUG의 `UMTP_TEST_BASE_URL`은 검증된 HTTP(S) loopback 주소에만 허용한다. OS cold launch는 XCTest 환경을 상속하지 않으므로 별도 DerivedData에 `UMTP_PARITY_FIXTURE_URL=http://127.0.0.1:18765`를 지정한 Debug Simulator 빌드를 사용한다. 설치 앱의 bundle ID·Simulator 플랫폼·정확한 fixture URL·DEBUG 조건을 preflight로 확인한 뒤 실제 로컬 등록→프로세스 종료 확인→simctl 알림 tap만으로 OS가 재실행하도록 검증한다. tap 이후 launch/activate를 호출하지 않고 alert101 상세·미읽음·GET 요청을 확인한다. bundled fixture는 Release/physical에서 무시하고 영구 UserDefaults API 변경을 만들지 않는다. 별도 DD를 사용하는 전체 UI 명령은 [iOS README](../ios/UMTP_IOS/UMTP_IOS/README.md#테스트)에 있다. fixture 테스트 성공과 운영 서버/DB 반영 성공을 구분한다.

재현에 사용한 baseline iOS 명령:

```sh
xcodebuild -project ios/UMTP_IOS/UMTP_IOS.xcodeproj -scheme UMTP_IOS -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/umtp-parity.PKH6ia/baseline-ios CODE_SIGNING_ALLOWED=NO build
```

위 명령은 과거 실행에 사용한 경로를 보존한 예시다. 재시작 후 test 실행 시 동일 project/scheme과 실제 Simulator destination을 사용하되 derivedDataPath/resultBundlePath/log는 새 보관 루트에 둔다. 원본 명령·최종 결과를 해당 log에 남기며, 아직 완료하지 않은 명령을 성공 목록에 올리지 않는다.

## 대응표 읽는 방법·근거 경로

아래 세 표는 **기능 ID로 결합되는 하나의 대응표**다. 첫 표는 Android 기능 명세, 둘째는 기존 iOS 차이와 구현 상태, 셋째는 검증·증거·commit·미해결 사항이다. 따라서 조사·구현·검증 상태가 서로를 대신하지 않는다.

- A = `android/app/src/main/java/com/boongtol/umtp_android/`.
- I = `ios/UMTP_IOS/UMTP_IOS/`.
- A-VM = [A/ui/MacBookAirSettingsViewModel.kt](../android/app/src/main/java/com/boongtol/umtp_android/ui/MacBookAirSettingsViewModel.kt), A-Main = [A/MainActivity.kt](../android/app/src/main/java/com/boongtol/umtp_android/MainActivity.kt).
- A-API = [A/network/UmtpApiService.kt](../android/app/src/main/java/com/boongtol/umtp_android/network/UmtpApiService.kt); API01..34는 [API 계약표](parity-api-contracts.md)의 ID.
- I-Alerts = `Models/AlertModels.swift`, `Services/AlertsAPI.swift`, `Services/AlertPollingService.swift`, `ViewModels/AlertFeedViewModel.swift`, `Views/AlertFeedView.swift`, `Views/ReadAlertArchiveView.swift`, `Views/AlertDetailView.swift`, `Views/AlertPresentation.swift`.
- I-Settings = `Models/UserFairPriceModels.swift`, `Services/SettingsAPI.swift`, `ViewModels/SettingsViewModel.swift`, `Views/SettingsView.swift`.
- I-Trade = `Models/ResaleTradeModels.swift`, `Services/ResaleTradeAPI.swift`, `ViewModels/ResaleTradeViewModel.swift`, `Views/ResaleTradeView.swift`.
- I-Push = `Services/PushService.swift`, `Views/NotificationSettingsView.swift`, `App/UMTPApp.swift`, `App/AppState.swift`, `Views/MainTabView.swift`, 앱 바깥 `ios/UMTP_IOS/Config/` 및 Xcode 설정. 외부 설정 절차는 [iOS push setup](ios-push-setup.md) 참조.
- T-DNS = `ios/UMTP_IOS/UMTP_IOSTests/DNSParityTests.swift`, 구현은 I/Services/DNSRecovery.swift 및 APIClient.swift.
- T-Core/T-Alerts/T-Settings/T-Trade/T-Push = [Unit Test 디렉터리](../ios/UMTP_IOS/UMTP_IOSTests/)의 `CoreParityTests.swift` / `AlertsParityTests.swift` / `SettingsParityTests.swift` / `TradeParityTests.swift` / `PushParityTests.swift`.
- UI-Core/UI-Alerts/UI-Settings/UI-Trade/UI-Push = [UI Test 디렉터리](../ios/UMTP_IOS/UMTP_IOSUITests/)의 `ParityUITests.swift` / `AlertFlowUITests.swift` / `SettingsFlowUITests.swift` / `TradeFlowUITests.swift` / `PushFlowUITests.swift`.
- C1 = `94623b7` 조사/기준 문서 commit. C2 = `2fb32ed` 공통 API·인증·식별자·테스트 기반 commit.
- C3 = `ccd2d98` 푸시SDK/delegate/token/권한설정UI·테스트4개·설정문서. C4 = `0400095` DNS 안전복구·테스트9개.
- C5 = `05ddb33` 가격/검색/조건/일괄설정·테스트20개. C6 = `30e562c` 알림/읽음/보관함·테스트12개. C3..C6의 독립 build 증거는 E-C3..E-C6.
- C7 = `4a4a4bd` 푸시 토큰 삭제 실패의 세션 간 보존·재시도 및 Push9. C8 = `411fba8` 거래 계약·저장 계층 및 Trade20. C9 = `ae839d9` 정확 확인만 저장할 때 단계 보존 및 Trade22. 각 시점 단위 증거는 R-M7/R-M11, 독립 빌드는 R-C7/R-C8/R-C9다.
- C10 = `a0db410` 불확실한 삭제의 초안/ID 보존·공백 offset 및 Trade27. R-UNIT-FINAL2와 commit 후 전체 작업 트리 R-UNIT-C10의 단위84개 및 R-C10 독립 build가 통과했다.
- C11 = `b04318e` 메인4탭/안정된 거래 Form·보관함 선택 접근성·fixture/도메인 UI. C12 = `a5e791d` 설정 탐색/일괄 초안 보존·Settings UI. C13 = `8d5dd38` 권한 안내·시스템 권한/푸시/외부 연동 UI. 각 독립 빌드는 R-C11/R-C12/R-C13 통과.
- C14 = `37cd0cb` 시장가 안내 여러 줄 표시와 UI 높이/전체 본문 회귀. R-FINAL3 전체103개·R-C14 독립 build 및 R-RELEASE2/R-DEVICE-COMPILE2가 통과했다.
- C15 = `9747629` Debug Simulator bundled loopback·Info preflight·Core URL2/Push cold UI·DNS mock HTTPS 격리, 6개 파일. R-COLD2 전체88개 및 R-RELEASE3/R-DEVICE-COMPILE3 통과. commit 후 R-FINAL4 전체106개도 통과했다.
- “조사 완료”는 관련 코드/진입/계약 대조이며 Android 실제 실행 완료가 아니다. “구현·연결 완료”는 iOS UI→VM→API 경로가 활성 상태라는 뜻이다. “단위/UI 통과”는 명시한 local fixture/Simulator 범위만 뜻하며 실서비스/APNs/실기기 동등성을 대신하지 않는다. R-FINAL3의 전체103개 성공과 이후 cold-start 격리 확장 실행은 서로 분리한다.

### A. 기능별 Android 명세·입출력·예외

| 기능 ID | 기능 이름 | Android 근거 파일·주요 심볼 | Android 진입 경로 | 입력 조건 | 기대 결과 | 주요 예외 상황 |
|---|---|---|---|---|---|---|
| AUTH-01 | 최초 등록 | A-Main `onCreate`; A/ui/UserSetupScreen.kt; A-VM `registerUser` | 미등록 시작→User ID→저장 및 시작 | trim 후2자 이상 ID + ANDROID_ID; API01 | 서버 resolved user_id 저장 후 메인/기본 목록 조회 | 빈값/중복입력·기기/ID 충돌·HTTP/ok:false; 실패 시 로컬 세션 미생성 |
| AUTH-02 | 세션 복원 | A/user/UserPreferences.kt; A-VM init | 앱 재실행→저장 ID 읽기 | `umtp_prefs/user_id` 존재 | 재등록 없이 같은 사용자 설정/알림/보관함 조회·토큰 등록 | 조회 실패로 ID 삭제 금지; access/refresh token·세션 만료 API 없음 |
| NAV-01 | 4탭·계층 이동 | A-Main `MainTabScreen/SettingsNavigator/Screen` | 알림/읽음 보관함/거래 입력/설정 | 등록 사용자; 설정에서 제품→칩→인치→RAM/SSD | 실제 목적 화면 이동; mini는 인치 단계 생략 | Android 다른 탭 Back→알림, 설정 하위 Back→상위; 프로세스 종료 후 UI 복원 없음 |
| ALERT-01 | 미읽음 피드·갱신 | A/ui/AlertFeedScreen.kt; A-VM `fetchAlerts/startAlertPolling` | 알림탭/ON_RESUME/새로고침 | API25 user_id,is_read=0; **10초** 주기 | 생성시각 내림차순·갱신시각·로딩·빈 결과 | 중복 억제, 장애 시 기존 목록 유지; 자동조회 오류 조용히; 페이지 cursor 없음 |
| ALERT-02 | 알림 카드 전체 정보 | A/ui/AlertFeedScreen.kt `AlertCard`, resolve helpers; A/network/AlertModels.kt | 피드 카드 | nullable 제목/메시지/URL/가격/스펙/사기 v1·v2·v3/위험 | 이미지·제목·가격·기준가·차이·출처·조건/위험/후보 badge·요약·시각 | title→message→제목 없음, product_url→url, 사기 null은0% 아님;0.25/0.65 경계 |
| ALERT-03 | 상세·검토 완료 | A/ui/AlertFeedScreen.kt `AlertDetailScreen/buildAlertDetailRows` | 카드 상세보기→검토 완료 | 선택 알림; API26/27 | 원본·분석·가격/위험·URL 등26개 필드; 명시적 검토 성공 뒤 읽음/복귀 | 상세 열기만으로 읽음 금지; 실패 시 표시 유지·재시도 |
| ALERT-04 | 선택/전체 읽음 | A-VM `markAlertAsRead/markAllAlertsAsRead`; A/ui/AlertFeedScreen.kt | 선택모드→전체선택/해제→선택읽음 또는 모두읽음 | id>0; API26..29 | 성공 항목만 반영; 선택은 순차 처리 후 수/목록 갱신 | 실패 항목 유지·다음 항목 계속; PATCH404/405/501만 POST fallback |
| LINK-01 | 매물/이미지 열기·복사 | A/ui/AlertFeedScreen.kt, ReadAlertArchiveScreen.kt URL handlers | 카드 복사·상세 매물/이미지 열기 | URL 존재 | 클립보드 복사 안내 또는 외부 브라우저 열기 | 없음은 비활성; Android scheme/외부앱 오류 처리 누락은 복제하지 않음 |
| ARCHIVE-01 | 읽음 보관함·상세 | A/ui/ReadAlertArchiveScreen.kt; A-VM `fetchReadGroupedAlerts` | 읽음 보관함탭→chip/screen→상세 | API30 user_id | 서버 읽음 항목 그룹·가격/사기/스펙/읽음시각; 빈/갱신 상태 | chip M1..M5 기타후순위·화면 숫자순; 실패 기존목록 보존 |
| ARCHIVE-02 | 보관함 선택/전체 비우기 | A-VM `clearSelectedReadArchive/clearAllReadArchive` | 보관함 선택/모두비우기 | API31/32; 양수·중복제거 **alert_event_ids** | cleared/skipped 표시·보관함 갱신 | archive row id를 쓰면 안 됨; 매물 삭제가 아님; 실패 기존목록 보존 |
| TRADE-01 | URL/상품 ID 자동채움 | A/ui/ResaleTradeInputScreen.kt; A-VM `startTradeJourneyFromUrl/applyStartedTradeJourneyResponse` | 거래 입력→URL 또는 product_id→시작 | API11 trim reference | nullable id draft 허용; row에 top-level identity 보완·기존기록 안내 | 빈 입력·중복 요청·ok:true/row:null 실패; 성공 없는 mock fallback 금지 |
| TRADE-02 | 알림/보관함에서 거래 시작 | A-Main callbacks; A-VM `startTradeJourneyFromAlert/FromReadArchive` | 알림/보관함→거래 입력 | API13 alert_event_id / API14 read_archive_event_id; archiveID 없으면 alertID | 해당 원본 자동채움 후 거래 입력 이동 | API 실패 시 Android 기존탭 유지; 원본 ID를 재시도에도 보존해야 함 |
| TRADE-03 | 자동정보·정확 확인 | A/ui/ResaleTradeInputScreen.kt `buildJourneyValueMap/firstImageUrl/ExactVerificationInputSection` | 시작/내역선택→자동정보·정확확인 | JSON row/image_urls 배열·객체·문자열; serial/model/battery/lock/MDM | 서버 정보 표시; 배터리 숫자, lock/MDM true/false/미입력 구분 | null·빈 이미지·불안전 URL; Android 스펙 편집은 저장 whitelist에서 누락되는 버그 |
| TRADE-04 | 구매 후 기록 저장 | A/ui/ResaleTradeInputScreen.kt `PURCHASE_INPUT_FIELDS/buildManualUpdates`; A-VM `patchSelectedResaleJourneyPurchase` | 구매 후 기록모드→필드편집→저장 | 제목/원문/시세/연락·구매시각/판매자/구매가/운송비/배송비/방법/검수/단계/정확확인; API15 또는08 | 변경된 비공백 필드만 저장; 최초 draft upsert, 기존 PATCH; 서버 비용/단계 반영 | false/0 보존; blank는 삭제 아님; 숫자/날짜 오류·실패 draft 유지; KEEP/SOLD 단계 회귀 방지 |
| TRADE-05 | 되팔이 후 기록 저장 | A/ui/ResaleTradeInputScreen.kt `RESALE_INPUT_FIELDS`; A-VM `patchSelectedResaleJourneyResale` | 되팔이 후 기록모드→필드편집→저장 | 플랫폼/URL/등록가/구매자/판매방법·장소·시각/판매가/단계/정확확인; API16 또는09 | 서버 여정 단계·손익/비용 값 반영; 사용자가 입력한 확인정보도 저장 | backend resale whitelist는 정확확인 제외; 보조 purchase PATCH 필요. 별도 sold 버튼은 활성 아님 |
| TRADE-06 | 구매/완료 내역·재선택 | A/ui/ResaleTradeInputScreen.kt history; A-VM `loadResaleJourneyHistory` | 거래 입력 내 완료/구매목록→기록선택/해제 | API18/19 limit=200; 구매는 KEEP 포함/SOLD 제외 | 단계·제목·금액 표시; 선택 row 자동채움/수정 | Android completed throw 시 purchased도 건너뛰는 한계; 기존 목록 보존; 무한 페이지 없음 |
| TRADE-07 | 완료 내역 삭제 | A-VM `deleteSelectedCompletedResaleJourneys/deleteAllCompletedResaleJourneys` | 완료목록 선택삭제/전체삭제 | API20 journey_ids / API21 | 현재 사용자의 SOLD 기록만 실제 삭제 후 재조회 | 되돌리기 API 없음; 실패 기존목록/선택 보존; Android 확인부재 개선 필요 |
| SETTINGS-01 | 제품·칩·규격 탐색 | A-Main `SettingsNavigator`; A/ui/ProductTypeListScreen.kt, ChipListScreen.kt, ScreenSizeListScreen.kt, RamSsdSettingsScreen.kt | 설정→제품→칩→인치→조합 | API02 units + API03 user settings | Air→mini→기타, 칩 지정순서/인치순, 서버 RAM/SSD 목록 | mini inch=0·단계생략; 두 응답 중하나 실패/빈 상태→재시도; 기본값으로 기존행 덮어쓰기 금지 |
| SETTINGS-02 | 개별 시세·가격·방향·경계 | A/ui/MacBookAirSettingCard.kt, FriendlyPriceText.kt, AlertBoundMapper.kt; A-VM `upsertItem` | 규격 카드 가격입력→저장 | market/target/gap -100..100; 아래/이상; min/max≥0 | (market-target)/market×100 소수2자리 HALF_UP; below min만·above max만; API04 | invalid 입력 안내;0/null 구분; 반대 bound 해제. bulk100%로 서버 target0이 생기는 호환성도 필요 |
| SETTINGS-03 | 검색어·속도·알림·후보 | A/ui/MacBookAirSettingCard.kt, WatchPriorityUi.kt; A-VM `upsertItem` | 규격 카드 토글/입력/속도→저장 | keyword≤255, FAST/NORMAL/LOW, enabled/candidate; API04 | 서버 추천/실효 검색어 표시; 즉시조회 요청·조건변경후보 결과 안내 | 빈 keyword=null 추천어; 최근7일 분석확인 기준; HTTP/ok:false·중복저장·저장중 이탈 |
| SETTINGS-04 | 전체/규칙 검색 기준 새로고침 | A-VM `refreshSettings/refreshSingleRuleSavedAt` | 설정 전체 새로고침/활성 override 카드 새로고침 | API22 전체 / API23 rule_id | **saved_at를 변경**하고 units/settings/feed/archive 갱신; 시각·결과 안내 | 단순 GET과 혼동금지; 활성 override만 개별가능; 실패/중복 방지·미저장 입력 보존 |
| SETTINGS-05 | 범위별 일괄 알림·후보·속도 | A/ui/RamSsdSettingsScreen.kt; A-VM bulk funcs/`applyBulkUpsertFallback` | 현재 칩·인치/제품 전체→동작→확인 | scope의 모든 settings, override 없는 행 포함; API04 순차 | 대상 필드만 바꾸고 기타 필드·설정 유지; 완료수 안내 | 첫 오류중단·부분 성공; 단일 미저장 draft가 성공 bulk를 이후 되돌리지 않아야 함 |
| SETTINGS-06 | 일괄 차이율·최소·최대 | A/ui/RamSsdSettingsScreen.kt; A-VM bulk funcs/`resolveBulkPriceBoundsScopeState` | 같은 scope→차이율/하한/상한→확인 | gap -100..100; below에 min·above에 max | scope/방향 맞는 행에만 적용; 같은 기존 bound 기본표시·불일치 빈칸 | 해당방향 없으면 비활성; 반대방향 불필요 upsert로 saved_at 변경 금지;100%/목표0 재저장 |
| SETTINGS-07 | 시스템 시장가로 초기화 | A-VM `resetFairPricesToSystem/resolveFallbackFairPrice` | scope→시스템 시장가 초기화→확인 | system_fair_price>0인 대상; API04 순차 | 시장가만 변경하고 방향/gap/bound/검색/속도/후보/활성 보존 | system시장가 null/≤0 skip; 전부skip을 성공으로 오판하지 않음; 부분실패 안내 |
| PUSH-01 | 권한·FCM 토큰 수명주기 | A-Main; A/fcm/PushTokenManager.kt; A/user/UserPreferences.kt | 등록/앱 진입/토큰 변경 | Android13+ 권한; FCM token; API24 | 실제 FCM token platform값으로 등록·변경 시 재등록·실패 다음진입 재시도 | 권한거부·token회전·중복·사용자교체; HTTP200/ok:false도 실패여야 함 |
| PUSH-02 | 알림 수신·클릭 이동 | A/fcm/UMTPFirebaseMessagingService.kt; A-Main `handleIntent`; 피드 `initialTargetAlertId` | foreground수신/시스템알림 tap/cold·warm start | notification/data payload의 양수 alert_id | 알림탭→해당 상세; 목록 로드 전 목적지 보존 | Android 읽음/목록밖 대상 못찾는 한계; URL deep link가 아니라 alert_id 라우트 |
| DATA-01 | 영속 상태·캐시·복귀 | A/user/UserPreferences.kt; A-VM/Compose remember/Coil | 앱 재실행·탭이동·백그라운드→복귀 | user_id/is_user_registered/fcm_token/push_token_registered | 계정·토큰 등록상태 복원; 도메인은 서버/메모리, 이미지 기본캐시 | 로컬 DB 없음; Android도 프로세스 종료 뒤 미저장 draft 복원 없음; 계정별 이전 응답 격리 |
| NET-01 | transport·파싱·안전 오류 | A/network/UmtpApiClient.kt; A/ui/SafeErrorMessage.kt; A-API/DTO | 모든 API 요청·응답 | HTTPS, query/path/body user_id; bool/숫자문자열/null/날짜 | 계약별 요청, HTTP와ok 별도 검사, 안전한 오류·기존데이터 보존 | Authorization 없음; 지정host DoH fallback; timeout/취소/422/잘못된JSON/연속입력 |
| NET-DNS | NET-01 하위: DNS 장애 복구 | A/network/UmtpApiClient.kt `duckDnsAwareDns.lookup/shouldRetryWithDnsOverHttps/dnsOverHttpsResolvers` | API host의 시스템 DNS lookup 실패 | base host 또는 *.duckdns.org; Cloudflare→Google DoH, 조회timeout4초 | 시스템 DNS 실패여도 허용 host에 대해 암호화 DNS 복구 후 기존 HTTPS 요청 | 다른 host로 확대하지 않음; 양쪽 DoH 실패는 원래 네트워크 오류; TLS 검증 우회 금지 |
| IOS-01 | 기존 로그아웃 보존 | Android 대응 진입 없음; 기존 I/App/AppState.swift `logout` | 기존 미연결 SettingsView의 로그아웃→연결된 설정 | 로그인된 iOS 사용자 | 로컬 사용자 ID 제거·등록화면, 기기식별/기타설정 보존 | 서버 탈퇴/토큰폐기 API 없음; 진행중 이전사용자 응답/푸시 토큰 재등록 경쟁 방지 |

### B. 기존 iOS 차이·필요 변경·조사/구현 상태

| 기능 ID | 대응하는 기존 iOS 구현 | 기준 대비 차이 | 필요한 변경 / 현재 구현 위치 | 조사 상태 | 구현 상태 | 플랫폼 차이 |
|---|---|---|---|---|---|---|
| AUTH-01 | UserSetupView/VM→UserAPI 등록은 동작 | 문구·입력비활성·빈 resolved ID·오류 mapping 차이 | 기존 등록 확장, 안전한 API 오류·중복 방지·Android 문구; I/Services/UserAPI.swift | 완료(코드) | 구현·연결 완료 · C2 | IDFV/기존fallback 승계; ANDROID_ID를 흉내내지 않음 |
| AUTH-02 | AppState/UserSessionService UserDefaults 복원 | 테스트주입/식별 승계 검증 없음 | I/Services/DeviceIdentity.swift Keychain 승계, 기존키/ID 보존·복원 테스트 | 완료(코드) | 구현·연결 완료 · C2 | iOS 저장키 그대로, Android 키로 대체하지 않음 |
| NAV-01 | ContentView→MainPlaceholderView; 미연결2탭 | 주요 기능에 도달 불가 | ContentView/MainTabView 기존 구조로4탭·NavigationStack·거래/알림 route 연결 | 완료(코드) | 구현·연결 완료 · C11/C12 | iOS 탭·NavigationStack 뒤로; Android 시스템 Back 강제재현 안 함 |
| ALERT-01 | 빈배열 VM·bool만 바꾸는 polling stub | 서버/주기/갱신 상태 모두 없음 | I-Alerts GET·10초 foreground task·resume·중복/오류 처리 | 완료(코드) | 구현·연결 완료 · C6/C11 | iOS background에서는 polling 중단, 복귀 재조회 |
| ALERT-02 | title/message만 가진 placeholder | 실제 nullable/numeric 모델과 정보 대부분 누락 | I-Alerts 모델/표시 fallback·risk/가격/출처·전체정보 카드 | 완료(코드) | 구현·연결 완료 · C6/C11 | AsyncImage/SwiftUI 접근성 버튼; HTTP(S)만 외부사용 |
| ALERT-03 | 없음 | 상세·명시적 읽음 흐름 없음 | I/Views/AlertDetailView.swift 26정보·검토완료→API→목록 반영 | 완료(코드) | 구현·연결 완료 · C6/C11 | iOS navigation/sheet 사용; 열기 자체 읽음 금지 동일 |
| ALERT-04 | 없음 | 선택상태·서버읽음 없음 | I-Alerts selection·부분실패·PATCH/POST fallback | 완료(코드) | 구현·연결 완료 · C6/C11 | 사용자 목적/결과 동일 |
| LINK-01 | 없음 | 외부 열기/복사 없음 | I/Views/AlertPresentation.swift·AlertDetailView.swift 안전 URL/clipboard/openURL | 완료(코드) | 구현·연결 완료 · C6/C13 | UIPasteboard/openURL; 불안전 scheme 거부·오류 피드백 |
| ARCHIVE-01 | 없음 | 모델/API/화면 전체 누락 | I/Views/ReadAlertArchiveView.swift + I-Alerts 그룹·상세 | 완료(코드) | 구현·연결 완료 · C6/C11 | NavigationStack, 서버 소유 읽음상태 유지 |
| ARCHIVE-02 | 없음 | 선택/전체 삭제 없음 | I-Alerts 올바른 원본ID·수/skip·확인·실패유지 | 완료(코드) | 구현·연결 완료 · C6/C11 | Android보다 삭제 확인 추가; 원본매물은 삭제 안 함 |
| TRADE-01 | 없음 | 새 거래 시작/초안모델 없음 | I-Trade prefill nullableID/top-level merge·참조입력·재시도 | 완료(코드) | 구현·연결 완료 · C8/C11 | 실제 Android와 같은2모드 스크롤;5단계 wizard로 재설계 안 함 |
| TRADE-02 | 없음 | 알림/보관함 출발 없음 | MainTabView + I-Trade alertId/fromArchive 전달·실패원본 retry·명시적 참조 우선 | 완료(코드) | 구현·연결 완료 · C8/C11 | iOS는 먼저 거래탭에서 로딩/오류/재시도 표시; Android는 성공 후 탭 이동 |
| TRADE-03 | 없음 | 자동정보·정확확인 입력 없음 | I-Trade 동적 JSON 이미지·삼상태·검증·원본스펙 표시 | 완료(코드) | 구현·연결 완료 · C8/C9/C11 | Android의 저장되지 않는 스펙편집은 읽기전용으로 정직하게 표시 |
| TRADE-04 | 없음 | 저장/API/계산/예외 없음 | I-Trade sparse PATCH/upsert·숫자/시각 validation·서버 row/단계·draft 유지 | 완료(코드) | 구현·연결 완료 · C8/C9/C10/C11 | 현재시각 입력은 UTC offset 명시; 사용자가 넣은 naive는 서버계약 유지 |
| TRADE-05 | 없음 | 되팔이 저장 없음 | I-Trade resale저장 + 정확확인 변경 purchase PATCH·부분실패·단계 보존 | 완료(코드) | 구현·연결 완료 · C8/C9/C11 | Android 확인정보 유실 버그 수정, 이중호출 부분실패 명시 |
| TRADE-06 | 없음 | 내역/재선택 없음 | I-Trade 구매/완료 독립조회·표시·선택/해제·실패목록 유지 | 완료(코드) | 구현·연결 완료 · C8/C11 | 한 목록 실패가 다른 목록조회를 막지 않도록 개선 |
| TRADE-07 | 없음 | 삭제 없음 | I-Trade 선택/전체 완료삭제 API·확인·범위제한·선택정리 | 완료(코드) | 구현·연결 완료 · C8/C10/C11 | 실제 삭제이므로 명시 확인 추가 |
| SETTINGS-01 | 도달불가 “준비 중” SettingsView·잘못된 stub모델 | catalog/단위별 서버행 없음 | I-Settings 서버트리/정렬/mini skip·두응답 완전성 guard·retry | 완료(코드) | 구현·연결 완료 · C5/C12 | 기존 SwiftUI 계층 사용, 서버 제품목록 유지 |
| SETTINGS-02 | 실제 가격 기능 없음 | 모델·계산·입력·저장 전체 누락 | I-Settings Decimal/연동·방향별 bound·서버target 우선·0원호환성 보강 | 완료(코드) | 구현·연결 완료 · C5/C12/C14 | Android 재계산 drift 대신 server target 유지; invalid 명시 오류 |
| SETTINGS-03 | 안내/로그아웃만 있음 | 실제 검색/속도/토글·저장 없음 | I-Settings full upsert·실효/추천어·속도·후보·즉시조회 결과 | 완료(코드) | 구현·연결 완료 · C5/C12 | 기존 poll_interval 보존(없는경우60); 추천어 별도API 호출하지 않음 |
| SETTINGS-04 | refresh가 “Stage1”만 변경 | 실제 saved_at 변경 없음 | I-Settings POST refresh·명시적 안내·변경 notification·dirty 보존 | 완료(코드) | 구현·연결 완료 · C5/C12 | .umtpSettingsDidChange로 알림/보관함 재조회 |
| SETTINGS-05 | 없음 | bulkscope/필드보존/부분실패 없음 | I-Settings 순차 full upsert·부분성공수·confirmed baseline·dirty field rebase | 완료(코드) | 구현·연결 완료 · C5/C12 | 명시적 bulk필드는 초안보다 우선, 독립 미저장필드만 보존 |
| SETTINGS-06 | 없음 | bulk수치·방향 필터 없음 | I-Settings scope/bounds·100%호환·aggregate 기본값 변경관찰 | 완료(코드) | 구현·연결 완료 · C5/C12 | 반대방향 행을 skip해 saved_at 불필요 변경 방지 |
| SETTINGS-07 | 없음 | 시스템시세 reset 없음 | I-Settings 기존 전체필드 보존·system fair검증·skip/부분실패수 | 완료(코드) | 구현·연결 완료 · C5/C12 | 적용0건을 성공으로 표시하지 않음 |
| PUSH-01 | SDK/delegate/entitlement/토큰/API 없음 | 원격푸시 기반 전체 누락 | I-Push FirebaseFCM/APNs등록·권한설정UI·token재시도·사용자별등록·logout경쟁 방어 | 완료(코드/서버) | iOS 구현 완료 · C3/C7/C13; 서버/APNs 별도 | APNs raw token이 아닌 FCM token platform=ios; 시스템설정으로 권한복구 |
| PUSH-02 | route/수신 없음 | cold/warm 목적지·알림표시 없음 | I-Push notification delegate→pendingAlertID→로그인/탭→unread/archive상세 | 완료(코드/서버) | iOS 구현·라우트 완료 · C3/C6/C11/C13; 원격 별도 | 읽음 보관함까지 fallback; Universal Link/URL Scheme 추가 대상 아님 |
| DATA-01 | UserDefaults세션/fallback·URLSession 기본캐시 | 도메인상태/사용자교체/push등록상태 없음 | 기존저장 보존+Keychain·ViewModel메모리초안·계정/화면별task수명주기 | 완료(코드) | 구현·연결 완료 · C2/C3/C5/C6/C7/C10/C11/C12 | 프로세스종료 뒤 미저장 초안 복원은 Android에도 없어 범위외 |
| NET-01 | POST전용 APIClient·10초 timeout | GET/PATCH/query·복합모델·안전실패처리 부족 | I/Services/APIClient.swift 공통확장 + 도메인 DTO/API 실제계약·URLProtocol 주입 | 완료(코드/서버) | 공통/도메인 구현 완료 · C2/C4/C5/C6/C8/C10 | DNS 복구 차이는 NET-DNS에서 별도 추적 |
| NET-DNS | URLSession 시스템DNS만 사용 | Android의 지정host DoH 장애복구 대응 없음 | I/Services/APIClient.swift + DNSRecovery.swift native복구·전송여부 관찰·재시도 제한 | 완료(코드/플랫폼계약) | OS 기본 기능으로 대안 구현 완료 · C4; 장애망 별도 | 앱 문맥의 encrypted DNS·시스템 resolver 우선; fallback은 프로세스동안 유지. URLSession에 공개 per-task DNS없음 |
| IOS-01 | AppState.logout/미연결설정버튼 | 기존기능을 실제설정에도 유지해야 함 | SettingsView→AppState.logout·세션/알림route초기화·token삭제/재등록경쟁 방어 | 완료(코드) | 기존 기능 보존·연결 완료 · C2/C3/C7/C11/C12 | 서버탈퇴를 추가하지 않음; 기기식별자 보존 |

### C. 기능별 검증 상태·방법·실제 결과·증거·미해결

모든 행의 “실서비스 미검증”은 E-LIVE/R-LIVE의 health/catalog 읽기 이외에 실서비스 사용자 흐름을 실행하지 않았다는 뜻이다. R-FINAL3는 C14 안내 수정 포함 전체103개(단위84+UI19)가 통과했다. 기존 R-FINAL의 기대값 실패와 R-FINAL2 중단은 위 이력에 남긴다. C15 cold-start 격리는 R-COLD2 전체88개가 통과했고 그전 R-COLD1의 단위2개 실패를 별도 기록한다. C15 이후 R-FINAL4 전체106개(단위86+UI20)도 모두 통과했으며 아래 각 행은 이 최신 결과를 기준으로 한다. 코드/fixture 결과를 운영 검증으로 바꾸지 않는다.

| 기능 ID | 검증 상태 | 검증 방법·대상 | 실제 검증 결과·증거 | 관련 commit | 외부 의존성 | 미해결 사항 |
|---|---|---|---|---|---|---|
| AUTH-01 | 단위·등록/재시도 UI 통과; 실서비스 미검증 | T-Core 입력/실패/세션; UI-Core·Authentication | R-FINAL4 Core9 및 R-FINAL4 등록 검증·실패 후 재시도 UI 통과 | C1/C2/C11 | B-ACCOUNT | 실계정 등록·기기 충돌 및 서버 쓰기 readback |
| AUTH-02 | 단위·세션 복원 UI 통과; 실기기 미검증 | T-Core 기존키/IDFV/fallback/Keychain; Authentication UI | R-FINAL4 Core9, 재실행 세션 복원·기기 ID 보존 통과 | C1/C2/C11 | B-ACCOUNT/B-APNS | 기존 설치 업데이트·재설치 전후 실기기 ID/계정 동일성 |
| NAV-01 | 4탭·주요 이동 UI 통과 | Alert/Archive/Trade/Settings UI 및 실제 도달성 대조 | R-FINAL4 UI20 통과: 4탭·mini 뒤로·초안 보호·설정 왕복·거래 저장/내역 연결 | C1/C5/C6/C8/C11/C12 | B-ACCOUNT | 실제 Android 화면 비교·실서비스 흐름 |
| ALERT-01 | 단위·장애/복구 UI 통과; 실서비스 미검증 | T-Alerts 쿼리/정렬/계정/polling; AlertFlow UI | R-FINAL4 Alerts12, AlertFlow5 중 기존 목록 유지·장애→재시도 복구 통과 | C1/C6/C11 | B-ACCOUNT | 운영 서버 주기·실제 장애/foreground 복귀 |
| ALERT-02 | 단위·카드/상세 UI 통과; 실데이터 시각 범위 제한 | T-Alerts nullable/fallback/risk; 카드 화면·접근성 | R-FINAL4 Alerts12, 카드·상세·선택 접근성 UI 통과 | C1/C6/C11 | 다양한 실제 매물 B-ACCOUNT | 모든 nullable/이미지 실패/긴 데이터 조합은 실데이터 검증 별도 |
| ALERT-03 | 단위·명시적 읽음 UI 통과; 실서비스 미검증 | T-Alerts read fallback; 상세 열기/검토 확인 | R-FINAL4 Alerts12, 상세만 열면 쓰기 없음·검토 완료→보관함→거래 통과 | C1/C6/C11 | B-ACCOUNT | 실제 26개 필드와 서버 읽음 readback |
| ALERT-04 | 단위·전체 읽음 UI 통과; 복합 실패 UI/실서비스 제한 | T-Alerts 순차 부분실패/404·405·501 fallback; Archive UI | R-FINAL4 Alerts12, 명시 단건/전체 읽음 통과; 부분 실패는 단위 검증 | C1/C6/C11 | B-ACCOUNT | 다중 선택 중 부분 오류 UI·운영 서버 결과 |
| LINK-01 | 단위·외부 handoff UI 통과 | T-Alerts/Trade URL; ExternalLink UI 복사/Safari/복귀 | R-FINAL4 URL 검증, 복사·Safari 본문 표시·앱 복귀 UI 통과 | C1/C6/C8/C11/C13 | 외부 매물/이미지 URL | 실제 외부 사이트 오류·모든 이미지 링크 조합은 별도 |
| ARCHIVE-01 | 단위·보관함/상세 UI 통과; 실서비스 미검증 | T-Alerts 그룹/nullable; AlertFlow·Archive UI | R-FINAL4 Alerts12, 읽음→그룹/상세→archive ID 거래 시작 통과 | C1/C6/C11 | B-ACCOUNT | 운영 데이터 그룹/실제 읽음 시각 |
| ARCHIVE-02 | 단위·선택/전체 비우기 UI 통과; 실서비스 미검증 | T-Alerts 원본 alert ID/중복/요청; Archive UI2 | R-FINAL4 Alerts12, 선택 상태·선택/전체 비우기·범위/취소 검증 통과 | C1/C6/C11 | 삭제 가능한 자료 B-ACCOUNT | 실서버 cleared/skipped readback |
| TRADE-01 | 단위·수동 prefill/저장 UI 통과; 실서비스 미검증 | T-Trade nullable/top identity/upsert/PATCH; TradeFlow | R-FINAL4 Trade27, 수동 product_id→prefill→구매 저장→내역 통과 | C1/C8/C9/C10/C11 | B-ACCOUNT/조회 가능한 매물 | 실서비스 URL/product_id·중복 existing 응답 |
| TRADE-02 | 단위·알림/보관함 route와 초안 보호 UI 통과 | T-Trade 원본 ID 재시도/명시 참조; AlertFlow | R-FINAL4 Trade27, unread/archive 시작·실패 재시도·초안 교체 확인 통과 | C1/C8/C11 | B-ACCOUNT | iOS 거래탭 선이동은 플랫폼 차이; 실서비스 원본 ID 검증 |
| TRADE-03 | 단위·확인정보 입력/보존 UI 통과 | T-Trade 이미지/삼상태/invalid/verification; TradeFlow | R-FINAL4 Trade27, 잘못된 확인정보 저장 차단·입력 보존·수동 입력 통과 | C1/C8/C9/C11 | 다양한 실제 row B-ACCOUNT | 실서버 정확 확인 저장·모든 이미지/삼상태 조합 |
| TRADE-04 | 단위·구매 저장/내역 UI 통과; 실서비스 미검증 | T-Trade sparse/날짜/오류/단계; TradeFlow | R-FINAL4 Trade27의 공백 offset·불가능 날짜·단계 회귀 통과; SwiftUI 수동 구매 저장→내역 통과 | C1/C8/C9/C10/C11 | B-ACCOUNT | 실제 비용 계산/readback·운영 시각 의미 |
| TRADE-05 | 단위·선택 기록 되팔이 수정 UI 통과 | T-Trade whitelist/부분실패/단계/identity; TradeHistory | R-FINAL4 Trade27, 기록401 선택→되팔이 수정 통과; 명시 단계/확인정보만 저장 회귀 포함 | C1/C8/C9/C10/C11 | B-ACCOUNT | 실제 API 저장/readback·부분 실패 재시도 |
| TRADE-06 | 단위·내역 선택/수정/보존 UI 통과 | T-Trade 독립 조회 실패/선택; TradeFlow·TradeHistory | R-FINAL4 Trade27, 구매/완료 내역·기록 선택/수정·KEEP 보존 통과 | C1/C8/C11 | B-ACCOUNT | 실제 limit200 경계·긴 목록 및 서버 조회 |
| TRADE-07 | 단위·선택/전체 삭제 UI 통과; 실서비스 미검증 | T-Trade 삭제 확정/부분/0건/초안; TradeHistory | R-FINAL4 Trade27에 원래 ID/초안·PATCH 재시도 보존 포함; 선택/전체 삭제·취소·구매/KEEP/다른 사용자 보존 통과 | C1/C8/C10/C11 | 삭제 가능한 SOLD 자료 B-ACCOUNT | 실제 삭제/readback; count만으로 ID를 확정 못 하면 입력 유지 |
| SETTINGS-01 | 단위·제품/규격 탐색 UI 통과 | T-Settings scope/완전성; Settings UI mini/뒤로 | R-FINAL4 Settings20, Settings3 중 mini 인치 생략·뒤로·조합 탐색 통과; R-LIVE catalog GET 성공 | C1/C5/C12 | 사용자 설정 B-ACCOUNT | 운영 units 성공/settings 실패 재시도 |
| SETTINGS-02 | 단위·가격 저장/안내 레이아웃 UI 통과 | T-Settings 계산/방향/경계; Settings UI 요청/안내 높이 | R-FINAL4 Settings20·가격/방향/경계 요청·안내 전체 본문/높이 회귀 통과. R-FINAL3/R-FINAL4 첨부에서 두 문장·두 줄 잘림 없음 직접 확인 | C1/C5/C12/C14 | B-ACCOUNT | 실제 서버 가격 roundtrip |
| SETTINGS-03 | 단위·개별 저장 UI 통과; 운영 결과 미검증 | T-Settings keyword/priority/candidate/bool; Settings UI | R-FINAL4 Settings20, 개별 저장·속도 입력/보존 포함 Settings3 통과 | C1/C5/C12 | B-ACCOUNT | 모든 토글 조합 UI·실제 poll/후보 worker 결과 |
| SETTINGS-04 | 단위·초안 보존 UI 통과; 실서비스 미검증 | T-Settings POST saved_at/rebase; Settings 탭 왕복 | R-FINAL4 Settings20의 refresh/서버 target/초안 회귀, 설정 왕복의 쓰기 없음 통과 | C1/C5/C12 | B-ACCOUNT | 실제 saved_at·신규 매물 범위·동시 목록 갱신 |
| SETTINGS-05 | 단위·범위/초안 UI 통과; 복합 bulk UI 제한 | T-Settings 부분실패/confirmed baseline/dirty rebase | R-FINAL4 Settings20의 부분 적용·POST 성공/GET 실패·초안 재조정 통과; 범위/초안 왕복 UI 통과 | C1/C5/C12 | B-ACCOUNT | 모든 일괄 동작의 부분 실패 UI·실서비스 readback |
| SETTINGS-06 | 단위·일괄 초안 탭 왕복 UI 통과 | T-Settings bound/gap/scope/100%; Settings UI | R-FINAL4 Settings20, 일괄 속도/최소/최대·개별 시장가·경로 보존 및 쓰기 요청 없음 통과 | C1/C5/C12 | B-ACCOUNT | 운영 반대 방향 saved_at 불변·scope/aggregate 변화 |
| SETTINGS-07 | 단위 통과; 초기화 예외 UI/실서비스 미검증 | T-Settings reset 필드보존/null skip/부분실패 | R-FINAL4 Settings20에서 모든 필드 보존·전부 skip·부분 실패 회귀 통과; 활성 초기화 컨트롤/API 연결 확인 | C1/C5/C12 | B-ACCOUNT | 전부 skip/부분 실패 UI·실서비스 초기화 readback |
| PUSH-01 | iOS 구현·단위/권한 UI 통과; 원격 전달 미검증 | T-Push 등록/경합/삭제 실패; NotificationPermission | R-FINAL4 Push9, 실제 시스템 OFF→앱 거부→ON→앱 허용 UI 통과. 공식 설정 링크가 루트면 안내된 Apps 경로 사용 | C1/C3/C7/C13 | B-PUSH-SERVER/B-APNS | 서버 iOS 발송·서명/APNs·실기기 token 회전 |
| PUSH-02 | 단위·warm/cold Simulator tap 통과; 원격 미검증 | T-Push 양수 alert ID/queue; PushFlow OS 배너 tap | R-FINAL4 전체106개에 단위 Push9와 warm/cold UI2개 통과 포함. 실제 로컬 등록→종료 확인→OS tap만으로 cold launch·alert101 미읽음 상세/GET 확인. R-COLD2 전체88개 통과 및 R-COLD1 화면 직접 검수도 별도 보존 | C1/C3/C6/C11/C13/C15 | B-PUSH-SERVER/B-APNS/B-ACCOUNT | 실제 APNs cold/warm/foreground 전달·실서비스 대상 |
| DATA-01 | 단위·복원/초안 UI 통과; 실제 설치 이행 미검증 | T-Core 키/ID·T-Alerts 계정·T-Push 삭제·Settings 초안 | R-FINAL4 관련 단위, 세션/기기 ID·로그아웃·설정/거래 초안 보존 UI 통과; 실제 기기는 미설치 | C1/C2/C3/C5/C6/C7/C10/C11/C12/C15 | 기존 설치 실기기/B-APNS | 실제 업데이트·캐시/계정 전환; 프로세스 종료 초안 복원은 Android도 범위 밖 |
| NET-01 | 단위·fixture 계약/실서비스 GET 통과; 실제 쓰기 미검증 | T-Core/도메인 HTTP·JSON·body·안전 오류 | R-FINAL4 단위86개 및 R-FINAL4 앱 요청 UI 검증, R-LIVE health/catalog 원본 HTTPS GET 통과 | C1/C2/C4/C5/C6/C8/C10/C11/C15 | B-ACCOUNT | 실제 사용자 쓰기·운영 장애 후 API 결과 |
| NET-DNS | OS 대안 구현·단위 통과; iOS 장애망 동등성 미검증 | T-DNS 허용 host/원본 TLS/전송 여부·native 복구 | R-FINAL4 DNS9 통과. E-DNS-LIVE 실제 구현 macOS CLI의 최초 실패 주입→native 설정→HTTPS health 성공은 과거 관찰 이력 | C1/C4/C15 | 실제 DNS 제약 재현 환경 | 실기기 장애망/선택 resolver·앱 문맥 지속/시스템 resolver 우선 확인 |
| IOS-01 | 기존 기능 보존·단위/로그아웃 UI 통과 | T-Core 세션/기기 ID; T-Push in-flight logout; Authentication | R-FINAL4 Core/Push, 로그아웃→등록 화면·기기 ID 유지·세션 복원 UI 통과 | C1/C2/C3/C5/C7/C11/C12 | 실기기 token 검증 B-APNS | SDK 실기기 경합·이전 사용자 token/새 사용자 실제 등록 |

## 비활성·부재 기능과 README 불일치

| 제외 ID | 항목 | 근거·판단 | 동등성에서 제외하는 이유 |
|---|---|---|---|
| EX-01 | 수동 URL 분석 화면/API34 | A/ui/UmtpUrlAnalyzeScreen.kt 정의, A-Main 진입/호출 없음; README도 메인 제외 명시 | 현재 Android 활성 메뉴 아님. 거래 URL시작 API11은 TRADE-01로 별도 이식 |
| EX-02 | WatchRuleSettingsScreen/과거 DTO·RequestPollNow | A/ui/WatchRuleSettingsScreen.kt, A/network/WatchRuleModels.kt 실제 navigation/API사용 없음 | 폐기/미연결 구조를 활성 설정으로 중복 이식하지 않음 |
| EX-03 | 추천검색어 전용 API33 | A-API 선언만, 활성카드는 API03 item.recommended_search_keyword 사용 | 별도 API화면은 없음. 추천어 표시/선택 목적은 SETTINGS-03 포함 |
| EX-04 | 전용 bulk API05/06/07 | 실제 A-VM은 개별 API04 upsert fallback 사용 | API 선언수와 활성호출수 구분. 활성 scope/필드보존을 SETTINGS-05..07에서 구현 |
| EX-05 | create-from-product/API10, prefill/API12, sold/API17 독립 버튼 | 선언/VM/callback은 있으나 화면에서 호출되지 않음 | 실제2모드 입력과5개 여정상태를 TRADE-01..06으로 구현. after-purchase/resale API08/09는 활성fallback이므로 제외 아님 |
| EX-06 | 외부앱 알림읽기/자동 URL추출 | Manifest에 NotificationListener 없음, README MVP후속 계획 | iOS OS제약 이전에 Android에도 미구현 |
| EX-07 | Universal Link/URL Scheme/App Link/공유확장·ACTION_SEND/Widget | Android Manifest는 launcher+FCM service, VIEW 링크 intent-filter 없음; 사용callsite 없음 | 실제외부연동은 LINK-01, push alert_id는 PUSH-02. 새로운 링크체계는 필수 동등성 아님 |
| EX-08 | 검색/카메라·사진·위치권한/Worker·Receiver/로컬DB/기능플래그 | Kotlin·Manifest·의존성·저장키 전수 대조에서 활성구현 없음 | 임의기능을 추가하지 않음. 앱foreground polling과 서버worker를 OS background job으로 오인하지 않음 |

근거 충돌과 채택한 기준:

- Android README의2탭/Air중심·읽음 로컬·mock피드·카드클릭 브라우저 설명보다 실제4탭/서버catalog/서버읽음·보관함/상세 후 명시적 검토를 따른다. 활성 mock fallback은 없다.
- README 30초 polling이 아니라 A-VM `ALERT_POLL_INTERVAL_MS=10_000L`을 따른다.
- 백엔드 README의 product_id 직접입력 불가/FCM 미구현 설명은 과거 버전이다. 현재 API11과 Android는 URL 또는product_id를 받고 worker는 FCM 발송을 구현한다.
- [변경 전 iOS 조사](parity-ios-inventory.md)의 “RamSsdSettingsScreen 직접 getRecommendedKeywords 호출” 행은 초기 추정이며 Android callsite 전수 확인으로 정정한다. 실제 추천어는 API03 응답이다.
- [API 조사](parity-api-contracts.md)의 간략 read fallback 행은404/405만 적었지만 Android 실제 조건에는501도 있다. PUSH의 “alert_id 및 url” 표현도 실제 tap route는 **alert_id만**이며 일반 URL deep link로 해석하지 않는다.
- 거래시간은 naive입력은 그대로 서버계약을 따르고, 명시offset 입력은 backend가 UTC naive로 정규화한다. iOS의 “현재시각” 보조입력에는 offset을 명시하도록 후속 보완했다. E-U3에서 현재시각 offset 테스트는 통과했으나 불가능한 ISO 날짜 거부 테스트는 실패했다. strict component 검증 후 E-U4에서15개 거래테스트가 모두통과했다.

## 설계 결정·독립 검토로 확인한 수정

| 결정 ID | 내용·근거 | 반영/검증 상태 |
|---|---|---|
| D-01 | user_id/device_id가 실제 등록계약. Authorization/JWT/refresh/서버logout API가 없으므로 가짜토큰 추가·네트워크오류 자동logout 금지 | C2 반영, T-Core E-U2 통과. 이후 요청이 user_id만 검사하는 서버 보안부채는 별도 기록 |
| D-02 | Android BODY/raw응답/입력·token 로그, unsafe URL, HTTP200 ok:false 성공오판을 복제하지 않음 | 공통안전오류 C2·도메인유효성 반영; R-M11 Core7/Push9 통과. 진단용 입력/포커스 코드는 제거 |
| D-03 | Android 저장중 key에서 product_type이 빠지는 버그 수정; iOS는 전체 복합키. 잘못된 숫자 조용한 생략/성공표시 금지 | I-Settings/I-Trade 반영, E-U2 기본중복/검증 통과 |
| D-04 | 설정 refresh는 saved_at 변경이다. bulk전용API로 임의대체하지 않고 scope의 실제행 전체필드를 보존한 upsert. 반대방향 bounds행은 skip | I-Settings 반영, 기본계약 E-U2 통과; 실제 saved_at/readback 미검증 |
| D-05 | dirty draft 전체행을 보존하면 bulk 성공필드를 다음 단일저장이 되돌리는 P1 발견. 원본baseline 대비 사용자편집필드만 rebase하고 명시bulk필드는 우선적용 | 독립검토 수정·5개회귀테스트 E-U4 통과; 실제서버/UI 검증 별도 |
| D-06 | POST성공→GET실패 뒤 구baseline으로 다음bulk가 값을 되돌리는 P1 및 units만성공시 기본값upsert P1 수정. 성공응답 직후 confirmed baseline 반영, 실제settings행없는 저장 차단 | I-Settings/T-Settings 수정, E-U4 관련회귀 통과 |
| D-07 | resale 정확확인 필드가 서버whitelist에서 유실되는 Android 버그는 보조purchase PATCH로 보완. KEEP/RESALE_LISTED/SOLD를 명시보존하고 두저장의 부분실패 설명 | I-Trade 반영, 관련 모의테스트 E-U2 통과, 실제서버 미검증 |
| D-08 | trade row.id nullable draft·숫자ID·복합JSON이미지·삼상태 유지; 실패alert/archive 시작 재시도 원본ID 보존, 명시 새reference는 기존실패route보다 우선. 거래탭 재진입 내역조회와 raw image_urls 전체표시 누락도 보완 | C8/C11 반영. R-UNIT-FINAL2 Trade27, R-FINAL TradeFlow2/TradeHistory2 통과; C14 안내 수정 후 R-FINAL3 전체103개도 통과 |
| D-09 | 보관함 비우기와 실제SOLD삭제 의미 구분, 확인대화상자 추가. archive start에는archiveID, clear에는원본alertID | R-TA1 보관함 선택/전체 처리, R-M9 거래 선택/전체 삭제·취소·범위·구매/KEEP/다른 사용자 보존 UI 통과; 실서비스 삭제 미검증 |
| D-10 | token등록 clear중queued사용자 유실·logout중SDK deleteToken/FCM callback 경합을 독립검토. 사용자generation·등록queue·SDK삭제순서 및 PushTokenFetchQueue 회전 중 재조회 방어 | Firebase 포함 compile·R-M11 Push9 통과. 실제SDK/기기토큰경합 검증은 별도 |
| D-11 | 같은scope 개별저장/refresh 후 bulk priority/min/max 기본값은 해당 aggregate 변경 시 갱신. 탭 복귀는 같은 사용자 navigation path를 유지하고 bulk 기본값을 다시 초기화하지 않음 | C5/C12 반영. R-UNIT-FINAL2 Settings20, R-FINAL Settings3의 경로·일괄 속도/최소/최대·개별 시장가 보존과 쓰기 요청 없음 통과 |
| D-12 | 서버가 bulk gap100%→target0을 만들 수 있어0/null을 분리하고 기존row 재저장을 막지 않아야 함 | I-Settings 후속수정·수치회귀 E-U4 통과 |
| D-13 | MainTab에서 작업 중 새 거래 시작 요청을 조용히 무시하지 않고 안내하며, 재시도가 현재 편집 초안을 덮어쓰지 않도록 보호 | C11 반영. R-FINAL AlertFlow의 초안 교체 확인·계속 작성·실패 재시도 UI 통과 |
| D-14 | Android DoH 지원 차이를 방치하지 않고 TLS/원본 URL을 유지하는 iOS native encrypted DNS 복구 검토/구현. 앱 문맥·시스템resolver 정책과의 차이는 별도 명시 | NET-DNS 코드연결·E-U4 T-DNS9개통과. 실제 OS resolver/장애네트워크 검증 별도 |
| D-15 | 새 되팔이 초안의 명시 단계는 identity 확보 후 단일 PATCH로 보존하고, 준비 성공/최종 저장 미확인을 구분. 재판매 URL은 단일 HTTP(S) 주소만 허용 | C8 반영, 실제 요청 순서/본문·실패/동일 ID 재시도·URL 검증 포함 Trade20 R-M7 통과 |
| D-16 | 기존 KEEP 기록의 정확 확인 정보만 저장한 뒤 빈 resale PATCH를 보내면 과거 판매정보로 SOLD가 다시 파생될 수 있음 | C9 수정, R-M11 Trade22 포함 단위79개 통과. 확인정보 변경 없는 명시적 빈 resale 저장 의미는 유지 |
| D-17 | Form의 입력 필드/날짜 보조 버튼이 행 재배치로 키보드 포커스를 잃는 문제를 안정된 단일 행 컨테이너로 해결 | R-FOCUS 실제 호출 스택 조사 후 R-SR1 중간 성공, 진단/native 입력 제거 후 R-SR2 SwiftUI TradeFlow2 통과 |
| D-18 | 삭제 count만으로 요청 ID 전체를 삭제했다고 가정하면 서버가 보존한 KEEP 기록의 초안까지 유실됨. 선택 ID 수와 삭제 수가 정확히 같을 때만 해제, 불확실하면 양수 ID/입력 보존. 제한된 내역의 부재는 삭제 증거 아님 | C10 반영. 0건/부분/전체·조회 실패/빈 결과·명확한 선택 삭제·동일 ID PATCH 재시도 회귀가 R-UNIT-FINAL2에서 통과. 첫 R-FINAL의 오류 타입 기대값 실패 이력은 별도 유지 |
| D-19 | Android/backend가 받는 공백 구분 offset 시각도 지원하면서 불가능한 달력 날짜·시/분/초를 계속 거부 | C10 반영, 공백+offset/Z/소수초 및 invalid 회귀 포함 R-UNIT-FINAL2 단위84개 통과 |
| D-20 | 기능 UI 통과 후 첨부 화면 검수에서 시장가 설명이 말줄임으로 잘리는 것을 발견. 수직 fixedSize와 접근성 ID를 추가해 여러 줄을 표시하고 기존 UI에 전체 본문/높이>30/스크린샷 회귀 보강 | C14 반영. R-FINAL3 전체103개 통과·최종 두 줄 화면 직접 확인, R-C14 독립 build·Release/무서명 기기용 빌드 통과 |

## 외부 의존·실제 차단 요인

아래는 로컬 구현·검증 완료와 별개로 추가 정보/환경이 필요한 외부 항목이다. 이를 이유로 접근 가능한 코드/fixture/Simulator 검증을 생략하지 않았고 R-FINAL4 전체106개를 완료했다.

| ID | 확인된 원인·Android 동작 | 필요한 정보/권한 또는 최소 변경안 | 제공 시 가능한 추가 작업 | 지금 독립 진행 가능한 일 |
|---|---|---|---|---|
| B-PUSH-SERVER | `umtp/src/notification_worker.py:1970`이 active token을 `platform="android"`만 조회하고 AndroidConfig로 발송. iOS FCM등록만으로 원격푸시 전달 불가 | backend가 android+ios FCMtoken을 대상으로 APNs alert/priority payload를 구성하는 최소변경 검토/배포. Android로 platform위장하지 않음 | 등록된 iOS계정 실제매물알림 송신→수신→상세 전체검증 | iOS등록/권한/수명주기/route·모의서버·Simulator주입 검증 |
| B-APNS | paired iPhone15Pro는 iOS27.0·developer mode enabled, 설치 Xcode는26.6뿐(`paired-device-final.json`/`.log`). R-DEVICE-SIGNED는 developer disk image mount 실패/목적지 timeout(exit70), 별도 R-SIGNING도 profile 부재로 실패. developer mode OFF가 원인이라는 근거 없음. Firebase iOS/APNs 자격 설정도 확인되지 않음 | paired 기기에 Xcode developer disk image를 마운트할 수 있는 상태, 올바른 bundle의 provisioning/push entitlement·Firebase설정·APNs key/certificate 및 설치 가능한 상태 | 서명된 기기 build/설치, APNs→FCM 매핑, 권한거부/복구·토큰회전·cold/warm/foreground 실제수신 검증 | 서명 없는 기기용 컴파일·Simulator 단위/UI·설정안내·local notification tap 검증 |
| B-ACCOUNT | 실서비스등록/설정/읽음/거래 등 쓰기는 기존사용자 데이터변경·삭제를 수반. 현재 live검증은 health/catalog만 | 테스트계정과 수정/삭제 가능한 매물·알림·SOLD기록, 서비스 접근 범위 | 실제API readback, saved_at/후보/시세계산·거래여정·선택/전체삭제 검증 | loopback fixture/URLProtocol로 요청·상태·오류·UI 전범위 검증 |
| B-ANDROID-RUN | 연결Android기기/AVD/systemimage 없음, 설치라이선스 미동의 | 사용가능 기기 또는 적법하게 준비된 AVD/systemimage·라이선스동의 | Android실행 화면/동작과 동일fixture/실계정으로 시각·조작 비교 | APK/19개단위테스트·모든코드/호출/문서 대조 완료 상태 유지 |
| B-ACCOUNT-MOVE | API01이 기기당user_id 하나를 강제. Android기기에 묶인ID를 iOS별도기기에서등록하면 거부 | 동일계정 다중기기/이전이 필요할 때만 서버의 계정이전정책·인증계약·최소API 결정 | 기존 Android 계정 데이터의 정식 iOS기기접근 검증 | 기존 iOS설치의 ID/기기승계 보존, 별도테스트계정으로 parity검증. 서버매핑우회 금지 |

남은 플랫폼 동작 차이:

- iOS 앱 background에서는10초 polling을 보장하지 않으며 foreground재조회+push로 대응한다. Android도 Worker/OS보장 background작업은 없다.
- iOS NavigationStack/탭 이동·권한설정/외부URL열기 방식을 사용한다. Android 시스템Back동작/권한대화상자의 외형을 복제하지 않는다.
- Android 지정host의 system DNS 실패→Cloudflare/Google DoH에 대응하는 iOS native encrypted DNS 복구를 NET-DNS로 구현했다. 허용 HTTPS host만 복구를 시작하고 원본 URL/TLS를 유지하며, mutation은 아직전송하지않았음이 확인될때만 재시도한다. URLSession 공개 per-task DNS가 없어 복구설정은 앱 문맥/프로세스동안 지속되며 시스템 encrypted resolver가 우선한다. T-DNS9개는 E-U4 통과했고 E-DNS-LIVE에서 실제구현을 macOS CLI로 컴파일해 최초DNS실패만 주입한 뒤 실제native설정/HTTPS health재조회에 성공했다. 이는 iOS실기기·실제망DNS장애·선택된DoH resolver 증명이 아니므로 그 범위의 결과동일성은 미검증이다.
- iOS 거래알림 진입은 거래탭에서 loading/error/retry를 제공하며 Android 성공 후 탭이동과 순서가 다르다. 원본 ID·목적지·초안 보호·재시도는 단위 및 R-FINAL UI에서 통과했다. 실서비스 결과는 별도다.
- 삭제확인, unsafeURL거부, 서버target보존·입력오류 표시, 정확확인유실 수정은 의도한 안전/데이터보존 개선이다.

## 누락 재검토·인계 체크포인트

- [x] A-Main/모든Compose화면·ViewModel·34개API선언·DTO·FCM2파일·Manifest·UserPreferences·리소스·테스트목록과28개활성ID 대조.
- [x] iOS변경전20개Swift파일·실제entrypoint·도달불가stub·Xcode설정·저장키 대조. 기존등록/세션/로그아웃 보존 항목을 별도로 남김.
- [x] API01..34 전부 활성/비활성 분류. bulk전용API/별도추천어API/sold callback 등을 실사용으로 잘못세지 않음.
- [x] 알림카드 가격/차이/출처 누락, archiveID대alertID, 설정batch필드보존·saved_at·partialfailure, 거래whitelist·nullrow·시간대·재시도, pushlogout경쟁을 독립검토하고 후속수정/테스트 연결.
- [x] 재시작 전 Firebase/DNS 포함 통합 XCTest E-U4 및 E-U-T4 67개 통과. E-U3 날짜 실패의 strict 검증 수정 회귀도 통과. 원본 자료 소실은 위 환경 기록 참조.
- [x] E-UI2에서 실패한 초안 교체 확인 흐름은 선택자 수정 후 E-UI-T4에서 통과. 인증·로그아웃·기기 ID 보존, 전체 읽음/전체 비우기도 대상 UI 실행에서 통과.
- [x] 재시작 후 R-M11 단위79개 및 C7/C8/C9 독립 체크포인트 빌드 통과. 푸시 삭제 실패 복구·거래 단계/URL·확인정보만 저장 회귀 포함. 원본은 새 보관 루트에 유지.
- [x] R-TA1 보관함 선택 상태·선택/전체 처리 UI 통과. 과거 실패와 구분.
- [x] R-A1 Android APK/19개 단위 및 R-LIVE 원본 HTTPS 두 조회 재실행 성공. R-FD 설정3개·R-M8 외부 링크 대상 UI 통과.
- [x] R-SR2 SwiftUI 수동 거래/잘못된 확인정보 보존2개, R-M9 거래 삭제, R-PERM1 실제 시스템 권한 OFF/ON 및 복귀 UI 통과. 과거 E-UI-T4 마지막 수동 거래 결과만 미상으로 유지.
- [x] R-RELEASE 최신 Simulator Release 및 R-DEVICE-COMPILE 서명 없는 기기용 Debug 컴파일 성공. 서명/설치/실기기 실행 성공을 뜻하지 않음.
- [x] 삭제 결과 불확실 시 초안/양수 ID 보존·공백 offset 회귀 포함 R-UNIT-FINAL2 단위84개 통과·실패0·skip0. 첫 R-FINAL 단위83/84 및 기대값 수정 이력 보존.
- [x] C10 커밋 후 전체 작업 트리 R-UNIT-C10 단위84개 통과·실패0·skip0.
- [x] C10 독립 Debug Simulator 빌드 R-C10 성공.
- [x] R-FINAL 전체 UI19개 통과·실패0·skip0 및 bundle102통과/1실패 집계를 구분. R-SIGNING profile 부재와 paired 기기 developer disk image 실패를 외부 준비 항목으로 기록.
- [x] 실제 첨부 화면에서 키보드/날짜 전체값·거래 저장 결과·삭제 후 KEEP/구매 보존·알림 전체 정보/위험·시스템 권한 화면 검수. 시장가 안내 잘림1건을 D-20으로 추적.
- [x] C14 안내 레이아웃 수정 후 R-FINAL3 총103개 통과·실패0·skip0·exit0, 최종 두 문장/두 줄 화면 검수, R-C14 독립 build 확인. R-FINAL2의 중단은 별도 보존.
- [x] R-COLD1 cold-start·warm Simulator 푸시 UI2개 통과 및 실제 등록/종료/OS tap/미읽음 상세 확인. 같은 실행의 DNS 단위2개 실패와 전체 실패는 별도 보존.
- [x] DNS 단위 mock의 명시적 HTTPS 격리 후 R-COLD2 전체88개(단위86+Push UI2) 통과·실패0·skip0·exit0 및 C15 commit 확인. cold 종료/배너/상세 첨부 직접 검수.
- [x] C15 기본 설정 R-RELEASE3/R-DEVICE-COMPILE3 성공·fixture Info 빈 값 확인, fixture 문법/프로젝트 plist/공백/범위 점검 통과.
- [x] C15 commit 후 R-FINAL4 전체106개(단위86+UI20) 통과·실패0·skip0·exit0, UI620.650초. 첨부 내보내기와 마지막 fixture 실제 요청 보관, 이후 앱 소스 변경 없음.
- [x] E-UI2 Simulator 권한→simctl 주입→OS banner→tap→상세 1흐름 통과. 실제FCM/APNs 전달은 별도이며 외부미검증으로 유지.
- [x] C1..C14 기능별 파일 분리·관련 검증·명시적 stage/commit 및 C3..C14 독립 빌드 확인. 사용자 SQL/자격정보/검증 산출물은 커밋 대상에서 제외.
- [x] 최종 문서5개의 로컬 검증 결과·실패 이력·외부 범위와 30개 ID를 정리. 신규 앱 소스는 C15까지 커밋됐으며 기존 사용자 SQL은 제외/보존. 문서 commit 후 Git 상태는 아래 인계 기록 방식으로 확인.
- [x] Android 활성28개 ID와 현재 iOS 도달 가능한 기능·컨트롤·API의 마지막 독립 대조에서 추가 확정 누락 없음. 의심한 first_inquiry_delay_minutes는 Android 표시 목록 선언만 있고 DTO/value map에 없어 실제 표시 기능이 아님. 런타임 동등성 성공 주장은 아님.
- [x] ID별 최신 R-FINAL4 결과와 C1..C15 commit을 기록. 최종 문서 C16의 자기 hash 대신 `git log -1` 및 commit 후 `final-git-status.txt`로 실제 Git 상태를 확인하도록 인계.

조사하지 못한 코드 영역은 현재 확인된 활성 Android 범위 내에서는 없다. 다만 Android 실화면·실서비스 사용자/worker 상태·APNs/실기기 동작은 실행하지 못했으므로 “조사 완료”를 실제 동작 동등성 확인으로 해석하면 안 된다. 접근 가능한 iOS 빌드/fixture/Simulator 검증과 필요한 코드 수정은 완료했다.

## Git 작업 기록·최종 보고 갱신 위치

| 기록 ID | commit | 범위 | 해당 시점 검증 |
|---|---|---|---|
| C1 | `94623b7` `docs: inventory Android features and iOS parity baseline` | Android/iOS/API 전수조사·Git/환경 baseline 문서 | 변경전iOS Debug, Android 격리build/19tests 증거기록. 기능이식완료 commit 아님 |
| C2 | `2fb32ed` `feat(ios): preserve identity and add tested API transport` | APIClient GET/send/query·안전오류, 식별자승계/등록/로컬세션, Xcode 테스트기반·공유scheme | 통합 E-U2 39개통과 중 C2 범위는 Core7. 나머지 도메인소스는 당시workingtree 테스트였고 이commit에 포함됐다는 뜻 아님 |
| C3 | `ccd2d98` `feat(ios): add APNs and FCM notification lifecycle` | PUSH-01/02 기반·DATA-01/IOS-01 푸시수명주기: Firebase SDK/delegate/APNs-FCM매핑/token/권한설정UI·테스트4개·setup | E-U4 Push4통과; 해당commit 독립Debugbuild E-C3 성공. main탭 route 최종연결은 후속commit 대상 |
| C4 | `0400095` `fix(ios): recover DNS failures without replaying sent writes` | NET-01/NET-DNS: APIClient DNS복구·원본HTTPS보존·전송된mutation재시도금지·테스트9개 | E-U4 DNS9통과; 해당commit 독립Debugbuild E-C4 성공 |
| C5 | `05ddb33` `feat(ios): port pricing rules and scoped settings updates` | SETTINGS-01..07·IOS-01 설정진입: 모델/API/VM/View·dirtybaseline·가격/조건/bulk·테스트20개 | E-U4 Settings20통과; 해당commit 독립Debugbuild E-C5 성공. E-UI2 설정3흐름통과 |
| C6 | `30e562c` `feat(ios): port alert review and read archive flows` | ALERT-01..04/LINK-01/ARCHIVE-01..02: 모델/API/polling/VM/카드·상세·보관함·테스트12개 | E-U4 Alerts12통과; 해당commit 독립Debugbuild E-C6 성공. E-UI2 기존알림4흐름통과 |
| C7 | `4a4a4bd` `fix(ios): persist failed push token cleanup across sessions` | 푸시 삭제 실패 marker 영속화·activation 재시도·삭제/fetch 경합·재등록 차단, Firebase 없는 OS 권한 처리 | R-M7 Push9 통과; 해당commit 독립Debugbuild R-C7 성공 |
| C8 | `411fba8` `feat(ios): port purchase and resale data workflows` | ResaleTradeModels/ResaleTradeAPI/ResaleTradeViewModel/TradeParityTests: 거래 모델·API·상태, 명시 단계·strict URL·부분실패·회귀20개 | R-M7 Trade20 통과; 해당commit 독립Debugbuild R-C8 성공. View/메인 navigation은 이 commit 범위 밖 |
| C9 | `ae839d9` `fix(ios): preserve trade stage on verification-only saves` | 되팔이 모드에서 정확 확인만 변경한 경우 빈 resale PATCH 생략·기존 KEEP 단계 보존. 명시적 빈 저장의 기존 의미는 유지 | R-M11 Trade22 포함 단위79개 통과; 해당commit 독립Debugbuild R-C9 성공 |
| C10 | `a0db410` `fix(ios): preserve trade drafts and offset timestamps` | ResaleTradeModels/ResaleTradeViewModel/TradeParityTests 3개 파일: 불확실한 삭제 초안/양수 ID 보존·공백 offset·회귀5개 추가 | R-UNIT-FINAL2 및 commit 후 전체 작업 트리 R-UNIT-C10 모두 Trade27 포함 단위84개 통과; 독립 Debug build R-C10 성공 |
| C11 | `b04318e` `feat(ios): connect Android-parity navigation and trade forms` | 메인4탭/route·안정된 ResaleTradeView·보관함 선택 접근성·fixture와 Alert5/Archive2/Auth1/Trade2/History2 UI12개 | R-FINAL 관련 UI 통과; 독립 Debug Simulator build R-C11 성공 |
| C12 | `a5e791d` `fix(ios): retain settings navigation and unsaved bulk inputs` | SettingsView 탭/탐색 경로·일괄 입력 보존 및 Settings UI3개 | R-FINAL Settings3 통과; 독립 Debug Simulator build R-C12 성공 |
| C13 | `8d5dd38` `feat(ios): verify notification permissions and external handoffs` | NotificationSettingsView 안내·ExternalLink/NotificationPermission/Push UI3개 | R-FINAL 해당 UI3개 통과; 독립 Debug Simulator build R-C13 성공 |
| C14 | `37cd0cbc5557898012bca3875dfded09887263d6` `fix(ios): show complete market price guidance` | 시장가 안내 fixedSize/접근성 ID와 기존 Settings UI 높이·본문·화면 회귀 | R-FINAL3 전체103개 통과 및 두 문장/두 줄 화면 검수, R-C14 독립 Debug build·R-RELEASE2/R-DEVICE-COMPILE2 성공 |
| C15 | `974762970a1ba566356bf5db7131c34419cf7bc7` `test(ios): cover isolated cold-start notification routing` | Debug Simulator cold-start fixture 격리·Info preflight·Core URL 회귀2개·Push cold UI·DNS 단위 HTTPS 격리, 6개 파일 | R-COLD2 전체88개 통과, R-RELEASE3/R-DEVICE-COMPILE3 성공. C15 후 R-FINAL4 전체106개도 통과·실패0·skip0·exit0 |
| C16 문서 묶음 | commit 후 `git log -1`로 확인 | 기능 대응표·세 조사 문서·iOS README, 총5개 | 최종 R-FINAL4 결과/외부 범위/과거 실패/재현 방법 정리. 자기 hash는 미리 추정하지 않으며 commit 후 Git 상태는 `final-git-status.txt`와 최종 응답으로 확인 |

앱 구현·테스트 변경은 C15까지 커밋됐으며 이후 앱 소스 변경 없이 전체106개 검증을 완료했다. 이 최종 문서5개는 C16 묶음으로 인계하며 기존 사용자 SQL은 stage 대상이 아니다. 문서 자신의 commit 후 상태를 사전에 단정하지 않는다. 최종 HEAD는 `git log -1`, staged/unstaged/untracked 결과는 새 보관 루트의 `final-git-status.txt`와 최종 응답에서 확인한다.

- 현재 branch: `feat/ios-android-parity`; 새 branch 생성 이유: main기준 별도 parity작업 분리.
- 기준 HEAD: `da769c31ba4afdfa5d3b07ad9ecca2c39d7cbb04`; 현재 앱 체크포인트: `9747629`(C15); **최종 문서 HEAD: 완료 후 `git log -1`로 확인**.
- 생성 commit: C1..C15 확인. 최종 문서는 별도 C16 묶음으로 검토/커밋하고 실제 HEAD는 완료 후 `git log -1`로 확인.
- 문서 commit 후 working tree/staged/unstaged/untracked 확인 위치: `/Users/boongtol_air/Library/Developer/UMTPParity/20260915-resume/final-git-status.txt`. 기존 사용자 SQL은 제외/보존하며 이 문서가 스스로 clean 상태를 가정하지 않는다.
- push: 수행하지 않음.
- 최종 로컬 판정: 활성28개 Android ID와 기존 iOS 보존 기능을 도달 가능한 iOS 코드로 구현·연결했고 C15 후 R-FINAL4 전체106개(단위86+UI20)가 모두 통과했다. C14까지 독립 빌드·C15 포함 최신 Release/기기용 무서명 컴파일·Android APK/단위19개도 통과했다. cold/warm Simulator 클릭과 실제 권한 OFF/ON까지 확인했지만 실서비스 쓰기·원격 APNs·서명/실기기·Android 실행 비교·실제 iOS DNS 장애망은 부분 검증/외부 제한이다. 최초 기대값 실패·DNS 격리 실패·중단 실행·과거 원본 소실을 보존하며 **로컬 구현·검증 완료를 모든 환경의 동등성 완료로 확대하지 않는다.**
