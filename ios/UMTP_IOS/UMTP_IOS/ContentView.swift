import SwiftUI

struct ContentView: View {
    var body: some View {
        RootContentView()
    }
}

private struct RootContentView: View {
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

#Preview {
    ContentView()
        .environmentObject(AppState())
}
