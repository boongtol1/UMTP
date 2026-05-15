import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published private(set) var appVersion: String = "Stage 1"

    // TODO(Stage2): 서버 연동
    func refresh() {
        appVersion = "Stage 1"
    }
}
