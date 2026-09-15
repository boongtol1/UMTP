import Combine
import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var userId: String?
    @Published var isLoadingSession: Bool = false
    @Published var pendingAlertID: Int?

    private let sessionService: UserSessionService

    init(sessionService: UserSessionService? = nil, userId: String? = nil) {
        self.sessionService = sessionService ?? .shared
        self.userId = userId
    }

    var isLoggedIn: Bool {
        guard let userId else { return false }
        return !userId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func restoreSession() {
        isLoadingSession = true
        defer { isLoadingSession = false }
        userId = sessionService.loadUserId()
        if userId != nil { _ = DeviceIdentity().resolve() }
    }

    func completeLogin(userId: String) {
        sessionService.saveUserId(userId)
        self.userId = userId
    }

    func logout() {
        PushService.shared.signOut()
        sessionService.clearUserId()
        userId = nil
        pendingAlertID = nil
    }
}
