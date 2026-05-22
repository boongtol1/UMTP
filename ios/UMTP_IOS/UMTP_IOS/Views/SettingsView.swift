import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = SettingsViewModel()

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("설정 화면 준비 중")
                    .font(.headline)

                Text("앱 상태: \(appState.isLoggedIn ? "로그인됨" : "로그아웃")")
                    .foregroundStyle(.secondary)

                Group {
                    Text("조건 변경 후보 안내")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Text("조건을 변경하면 최근 7일 안에 분석된 매물도 새 기준으로 다시 확인해요.")
                    Text("이전 기준에는 안 맞았지만 새 기준에는 맞는 매물은 조건 변경 후보로 알려드려요.")
                }
                .font(.footnote)
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
