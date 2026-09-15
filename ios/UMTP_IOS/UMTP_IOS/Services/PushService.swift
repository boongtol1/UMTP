import Combine
import FirebaseCore
import FirebaseMessaging
import UIKit
import UserNotifications

enum PushRoute {
    static func alertID(from payload: [AnyHashable: Any]) -> Int? {
        let value: Int?
        if let text = payload["alert_id"] as? String { value = Int(text) }
        else if let number = payload["alert_id"] as? NSNumber,
                CFGetTypeID(number) != CFBooleanGetTypeID() { value = Int(number.stringValue) }
        else { value = nil }
        return value.flatMap { $0 > 0 ? $0 : nil }
    }
}

@MainActor
final class PushTokenRegistration {
    private let defaults: UserDefaults
    private let upload: (String, String) async throws -> Void
    private var pending: (user: String, token: String)?
    private var running = false
    private var generation = 0
    private(set) var lastError: String?

    init(defaults: UserDefaults = .standard, upload: ((String, String) async throws -> Void)? = nil) {
        self.defaults = defaults
        self.upload = upload ?? { user, token in
            let response: PushTokenResponse = try await APIClient.shared.send(
                path: "users/\(APIClient.pathComponent(user))/push-token",
                body: PushTokenRequest(token: token, platform: "ios"))
            guard response.ok else { throw APIClientError.invalidResponse }
        }
    }

    func register(user: String, token: String) async {
        guard !user.isEmpty, (20...1024).contains(token.count) else { return }
        pending = (user, token)
        guard !running else { return }
        running = true
        defer { running = false }
        while let next = pending {
            let version = generation
            pending = nil
            if defaults.string(forKey: "umtp_ios_push_registered_user") == next.user,
               defaults.string(forKey: "umtp_ios_push_registered_token") == next.token { continue }
            do {
                try await upload(next.user, next.token)
                guard generation == version else { continue }
                defaults.set(next.user, forKey: "umtp_ios_push_registered_user")
                defaults.set(next.token, forKey: "umtp_ios_push_registered_token")
                lastError = nil
            } catch {
                guard generation == version else { continue }
                lastError = "푸시 등록을 완료하지 못했어요. 앱에 다시 돌아오면 재시도합니다."
            }
        }
    }

    func clear() {
        generation += 1
        pending = nil
        lastError = nil
        defaults.removeObject(forKey: "umtp_ios_push_registered_user")
        defaults.removeObject(forKey: "umtp_ios_push_registered_token")
    }
    private struct PushTokenRequest: Encodable { let token: String; let platform: String }
    private struct PushTokenResponse: Decodable { let ok: Bool }
}

@MainActor
final class PushTokenFetchQueue {
    private var running = false
    private var requested = false

    func run(_ operation: () async -> Void) async {
        requested = true
        guard !running else { return }
        running = true
        defer { running = false }
        repeat {
            requested = false
            await operation()
        } while requested
    }
}

@MainActor
final class PushService: NSObject, ObservableObject {
    static let shared = PushService()
    @Published var pendingAlertID: Int?
    @Published private(set) var authorization: UNAuthorizationStatus = .notDetermined
    @Published private(set) var message: String?
    @Published private(set) var isConfigured = false
    private let registration = PushTokenRegistration()
    private var currentUser: String?
    private var token: String?
    private var requestingPermission = false
    private var sessionGeneration = 0
    private var deletingToken: Task<Void, Never>?
    private var deletionID: UUID?
    private let tokenFetchQueue = PushTokenFetchQueue()
    private var hasAPNSToken = false

    func configure() {
        UNUserNotificationCenter.current().delegate = self
        guard FirebaseApp.app() == nil,
              let path = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist"),
              let options = FirebaseOptions(contentsOfFile: path),
              options.bundleID == Bundle.main.bundleIdentifier else {
            isConfigured = FirebaseApp.app() != nil
            return
        }
        FirebaseApp.configure(options: options)
        Messaging.messaging().delegate = self
        isConfigured = true
    }

    func activate(user: String?) async {
        if currentUser != user { sessionGeneration += 1; currentUser = user }
        let generation = sessionGeneration
        if let deletingToken { await deletingToken.value }
        guard generation == sessionGeneration else { return }
        authorization = await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
        guard generation == sessionGeneration, currentUser == user else { return }
        guard user != nil, isConfigured else { return }
        if authorization == .notDetermined { await requestPermission() }
        guard generation == sessionGeneration, currentUser == user else { return }
        if [.authorized, .provisional, .ephemeral].contains(authorization) {
            Messaging.messaging().isAutoInitEnabled = true
            UIApplication.shared.registerForRemoteNotifications()
            if let token { await register(token) }
        }
    }

    func requestPermission() async {
        guard !requestingPermission else { return }
        requestingPermission = true
        let generation = sessionGeneration
        defer { requestingPermission = false }
        do {
            _ = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound])
            guard generation == sessionGeneration else { return }
            authorization = await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
            guard generation == sessionGeneration else { return }
            if isConfigured && currentUser != nil && authorization == .authorized {
                Messaging.messaging().isAutoInitEnabled = true
                UIApplication.shared.registerForRemoteNotifications()
            }
        } catch { message = "알림 권한을 확인하지 못했어요. 설정에서 다시 확인해 주세요." }
    }

    func receivedAPNSToken(_ deviceToken: Data) {
        guard isConfigured, currentUser != nil, deletingToken == nil else { return }
        // SwiftUI + disabled swizzling requires the explicit APNs → FCM mapping.
        Messaging.messaging().apnsToken = deviceToken
        hasAPNSToken = true
        Task { await fetchToken() }
    }

    private func fetchToken() async {
        await tokenFetchQueue.run { [weak self] in await self?.fetchCurrentToken() }
    }

    private func fetchCurrentToken() async {
        guard isConfigured, currentUser != nil, deletingToken == nil, hasAPNSToken else { return }
        let generation = sessionGeneration
        // Server currently stores FCM registration tokens, not Firebase installation IDs.
        let value: String? = await withCheckedContinuation { continuation in
            Messaging.messaging().token { value, _ in continuation.resume(returning: value) }
        }
        guard generation == sessionGeneration else { return }
        if let value { await register(value) }
        else { message = "푸시 연결을 완료하지 못했어요. 다음 실행 때 다시 시도합니다." }
    }

    func registrationFailed() { message = "푸시 연결을 완료하지 못했어요. 앱 내 알림을 확인해 주세요." }

    private func register(_ value: String) async {
        guard let user = currentUser else { return }
        let generation = sessionGeneration
        token = value
        await registration.register(user: user, token: value)
        guard generation == sessionGeneration, currentUser == user else { return }
        message = registration.lastError
    }

    func signOut() {
        sessionGeneration += 1
        currentUser = nil
        pendingAlertID = nil
        token = nil
        hasAPNSToken = false
        registration.clear()
        UIApplication.shared.unregisterForRemoteNotifications()
        if isConfigured {
            Messaging.messaging().isAutoInitEnabled = false
            let previousDeletion = deletingToken
            let id = UUID()
            deletionID = id
            deletingToken = Task {
                if let previousDeletion { await previousDeletion.value }
                await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
                    Messaging.messaging().deleteToken { _ in continuation.resume() }
                }
                if deletionID == id { deletingToken = nil; deletionID = nil }
            }
        }
    }

    func route(_ payload: [AnyHashable: Any]) {
        if let id = PushRoute.alertID(from: payload) { pendingAlertID = id }
    }
}

extension PushService: MessagingDelegate {
    nonisolated func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
        guard fcmToken != nil else { return }
        // Delegate callbacks may arrive after logout. Fetch in the current session
        // instead of uploading a callback value produced by an earlier session.
        Task { @MainActor in await fetchToken() }
    }
}

extension PushService: UNUserNotificationCenterDelegate {
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
        willPresent notification: UNNotification, withCompletionHandler completion: @escaping (UNNotificationPresentationOptions) -> Void) {
        Task { @MainActor in NotificationCenter.default.post(name: .umtpRemoteAlertsDidChange, object: nil) }
        completion([.banner, .list, .sound])
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse, withCompletionHandler completion: @escaping () -> Void) {
        let id = PushRoute.alertID(from: response.notification.request.content.userInfo)
        if response.actionIdentifier == UNNotificationDefaultActionIdentifier, let id {
            Task { @MainActor in pendingAlertID = id }
        }
        completion()
    }
}

extension Notification.Name {
    static let umtpRemoteAlertsDidChange = Notification.Name("umtp.remoteAlertsDidChange")
}

final class UMTPAppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        PushService.shared.configure()
        if let payload = launchOptions?[.remoteNotification] as? [AnyHashable: Any] { PushService.shared.route(payload) }
        return true
    }
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        PushService.shared.receivedAPNSToken(deviceToken)
    }
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        PushService.shared.registrationFailed()
    }
    func application(_ application: UIApplication, didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
        NotificationCenter.default.post(name: .umtpRemoteAlertsDidChange, object: nil)
        completionHandler(.noData)
    }
}
