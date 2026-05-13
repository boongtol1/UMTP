# UMTP Android 프로젝트

UMTP(Used Market Tracker Project)의 Android 클라이언트 앱입니다.

## UMTP Android MVP Progress

| Version | Summary | Status |
|---|---|---|
| MVP-A | 수동 URL 전송 | ✅ 완료 |
| MVP-B | Notification Listener 권한 받기 | ✅ 완료 |
| MVP-C | 모든 알림 로그 출력 | ⏳ 대기 |
| MVP-D | 중고나라 알림 필터링 | ⏳ 대기 |
| MVP-E | 알림 텍스트에서 URL 추출 | ⏳ 대기 |
| MVP-F | 추출 URL 서버로 자동 전송 | ⏳ 대기 |

### MVP-A: 수동 URL 전송
사용자가 직접 중고나라 매물 URL을 입력하여 서버에 분석을 요청하고 결과를 확인하는 단계입니다.

#### 주요 기능
- 중고나라 매물 URL 입력 (TextField)
- 서버(FastAPI) `/analyze-url` API 호출 (Retrofit)
- 분석 결과 표시 (성공 여부, 제목, 가격, 적정가, 위험도 등)
- 로딩 상태 및 에러 처리

#### 실행 및 테스트 방법
1. UMTP FastAPI 서버를 실행합니다. (`http://183.111.181.122:8000`)
2. Android 기기(또는 에뮬레이터)를 서버와 같은 네트워크에 연결합니다.
3. 앱을 실행하고 URL 입력창에 중고나라 매물 URL을 입력합니다. (예: `https://web.joongna.com/product/228436846`)
4. '분석 요청' 버튼을 누르고 결과를 확인합니다.

#### 기술 스택
- Kotlin, Jetpack Compose
- Retrofit2, OkHttp3 (Logging Interceptor)
- Kotlin Coroutines
- Material 3

#### 주의사항
- 현재 단계에서는 **Notification Listener를 구현하지 않습니다.**
- 현재 단계에서는 **URL 자동 추출을 하지 않습니다.**
- `user_id`는 `"test_user"`로 고정되어 있습니다.

### MVP-B: Notification Listener 권한 받기 및 진단
나중에 중고나라 키워드 알림을 자동으로 읽기 위해 Android 시스템의 알림 접근 권한을 받는 단계입니다.

#### 주요 기능
- **Notification Listener Service**: 타 앱의 알림을 읽기 위한 서비스 선언 (`UmtpNotificationListenerService`)
- **권한 상태 UI 분리**: '알림 접근 권한(Listener)'과 '일반 앱 알림 권한'을 분리하여 표시
- **진단 로그 강화**: 서비스 연결 및 알림 수신 시 상세 로그 출력
- **설정 바로가기**: 알림 접근 권한 설정 및 앱 상세 알림 설정으로 바로가기 버튼 제공

#### 알림 권한 관련 주의사항
- **알림 접근 권한 (Notification Listener)**: 다른 앱(중고나라 등)의 알림을 읽기 위한 특수 권한입니다. **앱 상세 정보의 "허용된 권한" 목록에는 나타나지 않으며**, 전용 설정 화면(알림 접근 허용)에서 별도로 관리됩니다.
- **앱 알림 표시 권한 (POST_NOTIFICATIONS)**: UMTP 앱이 사용자에게 알림을 표시하기 위한 권한입니다. MVP-B의 핵심 기능(알림 읽기)과는 별개입니다.

#### 실행 및 테스트 방법
1. 앱을 실행하고 하단의 **'A. 알림 접근 권한'** 섹션에서 **'알림 접근 권한 설정 열기'**를 누릅니다.
2. Android 설정에서 **'UMTP Notification Listener'** 항목을 찾아 활성화합니다.
3. 앱으로 돌아와 상태가 **'허용됨'**으로 표시되는지 확인합니다.
4. 다른 앱에서 알림이 발생하면 Logcat에서 `UMTP_NOTIFICATION` 태그로 알림 내용이 출력되는지 확인합니다.

#### 디버깅 및 트러블슈팅
- **권한을 켰는데 로그가 안 나오는 경우**:
  - 권한 설정 화면에서 UMTP 권한을 **껐다가 다시 켜보세요**.
  - 앱을 완전히 종료(Recent Apps에서 스와이프) 후 **재실행**하세요.
  - 앱을 삭제 후 **재설치**해보세요.
  - 일부 기기에서는 **기기 재부팅**이 필요할 수 있습니다.
- **Logcat 태그**:
  - `UMTP_PERMISSION`: 권한 판별 로직 및 시스템 설정값 확인 로그
  - `UMTP_NOTIFICATION`: 서비스 연결 상태 및 수신된 알림 데이터 로그
