import XCTest

/// Changes only UMTP's notification permission on the dedicated test Simulator.
/// Restores permission to enabled so subsequent notification presentation tests can run.
@MainActor
final class NotificationPermissionUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!
    private let deniedMessage = "알림이 꺼져 있어요. iOS 설정에서 알림을 허용할 수 있어요."
    private var needsPermissionRestore = false

    func testSystemNotificationPermissionChangesRefreshOnAppReturn() async throws {
        continueAfterFailure = false
        var reset = URLRequest(url: baseURL.appendingPathComponent("__reset"))
        reset.httpMethod = "POST"
        reset.timeoutInterval = 3
        let (_, response) = try await URLSession.shared.data(for: reset)
        XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200,
                       "Start the loopback fixture on 127.0.0.1:18765 before this test.")

        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user"]
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["설정"].waitForExistence(timeout: 10))
        app.tabBars.buttons["설정"].tap()
        revealPermissionSection(in: app)

        let authorized = app.staticTexts["알림 허용됨"]
        let denied = app.staticTexts[deniedMessage]
        let allow = app.buttons["알림 허용"]
        if allow.exists {
            allow.tap()
            let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
            let dialog = springboard.alerts.firstMatch
            XCTAssertTrue(dialog.waitForExistence(timeout: 5))
            let accept = dialog.buttons.matching(
                NSPredicate(format: "label == %@ OR label == %@", "Allow", "허용")).firstMatch
            XCTAssertTrue(accept.waitForExistence(timeout: 3))
            accept.tap()
        }

        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        if denied.exists {
            let permission = try openNotificationSettings(from: app, settings: settings)
            try setPermission(true, using: permission)
            app.activate()
            XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        }
        XCTAssertTrue(authorized.waitForExistence(timeout: 10))
        XCTAssertFalse(denied.exists)
        attachScreenshot(app, name: "시스템 변경 전 알림 허용")

        addTeardownBlock { [self, app, settings] in
            try await restorePermissionIfNeeded(in: app, settings: settings)
        }

        let permission = try openNotificationSettings(from: app, settings: settings)
        XCTAssertEqual(permission.value as? String, "1")
        needsPermissionRestore = true
        try setPermission(false, using: permission)
        attachScreenshot(settings, name: "UMTP iOS 알림 허용 OFF")

        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        XCTAssertTrue(denied.waitForExistence(timeout: 10),
                      "Returning from iOS Settings must refresh the denied permission state.")
        XCTAssertFalse(authorized.exists)
        attachScreenshot(app, name: "앱 복귀 후 알림 꺼짐 안내")

        let disabledPermission = try openNotificationSettings(from: app, settings: settings)
        XCTAssertEqual(disabledPermission.value as? String, "0")
        try setPermission(true, using: disabledPermission)
        attachScreenshot(settings, name: "UMTP iOS 알림 허용 ON 복원")

        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        XCTAssertTrue(authorized.waitForExistence(timeout: 10),
                      "Returning from iOS Settings must refresh the authorized permission state.")
        XCTAssertFalse(denied.exists)
        XCTAssertTrue(app.buttons["iOS 알림 설정 열기"].exists)
        attachScreenshot(app, name: "앱 복귀 후 알림 허용 복원")
        needsPermissionRestore = false
    }

    private func revealPermissionSection(in app: XCUIApplication) {
        for _ in 0..<5 {
            if app.buttons["알림 허용"].isHittable
                || app.staticTexts["알림 허용됨"].isHittable
                || app.staticTexts[deniedMessage].isHittable { return }
            app.swipeUp()
        }
        XCTFail("The notification permission section must be visible in the app's Settings tab.")
    }

    private func openNotificationSettings(from app: XCUIApplication,
                                          settings: XCUIApplication) throws -> XCUIElement {
        let open = app.buttons["iOS 알림 설정 열기"]
        XCTAssertTrue(open.waitForExistence(timeout: 5))
        for _ in 0..<3 {
            if open.isHittable { break }
            app.swipeUp()
        }
        let guidance = app.staticTexts["notification.settings.guidance"]
        for _ in 0..<3 {
            if guidance.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(guidance.isHittable && guidance.label.contains("iOS 설정 → 알림 → UMTP_IOS")
                      && guidance.label.contains("iOS 설정 → 앱 → UMTP_IOS → 알림"),
                      "The app must show both supported manual Settings paths before opening system Settings.")
        XCTAssertTrue(open.isHittable)
        open.tap()
        XCTAssertTrue(settings.wait(for: .runningForeground, timeout: 10),
                      "The app's notification settings link must open iOS Settings.")
        return try notificationPermissionSwitch(in: settings)
    }

    private func notificationPermissionSwitch(in settings: XCUIApplication) throws -> XCUIElement {
        // Accept the exact app page or its Notifications child. The child's
        // navigation-bar BackButton identifies UMTP_IOS as the parent; a
        // status-bar return-to-app breadcrumb is not evidence of page identity.
        if !waitForUMTPSettingsPage(in: settings, timeout: 3) {
            try navigateFromSettingsRoot(in: settings)
        }
        guard waitForUMTPSettingsPage(in: settings, timeout: 5) else {
            attachScreenshot(settings, name: "알림 설정 앱 식별 실패")
            XCTFail("Expected UMTP_IOS notification settings; no system switch was changed.")
            throw PermissionUIError.unexpectedSettingsPage
        }

        // Inspect the whole exact app page before concluding this Simulator
        // exposes no notification controls. Navigation failures are not skips.
        guard scrollSettingsToTop(in: settings) else {
            XCTFail("Could not establish the top of UMTP_IOS's settings page.")
            throw PermissionUIError.unexpectedSettingsPage
        }
        if !permissionSwitches(in: settings).firstMatch.waitForExistence(timeout: 3) {
            attachScreenshot(settings, name: "UMTP_IOS 앱 설정 전체 확인 시작")
            let scan = scanSettingsRows(named: ["Notifications", "알림"], in: settings)
            if let notifications = scan.row {
                recordSettingsRoute("Settings displayed UMTP_IOS's app settings. The test selected Notifications; direct notification-page deep linking was not verified.")
                notifications.tap()
            } else {
                attachScreenshot(settings, name: "UMTP_IOS 앱 설정: 알림 행과 스위치 없음")
                let evidence = XCTAttachment(string: settings.debugDescription)
                evidence.name = "Exact UMTP_IOS Settings page without notification controls"
                evidence.lifetime = .keepAlways
                add(evidence)
                guard scan.reachedEnd, settings.navigationBars["UMTP_IOS"].exists,
                      permissionSwitches(in: settings).count == 0, !needsPermissionRestore else {
                    XCTFail("The app notification controls could not be fully inspected or restored.")
                    throw PermissionUIError.unexpectedPermissionSwitch
                }
                throw XCTSkip("This Simulator's exact UMTP_IOS Settings page exposes neither a Notifications row nor an Allow Notifications switch after full-page inspection. The attached screenshots/AX tree document the OS control limitation; permission toggling and direct per-app deep linking remain unverified.")
            }
        }
        guard waitForUMTPSettingsPage(in: settings, timeout: 5) else {
            attachScreenshot(settings, name: "앱 알림 페이지 이동 후 식별 실패")
            XCTFail("The notification switch must belong to the UMTP_IOS settings page.")
            throw PermissionUIError.unexpectedSettingsPage
        }
        if !settings.navigationBars["UMTP_IOS"].exists {
            recordSettingsRoute("Verified the Notifications child page by its exact Notifications/알림 navigation-bar title and that bar's BackButton labeled UMTP_IOS. This is the app-settings parent relationship, not the status-bar return-to-app link.")
            attachScreenshot(settings, name: "UMTP_IOS의 알림 하위 설정 확인")
        }
        let matches = permissionSwitches(in: settings)
        guard matches.firstMatch.waitForExistence(timeout: 5), matches.count == 1,
              matches.firstMatch.isHittable else {
            attachScreenshot(settings, name: "정확한 알림 허용 스위치 식별 실패")
            XCTFail("Expected exactly one visible Allow Notifications / 알림 허용 switch on UMTP_IOS's page.")
            throw PermissionUIError.unexpectedPermissionSwitch
        }
        return matches.firstMatch
    }

    private func waitForUMTPSettingsPage(in settings: XCUIApplication, timeout: TimeInterval) -> Bool {
        let page = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            if settings.navigationBars["UMTP_IOS"].exists { return true }
            let titles = ["Notifications", "알림"] as NSArray
            let notifications = settings.navigationBars.matching(NSPredicate(
                format: "identifier IN %@ OR label IN %@", titles, titles)).firstMatch
            guard notifications.exists else { return false }
            let parent = notifications.buttons.matching(NSPredicate(
                format: "identifier == %@ AND label == %@", "BackButton", "UMTP_IOS"))
            return parent.count == 1 && parent.firstMatch.isHittable
        }, object: nil)
        return XCTWaiter.wait(for: [page], timeout: timeout) == .completed
    }

    private func navigateFromSettingsRoot(in settings: XCUIApplication) throws {
        let root = settings.navigationBars.matching(NSPredicate(
            format: "identifier IN %@ OR label IN %@", ["Settings", "설정"] as NSArray,
            ["Settings", "설정"] as NSArray)).firstMatch
        guard root.waitForExistence(timeout: 3) else {
            attachScreenshot(settings, name: "알림 설정 링크의 예상하지 못한 도착 화면")
            XCTFail("The settings link reached neither UMTP_IOS nor Settings root; no switch was changed.")
            throw PermissionUIError.unexpectedSettingsPage
        }
        attachScreenshot(settings, name: "공식 알림 설정 링크가 Settings 루트를 엶")
        recordSettingsRoute("UIApplication.openNotificationSettingsURLString opened Settings root on this Simulator. The test must manually select Notifications or Apps, then UMTP_IOS. Direct per-app deep linking was not verified.")
        let category = try findSettingsRow(named: ["Notifications", "알림", "Apps", "앱"], in: settings)
        category.tap()
        let categories = ["Notifications", "알림", "Apps", "앱"] as NSArray
        let categoryPage = settings.navigationBars.matching(NSPredicate(
            format: "identifier IN %@ OR label IN %@", categories, categories)).firstMatch
        guard categoryPage.waitForExistence(timeout: 5) else {
            attachScreenshot(settings, name: "Settings 앱 또는 알림 목록 이동 실패")
            XCTFail("Manual navigation must reach the system Apps or Notifications list before choosing an app.")
            throw PermissionUIError.unexpectedSettingsPage
        }
        recordSettingsRoute("Manual system navigation reached \(categoryPage.identifier.isEmpty ? categoryPage.label : categoryPage.identifier). The next action selects the exact UMTP_IOS app row.")
        let appRow = try findSettingsRow(named: ["UMTP_IOS"], in: settings)
        appRow.tap()
    }

    private func findSettingsRow(named names: [String], in settings: XCUIApplication) throws -> XCUIElement {
        if let row = scanSettingsRows(named: names, in: settings).row { return row }
        attachScreenshot(settings, name: "Settings 목록에서 정확한 대상 찾기 실패: \(names.joined(separator: "/"))")
        XCTFail("Could not find the exact Settings row \(names); no system switch was changed.")
        throw PermissionUIError.unexpectedSettingsPage
    }

    private func scanSettingsRows(named names: [String], in settings: XCUIApplication) -> (row: XCUIElement?, reachedEnd: Bool) {
        for _ in 0..<15 {
            for name in names {
                let row = settings.cells.containing(.staticText, identifier: name).firstMatch
                if row.exists && row.isHittable { return (row, false) }
                let labeledRow = settings.cells.matching(NSPredicate(format: "label == %@", name)).firstMatch
                if labeledRow.exists && labeledRow.isHittable { return (labeledRow, false) }
                // Restrict fallback labels to scrolling page content, excluding
                // status-bar return-to-app links and navigation-bar buttons.
                for container in [settings.tables.firstMatch, settings.collectionViews.firstMatch, settings.scrollViews.firstMatch] {
                    guard container.exists else { continue }
                    let text = container.staticTexts[name].firstMatch
                    if text.exists && text.isHittable { return (text, false) }
                    let button = container.buttons[name].firstMatch
                    if button.exists && button.isHittable { return (button, false) }
                }
            }
            let before = settingsContentSignature(in: settings)
            settings.swipeUp()
            let after = settingsContentSignature(in: settings)
            if !before.isEmpty && before == after { return (nil, true) }
        }
        return (nil, false)
    }

    private func scrollSettingsToTop(in settings: XCUIApplication) -> Bool {
        for _ in 0..<15 {
            let before = settingsContentSignature(in: settings)
            settings.swipeDown()
            let after = settingsContentSignature(in: settings)
            if !before.isEmpty && before == after { return true }
        }
        return false
    }

    private func settingsContentSignature(in settings: XCUIApplication) -> [String] {
        let cells = settings.cells.allElementsBoundByIndex.filter(\.isHittable)
        if !cells.isEmpty { return cells.map { "\($0.identifier)|\($0.label)|\($0.frame)" } }
        for container in [settings.tables.firstMatch, settings.collectionViews.firstMatch, settings.scrollViews.firstMatch] {
            guard container.exists else { continue }
            let text = container.staticTexts.allElementsBoundByIndex.filter(\.isHittable)
            if !text.isEmpty { return text.map { "\($0.label)|\($0.frame)" } }
        }
        return []
    }

    private func permissionSwitches(in settings: XCUIApplication) -> XCUIElementQuery {
        settings.switches.matching(NSPredicate(
            format: "label == %@ OR label == %@", "Allow Notifications", "알림 허용"))
    }

    private func recordSettingsRoute(_ description: String) {
        let attachment = XCTAttachment(string: description)
        attachment.name = "Observed notification Settings navigation"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func setPermission(_ enabled: Bool, using permission: XCUIElement) throws {
        guard permission.identifier == "ALLOW_NOTIFICATIONS_ID",
              ["Allow Notifications", "알림 허용"].contains(permission.label),
              permission.isHittable,
              let current = permission.value as? String, ["0", "1"].contains(current) else {
            XCTFail("The exact visible notification permission switch must expose an explicit 0/1 state.")
            throw PermissionUIError.unexpectedPermissionSwitch
        }
        let expected = enabled ? "1" : "0"
        if current != expected {
            // Settings exposes ALLOW_NOTIFICATIONS_ID as a 330-point labeled
            // row; its visual toggle occupies the trailing 63 points. A center
            // tap hits the empty label area. Stay inside this exact identified
            // row and tap the visible toggle, as verified in the Simulator AX tree.
            permission.coordinate(withNormalizedOffset: CGVector(dx: 0.9, dy: 0.5)).tap()
        }
        let changed = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", expected), object: permission)
        guard XCTWaiter.wait(for: [changed], timeout: 5) == .completed else {
            XCTFail("The UMTP notification permission switch must reach state \(expected) before returning to the app.")
            throw PermissionUIError.unexpectedPermissionSwitch
        }
    }

    private func restorePermissionIfNeeded(in app: XCUIApplication,
                                           settings: XCUIApplication) throws {
        guard needsPermissionRestore else { return }
        settings.activate()
        XCTAssertTrue(settings.wait(for: .runningForeground, timeout: 10))
        let permission = try notificationPermissionSwitch(in: settings)
        try setPermission(true, using: permission)
        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        XCTAssertTrue(app.staticTexts["알림 허용됨"].waitForExistence(timeout: 10))
        needsPermissionRestore = false
    }

    private func attachScreenshot(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private enum PermissionUIError: Error {
        case unexpectedSettingsPage
        case unexpectedPermissionSwitch
    }
}
