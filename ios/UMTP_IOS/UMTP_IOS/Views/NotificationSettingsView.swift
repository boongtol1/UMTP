import SwiftUI

struct NotificationSettingsView: View {
    @ObservedObject private var push = PushService.shared
    var body: some View {
        Section("알림") {
            switch push.authorization {
            case .authorized, .provisional, .ephemeral:
                Text("알림 허용됨")
            case .denied:
                Text("알림이 꺼져 있어요. iOS 설정에서 알림을 허용할 수 있어요.")
                Button("iOS 알림 설정 열기") {
                    if let url = URL(string: UIApplication.openNotificationSettingsURLString) { UIApplication.shared.open(url) }
                }
            default:
                Button("알림 허용") { Task { await push.requestPermission() } }
            }
            if !push.isConfigured {
                Text("이 앱의 푸시 연결이 아직 준비되지 않았어요. 앱 내 알림 피드는 사용할 수 있어요.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if let message = push.message { Text(message).font(.caption).foregroundStyle(.secondary) }
        }
    }
}
