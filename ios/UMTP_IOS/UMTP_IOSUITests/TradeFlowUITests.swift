import XCTest

/// The service below is an in-memory loopback fixture, never the production UMTP API.
@MainActor
final class TradeFlowUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!

    override func setUp() async throws {
        continueAfterFailure = false
        var request = URLRequest(url: baseURL.appendingPathComponent("__reset"))
        request.httpMethod = "POST"
        request.timeoutInterval = 2
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw XCTSkip("로컬 parity fixture가 준비되지 않았습니다.") }
        } catch { throw XCTSkip("로컬 parity fixture를 실행해야 거래 UI 테스트가 가능합니다: \(error.localizedDescription)") }
    }

    func testManualPrefillPurchaseSavesOnlyChangedFieldsAndShowsHistory() async throws {
        let app = launchTrade()
        start(app)
        let title = app.textFields["trade.field.title"]
        scrollTo(title, in: app)
        XCTAssertEqual(title.value as? String, "검증용 맥북 에어 M1")

        let purchasedAt = app.textFields["trade.field.purchased_at"]
        scrollTo(purchasedAt, in: app)
        try enter("2026-09-15 15:30:00", into: purchasedAt, in: app)
        XCTAssertEqual(purchasedAt.value as? String, "2026-09-15 15:30:00")
        attachScreenshot(app, name: "구매 시각 전체 입력 유지")

        let method = app.textFields["trade.field.purchase_method"]
        scrollTo(method, in: app)
        try enter("direct pickup", into: method, in: app)
        XCTAssertEqual(method.value as? String, "direct pickup")

        let price = app.textFields["trade.field.purchase_price_krw"]
        scrollTo(price, in: app)
        try enter("450000", into: price, in: app)
        XCTAssertEqual(price.value as? String, "450000")
        let transport = app.textFields["trade.field.transport_cost_krw"]
        scrollTo(transport, in: app)
        try enter("2000", into: transport, in: app)
        XCTAssertEqual(transport.value as? String, "2000")

        let notes = app.textFields["trade.field.inspection_notes"]
        scrollTo(notes, in: app)
        try enter("Checked battery and display", into: notes, in: app)
        XCTAssertEqual(notes.value as? String, "Checked battery and display")

        let save = app.buttons["trade.save"]
        scrollTo(save, in: app)
        save.tap()
        let event = try await waitForSaveEvent()
        XCTAssertEqual(event["method"] as? String, "POST")
        XCTAssertEqual(event["path"] as? String, "/resale-trades/after-purchase/upsert")
        let body = try XCTUnwrap(event["body"] as? [String: Any])
        XCTAssertEqual(body["user_id"] as? String, "parity-fixture-user")
        XCTAssertEqual(body["product_id"] as? String, "123456")
        let updates = try XCTUnwrap(body["updates"] as? [String: Any])
        XCTAssertEqual(updates["purchase_price_krw"] as? Int, 450000)
        XCTAssertEqual(updates["transport_cost_krw"] as? Int, 2000)
        XCTAssertEqual(updates["purchased_at"] as? String, "2026-09-15 15:30:00")
        XCTAssertEqual(updates["purchase_method"] as? String, "direct pickup")
        XCTAssertEqual(updates["inspection_notes"] as? String, "Checked battery and display")
        XCTAssertNil(updates["title"], "수정하지 않은 자동채움 값은 재전송하지 않습니다.")
        XCTAssertNil(updates["shipping_cost_krw"], "미입력 값은 서버의 기존 값을 지우지 않습니다.")

        let history = app.buttons.matching(NSPredicate(format: "label CONTAINS %@ AND label CONTAINS %@", "검증용 맥북 에어 M1", "450,000원")).firstMatch
        scrollTo(history, in: app)
        XCTAssertTrue(history.exists)
        attachScreenshot(app, name: "수동 구매 저장 후 내역과 금액")
        app.tabBars.buttons["알림"].tap()
        app.tabBars.buttons["거래 입력"].tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].exists)
    }

    func testInvalidVerificationIsNotSentAndRemainsForCorrection() async throws {
        let app = launchTrade()
        start(app)
        let battery = app.textFields["trade.field.battery_health_percent"]
        scrollTo(battery, in: app)
        try enter("101", into: battery, in: app)
        let save = app.buttons["trade.save"]
        scrollTo(save, in: app)
        save.tap()
        // A validation rejection occurs synchronously before the first API await.
        let error = app.staticTexts["trade.error"]
        scrollTo(error, in: app, upward: false)
        XCTAssertTrue(error.exists)
        XCTAssertTrue(error.label.contains("배터리 성능"))
        attachScreenshot(app, name: "잘못된 확인 정보 저장 차단")
        let eventsBeforeCorrection = try await saveEvents()
        XCTAssertEqual(eventsBeforeCorrection.count, 0)

        scrollTo(battery, in: app)
        XCTAssertEqual(battery.value as? String, "101")
        try enter(String(repeating: XCUIKeyboardKey.delete.rawValue, count: 3) + "99", into: battery, in: app)
        scrollTo(save, in: app)
        save.tap()
        let event = try await waitForSaveEvent()
        let body = try XCTUnwrap(event["body"] as? [String: Any])
        let updates = try XCTUnwrap(body["updates"] as? [String: Any])
        XCTAssertEqual(updates["battery_health_percent"] as? Int, 99)
        XCTAssertNil(updates["purchase_price_krw"])
        XCTAssertNil(updates["activation_lock_off"])
        XCTAssertNil(updates["mdm_lock_none"])
    }

    private func launchTrade() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user"]
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["거래 입력"].waitForExistence(timeout: 10))
        app.tabBars.buttons["거래 입력"].tap()
        return app
    }

    private func start(_ app: XCUIApplication) {
        let reference = app.textFields["trade.reference"]
        XCTAssertTrue(reference.waitForExistence(timeout: 10))
        reference.tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5), "거래 시작 입력에도 소프트웨어 키보드가 표시되어야 합니다.")
        reference.typeText("123456")
        app.buttons["trade.start"].tap()
        XCTAssertTrue(app.staticTexts["제품 기본 스펙"].waitForExistence(timeout: 10))
    }

    private func scrollTo(_ element: XCUIElement, in app: XCUIApplication, upward: Bool = true, file: StaticString = #filePath, line: UInt = #line) {
        dismissKeyboard(in: app)
        for _ in 0..<24 {
            var moveUp = upward
            if element.exists {
                // Bring the entire control between the navigation and tab bars
                // before testing a normal center tap. The system's translucent
                // edge effect above the tab bar is still scrollable content.
                let top = app.navigationBars.firstMatch.frame.maxY + 12
                let bottom = app.tabBars.firstMatch.frame.minY - 12
                let frame = element.frame
                if element.isHittable && frame.minY >= top && frame.maxY <= bottom { return }
                if frame.minY < top { moveUp = false }
                else if frame.maxY > bottom { moveUp = true }
            }
            // Start above the tab bar, after dismissing number-pad/keyboard overlays.
            // Drag the form's trailing padding so an editable multiline field cannot absorb the gesture.
            let from = app.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: moveUp ? 0.70 : 0.35))
            let to = app.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: moveUp ? 0.35 : 0.70))
            from.press(forDuration: 0.05, thenDragTo: to)
        }
        XCTFail("거래 화면 요소를 스크롤하여 찾지 못했습니다: \(element)", file: file, line: line)
    }

    private enum InputFailure: Error { case missingKeyboard }

    private func enter(_ text: String, into field: XCUIElement, in app: XCUIApplication,
                       file: StaticString = #filePath, line: UInt = #line) throws {
        // Deliberately tap the normal accessibility target's center. Do not hide
        // a focus regression by aiming at a narrow placeholder glyph or typing
        // through a hardware-keyboard shortcut without visible input focus.
        XCTAssertTrue(field.isEnabled, "입력칸이 비활성화되어 있습니다.", file: file, line: line)
        field.tap()
        guard app.keyboards.firstMatch.waitForExistence(timeout: 5) else {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "거래 입력 포커스 실패: \(field.identifier)"
            screenshot.lifetime = .keepAlways
            add(screenshot)
            XCTFail("입력 필드 중앙을 탭하면 키보드가 표시되어야 합니다: \(field.identifier)", file: file, line: line)
            throw InputFailure.missingKeyboard
        }
        field.typeText(text)
        if field.identifier == "trade.field.purchased_at" {
            attachScreenshot(app, name: "구매 시각 입력 중 키보드와 입력값")
        }
        dismissKeyboard(in: app)
    }

    private func attachScreenshot(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func dismissKeyboard(in app: XCUIApplication) {
        let done = app.buttons["trade.keyboard.done"]
        if done.exists && done.isHittable { done.tap() }
    }

    private func saveEvents() async throws -> [[String: Any]] {
        let (data, _) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("__events"))
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        return (json["events"] as? [[String: Any]] ?? []).filter {
            let path = $0["path"] as? String ?? ""
            return path.hasPrefix("/resale-trades/") || (($0["method"] as? String) == "PATCH" && path.contains("resale-trade-journeys"))
        }
    }

    private func waitForSaveEvent() async throws -> [String: Any] {
        for _ in 0..<30 {
            if let event = try await saveEvents().last { return event }
            try await Task.sleep(for: .milliseconds(200))
        }
        XCTFail("거래 저장 요청을 fixture에서 확인하지 못했습니다.")
        throw URLError(.timedOut)
    }
}
