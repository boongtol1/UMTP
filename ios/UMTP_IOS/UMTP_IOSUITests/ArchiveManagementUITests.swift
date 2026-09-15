import XCTest

/// Exercises visible selection/confirmation controls against loopback fixtures.
/// No production account, notification delivery, or service write is involved.
@MainActor
final class ArchiveManagementUITests: XCTestCase {
    func testSelectAllReadAndSelectedArchiveClearUseAlertEventIDs() async throws {
        let app = try await launchFixtureApp()
        chooseMenuAction("선택", menu: "알림 관리", in: app)
        let unreadCard = app.buttons["alert.card.101"].firstMatch
        assertSelection(false, of: unreadCard)
        chooseMenuAction("전체 선택", menu: "알림 관리", in: app)
        assertSelection(true, of: unreadCard)
        chooseMenuAction("선택 읽음 (1건)", menu: "알림 관리", in: app)
        XCTAssertTrue(app.staticTexts["알림이 없습니다."].waitForExistence(timeout: 10))

        var events = try await fixtureEvents()
        let reads = events.filter { ($0["path"] as? String) == "/alert-events/101/read" }
        XCTAssertEqual(reads.count, 1)
        XCTAssertEqual(reads.first?["method"] as? String, "PATCH")
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read-all" })

        app.tabBars.buttons["읽음 보관함"].tap()
        XCTAssertTrue(app.navigationBars["읽음 알림 보관함"].waitForExistence(timeout: 5))
        let archiveCard = app.buttons["alert.card.101"].firstMatch
        XCTAssertTrue(archiveCard.waitForExistence(timeout: 10))
        chooseMenuAction("선택", menu: "보관함 관리", in: app)
        assertSelection(false, of: archiveCard)
        archiveCard.tap()
        assertSelection(true, of: archiveCard)
        XCTAssertFalse(app.navigationBars["읽음 알림 상세"].exists,
                       "In selection mode a card tap must select it, not open details")
        chooseMenuAction("선택 비우기 (1건)", menu: "보관함 관리", in: app)
        let explanation = app.staticTexts["비운 알림은 보관함에서 숨겨져요. 거래 기록은 유지돼요."].firstMatch
        XCTAssertTrue(explanation.waitForExistence(timeout: 5))
        events = try await fixtureEvents()
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read/archive/clear-selected" },
                       "Choosing the menu action alone must not clear the archive")
        attachScreenshot(app, name: "선택한 읽음 알림 비우기 확인")
        confirm("선택 1건 비우기", in: app)
        XCTAssertTrue(app.staticTexts["읽음 처리된 알림이 없습니다."].waitForExistence(timeout: 10))
        XCTAssertFalse(archiveCard.exists)

        events = try await fixtureEvents()
        let clears = events.filter { ($0["path"] as? String) == "/alert-events/read/archive/clear-selected" }
        XCTAssertEqual(clears.count, 1)
        let clear = try XCTUnwrap(clears.first)
        XCTAssertEqual(clear["method"] as? String, "PATCH")
        let body = try XCTUnwrap(clear["body"] as? [String: Any])
        XCTAssertEqual(body["alert_event_ids"] as? [Int], [101],
                       "Archive clearing uses alert event IDs, not archive identity 1101")
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read/archive/clear-all" })
    }

    func testReadAllAndClearAllRequireExplicitConfirmation() async throws {
        let app = try await launchFixtureApp()
        chooseMenuAction("모두 읽음", menu: "알림 관리", in: app)
        XCTAssertTrue(app.staticTexts["읽음 처리한 알림은 읽음 보관함에서 다시 확인할 수 있어요."].firstMatch
            .waitForExistence(timeout: 5))
        var events = try await fixtureEvents()
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read-all" },
                       "Read-all must wait for confirmation")
        confirm("모두 읽음", in: app)
        XCTAssertTrue(app.staticTexts["알림이 없습니다."].waitForExistence(timeout: 10))
        events = try await fixtureEvents()
        let reads = events.filter { ($0["path"] as? String) == "/alert-events/read-all" }
        XCTAssertEqual(reads.count, 1)
        XCTAssertEqual(reads.first?["method"] as? String, "PATCH")
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/101/read" })

        app.tabBars.buttons["읽음 보관함"].tap()
        XCTAssertTrue(app.navigationBars["읽음 알림 보관함"].waitForExistence(timeout: 5))
        let archiveCard = app.buttons["alert.card.101"].firstMatch
        XCTAssertTrue(archiveCard.waitForExistence(timeout: 10))
        chooseMenuAction("전체 비우기", menu: "보관함 관리", in: app)
        XCTAssertTrue(app.staticTexts["비운 알림은 보관함에서 숨겨져요. 거래 기록은 유지돼요."].firstMatch
            .waitForExistence(timeout: 5))
        events = try await fixtureEvents()
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read/archive/clear-all" },
                       "Clear-all must wait for confirmation")
        attachScreenshot(app, name: "읽음 보관함 전체 비우기 확인")
        confirm("전체 비우기", in: app)
        XCTAssertTrue(app.staticTexts["읽음 처리된 알림이 없습니다."].waitForExistence(timeout: 10))
        XCTAssertFalse(archiveCard.exists)

        events = try await fixtureEvents()
        let clears = events.filter { ($0["path"] as? String) == "/alert-events/read/archive/clear-all" }
        XCTAssertEqual(clears.count, 1)
        let clear = try XCTUnwrap(clears.first)
        XCTAssertEqual(clear["method"] as? String, "PATCH")
        XCTAssertNil((clear["body"] as? [String: Any])?["alert_event_ids"])
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/read/archive/clear-selected" })
    }

    private func launchFixtureApp() async throws -> XCUIApplication {
        continueAfterFailure = false
        do { _ = try await fixture("/__reset", method: "POST") }
        catch { throw XCTSkip("Loopback fixture not running. Start TestsSupport/parity_server.py on 127.0.0.1:18765.") }
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = "http://127.0.0.1:18765"
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user"]
        app.launch()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 10))
        return app
    }

    private func chooseMenuAction(_ title: String, menu: String, in app: XCUIApplication,
                                  file: StaticString = #filePath, line: UInt = #line) {
        let menuButton = app.navigationBars.buttons[menu].firstMatch
        XCTAssertTrue(menuButton.waitForExistence(timeout: 5), file: file, line: line)
        menuButton.tap()
        let action = app.buttons[title].firstMatch
        XCTAssertTrue(action.waitForExistence(timeout: 5), file: file, line: line)
        XCTAssertTrue(action.isEnabled, file: file, line: line)
        action.tap()
    }

    private func assertSelection(_ selected: Bool, of card: XCUIElement,
                                 file: StaticString = #filePath, line: UInt = #line) {
        let expectedValue = selected ? "선택됨" : "선택 안 됨"
        let expectation = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", expectedValue), object: card)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: 5), .completed,
                       "Expected card selection value: \(expectedValue)", file: file, line: line)
    }

    private func confirm(_ title: String, in app: XCUIApplication,
                         file: StaticString = #filePath, line: UInt = #line) {
        // A confirmationDialog can appear as a sheet or a popover. Its destructive
        // action is present in both; a popover is not required to expose Cancel.
        let action = app.buttons[title].firstMatch
        XCTAssertTrue(action.waitForExistence(timeout: 5), file: file, line: line)
        XCTAssertTrue(action.isHittable, file: file, line: line)
        action.tap()
    }

    private func attachScreenshot(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func fixtureEvents() async throws -> [[String: Any]] {
        let response = try await fixture("/__events")
        return try XCTUnwrap(response["events"] as? [[String: Any]])
    }

    private func fixture(_ path: String, method: String = "GET") async throws -> [String: Any] {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18765" + path)!)
        request.httpMethod = method
        request.timeoutInterval = 3
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    }
}
