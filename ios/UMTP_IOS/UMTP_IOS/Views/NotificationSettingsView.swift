import SwiftUI

struct NotificationSettingsView: View {
    @ObservedObject private var push = PushService.shared
    @State private var openingSettings = false
    @State private var settingsOpenError: String?

    private var appSettingsName: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String
            ?? Bundle.main.object(forInfoDictionaryKey: "CFBundleName") as? String
            ?? "UMTP"
    }

    var body: some View {
        Section("알림") {
            switch push.authorization {
            case .authorized, .provisional, .ephemeral:
                Text("알림 허용됨")
            case .denied:
                Text("알림이 꺼져 있어요. iOS 설정에서 알림을 허용할 수 있어요.")
            default:
                Button("알림 허용") { Task { await push.requestPermission() } }
            }
            if [.authorized, .provisional, .ephemeral, .denied].contains(push.authorization) {
                Button("iOS 알림 설정 열기") {
                    Task { await openNotificationSettings() }
                }
                .disabled(openingSettings)
                Text("바로 열리지 않으면 iOS 설정 → 알림 → \(appSettingsName)을 선택해 주세요. 알림 메뉴가 없으면 iOS 설정 → 앱 → \(appSettingsName) → 알림을 확인해 주세요.")
                    .font(.caption).foregroundStyle(.secondary)
                    .accessibilityIdentifier("notification.settings.guidance")
            }
            if let settingsOpenError {
                Text(settingsOpenError).font(.caption).foregroundStyle(.red)
                    .accessibilityIdentifier("notification.settings.openError")
            }
            if !push.isConfigured {
                Text("이 앱의 푸시 연결이 아직 준비되지 않았어요. 앱 내 알림 피드는 사용할 수 있어요.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if let message = push.message { Text(message).font(.caption).foregroundStyle(.secondary) }
        }
    }

    private func openNotificationSettings() async {
        guard !openingSettings else { return }
        openingSettings = true
        settingsOpenError = nil
        defer { openingSettings = false }
        guard let url = URL(string: UIApplication.openNotificationSettingsURLString),
              await UIApplication.shared.open(url) else {
            settingsOpenError = "iOS 설정을 열지 못했어요. 설정 앱을 직접 열어 알림 권한을 확인해 주세요."
            return
        }
    }
}
