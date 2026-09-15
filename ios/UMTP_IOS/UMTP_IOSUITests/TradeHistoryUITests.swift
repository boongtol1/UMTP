import XCTest

/// Exercises existing completed journeys against a separate in-memory scenario.
/// Other users' journeys and this user's purchased/KEEP rows must survive each mutation.
@MainActor
final class TradeHistoryUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!
    private let user = "parity-fixture-user"
    private var journeysPath: String { "users/\(user)/resale-trade-journeys" }

    override func setUp() async throws {
        continueAfterFailure = false
        _ = try await fixture("__reset", method: "POST")
        _ = try await fixture("__scenario/trade-history", method: "POST")
    }

    func testCompletedSelectionResaleSaveUpdatesOnlyChosenJourney() async throws {
        let app = launchTrade()
        let completed = historyButton(401, title: "완료 거래 맥북 에어 401", in: app)
        scrollTo(completed, in: app)
        XCTAssertTrue(completed.label.contains("620,000원"))
        completed.tap()

        let deselect = app.buttons["선택 해제"]
        scrollTo(deselect, in: app, upward: false)
        XCTAssertTrue(deselect.exists)
        let resaleMode = app.segmentedControls.buttons["되팔이 후 기록"]
        scrollTo(resaleMode, in: app)
        resaleMode.tap()
        XCTAssertTrue(resaleMode.isSelected)

        let listingPrice = app.textFields["trade.field.resale_listing_price_krw"]
        scrollTo(listingPrice, in: app)
        try replaceText("700000", original: "", in: listingPrice, app: app)
        let price = app.textFields["trade.field.sale_price_krw"]
        scrollTo(price, in: app)
        XCTAssertEqual(price.value as? String, "620000")
        try replaceText("650000", original: "620000", in: price, app: app)
        XCTAssertEqual(price.value as? String, "650000")

        let save = app.buttons["trade.save"]
        scrollTo(save, in: app)
        XCTAssertEqual(save.label, "되팔이 후 기록 저장")
        attachScreenshot(app, name: "완료 거래 401 재판매 수정")
        save.tap()
        let events = try await waitForHistoryRefresh(after: "/\(journeysPath)/401/resale")
        let saves = events.filter { ($0["method"] as? String) == "PATCH" }
        XCTAssertEqual(saves.count, 1)
        let saved = try XCTUnwrap(saves.first)
        XCTAssertEqual(saved["path"] as? String, "/\(journeysPath)/401/resale")
        let body = try XCTUnwrap(saved["body"] as? [String: Any])
        XCTAssertEqual(Set(body.keys), ["updates"])
        let updates = try XCTUnwrap(body["updates"] as? [String: Any])
        XCTAssertEqual(Set(updates.keys), ["resale_listing_price_krw", "sale_price_krw"])
        XCTAssertEqual(updates["resale_listing_price_krw"] as? Int, 700000)
        XCTAssertEqual(updates["sale_price_krw"] as? Int, 650000)
        XCTAssertFalse(events.contains { ($0["path"] as? String)?.hasPrefix("/resale-trades/") == true },
                       "Selecting an existing journey must PATCH that ID instead of creating an upsert.")

        let updatedHistory = historyButton(401, title: "완료 거래 맥북 에어 401", in: app)
        scrollTo(updatedHistory, in: app)
        XCTAssertTrue(updatedHistory.label.contains("650,000원"))
        XCTAssertTrue(updatedHistory.label.contains("선택됨"))
        attachScreenshot(app, name: "재판매 저장 후 완료 거래 내역")

        let rows = try await assertHistoryIDs([401, 402], collection: "completed")
        let row = try XCTUnwrap(rows.first { ($0["id"] as? Int) == 401 })
        XCTAssertEqual(row["sale_price_krw"] as? Int, 650000)
        XCTAssertEqual(row["resale_listing_price_krw"] as? Int, 700000)
        XCTAssertEqual(row["sold_at"] as? String, "2026-09-14 12:00:00")
        XCTAssertEqual(row["serial_number"] as? String, "FIXTURE-SERIAL")
        XCTAssertEqual(row["purchase_price_krw"] as? Int, 450000)
        XCTAssertEqual(row["current_stage"] as? String, "SOLD")
        XCTAssertEqual(rows.first { ($0["id"] as? Int) == 402 }?["sale_price_krw"] as? Int, 610000)
        try await assertPurchasedAndOtherUserRemain()
    }

    func testSelectedAndAllCompletedDeletionRequireConfirmationAndPreservePurchases() async throws {
        let app = launchTrade()
        let selectedDelete = app.buttons["선택 삭제"]
        scrollTo(selectedDelete, in: app)
        XCTAssertFalse(selectedDelete.isEnabled)

        let completed = historyButton(401, title: "완료 거래 맥북 에어 401", in: app)
        scrollTo(completed, in: app, upward: false)
        completed.tap()
        let deselect = app.buttons["선택 해제"]
        scrollTo(deselect, in: app, upward: false)
        XCTAssertTrue(deselect.exists)
        let markForDeletion = app.buttons["삭제 선택: 완료 거래 맥북 에어 401"]
        scrollTo(markForDeletion, in: app)
        markForDeletion.tap()
        scrollTo(selectedDelete, in: app)
        XCTAssertTrue(selectedDelete.isEnabled)
        selectedDelete.tap()
        let selectedConfirmation = app.alerts["선택한 거래 삭제"]
        XCTAssertTrue(selectedConfirmation.waitForExistence(timeout: 5))
        XCTAssertTrue(selectedConfirmation.staticTexts["선택한 완료 거래 1건을 삭제합니다. 되돌릴 수 없습니다."].exists)
        var deletions = try await deleteEvents()
        XCTAssertEqual(deletions.count, 0)
        attachScreenshot(app, name: "완료 거래 선택 삭제 확인")
        selectedConfirmation.buttons["취소"].tap()
        XCTAssertTrue(selectedConfirmation.waitForNonExistence(timeout: 5))
        _ = try await assertHistoryIDs([401, 402], collection: "completed")
        deletions = try await deleteEvents()
        XCTAssertEqual(deletions.count, 0)

        selectedDelete.tap()
        XCTAssertTrue(selectedConfirmation.waitForExistence(timeout: 5))
        selectedConfirmation.buttons["삭제"].tap()
        var events = try await waitForHistoryRefresh(after: "/\(journeysPath)/completed/delete-selected")
        let selectedDeletes = events.filter { ($0["path"] as? String) == "/\(journeysPath)/completed/delete-selected" }
        XCTAssertEqual(selectedDeletes.count, 1)
        let selectedRequest = try XCTUnwrap(selectedDeletes.first)
        XCTAssertEqual(selectedRequest["method"] as? String, "PATCH")
        let selectedBody = try XCTUnwrap(selectedRequest["body"] as? [String: Any])
        XCTAssertEqual(selectedBody["journey_ids"] as? [Int], [401])
        XCTAssertFalse(app.buttons["선택 해제"].exists,
                       "Deleting the journey currently open in the editor must clear that selection.")
        XCTAssertFalse(completed.exists)
        let remaining = historyButton(402, title: "완료 거래 맥북 에어 402", in: app)
        scrollTo(remaining, in: app)
        XCTAssertTrue(remaining.exists)
        XCTAssertFalse(selectedDelete.isEnabled)
        _ = try await assertHistoryIDs([402], collection: "completed")
        try await assertPurchasedAndOtherUserRemain()

        let allDelete = app.buttons["전체 삭제"]
        scrollTo(allDelete, in: app)
        allDelete.tap()
        let allConfirmation = app.alerts["완료된 거래 전체 삭제"]
        XCTAssertTrue(allConfirmation.waitForExistence(timeout: 5))
        XCTAssertTrue(allConfirmation.staticTexts["서버에 저장된 완료 거래 전체를 삭제합니다. 되돌릴 수 없습니다. 구매 중인 거래는 유지됩니다."].exists)
        deletions = try await deleteEvents()
        XCTAssertFalse(deletions.contains { ($0["path"] as? String)?.hasSuffix("delete-all") == true })
        attachScreenshot(app, name: "완료 거래 전체 삭제 확인")
        allConfirmation.buttons["취소"].tap()
        XCTAssertTrue(allConfirmation.waitForNonExistence(timeout: 5))
        _ = try await assertHistoryIDs([402], collection: "completed")
        deletions = try await deleteEvents()
        XCTAssertFalse(deletions.contains { ($0["path"] as? String)?.hasSuffix("delete-all") == true })

        allDelete.tap()
        XCTAssertTrue(allConfirmation.waitForExistence(timeout: 5))
        allConfirmation.buttons["삭제"].tap()
        events = try await waitForHistoryRefresh(after: "/\(journeysPath)/completed/delete-all")
        let allDeletes = events.filter { ($0["path"] as? String) == "/\(journeysPath)/completed/delete-all" }
        XCTAssertEqual(allDeletes.count, 1)
        let allRequest = try XCTUnwrap(allDeletes.first)
        XCTAssertEqual(allRequest["method"] as? String, "PATCH")
        XCTAssertTrue((allRequest["body"] as? [String: Any] ?? [:]).isEmpty,
                      "All completed deletion is user scoped and must not be limited to visible IDs.")
        XCTAssertTrue(app.staticTexts["완료된 거래가 없습니다."].waitForExistence(timeout: 10))
        XCTAssertFalse(remaining.exists)
        XCTAssertFalse(allDelete.isEnabled)
        XCTAssertFalse(selectedDelete.isEnabled)
        let keep = historyButton(403, title: "보유 거래 맥북 에어 403", in: app)
        scrollTo(keep, in: app)
        XCTAssertTrue(keep.label.contains("보유(KEEP)"))
        attachScreenshot(app, name: "완료 거래 전체 삭제 후 구매와 KEEP 유지")
        _ = try await assertHistoryIDs([], collection: "completed")
        try await assertPurchasedAndOtherUserRemain()
    }

    private func launchTrade() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", user]
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["거래 입력"].waitForExistence(timeout: 10))
        app.tabBars.buttons["거래 입력"].tap()
        XCTAssertTrue(app.navigationBars["거래 기록"].waitForExistence(timeout: 10))
        return app
    }

    private func historyButton(_ id: Int, title: String, in app: XCUIApplication) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label CONTAINS %@ AND label CONTAINS %@", title, "#\(id) ·")).firstMatch
    }

    private func scrollTo(_ element: XCUIElement, in app: XCUIApplication, upward: Bool = true,
                          file: StaticString = #filePath, line: UInt = #line) {
        dismissKeyboard(in: app)
        for _ in 0..<24 {
            var moveUp = upward
            if element.exists {
                let top = app.navigationBars.firstMatch.frame.maxY + 12
                let bottom = app.tabBars.firstMatch.frame.minY - 12
                let frame = element.frame
                if element.isHittable && frame.minY >= top && frame.maxY <= bottom { return }
                if frame.minY < top { moveUp = false }
                else if frame.maxY > bottom { moveUp = true }
            }
            let from = app.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: moveUp ? 0.70 : 0.35))
            let to = app.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: moveUp ? 0.35 : 0.70))
            from.press(forDuration: 0.05, thenDragTo: to)
        }
        XCTFail("거래 화면 요소를 찾지 못했습니다: \(element)", file: file, line: line)
    }

    private func replaceText(_ text: String, original: String, in field: XCUIElement,
                             app: XCUIApplication) throws {
        field.tap()
        guard app.keyboards.firstMatch.waitForExistence(timeout: 5) else {
            attachScreenshot(app, name: "완료 거래 입력 포커스 실패")
            XCTFail("Tapping the resale field must focus it and show the keyboard.")
            throw URLError(.cannotLoadFromNetwork)
        }
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: original.count) + text)
        dismissKeyboard(in: app)
        XCTAssertEqual(field.value as? String, text)
    }

    private func dismissKeyboard(in app: XCUIApplication) {
        let done = app.buttons["trade.keyboard.done"]
        if done.exists && done.isHittable { done.tap() }
    }

    private func waitForHistoryRefresh(after path: String) async throws -> [[String: Any]] {
        for _ in 0..<60 {
            let events = try await fixtureEvents()
            if let mutation = events.lastIndex(where: { ($0["path"] as? String) == path && ($0["method"] as? String) == "PATCH" }) {
                let following = events.dropFirst(mutation + 1)
                let refreshed = ["completed", "purchased"].allSatisfy { collection in
                    following.contains { event in
                        (event["method"] as? String) == "GET"
                            && (event["path"] as? String) == "/\(journeysPath)/\(collection)"
                            && (event["query"] as? [String: [String]])?["limit"] == ["200"]
                    }
                }
                if refreshed { return events }
            }
            try await Task.sleep(for: .milliseconds(200))
        }
        XCTFail("The mutation must be followed by the app refreshing both history lists with limit=200: \(path)")
        throw URLError(.timedOut)
    }

    private func assertHistoryIDs(_ ids: [Int], collection: String,
                                  for userID: String = "parity-fixture-user") async throws -> [[String: Any]] {
        let response = try await fixture("users/\(userID)/resale-trade-journeys/\(collection)")
        let rows = try XCTUnwrap(response["items"] as? [[String: Any]])
        XCTAssertEqual(Set(rows.compactMap { $0["id"] as? Int }), Set(ids))
        return rows
    }

    private func assertPurchasedAndOtherUserRemain() async throws {
        let purchased = try await assertHistoryIDs([403, 404], collection: "purchased")
        XCTAssertEqual(purchased.first { ($0["id"] as? Int) == 403 }?["current_stage"] as? String, "KEEP")
        XCTAssertEqual(purchased.first { ($0["id"] as? Int) == 404 }?["current_stage"] as? String, "INSPECTED")
        _ = try await assertHistoryIDs([490], collection: "completed", for: "other-fixture-user")
        _ = try await assertHistoryIDs([491], collection: "purchased", for: "other-fixture-user")
    }

    private func fixtureEvents() async throws -> [[String: Any]] {
        let response = try await fixture("__events")
        return try XCTUnwrap(response["events"] as? [[String: Any]])
    }

    private func deleteEvents() async throws -> [[String: Any]] {
        try await fixtureEvents().filter { ($0["path"] as? String)?.contains("/completed/delete-") == true }
    }

    private func fixture(_ path: String, method: String = "GET") async throws -> [String: Any] {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = 3
        let (data, response) = try await URLSession.shared.data(for: request)
        XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        if let ok = json["ok"] as? Bool { XCTAssertTrue(ok) }
        return json
    }

    private func attachScreenshot(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
