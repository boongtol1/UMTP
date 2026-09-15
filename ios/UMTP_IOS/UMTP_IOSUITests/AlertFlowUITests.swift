import XCTest

/// End-to-end UI against the loopback fixture. No production account or API is used.
@MainActor
final class AlertFlowUITests: XCTestCase {
    func testReviewArchivesOnlyAfterExplicitConfirmationAndStartsArchiveTrade() async throws {
        let app = try await launchFixtureApp()
        let card = app.buttons["alert.card.101"].firstMatch
        XCTAssertTrue(card.waitForExistence(timeout: 10))
        card.tap()
        XCTAssertTrue(app.navigationBars["거래 알림 상세"].waitForExistence(timeout: 5))
        var events = try await fixtureEvents()
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/101/read" },
                       "Opening details must not mark the alert read")

        let review = app.buttons["alert.review"]
        scrollTo(review, in: app)
        XCTAssertTrue(review.isHittable)
        let detail = XCTAttachment(screenshot: app.screenshot())
        detail.name = "알림 상세 및 명시적 검토 완료"
        detail.lifetime = .keepAlways
        add(detail)
        review.tap()
        XCTAssertTrue(app.navigationBars["거래 알림 피드"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["알림이 없습니다."].waitForExistence(timeout: 5))
        events = try await fixtureEvents()
        XCTAssertTrue(events.contains { ($0["method"] as? String) == "PATCH" && ($0["path"] as? String) == "/alert-events/101/read" })

        app.tabBars.buttons["읽음 보관함"].tap()
        XCTAssertTrue(app.navigationBars["읽음 알림 보관함"].waitForExistence(timeout: 5))
        let archiveCard = app.buttons["alert.card.101"].firstMatch
        XCTAssertTrue(archiveCard.waitForExistence(timeout: 5))
        XCTAssertTrue(archiveCard.label.contains("읽음 시각: 2026-09-15 16:00:00"))
        app.buttons["거래 기록 시작"].firstMatch.tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["검증용 맥북 에어 M1"].firstMatch.waitForExistence(timeout: 10))
        events = try await fixtureEvents()
        let trade = try XCTUnwrap(events.last { ($0["path"] as? String) == "/trade-journeys/start-from-read-archive" })
        XCTAssertEqual(trade["method"] as? String, "POST")
        XCTAssertEqual((trade["body"] as? [String: Any])?["read_archive_event_id"] as? Int, 1101)
    }

    func testStartTradeFromUnreadKeepsUnreadAndUsesAlertEventID() async throws {
        let app = try await launchFixtureApp()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 10))
        app.buttons["거래 기록 시작"].firstMatch.tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["검증용 맥북 에어 M1"].firstMatch.waitForExistence(timeout: 10))
        let events = try await fixtureEvents()
        let trade = try XCTUnwrap(events.last { ($0["path"] as? String) == "/trade-journeys/start-from-alert" })
        XCTAssertEqual((trade["body"] as? [String: Any])?["alert_event_id"] as? Int, 101)
        XCTAssertFalse(events.contains { ($0["path"] as? String) == "/alert-events/101/read" })
        app.tabBars.buttons["알림"].tap()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 5))
    }

    func testOutagePreservesFeedAndRetryRecovers() async throws {
        let app = try await launchFixtureApp()
        let card = app.buttons["alert.card.101"].firstMatch
        XCTAssertTrue(card.waitForExistence(timeout: 10))
        _ = try await fixture("/__fail", method: "POST", body: ["enabled": true])
        app.navigationBars["거래 알림 피드"].buttons["새로고침"].tap()
        let retry = app.buttons["다시 시도"].firstMatch
        XCTAssertTrue(retry.waitForExistence(timeout: 10))
        XCTAssertTrue(card.exists, "A failed refresh must preserve the last successful feed")
        XCTAssertFalse(app.staticTexts["fixture outage"].exists, "Raw backend errors must not be shown")
        let failed = XCTAttachment(screenshot: app.screenshot())
        failed.name = "알림 새로고침 오류 및 기존 목록 보존"
        failed.lifetime = .keepAlways
        add(failed)

        _ = try await fixture("/__fail", method: "POST", body: ["enabled": false])
        retry.tap()
        let recovered = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: retry)
        await fulfillment(of: [recovered], timeout: 10)
        XCTAssertTrue(card.exists)
        let events = try await fixtureEvents()
        XCTAssertGreaterThanOrEqual(events.filter { ($0["path"] as? String) == "/alerts" }.count, 3)
    }

    func testFailedAlertTradeStartCanRetryWithoutTypingReference() async throws {
        let app = try await launchFixtureApp()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 10))
        _ = try await fixture("/__fail", method: "POST", body: ["enabled": true])
        app.buttons["거래 기록 시작"].firstMatch.tap()
        let retry = app.buttons["trade.retryStart"]
        XCTAssertTrue(retry.waitForExistence(timeout: 10))
        _ = try await fixture("/__fail", method: "POST", body: ["enabled": false])
        retry.tap()
        XCTAssertTrue(app.staticTexts["검증용 맥북 에어 M1"].firstMatch.waitForExistence(timeout: 10))
        let events = try await fixtureEvents().filter { ($0["path"] as? String) == "/trade-journeys/start-from-alert" }
        XCTAssertEqual(events.count, 2)
        XCTAssertTrue(events.allSatisfy { (($0["body"] as? [String: Any])?["alert_event_id"] as? Int) == 101 })
    }

    func testAlertTradeNavigationPreservesDraftUnlessReplacementConfirmed() async throws {
        let app = try await launchFixtureApp()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 10))
        app.buttons["거래 기록 시작"].firstMatch.tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].waitForExistence(timeout: 10))
        let serial = app.textFields["trade.field.serial_number"]
        scrollTo(serial, in: app)
        serial.tap()
        serial.typeText("DRAFT-SERIAL")
        app.buttons["trade.keyboard.done"].tap()
        XCTAssertEqual(serial.value as? String, "DRAFT-SERIAL", "The draft must exist before leaving its tab")

        app.tabBars.buttons["알림"].tap()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 5))
        // Tab navigation alone must preserve the form without issuing another start.
        app.tabBars.buttons["거래 입력"].tap()
        scrollTo(serial, in: app)
        XCTAssertEqual(serial.value as? String, "DRAFT-SERIAL")
        app.tabBars.buttons["알림"].tap()
        app.buttons["거래 기록 시작"].firstMatch.tap()
        let keep = app.alerts.firstMatch.buttons["trade.draft.keep"].firstMatch
        guard keep.waitForExistence(timeout: 5) else {
            XCTFail("The replacement prompt must offer an explicit continue-editing action")
            return
        }
        let prompt = XCTAttachment(screenshot: app.screenshot())
        prompt.name = "다른 알림을 열기 전 거래 초안 보호"
        prompt.lifetime = .keepAlways
        add(prompt)
        keep.tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].waitForExistence(timeout: 5))
        scrollTo(serial, in: app)
        XCTAssertEqual(serial.value as? String, "DRAFT-SERIAL")
        var events = try await fixtureEvents()
        XCTAssertEqual(events.filter { ($0["path"] as? String) == "/trade-journeys/start-from-alert" }.count, 1)

        app.tabBars.buttons["알림"].tap()
        app.buttons["거래 기록 시작"].firstMatch.tap()
        let replace = app.alerts.firstMatch.buttons["trade.draft.replace"].firstMatch
        guard replace.waitForExistence(timeout: 5) else {
            XCTFail("Discarding the draft must require an explicit replacement action")
            return
        }
        replace.tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].waitForExistence(timeout: 5))
        scrollTo(serial, in: app)
        let cleared = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value != %@", "DRAFT-SERIAL"), object: serial)
        await fulfillment(of: [cleared], timeout: 10)
        events = try await fixtureEvents()
        XCTAssertEqual(events.filter { ($0["path"] as? String) == "/trade-journeys/start-from-alert" }.count, 2)
    }

    private func launchFixtureApp() async throws -> XCUIApplication {
        continueAfterFailure = false
        do { _ = try await fixture("/__reset", method: "POST") }
        catch { throw XCTSkip("Loopback fixture not running. Start TestsSupport/parity_server.py on 127.0.0.1:18765.") }
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = "http://127.0.0.1:18765"
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user"]
        app.launch()
        return app
    }

    private func scrollTo(_ element: XCUIElement, in app: XCUIApplication) {
        for _ in 0..<25 {
            if element.exists && element.isHittable { return }
            app.swipeUp()
        }
    }

    private func fixtureEvents() async throws -> [[String: Any]] {
        let response = try await fixture("/__events")
        return response["events"] as? [[String: Any]] ?? []
    }

    private func fixture(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> [String: Any] {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:18765" + path)!)
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
