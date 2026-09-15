import XCTest

/// Real Simulator notification presentation/tap routing with a loopback fixture.
/// This verifies UNUserNotificationCenter handling, not APNs/FCM delivery.
@MainActor
final class PushFlowUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!
    private let pushTitle = "UMTP 검증 알림"

    func testSimulatorNotificationPermissionTapRoutesToUnreadAlertDetail() async throws {
        continueAfterFailure = false
        do {
            _ = try await fixture("__reset", method: "POST")
            let status = try await fixture("__push-status")
            guard status["configured"] as? Bool == true else {
                throw XCTSkip("Start the loopback fixture with UMTP_SIMULATOR_ID set to this test Simulator UUID.")
            }
        } catch let skip as XCTSkip { throw skip }
        catch { throw XCTSkip("Loopback push fixture unavailable: start TestsSupport/parity_server.py on port 18765.") }

        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user"]
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["설정"].waitForExistence(timeout: 10))
        app.tabBars.buttons["설정"].tap()
        let allow = app.buttons["알림 허용"]
        let authorized = app.staticTexts["알림 허용됨"]
        for _ in 0..<5 {
            if allow.exists || authorized.exists { break }
            app.swipeUp()
        }
        if allow.exists {
            allow.tap()
            let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
            let dialog = springboard.alerts.firstMatch
            XCTAssertTrue(dialog.waitForExistence(timeout: 5))
            let accept = dialog.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "Allow", "허용")).firstMatch
            XCTAssertTrue(accept.waitForExistence(timeout: 3))
            accept.tap()
        }
        XCTAssertTrue(authorized.waitForExistence(timeout: 5),
                      "Notification permission must be enabled in the test Simulator.")
        let permission = XCTAttachment(screenshot: app.screenshot())
        permission.name = "Simulator 알림 권한 허용"
        permission.lifetime = .keepAlways
        add(permission)

        // Background the application so the operating system presents a notification.
        XCUIDevice.shared.press(.home)
        let injection = try await fixture("__simulate-push", method: "POST")
        XCTAssertEqual(injection["transport"] as? String, "simctl")
        XCTAssertEqual(injection["alert_id"] as? Int, 101)

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let notification = springboard.descendants(matching: .any)
            .matching(NSPredicate(format: "label CONTAINS %@", pushTitle)).firstMatch
        if !notification.waitForExistence(timeout: 4) {
            // The banner may already be in Notification Center on slower Simulator hosts.
            let top = springboard.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.01))
            let lower = springboard.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.75))
            top.press(forDuration: 0.05, thenDragTo: lower)
        }
        XCTAssertTrue(notification.waitForExistence(timeout: 5))
        let banner = XCTAttachment(screenshot: springboard.screenshot())
        banner.name = "simctl 주입 알림"
        banner.lifetime = .keepAlways
        add(banner)
        notification.tap()

        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        XCTAssertTrue(app.navigationBars["거래 알림 상세"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["검증용 맥북 에어 M1"].firstMatch.exists)
        let routed = XCTAttachment(screenshot: app.screenshot())
        routed.name = "알림 클릭 후 alert 101 상세"
        routed.lifetime = .keepAlways
        add(routed)

        let result = try await fixture("__events")
        let events = result["events"] as? [[String: Any]] ?? []
        XCTAssertTrue(events.contains { ($0["path"] as? String) == "/__simulate-push" })
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/101/read" },
                       "Opening a notification must not mark it reviewed.")
        if let injectedAt = events.lastIndex(where: { ($0["path"] as? String) == "/__simulate-push" }) {
            XCTAssertTrue(events.dropFirst(injectedAt + 1).contains { ($0["path"] as? String) == "/alerts" },
                          "Returning from a notification refreshes the feed before showing its detail.")
        }
    }

    private func fixture(_ path: String, method: String = "GET") async throws -> [String: Any] {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = path == "__simulate-push" ? 20 : 3
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    }
}
