import XCTest

/// Uses a local HTML listing and the dedicated Simulator's clipboard only.
@MainActor
final class ExternalLinkUITests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:18765")!
    private let listingURL = "http://127.0.0.1:18765/__listing/101"
    private let listingHeading = "UMTP Local Listing 101"

    func testProductURLCopyOpensSafariAndReturnsToUnreadDetail() async throws {
        continueAfterFailure = false
        do { _ = try await fixture("__reset", method: "POST") }
        catch { throw XCTSkip("Start TestsSupport/parity_server.py before running external-link UI tests.") }
        let simulator = try await fixture("__push-status")
        guard simulator["configured"] as? Bool == true else {
            throw XCTSkip("Set UMTP_SIMULATOR_ID to the dedicated test Simulator to verify its clipboard.")
        }
        let setup = try await fixture("__external-link-fixture", method: "POST")
        guard setup["product_url"] as? String == listingURL else {
            XCTFail("The test must use the loopback listing URL before opening any browser.")
            return
        }

        let app = XCUIApplication()
        app.launchEnvironment["UMTP_TEST_BASE_URL"] = baseURL.absoluteString
        app.launchArguments = ["-umtp_user_id", "parity-fixture-user"]
        app.launch()
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 10))

        let copy = app.buttons["URL 복사"].firstMatch
        scrollTo(copy, in: app)
        XCTAssertTrue(copy.isHittable)
        copy.tap()
        XCTAssertTrue(app.staticTexts["URL을 복사했어요."].waitForExistence(timeout: 5))
        let clipboard = try await fixture("__clipboard")
        guard clipboard["text"] as? String == listingURL else {
            XCTFail("URL 복사 must write the exact loopback product URL to the Simulator clipboard.")
            return
        }
        attach(app.screenshot(), named: "매물 URL 복사 및 Simulator 클립보드 확인")

        let details = app.buttons["상세 보기"].firstMatch
        scrollTo(details, in: app)
        details.tap()
        XCTAssertTrue(app.navigationBars["거래 알림 상세"].waitForExistence(timeout: 5))
        let openListing = app.buttons["매물 보러가기"]
        scrollTo(openListing, in: app)
        XCTAssertTrue(openListing.isEnabled && openListing.isHittable)

        let safari = XCUIApplication(bundleIdentifier: "com.apple.mobilesafari")
        openListing.tap()
        XCTAssertTrue(safari.wait(for: .runningForeground, timeout: 10),
                      "Opening a product must bring the external browser to the foreground.")
        let background = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            app.state == .runningBackground || app.state == .runningBackgroundSuspended
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [background], timeout: 10), .completed,
                       "UMTP must move to the background while Safari displays the listing.")
        // Safari's start-page content can remain visible while its first web
        // process loads. Wait for the requested page without tapping unrelated UI.
        let heading = safari.webViews.staticTexts[listingHeading].firstMatch
        let loaded = heading.waitForExistence(timeout: 15)
        if !loaded {
            attach(safari.screenshot(), named: "Safari 매물 페이지 표시 실패")
            let hierarchy = XCTAttachment(string: safari.debugDescription)
            hierarchy.name = "Safari 매물 페이지 표시 실패 접근성 구조"
            hierarchy.lifetime = .keepAlways
            add(hierarchy)
        }
        XCTAssertTrue(loaded,
                      "Safari must render the actual local listing, not only open a browser window.")
        attach(safari.screenshot(), named: "Safari에서 로컬 매물 페이지 열기")

        let browserEvents = try await fixtureEvents()
        XCTAssertTrue(browserEvents.contains {
            ($0["method"] as? String) == "GET" && ($0["path"] as? String) == "/__listing/101"
        }, "The fixture must receive Safari's listing request.")
        let refreshesBeforeReturn = browserEvents.filter { ($0["path"] as? String) == "/alerts" }.count

        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        XCTAssertTrue(app.navigationBars["거래 알림 상세"].waitForExistence(timeout: 5),
                      "Returning from Safari must preserve the alert detail screen.")
        let events = try await waitForFeedRefresh(after: refreshesBeforeReturn)
        XCTAssertFalse(events.contains {
            ["/alert-events/101/read", "/alert-events/read-all"].contains($0["path"] as? String ?? "")
        }, "Copying/opening a product URL and returning must not mark the alert reviewed.")
        attach(app.screenshot(), named: "Safari에서 돌아온 뒤 알림 상세 유지")

        app.buttons["목록으로"].tap()
        XCTAssertTrue(app.navigationBars["거래 알림 피드"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["alert.card.101"].firstMatch.waitForExistence(timeout: 5),
                      "The same alert must remain in the unread feed after the browser round trip.")
    }

    private func scrollTo(_ element: XCUIElement, in app: XCUIApplication) {
        for _ in 0..<25 {
            if element.exists && element.isHittable { return }
            app.swipeUp()
        }
    }

    private func attach(_ screenshot: XCUIScreenshot, named name: String) {
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func waitForFeedRefresh(after count: Int) async throws -> [[String: Any]] {
        for _ in 0..<30 {
            let events = try await fixtureEvents()
            if events.filter({ ($0["path"] as? String) == "/alerts" }).count > count { return events }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        XCTFail("Returning from Safari must refresh the unread feed.")
        throw URLError(.timedOut)
    }

    private func fixtureEvents() async throws -> [[String: Any]] {
        let result = try await fixture("__events")
        return result["events"] as? [[String: Any]] ?? []
    }

    private func fixture(_ path: String, method: String = "GET") async throws -> [String: Any] {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.timeoutInterval = path == "__clipboard" ? 15 : 3
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    }
}
