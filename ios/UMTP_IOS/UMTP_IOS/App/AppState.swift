import Combine
import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var userId: String?

    init(userId: String? = nil) {
        self.userId = userId
    }

    var isLoggedIn: Bool {
        guard let userId else { return false }
        return !userId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}
