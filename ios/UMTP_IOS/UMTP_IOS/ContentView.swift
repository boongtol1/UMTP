import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @State private var didRestoreSession = false

    var body: some View {
        Group {
            if appState.isLoadingSession {
                ProgressView("세션 확인 중...")
            } else if appState.isLoggedIn {
                MainPlaceholderView(userId: appState.userId ?? "")
            } else {
                UserSetupView()
            }
        }
        .task {
            guard !didRestoreSession else { return }
            didRestoreSession = true
            appState.restoreSession()
        }
    }
}
