import Foundation

@MainActor
final class UserSetupViewModel: ObservableObject {
    @Published var userIdInput = ""

    private let sessionService: UserSessionService

    init(sessionService: UserSessionService = .shared) {
        self.sessionService = sessionService
    }

    var canSave: Bool {
        !userIdInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func save(appState: AppState) {
        let trimmed = userIdInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        sessionService.saveUserId(trimmed)
        appState.userId = trimmed
    }
}
