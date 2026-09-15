import SwiftUI

@main
struct UMTPApp: App {
    @UIApplicationDelegateAdaptor(UMTPAppDelegate.self) private var appDelegate
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var pushes = PushService.shared
    @StateObject private var appState: AppState

    init() {
        _appState = StateObject(wrappedValue: AppState(sessionService: .shared))
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .task(id: appState.userId) { await pushes.activate(user: appState.userId) }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { Task { await pushes.activate(user: appState.userId) } }
                }
                .onReceive(pushes.$pendingAlertID) { id in
                    if let id { appState.pendingAlertID = id; pushes.pendingAlertID = nil }
                }
        }
    }
}
