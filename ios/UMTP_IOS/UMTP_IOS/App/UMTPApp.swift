import SwiftUI

@main
struct UMTPApp: App {
    @StateObject private var appState: AppState

    init() {
        _appState = StateObject(wrappedValue: AppState(sessionService: .shared))
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}
