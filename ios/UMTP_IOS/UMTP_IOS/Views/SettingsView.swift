import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = SettingsViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("설정 화면 준비 중")
                    .font(.headline)

                Text("앱 상태: \(appState.isLoggedIn ? "로그인됨" : "로그아웃")")
                    .foregroundStyle(.secondary)

                Button("로그아웃") {
                    UserSessionService.shared.clearUserId()
                    appState.userId = nil
                }
                .buttonStyle(.bordered)
            }
            .padding()
            .navigationTitle("설정")
        }
    }
}
