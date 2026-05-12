# UMTP Android 프로젝트

UMTP(Used Market Tracker Project)의 Android 클라이언트 앱입니다.

## UMTP Android MVP Progress

| Version | Summary | Status |
|---|---|---|
| MVP-A | 수동 URL 전송 | ✅ 완료 |
| MVP-B | Notification Listener 권한 받기 | ⏳ 대기 |
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
