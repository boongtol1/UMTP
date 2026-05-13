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

### MVP-B: Notification Listener 권한 받기
나중에 중고나라 키워드 알림을 자동으로 읽기 위해 Android 시스템의 알림 접근 권한을 받는 단계입니다.

#### 주요 기능
- Notification Listener Service 선언 및 등록
- 앱 내 알림 접근 권한 상태 표시 (허용됨 / 필요함)
- Android 알림 접근 권한 설정 화면으로 이동 버튼 추가
- 앱 복귀 시 권한 상태 자동 갱신

#### 실행 및 테스트 방법
1. 앱을 실행합니다.
2. 하단의 'Notification Listener 권한' 섹션에서 '알림 접근 권한 열기' 버튼을 누릅니다.
3. Android 설정 화면에서 'UMTP' 앱의 알림 접근 권한을 허용합니다.
4. 앱으로 돌아오면 상태가 '허용됨'으로 변경된 것을 확인합니다.
5. Logcat에서 `UMTP_NOTIFICATION: Notification Listener connected` 로그를 확인합니다.

#### 주의사항
- **MVP-B에서는 아직 알림 내용을 읽거나 로그를 출력하지 않습니다.** (MVP-C 예정)
- **MVP-B에서는 아직 필터링이나 URL 추출을 하지 않습니다.** (MVP-D, E 예정)
