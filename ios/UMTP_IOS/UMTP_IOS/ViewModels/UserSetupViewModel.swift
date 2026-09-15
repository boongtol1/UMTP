import Combine
import Foundation

@MainActor
final class UserSetupViewModel: ObservableObject {
    @Published var userIdInput = ""
    @Published private(set) var isSubmitting = false
    @Published var errorMessage: String?

    private let sessionService: UserSessionService
    private let userAPI: UserAPIProtocol

    init(
        sessionService: UserSessionService,
        userAPI: UserAPIProtocol? = nil
    ) {
        self.sessionService = sessionService
        self.userAPI = userAPI ?? UserAPI.shared
    }

    var canSubmit: Bool {
        (2...100).contains(userIdInput.trimmingCharacters(in: .whitespacesAndNewlines).count) && !isSubmitting
    }

    func register(appState: AppState) async {
        if isSubmitting {
            return
        }

        let trimmed = userIdInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard (2...100).contains(trimmed.count) else {
            errorMessage = UserAPIError.invalidInput.userMessage
            return
        }

        isSubmitting = true
        defer { isSubmitting = false }
        errorMessage = nil

        do {
            let result = try await userAPI.register(userId: trimmed)
            sessionService.saveUserId(result.userId)
            appState.completeLogin(userId: result.userId)
        } catch is CancellationError {
            return
        } catch let error as UserAPIError {
            errorMessage = error.userMessage
        } catch {
            errorMessage = UserAPIError.unknown.userMessage
        }

    }
}
