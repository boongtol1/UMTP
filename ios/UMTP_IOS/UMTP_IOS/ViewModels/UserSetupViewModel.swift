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
        userAPI: UserAPIProtocol = UserAPI.shared
    ) {
        self.sessionService = sessionService
        self.userAPI = userAPI
    }

    var canSubmit: Bool {
        userIdInput.trimmingCharacters(in: .whitespacesAndNewlines).count >= 2 && !isSubmitting
    }

    func register(appState: AppState) async {
        if isSubmitting {
            return
        }

        let trimmed = userIdInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else {
            errorMessage = "사용자 ID는 2자 이상 입력해 주세요."
            return
        }

        isSubmitting = true
        errorMessage = nil

        do {
            let result = try await userAPI.register(userId: trimmed)
            sessionService.saveUserId(result.userId)
            appState.completeLogin(userId: result.userId)
        } catch let error as UserAPIError {
            errorMessage = error.userMessage
        } catch {
            errorMessage = UserAPIError.unknown.userMessage
        }

        isSubmitting = false
    }
}
