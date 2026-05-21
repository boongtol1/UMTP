# UMTP

- iOS Stage1: 앱 시작 시 `user_id` 세션 복원 후 진입 분기(등록 화면/메인 화면)를 구현했습니다.
- iOS Stage1: `POST /users/register` API 연동과 `UserDefaults` 기반 세션 저장을 구현했습니다.
- iOS Stage1: 메인 화면은 placeholder이며 Alert Feed/Settings는 Stage2에서 연결 예정입니다.
- TODO(Stage2): Keychain 영구 UUID, Alert Feed API, Settings, Push 알림 연동.
