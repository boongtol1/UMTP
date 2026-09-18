import XCTest

@MainActor
final class SettingsFlowUITests: XCTestCase {
    private let baseURL = "http://127.0.0.1:18765"
    private let unitKey = "MacBook Air|M1|13|8|256"

    func testMacBookNeoSeedCatalogAndSaveReachTheAPI() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        app.tabBars.buttons["설정"].tap()
        let product = app.buttons["MacBook Neo"]
        XCTAssertTrue(product.waitForExistence(timeout: 10))
        product.tap()
        app.buttons["A18 Pro"].tap()
        XCTAssertTrue(app.buttons["13인치"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["14인치"].exists)
        app.buttons["13인치"].tap()
        XCTAssertTrue(app.navigationBars["A18 Pro MacBook Neo 13인치 설정"].waitForExistence(timeout: 5))
        let baseMarket = app.textFields["settings.market.MacBook Neo|A18 Pro|13|8|256"]
        scrollTo(baseMarket, in: app)
        XCTAssertEqual(baseMarket.value as? String, "850000")
        let key = "MacBook Neo|A18 Pro|13|8|512"
        let market = app.textFields["settings.market.\(key)"]
        scrollTo(market, in: app)
        XCTAssertEqual(market.value as? String, "900000")
        replace(market, with: "1000000")
        dismissKeyboard(app)
        let save = app.buttons["settings.save.\(key)"]
        scrollTo(save, in: app)
        save.tap()
        XCTAssertTrue(app.alerts["설정"].waitForExistence(timeout: 10))
        app.alerts.buttons["확인"].tap()
        let requests = try await events()
        let saved = requests.filter { $0["path"] as? String == "/user-fair-prices/upsert" }
        XCTAssertEqual(saved.count, 1)
        let body = try XCTUnwrap(saved.first?["body"] as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "MacBook Neo")
        XCTAssertEqual(body["chip"] as? String, "A18 Pro")
        XCTAssertEqual(body["screen_inch"] as? Int, 13)
        XCTAssertEqual(body["ram_gb"] as? Int, 8)
        XCTAssertEqual(body["ssd_gb"] as? Int, 512)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 1000000)
        XCTAssertEqual(body["search_keyword"] as? String, "맥북 네오")
    }

    func testIMacSeedCatalogAndIndividualSaveReachTheAPI() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        app.tabBars.buttons["설정"].tap()
        let imac = app.buttons["iMac"]
        XCTAssertTrue(imac.waitForExistence(timeout: 10)); imac.tap()
        XCTAssertTrue(app.buttons["M1"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["M3"].exists)
        XCTAssertTrue(app.buttons["M4"].exists)
        XCTAssertFalse(app.buttons["M2"].exists)
        app.buttons["M4"].tap()
        XCTAssertTrue(app.buttons["24인치"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["27인치"].exists)
        app.buttons["24인치"].tap()
        XCTAssertTrue(app.navigationBars["M4 iMac 24인치 설정"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["현재 칩/인치"].exists)
        let key = "iMac|M4|24|16|256"
        let market = app.textFields["settings.market.\(key)"]
        scrollTo(market, in: app)
        XCTAssertEqual(market.value as? String, "1500000")
        replace(market, with: "1600000")
        dismissKeyboard(app)
        let save = app.buttons["settings.save.\(key)"]
        scrollTo(save, in: app); save.tap()
        XCTAssertTrue(app.alerts["설정"].waitForExistence(timeout: 10))
        app.alerts.buttons["확인"].tap()
        let requests = try await events()
        let saved = try XCTUnwrap(requests.last { $0["path"] as? String == "/user-fair-prices/upsert" })
        let body = try XCTUnwrap(saved["body"] as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "iMac")
        XCTAssertEqual(body["chip"] as? String, "M4")
        XCTAssertEqual(body["screen_inch"] as? Int, 24)
        XCTAssertEqual(body["ram_gb"] as? Int, 16)
        XCTAssertEqual(body["ssd_gb"] as? Int, 256)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 1600000)
        XCTAssertEqual(body["search_keyword"] as? String, "아이맥 M4")
        XCTAssertEqual(body["enabled"] as? Bool, false)
    }

    func testMacBookProBaseChipUsesThirteenInchSeedCatalog() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        openProSettings(app, chip: "M1")
        XCTAssertTrue(app.buttons["13인치"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["14인치"].exists)
        XCTAssertFalse(app.buttons["16인치"].exists)
        app.buttons["13인치"].tap()
        XCTAssertTrue(app.navigationBars["M1 MacBook Pro 13인치 설정"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["현재 칩/인치"].exists)
        let market = app.textFields["settings.market.MacBook Pro|M1|13|8|256"]
        scrollTo(market, in: app)
        XCTAssertEqual(market.value as? String, "700000")
    }

    func testMacBookProMaxScreenSelectionAndSaveReachTheAPI() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        openProSettings(app, chip: "M5 Max")
        XCTAssertTrue(app.buttons["14인치"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["16인치"].exists)
        XCTAssertFalse(app.buttons["13인치"].exists)
        app.buttons["16인치"].tap()
        XCTAssertTrue(app.navigationBars["M5 Max MacBook Pro 16인치 설정"].waitForExistence(timeout: 5))
        let key = "MacBook Pro|M5 Max|16|36|2048"
        let market = app.textFields["settings.market.\(key)"]
        scrollTo(market, in: app)
        XCTAssertEqual(market.value as? String, "5850000")
        replace(market, with: "6000000")
        dismissKeyboard(app)
        let save = app.buttons["settings.save.\(key)"]
        scrollTo(save, in: app)
        save.tap()
        XCTAssertTrue(app.alerts["설정"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.alerts.staticTexts["저장 완료. 즉시 검색을 요청했어요."].exists)
        app.alerts.buttons["확인"].tap()

        let requests = try await events()
        let saved = requests.filter { $0["path"] as? String == "/user-fair-prices/upsert" }
        XCTAssertEqual(saved.count, 1)
        let body = try XCTUnwrap(saved.first?["body"] as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "MacBook Pro")
        XCTAssertEqual(body["chip"] as? String, "M5 Max")
        XCTAssertEqual(body["screen_inch"] as? Int, 16)
        XCTAssertEqual(body["ram_gb"] as? Int, 36)
        XCTAssertEqual(body["ssd_gb"] as? Int, 2048)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 6000000)
        XCTAssertEqual(body["alert_drop_rate_percent"] as? Double, 22)
        XCTAssertEqual(body["search_keyword"] as? String, "맥북 프로 M5 Max")
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["M5 Max MacBook Pro 선택"].waitForExistence(timeout: 5))
    }

    func testIndividualPriceDirectionAndBoundReachTheAPI() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        openAirSettings(app)

        // This pending bulk input is unrelated to the upper-bound save below.
        // It must survive while the changed aggregate maximum is reloaded.
        let bulkMinimum = app.textFields["최소 가격 (원)"]
        scrollTo(bulkMinimum, in: app)
        replace(bulkMinimum, with: "12345")
        dismissKeyboard(app)
        let market = app.textFields["settings.market.\(unitKey)"]
        scrollTo(market, in: app)
        replace(market, with: "1000000")
        dismissKeyboard(app)
        let target = app.textFields["알림 기준 가격 (원)"]
        scrollTo(target, in: app)
        replace(target, with: "800000")
        dismissKeyboard(app)
        let guidance = app.staticTexts["settings.market.guidance.\(unitKey)"]
        scrollTo(guidance, in: app)
        XCTAssertTrue(guidance.label.hasSuffix("설정할 수 있습니다."))
        XCTAssertGreaterThan(guidance.frame.height, 30,
                             "시장가 안내문은 한 줄로 잘리지 않고 전체 문장이 표시되어야 합니다.")
        let guidanceScreenshot = XCTAttachment(screenshot: app.screenshot())
        guidanceScreenshot.name = "시장가 안내문 전체 표시"
        guidanceScreenshot.lifetime = .keepAlways
        add(guidanceScreenshot)
        let above = app.buttons["이상 알림"]
        scrollTo(above, in: app)
        above.tap()
        let maximum = app.textFields["예: 900000"]
        scrollTo(maximum, in: app)
        replace(maximum, with: "1400000")
        dismissKeyboard(app)
        let save = app.buttons["settings.save.\(unitKey)"]
        scrollTo(save, in: app)
        let settingsScreenshot = XCTAttachment(screenshot: app.screenshot())
        settingsScreenshot.name = "개별 가격 방향과 최대 가격 저장 전"
        settingsScreenshot.lifetime = .keepAlways
        add(settingsScreenshot)
        save.tap()
        XCTAssertTrue(app.alerts["설정"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.alerts.staticTexts["저장 완료. 즉시 검색을 요청했어요."].exists)
        app.alerts.buttons["확인"].tap()

        let requests = try await events()
        let saved = try XCTUnwrap(requests.last { $0["path"] as? String == "/user-fair-prices/upsert" })
        let body = try XCTUnwrap(saved["body"] as? [String: Any])
        XCTAssertEqual(saved["method"] as? String, "POST")
        XCTAssertEqual(body["product_type"] as? String, "MacBook Air")
        XCTAssertEqual(body["chip"] as? String, "M1")
        XCTAssertEqual(body["fair_price_krw"] as? Int, 1000000)
        XCTAssertEqual(body["alert_drop_rate_percent"] as? Double, 20)
        XCTAssertEqual(body["alert_price_direction"] as? String, "ABOVE_OR_EQUAL")
        XCTAssertEqual(body["max_price_krw"] as? Int, 1400000)
        XCTAssertNil(body["min_price_krw"])
        XCTAssertEqual(body["user_id"] as? String, "parity-fixture-user")

        for _ in 0..<18 {
            if bulkMinimum.exists && bulkMinimum.isHittable { break }
            app.swipeDown()
        }
        XCTAssertEqual(bulkMinimum.value as? String, "12345", "Unchanged aggregates must preserve pending input")
        let bulkMaximum = app.textFields["최대 가격 (원)"]
        scrollTo(bulkMaximum, in: app)
        XCTAssertEqual(bulkMaximum.value as? String, "1400000", "Individual saves must refresh the corresponding bulk default")
    }

    func testMacMiniSkipsScreenSizeAndSupportsBackNavigation() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        app.tabBars.buttons["설정"].tap()
        let mini = app.buttons["Mac mini"]
        XCTAssertTrue(mini.waitForExistence(timeout: 10))
        mini.tap()
        let m4 = app.buttons["M4"]
        XCTAssertTrue(m4.waitForExistence(timeout: 5))
        m4.tap()
        XCTAssertTrue(app.navigationBars["M4 Mac mini 설정"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["화면 크기 선택"].exists)
        XCTAssertTrue(app.buttons["현재 칩"].exists)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["Mac mini 설정"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["M4"].exists)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["실리콘 Mac 설정"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["MacBook Air"].exists)
    }

    func testUnsavedPriceSurvivesTabRoundTripWithoutWritingServer() async throws {
        try await resetFixture()
        let app = launchFixtureApp()
        openAirSettings(app)
        let priority = app.segmentedControls["settings.bulk.priority"]
        scrollTo(priority, in: app)
        priority.buttons["빠름"].tap()
        let bulkMinimum = app.textFields["최소 가격 (원)"]
        scrollTo(bulkMinimum, in: app)
        replace(bulkMinimum, with: "350000")
        dismissKeyboard(app)
        let bulkMaximum = app.textFields["최대 가격 (원)"]
        scrollTo(bulkMaximum, in: app)
        replace(bulkMaximum, with: "1250000")
        dismissKeyboard(app)
        let market = app.textFields["settings.market.\(unitKey)"]
        scrollTo(market, in: app)
        replace(market, with: "910000")
        dismissKeyboard(app)
        app.tabBars.buttons["알림"].tap()
        XCTAssertTrue(app.navigationBars["거래 알림 피드"].waitForExistence(timeout: 5))
        app.tabBars.buttons["설정"].tap()
        XCTAssertTrue(app.navigationBars["M1 MacBook Air 13인치 설정"].waitForExistence(timeout: 5))
        let restored = app.textFields["settings.market.\(unitKey)"]
        scrollTo(restored, in: app)
        XCTAssertEqual(restored.value as? String, "910000")
        scrollTo(priority, in: app, towardTop: true)
        XCTAssertTrue(priority.buttons["빠름"].isSelected, "The unsaved bulk priority must survive tab navigation")
        scrollTo(bulkMinimum, in: app)
        XCTAssertEqual(bulkMinimum.value as? String, "350000")
        scrollTo(bulkMaximum, in: app)
        XCTAssertEqual(bulkMaximum.value as? String, "1250000")
        let requests = try await events()
        XCTAssertFalse(requests.contains { ["POST", "PATCH", "PUT", "DELETE"].contains($0["method"] as? String ?? "") },
                       "Editing drafts and changing tabs must not write to the server")
    }

    private func launchFixtureApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user", "-AppleLanguages", "(ko)", "-AppleLocale", "ko_KR"]
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["설정"].waitForExistence(timeout: 10))
        return app
    }

    private func openAirSettings(_ app: XCUIApplication) {
        app.tabBars.buttons["설정"].tap()
        navigateAirTree(app)
    }

    private func openProSettings(_ app: XCUIApplication, chip: String) {
        app.tabBars.buttons["설정"].tap()
        let pro = app.buttons["MacBook Pro"]
        XCTAssertTrue(pro.waitForExistence(timeout: 10)); pro.tap()
        let selectedChip = app.buttons[chip]
        scrollTo(selectedChip, in: app)
        selectedChip.tap()
        XCTAssertTrue(app.navigationBars["\(chip) MacBook Pro 선택"].waitForExistence(timeout: 5))
    }

    private func navigateAirTree(_ app: XCUIApplication) {
        let air = app.buttons["MacBook Air"]
        XCTAssertTrue(air.waitForExistence(timeout: 10)); air.tap()
        let chip = app.buttons["M1"]
        XCTAssertTrue(chip.waitForExistence(timeout: 5)); chip.tap()
        let inch = app.buttons["13인치"]
        XCTAssertTrue(inch.waitForExistence(timeout: 5)); inch.tap()
        XCTAssertTrue(app.navigationBars["M1 MacBook Air 13인치 설정"].waitForExistence(timeout: 5))
    }

    private func scrollTo(_ element: XCUIElement, in app: XCUIApplication, towardTop: Bool = false,
                          file: StaticString = #filePath, line: UInt = #line) {
        for _ in 0..<18 {
            if element.exists && element.isHittable { return }
            if towardTop { app.swipeDown() } else { app.swipeUp() }
        }
        XCTFail("설정 화면에서 필요한 항목에 접근하지 못했습니다: \(element)", file: file, line: line)
    }

    private func replace(_ field: XCUIElement, with value: String) {
        field.tap()
        let previous = field.value as? String ?? ""
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: previous.count) + value)
    }

    private func dismissKeyboard(_ app: XCUIApplication) {
        let done = app.toolbars.buttons["완료"].firstMatch
        if done.exists && done.isHittable { done.tap() }
    }

    private func resetFixture() async throws {
        var request = URLRequest(url: URL(string: baseURL + "/__reset")!)
        request.httpMethod = "POST"
        request.timeoutInterval = 3
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else {
                throw XCTSkip("Loopback fixture server is unavailable.")
            }
        } catch {
            throw XCTSkip("Start TestsSupport/parity_server.py to run settings UI flows: \(error.localizedDescription)")
        }
    }

    private func events() async throws -> [[String: Any]] {
        let (data, _) = try await URLSession.shared.data(from: URL(string: baseURL + "/__events")!)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        return try XCTUnwrap(object["events"] as? [[String: Any]])
    }
}
