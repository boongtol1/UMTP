import XCTest
@testable import UMTP_IOS

final class CoreURLProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var handler: ((URLRequest) throws -> (Int, Data))?
    nonisolated override class func canInit(with request: URLRequest) -> Bool { true }
    nonisolated override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    nonisolated override func startLoading() {
        do {
            let (status, data) = try Self.handler!(request)
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch { client?.urlProtocol(self, didFailWithError: error) }
    }
    nonisolated override func stopLoading() {}
}

@MainActor
final class CoreParityTests: XCTestCase {
    private struct Response: Decodable { let ok: Bool; let value: Int? }
    private func client() -> APIClient {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [CoreURLProtocol.self]
        return APIClient(baseURLString: "https://example.invalid/api/", session: URLSession(configuration: config))
    }

    func testQueryAndIdentifierAreEncodedWithoutChangingEndpoint() async throws {
        CoreURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/api/alerts")
            XCTAssertEqual(URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems?.first?.value, "한글/a?x=1&b=2")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "application/json")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            return (200, Data(#"{"ok":true,"value":5}"#.utf8))
        }
        let result: Response = try await client().get(path: "alerts", query: [.init(name: "user_id", value: "한글/a?x=1&b=2")])
        XCTAssertEqual(result.value, 5)
        CoreURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.absoluteString, "https://example.invalid/api/users/a%2Fb%3Fx%23y/rules/refresh")
            XCTAssertEqual(request.httpMethod, "POST")
            return (200, Data(#"{"ok":true}"#.utf8))
        }
        let _: Response = try await client().send(path: "users/\(APIClient.pathComponent("a/b?x#y"))/rules/refresh", method: "POST")
    }

    func testHTTP200FailureNeverBecomesSuccessOrLeaksReason() async throws {
        CoreURLProtocol.handler = { _ in (200, Data(#"{"ok":false,"reason":"token=secret https://internal.invalid /private/server.py"}"#.utf8)) }
        do {
            let _: Response = try await client().get(path: "alerts")
            XCTFail("Domain failure must throw")
        } catch {
            XCTAssertFalse(error.localizedDescription.contains("secret"))
            XCTAssertFalse(error.localizedDescription.contains("internal"))
        }
    }

    func testHTTPFailureAndMalformedJSONAndTimeout() async {
        for (status, data) in [(422, Data()), (200, Data("not json".utf8))] {
            CoreURLProtocol.handler = { _ in (status, data) }
            do { let _: Response = try await client().get(path: "alerts"); XCTFail("Expected failure") }
            catch { XCTAssertTrue(error is APIClientError) }
        }
        CoreURLProtocol.handler = { _ in throw URLError(.timedOut) }
        do { let _: Response = try await client().get(path: "alerts"); XCTFail("Expected timeout") }
        catch { XCTAssertTrue(error.localizedDescription.contains("초과")) }
    }

    func testLegacyUserDefaultsAndLogoutPreserveDeviceAndOtherSettings() {
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        defaults.set(" old-user ", forKey: "umtp_user_id")
        defaults.set("legacy-device", forKey: "umtp_ios_fallback_device_id")
        defaults.set(5, forKey: "other-setting")
        let session = UserSessionService(defaults: defaults)
        let app = AppState(sessionService: session)
        app.restoreSession()
        XCTAssertEqual(app.userId, "old-user")
        app.logout()
        XCTAssertNil(session.loadUserId())
        XCTAssertEqual(defaults.string(forKey: "umtp_ios_fallback_device_id"), "legacy-device")
        XCTAssertEqual(defaults.integer(forKey: "other-setting"), 5)
        app.completeLogin(userId: " old-user ")
        XCTAssertEqual(session.loadUserId(), "old-user")
    }

    func testIdentityUpgradePinsPreviousIDFVAndSurvivesIDFVChange() {
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        var secured: String?
        defaults.set("legacy-fallback", forKey: "umtp_ios_fallback_device_id")
        let identity = DeviceIdentity(defaults: defaults, vendorID: { "existing-idfv" }, readKeychain: { secured }, writeKeychain: { secured = $0 })
        XCTAssertEqual(identity.resolve(), "existing-idfv")
        let next = DeviceIdentity(defaults: defaults, vendorID: { "new-idfv" }, readKeychain: { secured }, writeKeychain: { secured = $0 })
        XCTAssertEqual(next.resolve(), "existing-idfv")
        XCTAssertEqual(secured, "existing-idfv")
    }

    func testFallbackMigrationAndKeychainRestore() {
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        defaults.set("legacy-fallback", forKey: "umtp_ios_fallback_device_id")
        XCTAssertEqual(DeviceIdentity(defaults: defaults, vendorID: { nil }, readKeychain: { nil }, writeKeychain: { _ in }).resolve(), "legacy-fallback")
        let cleanDefaults = UserDefaults(suiteName: UUID().uuidString)!
        XCTAssertEqual(DeviceIdentity(defaults: cleanDefaults, vendorID: { "new" }, readKeychain: { "secured" }, writeKeychain: { _ in }).resolve(), "secured")
    }

    func testRegistrationFailureDoesNotSaveSession() async {
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        let session = UserSessionService(defaults: defaults)
        let app = AppState(sessionService: session)
        let mock = RegistrationMock()
        let model = UserSetupViewModel(sessionService: session, userAPI: mock)
        model.userIdInput = "test-user"
        mock.failure = true
        await model.register(appState: app)
        XCTAssertNil(session.loadUserId())
        XCTAssertFalse(app.isLoggedIn)
        XCTAssertFalse(model.isSubmitting)
        XCTAssertNotNil(model.errorMessage)
        mock.failure = false
        await model.register(appState: app)
        XCTAssertEqual(session.loadUserId(), "test-user")
        XCTAssertTrue(app.isLoggedIn)
        model.userIdInput = String(repeating: "a", count: 101)
        XCTAssertFalse(model.canSubmit)
    }
}

@MainActor
private final class RegistrationMock: UserAPIProtocol {
    var failure = false
    func register(userId: String) async throws -> RegisterUserResult {
        if failure { throw UserAPIError.identityMismatch }
        return RegisterUserResult(userId: userId)
    }
}
