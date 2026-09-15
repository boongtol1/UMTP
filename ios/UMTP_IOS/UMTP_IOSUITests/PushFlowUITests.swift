import XCTest

/// Real Simulator notification presentation/tap routing with a loopback fixture.
/// This verifies UNUserNotificationCenter handling, not APNs/FCM delivery.
@MainActor
final class PushFlowUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!
    private let pushTitle = "UMTP 검증 알림"
    private enum PushTestError: Error { case unsafeColdLaunchConfiguration }

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

        let app = launchFixtureApp(userID: "parity-fixture-user")
        ensureNotificationPermission(in: app, evidence: "Warm/background")

        // Background the application so the operating system presents a notification.
        XCUIDevice.shared.press(.home)
        try await injectNotificationAndVerifyUnreadDetail(in: app, evidence: "Warm/background")
    }

    func testColdStartSimulatorNotificationTapRoutesToUnreadAlertDetail() async throws {
        continueAfterFailure = false
        // This check happens before any app launch/termination. A SpringBoard cold
        // launch has no XCTest environment, so the installed build must be local-only.
        try await requireColdLaunchFixtureBuild()
        _ = try await fixture("__reset", method: "POST")

        let app = launchFixtureApp(userID: "")
        let userID = app.textFields["registration.userId"]
        XCTAssertTrue(userID.waitForExistence(timeout: 10))
        userID.tap()
        userID.typeText("parity-fixture-user")
        app.buttons["registration.submit"].tap()
        XCTAssertTrue(app.tabBars.buttons["설정"].waitForExistence(timeout: 10))
        let registration = try await fixture("__events")
        let registrationEvents = registration["events"] as? [[String: Any]] ?? []
        XCTAssertTrue(registrationEvents.contains {
            ($0["method"] as? String) == "POST" && ($0["path"] as? String) == "/users/register"
                && (($0["body"] as? [String: Any])?["user_id"] as? String) == "parity-fixture-user"
        }, "The cold launch must restore an actual persisted fixture registration, not a launch argument.")
        ensureNotificationPermission(in: app, evidence: "Cold start")

        app.terminate()
        XCTAssertTrue(app.wait(for: .notRunning, timeout: 5), "The process must stop before push injection.")
        attach(XCUIApplication(bundleIdentifier: "com.apple.springboard"), name: "Cold start 앱 종료 확인")
        // Do not call launch()/activate() again: only the OS notification tap may launch it.
        try await injectNotificationAndVerifyUnreadDetail(in: app, evidence: "Cold start")
    }

    private func requireColdLaunchFixtureBuild() async throws {
        let status = try await fixture("__cold-launch-status")
        if status["ready"] as? Bool != true, status["reason"] as? String == "fixture_build_required" {
            throw XCTSkip("Cold push requires an installed Debug Simulator fixture build. Run xcodebuild test -project ios/UMTP_IOS/UMTP_IOS.xcodeproj -scheme UMTP_IOS -configuration Debug -destination 'platform=iOS Simulator,id=<dedicated UUID>' -derivedDataPath <separate cold-build directory> UMTP_PARITY_FIXTURE_URL=http://127.0.0.1:18765 -only-testing:UMTP_IOSUITests/PushFlowUITests/testColdStartSimulatorNotificationTapRoutesToUnreadAlertDetail, with UMTP_SIMULATOR_ID set on the running loopback fixture.")
        }
        let safetyFlags = ["ready", "simulator_configured", "app_installed", "bundle_identifier_matches",
                           "simulator_platform_matches", "fixture_url_matches", "debug_build_matches"]
        guard safetyFlags.allSatisfy({ status[$0] as? Bool == true }) else {
            XCTFail("Cold launch preflight failed; the app was not launched or terminated. Verify the dedicated Simulator and restart the current loopback fixture.")
            throw PushTestError.unsafeColdLaunchConfiguration
        }
    }

    private func launchFixtureApp(userID: String) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", userID]
        app.launch()
        return app
    }

    private func ensureNotificationPermission(in app: XCUIApplication, evidence: String) {
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
        attach(app, name: "\(evidence) Simulator 알림 권한 허용")
    }

    private func injectNotificationAndVerifyUnreadDetail(in app: XCUIApplication, evidence: String) async throws {
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
        attach(springboard, name: "\(evidence) simctl 주입 알림")
        notification.tap()

        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        XCTAssertTrue(app.navigationBars["거래 알림 상세"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["검증용 맥북 에어 M1"].firstMatch.exists)
        attach(app, name: "\(evidence) 알림 클릭 후 alert 101 상세")

        let result = try await fixture("__events")
        let events = result["events"] as? [[String: Any]] ?? []
        XCTAssertTrue(events.contains { ($0["path"] as? String) == "/__simulate-push" })
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/101/read" },
                       "Opening a notification must not mark it reviewed.")
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read-all" })
        if let injectedAt = events.lastIndex(where: { ($0["path"] as? String) == "/__simulate-push" }) {
            XCTAssertTrue(events.dropFirst(injectedAt + 1).contains {
                ($0["method"] as? String) == "GET" && ($0["path"] as? String) == "/alerts"
                    && (($0["query"] as? [String: [String]])?["user_id"] == ["parity-fixture-user"])
            },
                          "Returning from a notification refreshes the feed before showing its detail.")
        }
    }

    private func attach(_ application: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: application.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func fixture(_ path: String, method: String = "GET") async throws -> [String: Any] {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = ["__simulate-push", "__cold-launch-status"].contains(path) ? 20 : 3
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    }
}
