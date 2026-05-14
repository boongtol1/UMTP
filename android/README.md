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
| MVP-G | 앱 내부 사용자 ID 기반 구조 | ✅ 완료 |
| MVP-H | 사용자별 MacBook Air 공정가/차이비율 설정 UI | ✅ 완료 |

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

### MVP-G: 앱 내부 사용자 ID 기반 구조
앱 내에서 사용자 고유 ID를 관리하고 서버 요청 시 포함하는 단계입니다.

#### 주요 기능
- SharedPreferences를 이용한 user_id 로컬 저장 및 로드
- 모든 API 요청 시 저장된 user_id 사용

### MVP-H: 사용자별 MacBook Air 공정가/차이비율 설정 UI
사용자가 104개 MacBook Air 모델별로 알림 설정, 공정가, 차이비율을 직접 설정하고 서버에 저장하는 단계입니다.

#### 주요 기능
- 서버에서 MacBook Air unit 목록 및 사용자별 설정 로드
- 칩(Chip) 및 화면 크기별 그룹화된 목록 표시
- 모델별 ON/OFF 토글, 사용자 공정가 입력, 알림 차이비율 입력
- 서버 `/user-fair-prices/upsert` API를 통한 설정 저장
- 입력값 검증 (공정가 > 0, 차이비율 0-100)

#### 실행 및 테스트 방법
1. 메인 화면 상단의 'MacBook Air 설정' 버튼을 클릭합니다.
2. 설정 화면에서 원하는 모델의 스위치를 켜고 공정가와 차이비율을 입력합니다.
3. '저장' 버튼을 눌러 서버에 반영합니다.
4. 앱 재실행 후에도 설정이 유지되는지 확인합니다.
