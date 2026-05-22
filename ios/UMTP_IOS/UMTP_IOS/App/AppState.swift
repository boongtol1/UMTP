import Combine
import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var userId: String?
    @Published var isLoadingSession: Bool = false

    private let sessionService: UserSessionService

    init(sessionService: UserSessionService = .shared, userId: String? = nil) {
        self.sessionService = sessionService
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
    }

    func completeLogin(userId: String) {
        self.userId = userId
    }

    func logout() {
        sessionService.clearUserId()
        userId = nil
        // TODO(Stage2): 로그아웃 시 푸시 토큰 해제/서버 세션 정리 연동
    }
}
