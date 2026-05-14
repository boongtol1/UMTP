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
| MVP-H | 사용자별 MacBook Air 설정 트리 UI | ✅ 완료 |

### MVP-A: 수동 URL 전송
사용자가 직접 중고나라 매물 URL을 입력하여 서버에 분석을 요청하고 결과를 확인하는 단계입니다. (현재 메인 화면에서 제외됨)

#### 주요 기능
- 중고나라 매물 URL 입력 (TextField)
- 서버(FastAPI) `/analyze-url` API 호출 (Retrofit)
- 분석 결과 표시 (성공 여부, 제목, 가격, 적정가, 위험도 등)
- 로딩 상태 및 에러 처리

### MVP-G: 앱 내부 사용자 ID 기반 구조
앱 내에서 사용자 고유 ID를 관리하고 서버 요청 시 포함하는 단계입니다.

#### 주요 기능
- SharedPreferences를 이용한 user_id 로컬 저장 및 로드
- 모든 API 요청 시 저장된 user_id 사용

### MVP-H: 사용자별 MacBook Air 설정 트리 UI
사용자가 칩, 화면 크기, RAM/SSD 조합을 단계별로 선택하여 설정을 관리하는 트리 구조 UI 단계입니다.

#### 주요 기능
- **User ID 기반 접근**: 앱 최초 실행 시 `user_id` 등록 필수. 서버(`/users/register`) 연동.
- **계층형 탐색**:
    - 칩 리스트 (M1 ~ M5)
    - 화면 크기 리스트 (13인치, 15인치 등)
    - RAM/SSD 조합별 설정 카드
- **항목별 개별 저장**: 각 조합마다 '저장' 버튼을 통해 개별적으로 서버(`/user-fair-prices/upsert`)에 반영.
- **상태 유지**: `SharedPreferences`를 통한 로그인 세션 유지 및 로그아웃 기능.

#### 실행 및 테스트 방법
1. 앱 실행 시 User ID를 입력하고 등록합니다.
2. 원하는 칩(예: M2)을 선택합니다.
3. 원하는 화면 크기(예: 15인치)를 선택합니다.
4. 각 모델별로 스위치, 공정가, 차이비율을 설정하고 '저장'을 누릅니다.
5. 앱 재실행 후 설정값이 서버에서 다시 로드되는지 확인합니다.

#### 기술 스택
- Kotlin, Jetpack Compose
- Retrofit2, OkHttp3 (Logging Interceptor)
- Kotlin Coroutines
- Material 3
