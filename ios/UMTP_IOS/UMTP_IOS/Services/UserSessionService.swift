import Foundation

final class UserSessionService {
    static let shared = UserSessionService()

    private let userIdKey = "umtp_user_id"
    private let defaults = UserDefaults.standard

    private init() {}

    func saveUserId(_ userId: String) {
        defaults.set(userId, forKey: userIdKey)
    }

    func loadUserId() -> String? {
        defaults.string(forKey: userIdKey)
    }

    func clearUserId() {
        defaults.removeObject(forKey: userIdKey)
    }
}
