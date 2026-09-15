import XCTest

/// Registration/session persistence against the loopback service, never a live account.
@MainActor
final class AuthenticationFlowUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!

    func testRegistrationRetryRelaunchAndLogoutPreserveDeviceIdentity() async throws {
        continueAfterFailure = false
        do { _ = try await fixture("__reset", method: "POST") }
        catch { throw XCTSkip("Start TestsSupport/parity_server.py before running fixture UI tests.") }
        _ = try await fixture("__fail", method: "POST", body: ["enabled": true])
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", " "]
        app.launch()
        let input = app.textFields["registration.userId"]
        XCTAssertTrue(input.waitForExistence(timeout: 10))
        input.tap()
        input.typeText("parity-fixture-user")
        let submit = app.buttons["registration.submit"]
        submit.tap()
        _ = try await waitForRegistrations(1)
        let retryable = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true"), object: submit)
        await fulfillment(of: [retryable], timeout: 10)
        XCTAssertTrue(input.exists, "Failed registration must not enter the app")
        XCTAssertEqual(input.value as? String, "parity-fixture-user")

        _ = try await fixture("__fail", method: "POST", body: ["enabled": false])
        submit.tap()
        XCTAssertTrue(app.tabBars.buttons["설정"].waitForExistence(timeout: 10))
        let requests = try await waitForRegistrations(2)
        let first = try XCTUnwrap(requests.first?["body"] as? [String: Any])
        XCTAssertEqual(first["platform"] as? String, "ios")
        let deviceID = try XCTUnwrap(first["device_id"] as? String)
        XCTAssertFalse(deviceID.isEmpty)

        app.terminate()
        app.launchArguments = []
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["설정"].waitForExistence(timeout: 10), "Saved session must survive relaunch")
        let afterRelaunch = try await registrations()
        XCTAssertEqual(afterRelaunch.count, 2, "Relaunch must not register a second account")
        app.tabBars.buttons["설정"].tap()
        let logout = app.buttons["로그아웃"]
        for _ in 0..<5 {
            if logout.exists && logout.isHittable { break }
            app.swipeUp()
        }
        logout.tap()
        XCTAssertTrue(input.waitForExistence(timeout: 10))
        input.tap()
        input.typeText("parity-fixture-user")
        submit.tap()
        XCTAssertTrue(app.tabBars.buttons["알림"].waitForExistence(timeout: 10))
        let finalRequests = try await waitForRegistrations(3)
        for request in finalRequests {
            let body = try XCTUnwrap(request["body"] as? [String: Any])
            XCTAssertEqual(body["device_id"] as? String, deviceID)
            XCTAssertEqual(body["user_id"] as? String, "parity-fixture-user")
        }
    }

    private func registrations() async throws -> [[String: Any]] {
        let events = try await fixture("__events")["events"] as? [[String: Any]] ?? []
        return events.filter { ($0["path"] as? String) == "/users/register" }
    }

    private func waitForRegistrations(_ count: Int) async throws -> [[String: Any]] {
        for _ in 0..<30 {
            let events = try await registrations()
            if events.count >= count { return events }
            try await Task.sleep(for: .milliseconds(200))
        }
        throw URLError(.timedOut)
    }

    private func fixture(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> [String: Any] {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = 3
        if let body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    }
}
