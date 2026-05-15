import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            AlertFeedView()
                .tabItem {
                    Label("알림", systemImage: "bell")
                }

            SettingsView()
                .tabItem {
                    Label("설정", systemImage: "gearshape")
                }
        }
    }
}
