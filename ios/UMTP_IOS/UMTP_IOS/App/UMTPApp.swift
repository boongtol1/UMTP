import SwiftUI

@main
struct UMTPApp: App {
    @StateObject private var appState: AppState

    init() {
        let sessionService = UserSessionService.shared
        let initialUserId = sessionService.loadUserId()
        _appState = StateObject(wrappedValue: AppState(userId: initialUserId))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
        }
    }
}

private struct RootView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Group {
            if appState.isLoggedIn {
                MainTabView()
            } else {
                UserSetupView()
            }
        }
    }
}
