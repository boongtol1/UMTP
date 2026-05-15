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
            ContentView()
                .environmentObject(appState)
        }
    }
}
