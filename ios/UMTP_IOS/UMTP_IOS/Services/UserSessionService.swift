import Foundation

final class UserSessionService {
    static let shared = UserSessionService()

    private let userIdKey = "umtp_user_id"
    private let defaults = UserDefaults.standard

    private init() {}

    func saveUserId(_ userId: String) {
        let trimmed = userId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        defaults.set(trimmed, forKey: userIdKey)
    }

    func loadUserId() -> String? {
        let stored = defaults.string(forKey: userIdKey)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard let stored, !stored.isEmpty else { return nil }
        return stored
    }

    func clearUserId() {
        defaults.removeObject(forKey: userIdKey)
    }

    // TODO(Stage2): Keychain 기반 사용자 세션 저장소로 확장
}
