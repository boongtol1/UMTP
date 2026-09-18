# UMTP iOS

기존 SwiftUI·Combine·URLSession 구조를 유지하면서 Android의 활성 알림, 읽음 보관함, 거래 입력, 설정 흐름을 구현·연결한 앱입니다. 앱 코드 구현, Simulator 검증, 실서비스/APNs 검증은 구분합니다. 기능별 근거·플랫폼 차이·커밋·최신 결과는 [Android–iOS 기능 대응표](../../../docs/android-ios-parity.md)를 확인하세요.

## 현재 구조와 기능

- `App/UMTPApp.swift`: 앱 진입점과 알림 delegate 연결. `ContentView`가 저장된 세션을 복원하고 등록 화면 또는 메인 화면으로 분기합니다.
- `Models/`, `Services/`, `ViewModels/`, `Views/`: 데이터 계약, API·로컬 저장, 상태 관리, SwiftUI 화면을 분리합니다.
- `MainTabView`: 알림 / 읽음 보관함 / 거래 입력 / 설정의 네 탭. 알림과 보관함은 상태를 공유하고, 거래 입력 초안은 탭을 바꿔도 유지합니다.
- 알림: 상세·본문·이미지·가격·위험 정보, 선택/전체 검토 완료, 읽음 보관함 그룹·삭제, 실패 재시도. 상세를 여는 것만으로 읽음 처리하지 않습니다. 화면이 활성화된 foreground에서 10초 간격으로 갱신하고 복귀 시 재조회합니다.
- 거래: URL·상품 ID·알림·보관함에서 시작, 사전 입력, 구매/판매 기록, 검증 및 변경 필드 저장, 거래 내역·삭제. 기존 초안을 다른 알림으로 교체할 때 확인합니다.
- 설정: MacBook Air·Mac mini·MacBook Pro·iMac의 제품·칩·화면·메모리·저장장치별 조건, 기준/희망 가격, 키워드, 우선순위·활성화, 후보 알림, 일괄 적용·초기화·규칙 갱신. MacBook Pro는 M1~M5의 기본·Pro·Max 칩을 세대순으로 표시하며 화면 크기와 RAM/SSD 조합은 서버 카탈로그를 따릅니다. iMac은 M1·M3·M4의 24인치, SQL 시드의 32개 조합을 같은 방식으로 표시합니다.
- 세션: 기존 `umtp_user_id`를 보존합니다. 기기 식별자는 기존 값과 호환되도록 UserDefaults와 Keychain에 고정하며, 로그아웃으로 기기 식별자를 바꾸지 않습니다.
- 원격 알림: 권한 요청, FCM 토큰 등록, 알림 클릭 후 상세 이동을 연결합니다. Firebase 설정 없이도 나머지 앱 기능은 동작하지만 실서비스 푸시 수신은 별도 설정과 서버 대응이 필요합니다.

Mac Studio는 서버의 SQL 시드 80개 조합을 표시합니다. M1/M2 Max·Ultra, M3 Ultra, M4 Max를 세대순으로 정렬하며 Mac mini와 같이 화면 선택 없이 RAM/SSD 설정으로 이동합니다. 개별 저장과 현재 칩/제품 전체 일괄 적용에서 화면 값은 0을 유지하며, 제목과 알림 사양에는 0인치를 표시하지 않습니다.

프로젝트 주변 경로:

```text
ios/UMTP_IOS/
  UMTP_IOS.xcodeproj/       # 공유 scheme: UMTP_IOS
  UMTP_IOS/                # 앱 소스, 이 README
  Config/                  # Info.plist, UMTP.entitlements
  UMTP_IOSTests/            # 모델·API·상태 전이 단위 테스트
  UMTP_IOSUITests/          # 등록·알림·설정·거래·푸시 UI 테스트
  TestsSupport/            # 로컬 HTTP fixture
```

## 빌드

iOS 배포 대상은 17.0 이상입니다. 호환되는 iOS SDK가 포함된 Xcode와 Simulator runtime이 필요합니다. Firebase Apple SDK `12.19.1`을 Swift Package Manager로 사용하므로 최초 패키지 확인에는 네트워크가 필요합니다. 아래 명령은 모두 **저장소 루트**에서 실행합니다.

```sh
xcodebuild -list -project ios/UMTP_IOS/UMTP_IOS.xcodeproj
xcrun simctl list devices available
xcodebuild -resolvePackageDependencies \
  -project ios/UMTP_IOS/UMTP_IOS.xcodeproj -scheme UMTP_IOS
xcodebuild -project ios/UMTP_IOS/UMTP_IOS.xcodeproj \
  -scheme UMTP_IOS -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/umtp-ios-build CODE_SIGNING_ALLOWED=NO build
```

Xcode에서 `UMTP_IOS.xcodeproj`를 열고 공유 scheme `UMTP_IOS`를 선택해 실행할 수도 있습니다. Bundle ID는 `boongtol.UMTP-IOS`입니다. 실제 기기 설치에는 유효한 Apple Developer 서명·프로비저닝이 필요합니다. 서명 없는 컴파일은 Simulator뿐 아니라 generic iOS 대상으로도 가능하지만 실기기 설치·실행용 산출물이라는 뜻은 아닙니다.

## 테스트

공유 scheme에 `UMTP_IOSTests`와 `UMTP_IOSUITests`가 연결되어 있습니다. 먼저 자동화 전용 Simulator의 실제 UUID를 선택합니다. UI 테스트는 앱의 테스트 사용자 세션과 해당 Simulator의 알림 권한을 변경하므로 평소 사용하는 앱/기기와 분리하세요.

```sh
export UMTP_SIMULATOR_ID="사용할 Simulator UUID"
xcodebuild -project ios/UMTP_IOS/UMTP_IOS.xcodeproj \
  -scheme UMTP_IOS -configuration Debug \
  -destination "platform=iOS Simulator,id=$UMTP_SIMULATOR_ID" \
  -derivedDataPath /tmp/umtp-ios-build \
  -only-testing:UMTP_IOSTests CODE_SIGNING_ALLOWED=NO test
```

UI 테스트는 실제 서비스 대신 Python 표준 라이브러리로 작성된 메모리 기반 fixture를 사용합니다. 별도 터미널에서 같은 Simulator UUID를 지정한 뒤 서버를 계속 실행해 둡니다.

MacBook Pro와 Mac Studio 설정 fixture는 저장소의 각 `seed_silicon_*_fair_prices.sql`에서 사양과 시스템 시장가를 읽습니다. `SettingsFlowUITests`는 13인치 기본 칩 탐색과 14/16인치 Max 칩 선택·개별 저장에 더해 Studio Max/Ultra의 화면 선택 생략과 저장 요청을 확인합니다. Studio 단위 테스트는 512GB RAM·16TB SSD 직렬화와 제품/칩 일괄 적용 범위를 확인합니다.

iMac fixture는 `umtp/sql/seed_silicon_imac_fair_prices.sql`의 32개 사양·공정가를 그대로 읽고 신규 조건은 감시 OFF로 시작합니다. `SettingsParityTests`는 제품/칩/24인치 그룹, 시드 가격·저장 요청, 제품/칩별 일괄 설정 범위를 검증하고 `AlertsParityTests`는 알림 사양 표시를 확인합니다. `SettingsFlowUITests/testIMacSeedCatalogAndIndividualSaveReachTheAPI`는 `iMac → M4 → 24인치` 탐색과 150만원 기본 시장가, 개별 저장 API 요청을 검증합니다.

2026-09-18 iMac 확장 검증: Xcode 27.0 / iOS 26.5 Simulator에서 전체 설정 UI 6개가 실패 없이 통과했습니다. 단위 테스트의 `effective_search_keyword` fixture 누락을 실제 API 응답에 맞춰 수정한 뒤 전체 단위 94개를 재실행해 실패·skip 없이 통과했습니다. 이 수정은 테스트 데이터에만 적용했고 앱 코드와 UI 테스트는 바꾸지 않았습니다. 서버는 417개 통과·DB 의존 15개 skip이며 DB/ML 의존 모듈 2개는 제외했습니다. 시드 32개 사양 일치와 기존 제품을 포함한 파싱 표현 1,407건도 확인했습니다. 검증은 loopback fixture와 테스트 환경에서 수행했으며 운영 DB 적용·배포·실기기·APNs 검증은 포함하지 않습니다.

2026-09-18 MacBook Pro 확장 검증은 Xcode 27.0 / iOS 26.5 Simulator에서 단위 90개와 설정 UI 5개를 통과했습니다(실패·skip 0). 실제 서비스에 쓰지 않는 loopback fixture의 SQL 시드 276개 조합으로 확인했으며, 배포·실기기·APNs 검증은 포함하지 않습니다.

MacBook Neo도 같은 `제품 → 칩 → 화면 크기 → RAM/SSD` 설정 흐름을 사용합니다. `A18 Pro → 13인치`에서 서버 카탈로그의 8GB/256GB·8GB/512GB만 표시하며, 시장가·알림 기준·활성화·우선순위·일괄 적용을 기존 제품과 같은 방식으로 저장합니다. 알림에도 제품명과 A18 Pro 사양을 표시합니다.

Neo fixture는 `umtp/sql/seed_silicon_macbook_neo_fair_prices.sql`에서 두 사양과 850,000원·900,000원 시장가를 읽습니다. `SettingsFlowUITests/testMacBookNeoSeedCatalogAndSaveReachTheAPI`가 13인치 선택, 두 시장가 표시, 512GB 조건 저장 요청을 검증합니다. 2026-09-18 Xcode 27.0 / iOS 26.5 Simulator에서 단위 93개와 설정 UI 6개가 통과했습니다(실패·skip 0). 운영 서비스·실기기·APNs 테스트는 포함하지 않습니다.

2026-09-18 Mac Studio 확장 검증은 Xcode 27.0 / iOS 26.5 Simulator에서 단위 94개와 설정 UI 7개, 총 101개를 통과했습니다(실패·skip 0). loopback fixture로 Max/Ultra의 화면 선택 생략과 설정 저장을 확인했습니다. 서버는 412개 통과·DB 의존 15개 skip이며 환경 의존 DB/ML 모듈 2개는 제외했습니다. 시드 80개 사양의 정확한 일치와 기존 Air/Mini/Pro를 포함한 1,551개 사양 표현을 별도로 검증했습니다. 운영 DB 변경·배포·실제 메시지 발송은 수행하지 않았습니다.

```sh
export UMTP_SIMULATOR_ID="사용할 Simulator UUID"
python3 ios/UMTP_IOS/TestsSupport/parity_server.py
```

서버는 `127.0.0.1:18765`에만 바인딩합니다. 전체 UI에는 OS가 종료된 앱을 직접 시작하는 cold 알림 테스트가 포함되므로, 테스트 터미널에서는 아래 전용 빌드 설정과 일반 빌드와 다른 DerivedData 경로를 사용합니다.

```sh
xcodebuild -project ios/UMTP_IOS/UMTP_IOS.xcodeproj \
  -scheme UMTP_IOS -configuration Debug \
  -destination "platform=iOS Simulator,id=$UMTP_SIMULATOR_ID" \
  -derivedDataPath /tmp/umtp-ios-parity-fixture \
  UMTP_PARITY_FIXTURE_URL=http://127.0.0.1:18765 \
  -only-testing:UMTP_IOSUITests CODE_SIGNING_ALLOWED=NO test
```

UI 테스트가 앱의 `UMTP_TEST_BASE_URL`을 `http://127.0.0.1:18765`로 설정하고 가상의 테스트 사용자로 실행합니다. fixture의 `POST /__reset`은 테스트 상태 초기화, `GET /__events`는 실제 도착한 요청 확인, `POST /__fail`은 API 오류 모사에 사용합니다. 일부 기존 UI는 서버가 없으면 skip하지만 cold 테스트는 fixture 연결 실패나 UUID 등 안전 조건 누락을 실패로 처리합니다. cold 테스트에서 명시적으로 skip하는 경우는 설치 앱에 전용 fixture 빌드가 필요한 `fixture_build_required`뿐입니다. skip은 성공이 아니며 같은 fixture를 여러 Simulator의 UI 실행에 동시에 사용하지 마세요.

`PushFlowUITests`는 fixture 프로세스의 `UMTP_SIMULATOR_ID`를 사용하여 고정 payload를 `xcrun simctl push`로 주입합니다. UUID는 테스트 대상 Simulator와 같아야 하며 서버 시작 전에 지정해야 합니다. warm/background와 cold 시작 모두 권한 승인·OS 알림 클릭·상세 이동을 검증하지만 Firebase/APNs 서버 전달 성공은 검증하지 않습니다.

cold 시작은 `GET /__cold-launch-status`로 설치 앱의 bundle ID·Simulator 플랫폼·정확한 fixture URL·DEBUG 조건을 먼저 검사합니다. 실제 로컬 등록 요청과 세션 저장을 확인하고 앱을 종료한 뒤, 이후 `launch`/`activate` 없이 OS 알림 tap만으로 시작시킵니다. alert101 상세 표시·미읽음 유지·새 GET 요청을 확인합니다. OS 시작에는 XCTest 환경변수가 전달되지 않으므로 위 `UMTP_PARITY_FIXTURE_URL` 설정이 필요하며 영구 UserDefaults API override는 만들지 않습니다.

2026-09-15 패리티 작업의 앱 commit은 `974762970a1ba566356bf5db7131c34419cf7bc7`(C15)입니다. commit 후 `integrated-final-4` 전체106개(단위86+UI20)가 통과·실패0·skip0·exit0이며 UI는620.650초였습니다. 단위는 Core9·Alerts12·DNS9·Push9·Settings20·Trade27입니다. 수동 거래 키보드/저장·삭제·설정 초안/탐색 보존·안내 전체 표시·외부 링크·실제 시스템 권한 OFF/ON·warm/cold OS 알림 클릭을 포함한 당시 결과입니다. 로컬 구현·검증 완료와 실서비스/원격 APNs/실기기 검증은 구분합니다. C14의 전체103개 `integrated-final-3`(UI594.045초), C15 격리 검증88개 `cold-launch-2`(UI33.543초) 성공도 별도 이력으로 보존합니다.

첫 `integrated-final-1`은 잘못된 단위 오류 타입 기대값1개로 102통과/1실패였고 이후 기대값만 수정해 재검증했습니다. `integrated-final-2`는 수정 전 binary여서 중단했습니다. `cold-launch-1`은 cold/warm UI2개가 통과했지만 fixture HTTP 기본값에 의존한 DNS 단위2개가 실패하여 전체88개는 실패했습니다. DNS mock에 명시적 HTTPS를 주입한 뒤 `cold-launch-2`가 모두 통과했습니다. 각 실패/중단은 후속 성공과 별도 이력으로 유지합니다.

C14까지 독립 Debug 빌드가 통과했고 C15 포함 최신 `release-final-3` Simulator Release 및 `device-unsigned-final-3` generic iOS Debug 컴파일도 성공했습니다. 해당 Release의 fixture/DEBUG Info 값과 기기용 Debug의 fixture Info 값은 비어 있음을 확인했습니다. 실제 AppConfig를 DEBUG 없이 macOS에서 컴파일한 격리 검사도 환경변수를 무시하고 실서비스 URL을 반환했지만, 이는 iOS Release 실행 검증을 뜻하지 않습니다. 최종 문서 commit은 완료 후 `git log -1`로 확인합니다.

기기용 컴파일 성공은 서명·설치·실기기 실행을 뜻하지 않습니다. paired iPhone15Pro는 iOS27.0이며 developer mode는 enabled이고 설치 Xcode는26.6뿐입니다. 직접 기기 빌드는 developer disk image 마운트 실패, 별도 generic signed build는 provisioning profile 부재로 실패했습니다. developer mode OFF로 오해하면 안 됩니다. 공식 알림 설정 링크가 설정 루트에 도착할 때는 안내된 수동 경로를 사용하며 이 OS 대안의 권한 OFF/ON 흐름은 Simulator에서 통과했습니다.

재시작 전 단위67개·UI 2차12개 중10개 및 후속 대상 UI/Release 성공은 과거 이력입니다. `/tmp/umtp-parity.PKH6ia/` 원본 로그·xcresult는 재시작으로 없어졌고 새 자료는 `/Users/boongtol_air/Library/Developer/UMTPParity/20260915-resume/`에 보관합니다. Android APK/단위19개와 원본 HTTPS health/catalog 조회 재실행은 성공했지만 실서비스 사용자 쓰기·APNs/서명된 실기기 검증은 별도입니다. 실행별 결과와 남은 검증은 [기능 대응표](../../../docs/android-ios-parity.md)를 확인하세요.

## API 환경과 실서비스 주의

기본 API는 `https://umtp.duckdns.org`입니다. `UMTP_TEST_BASE_URL` 환경변수는 **DEBUG 빌드에서만** 유효한 HTTP(S) loopback 주소(`127.0.0.1`, `localhost`, `::1`)에 적용됩니다. 공백·userinfo·query·fragment·잘못된 port 등 모호한 주소는 거부합니다. 환경변수가 없으면 **Debug Simulator 전용** `UMTP_PARITY_FIXTURE_URL`의 bundled 값을 같은 기준으로 확인합니다. bundled fixture는 Release와 physical 기기에서 무시하고 Release는 환경변수도 무시합니다. 일반 Debug도 두 override가 모두 없으면 실서비스를 사용하므로 전용 빌드 설정을 일반 배포 설정에 추가하지 마세요.

등록, 검토 완료, 보관함 삭제, 설정 저장, 거래 저장·삭제는 실제 서버 데이터를 변경합니다. 자동화에는 위 fixture를 사용하고, 실서비스 확인은 용도가 명확한 테스트 계정으로 수행하세요. 실제 사용자 데이터나 인증 정보로 fixture를 채우지 마세요.

## APNs / Firebase 설정

[iOS 원격 알림 설정과 검증 범위](../../../docs/ios-push-setup.md)에 Firebase 앱 등록, `GoogleService-Info.plist`, APNs 키, 서명, 서버 발송 변경안과 검증 절차를 정리했습니다. 실제 설정 파일·인증 키는 Git에 넣지 않습니다.

현재 백엔드는 iOS 토큰 저장을 허용하지만 발송 worker가 Android 토큰만 조회합니다. 실서비스 iOS 수신에는 문서의 최소 서버 대응과 Firebase/APNs 설정이 필요합니다. 실제 기기의 서비스 수신·종료 상태 전달·토큰 회전 검증과 Simulator 주입 검증을 구분해야 합니다. iOS 백그라운드에서 지속적인 10초 폴링을 보장하지 않습니다.
