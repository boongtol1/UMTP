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
| MVP-I | 기기당 단일 user_id + 앱 내부 거래 알림 피드 | ✅ 완료 |

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
- **상태 유지**: `SharedPreferences`를 통한 로그인 세션 유지.

### MVP-I: 기기당 단일 user_id + 앱 내부 거래 알림 피드
사용자 경험을 강화하기 위해 기기별 고정 ID 정책을 적용하고 앱 내에서 실시간 알림을 확인할 수 있는 피드 기능을 추가한 단계입니다.

#### 주요 기능
- **기기당 단일 ID 고정**: 최초 1회 등록 후 `user_id` 변경 불가 정책 적용.
- **거래 알림 피드**: 서버(`GET /alerts`) 데이터를 기반으로 대화창 형태의 실시간 거래 피드 구현.
- **자동 폴링(Polling)**: 30초 간격으로 새로운 알림 자동 조회.
- **상세 정보 확인**: 알림 카드 클릭 시 중고나라 해당 매물 URL로 브라우저 연결.
- **읽음 상태 관리**: 로컬 상태 기반으로 확인한 알림 시각적 구분.
- **Mock 데이터 지원**: 서버 API 미준비 시 샘플 데이터를 통한 UI 확인 기능 포함.

#### 실행 및 테스트 방법
1. 앱 재실행 시 기존 등록된 ID로 자동 진입하는지 확인합니다.
2. 하단 탭의 '알림' 메뉴에서 최신 거래 목록이 표시되는지 확인합니다.
3. 알림 카드를 클릭하여 브라우저가 정상적으로 열리는지, 카드가 '읽음' 상태(흐릿한 색상)로 변하는지 확인합니다.
4. '설정' 탭에서 기존의 MacBook Air 상세 설정이 정상 동작하는지 확인합니다.

#### 기술 스택
- Kotlin, Jetpack Compose
- Retrofit2, OkHttp3 (Logging Interceptor)
- Kotlin Coroutines
- Material 3

### 서버 주소 설정
- 기본 서버 주소는 `http://183.111.181.122:8000/` 입니다.
- 다른 서버를 쓰려면 `android/gradle.properties` 또는 사용자 전역 `~/.gradle/gradle.properties`에 아래를 추가하세요.

```properties
UMTP_BASE_URL=http://<SERVER_HOST>:8000/
```

- 주소 끝 `/`는 없어도 자동 보정됩니다.
