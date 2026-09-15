# iOS 원격 알림 연결과 검증 범위

## 현재 구현

`PushService.swift`는 UIApplicationDelegate + UNUserNotificationCenterDelegate를 기존 SwiftUI lifecycle에 연결한다. FirebaseMessaging 12.19.1을 고정하고 APNs 기기 토큰을 FCM에 명시 전달한다. 서버에는 **FCM token, platform=ios**를 등록한다. APNs raw token 또는 Firebase installation ID를 기존 FCM token API로 보내지 않는다.

- Firebase 설정이 없는 개발 빌드에서도 앱은 실행된다. 알림 피드·설정·거래 API는 별개로 동작하며 원격 알림 연결 상태를 설정에 표시한다.
- 사용자 로그인 이후 권한 확인, 거부 시 iOS 설정 이동, 토큰 회전 및 등록 실패 재시도, 실제 `ok:true` 확인 후 사용자/토큰별 등록 기록을 저장한다.
- 로그아웃 시 원격 알림 등록과 FCM 자동 등록을 해제하고 FCM token 삭제가 끝나야 재로그인 등록을 진행한다. 이전 세션의 비동기 응답은 새 세션에 반영하지 않는다.
- foreground 수신은 OS banner를 한 번 표시하고 피드를 새로 조회한다. 표준/data를 각각 로컬 알림으로 중복 생성하지 않는다.
- 알림 클릭은 양수 정수 `alert_id`를 보존하고 로그인/세션 복원 후 알림 탭으로 이동한다. 최신 피드→읽음 보관함에서 상세를 찾는다. 조회 실패 시 재시도할 수 있도록 pending ID를 유지한다.
- 앱을 닫은 상태에서 지속적인 10초 polling을 보장하지 않는다. iOS foreground에서만 polling하고 복귀 시 즉시 재조회한다. background 원격 알림은 iOS 전달 정책을 따른다.

SDK의 기본 registration-token 모드를 유지한다(`FirebaseMessagingInstallationIdEnabled=false`). 최신 SDK 문서의 installation-ID 모드는 현재 backend 발송 계약과 다른 방식이며 의도적으로 활성화하지 않는다. 근거: [Firebase Apple SDK 12.19.1 FIRMessaging.h](https://github.com/firebase/firebase-ios-sdk/blob/12.19.1/FirebaseMessaging/Sources/Public/FirebaseMessaging/FIRMessaging.h), [Firebase Apple FCM 설정](https://firebase.google.com/docs/cloud-messaging/ios/get-started).

## 실제 발송에 필요한 설정

1. 기존 Firebase 프로젝트에 iOS bundle ID `boongtol.UMTP-IOS` 앱을 등록한다. 이 앱용 `GoogleService-Info.plist`를 `ios/UMTP_IOS/UMTP_IOS/`에 둔다. 실제 파일은 `.gitignore`로 제외한다. Android `google-services.json`을 iOS 설정으로 변환하지 않는다.
2. Firebase console의 Apple 앱 Cloud Messaging 설정에 APNs authentication key 또는 인증서를 연결한다. 키/인증서 파일을 Git에 넣지 않는다.
3. Apple Developer App ID에 Push Notifications를 활성화하고 기존 team의 유효한 profile로 서명한다. `Config/UMTP.entitlements`의 환경은 Debug=development, Release=production이다. 서명 설정을 다른 사용자/team으로 임의 변경하지 않는다.
4. 아래 backend 발송 필터를 iOS도 포함하도록 변경/배포해야 한다. 현재 API는 iOS token 저장을 허용하지만 worker가 이를 읽지 않는다.

권한/APNs 필요사항의 근거: [Apple APNs 등록](https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns), [Firebase APNs key 업로드](https://firebase.google.com/docs/cloud-messaging/ios/get-started#upload_your_apns_authentication_key). 실서비스 수신 완료는 이 설정과 서버 발송 후 기기에서 확인해야 한다.

## 필요한 최소 backend 변경안 (실제 backend 코드는 수정하지 않음)

근거 `umtp/src/notification_worker.py:_send_fcm_to_user`, 현재 약 1970행:

```python
push_tokens = list_active_user_push_tokens(normalized_user_id, platform="android")
```

현재 Android 발송을 보존하면서 `platform="ios"` 목록을 추가하고 플랫폼에 맞는 FCM config를 설정해야 한다. 예시 변경 범위:

```python
push_tokens = (
    list_active_user_push_tokens(normalized_user_id, platform="android")
    + list_active_user_push_tokens(normalized_user_id, platform="ios")
)
# 기존 messaging.Message의 notification/data/android는 유지하고 APNs 구성을 추가:
apns=messaging.APNSConfig(
    headers={"apns-push-type": "alert", "apns-priority": "10"},
    payload=messaging.APNSPayload(aps=messaging.Aps(sound="default")),
)
```

실제 적용 전에 같은 token의 중복 행 및 서버 SDK 버전 계약을 확인하고 android/ios 각각 발송·무효토큰 비활성화·Telegram 병행·둘 다 실패·채널 없음 정책을 회귀 테스트한다. backend 수정·배포는 본 이식의 기본 범위를 벗어나므로 이 문서에 최소안만 남겼다.

## 검증 구분

- `PushParityTests`: payload 파싱, 토큰 회전, 사용자별 중복 등록 방지, 실패 재시도, 로그아웃과 등록 경합을 모의 upload로 검증한다. 실제 APNs 검증이 아니다.
- `PushFlowUITests`/`simctl push`: iOS Simulator에 APNs 형태 payload를 주입해 권한·OS 알림 클릭·화면 이동을 검증한다. Firebase/APNs 서버에서 인터넷을 통해 전달된 알림과 구분한다.
- 실제 Firebase token 생성/서비스 token 등록/서버 발송/APNs 수신/잠금화면·종료상태 전달은 위 설정과 테스트 계정이 있어야 검증할 수 있다.
- 실제 실행 여부·통과/실패는 [기능 대응표](android-ios-parity.md)의 최신 검증 기록을 따른다. 이 문서의 테스트 설명 자체는 성공 주장 아님.
