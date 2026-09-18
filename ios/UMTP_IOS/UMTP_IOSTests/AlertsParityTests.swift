import XCTest
@testable import UMTP_IOS

private final class AlertsURLProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var handler: ((URLRequest) throws -> (Int, Data))?
    nonisolated override class func canInit(with request: URLRequest) -> Bool { true }
    nonisolated override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    nonisolated override func startLoading() {
        do {
            let (status, data) = try Self.handler!(request)
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch { client?.urlProtocol(self, didFailWithError: error) }
    }
    nonisolated override func stopLoading() {}
}

@MainActor
final class AlertsParityTests: XCTestCase {
    func testMacStudioAlertDisplaysHighCapacitySpecificationWithoutZeroInches() throws {
        let data = Data(#"{"id":101,"product_type":"Mac Studio","chip":"M3 Ultra","screen_inch":0,"ram_gb":512,"ssd_gb":16384}"#.utf8)
        let alert = try JSONDecoder().decode(AlertItem.self, from: data)
        XCTAssertEqual(alert.displaySpec, "Mac Studio · M3 Ultra · 512GB · 16,384GB SSD")
        let rows = Dictionary(uniqueKeysWithValues: alert.detailRows(archive: false))
        XCTAssertEqual(rows["제품 분류"], "Mac Studio")
        XCTAssertEqual(rows["칩"], "M3 Ultra")
        XCTAssertFalse(alert.displaySpec.contains("0인치"))
    }

    func testMacBookProAlertDisplaysCompleteSiliconSpecification() throws {
        let data = Data(#"{"id":101,"product_type":"MacBook Pro","chip":"M5 Max","screen_inch":16,"ram_gb":128,"ssd_gb":8192}"#.utf8)
        let alert = try JSONDecoder().decode(AlertItem.self, from: data)
        XCTAssertEqual(alert.displaySpec, "MacBook Pro · M5 Max · 16인치 · 128GB · 8,192GB SSD")
        let rows = Dictionary(uniqueKeysWithValues: alert.detailRows(archive: false))
        XCTAssertEqual(rows["제품 분류"], "MacBook Pro")
        XCTAssertEqual(rows["칩"], "M5 Max")
    }

    private func api() -> AlertsAPI {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [AlertsURLProtocol.self]
        return AlertsAPI(client: APIClient(baseURLString: "https://alerts.invalid/", session: URLSession(configuration: config)))
    }

    func testNullableSnakeCaseAndFlexibleBooleanContract() throws {
        let json = #"""
        {"ok":"yes","items":[{"id":9007199254740993,"alert_event_id":"123","title":null,
          "message":" 대체 제목 ","created_at":"2026-09-15T00:00:00","listing_price_krw":"1250000",
          "fraud_probability":0.65,"is_alert_target":"0","is_read":1,
          "trade_type_flags":{"is_exchange":"on","is_free":0,"is_suspicious":null},
          "fraud_probability_v1":"0.25","fraud_probability_v2":0.3,"fraud_probability_v3":0.65}]}
        """#
        let result = try JSONDecoder().decode(AlertsResponse.self, from: Data(json.utf8))
        let alert = try XCTUnwrap(result.items.first)
        XCTAssertEqual(alert.id, 9_007_199_254_740_993)
        XCTAssertEqual(alert.eventID, 123)
        XCTAssertEqual(alert.listing_price_krw, 1_250_000)
        XCTAssertEqual(alert.displayTitle, "대체 제목")
        XCTAssertEqual(alert.displayFraud, "높음 (65%)")
        XCTAssertTrue(alert.isCandidateNotice)
        XCTAssertEqual(alert.displayTradeFlags, "교환")
        XCTAssertEqual(alert.detailRows(archive: false).filter { $0.0.hasPrefix("사기 가능성 V") }.count, 3)
    }

    func testMissingOrFailedSuccessAndInvalidBooleanAreRejected() {
        for json in [#"{}"#, #"{"ok":false}"#, #"{"ok":2}"#] {
            XCTAssertThrowsError(try JSONDecoder().decode(AlertMutationResponse.self, from: Data(json.utf8)))
        }
        XCTAssertThrowsError(try JSONDecoder().decode(AlertItem.self, from: Data(#"{"id":1,"is_read":"sometimes"}"#.utf8)))
        XCTAssertThrowsError(try JSONDecoder().decode(AlertItem.self, from: Data(#"{"id":1.5}"#.utf8)))
    }

    func testDisplayFallbacksContentChangeAndUnsafeLinks() {
        var alert = AlertItem(id: 1)
        alert.trigger_reason = "price_changed"
        alert.alert_condition_label = "내용 변경 알림"
        alert.alert_price_direction = "ABOVE_OR_EQUAL"
        alert.fair_price_krw = 1_000_000
        alert.alert_target_price_krw = 900_000
        alert.body_excerpt = "본문 요약"
        alert.used_refresh_info = true
        alert.product_url = "javascript:alert(1)"
        XCTAssertEqual(alert.displayTitle, "제목 없음")
        XCTAssertEqual(alert.displayType, "내용 변경 알림")
        XCTAssertEqual(alert.displayCondition, "이 가격 이상이면 알림")
        XCTAssertEqual(alert.displayPreview, "끌올된 정보를 사용한 알림입니다\n본문 요약")
        XCTAssertEqual(alert.displayBody, "본문 요약")
        XCTAssertNil(alert.resolvedURL)
        XCTAssertEqual(AlertDisplay.krw(1_200_000.9), "1,200,000원")
        XCTAssertEqual(AlertDisplay.percent(-12.345), "-12.35%")
        alert.fraud_probability = 0.249
        XCTAssertEqual(alert.displayFraudLabel, "낮음")
        alert.fraud_probability = 0.25
        XCTAssertEqual(alert.displayFraudLabel, "주의")
        alert.formatted_fraud_probability_label = "위험"
        XCTAssertEqual(alert.displayFraudLabel, "위험")
    }

    func testReadFallbackOnlyForUnsupportedMethods() async throws {
        for fallbackCode in [404, 405, 501] {
            nonisolated(unsafe) var methods: [String] = []
            AlertsURLProtocol.handler = { request in
                methods.append(request.httpMethod!)
                XCTAssertEqual(request.url?.path, "/alert-events/42/read")
                XCTAssertEqual(URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems,
                               [URLQueryItem(name: "user_id", value: "한글 & id")])
                return request.httpMethod == "PATCH"
                    ? (fallbackCode, Data()) : (200, Data(#"{"ok":true,"is_read":true}"#.utf8))
            }
            try await api().markRead(id: 42, userID: "한글 & id")
            XCTAssertEqual(methods, ["PATCH", "POST"])
        }
        nonisolated(unsafe) var requests = 0
        AlertsURLProtocol.handler = { _ in requests += 1; return (500, Data()) }
        do { try await api().markRead(id: 42, userID: "user"); XCTFail("Expected HTTP error") }
        catch { XCTAssertEqual(requests, 1) }
    }

    func testFeedQueryAndStableDescendingOrder() async throws {
        AlertsURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/alerts")
            let query = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
            XCTAssertTrue(query.contains(URLQueryItem(name: "is_read", value: "0")))
            return (200, Data(#"{"ok":true,"items":[{"id":1,"created_at":"2026-09-01"},{"id":3,"created_at":"2026-09-15"},{"id":2,"created_at":"2026-09-15"},{"id":4}]}"#.utf8))
        }
        let items = try await api().alerts(userID: "user")
        XCTAssertEqual(items.map(\.id), [3, 2, 1, 4])
    }

    func testClearSelectedSendsOnlyPositiveDistinctAlertIDsAndCounts() async throws {
        AlertsURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(request.url?.path, "/alert-events/read/archive/clear-selected")
            var data = request.httpBody
            if data == nil, let stream = request.httpBodyStream {
                stream.open()
                defer { stream.close() }
                var bytes: [UInt8] = []
                let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 512)
                defer { buffer.deallocate() }
                while stream.hasBytesAvailable {
                    let count = stream.read(buffer, maxLength: 512)
                    if count <= 0 { break }
                    bytes.append(contentsOf: UnsafeBufferPointer(start: buffer, count: count))
                }
                data = Data(bytes)
            }
            let body = try JSONSerialization.jsonObject(with: XCTUnwrap(data)) as? [String: [Int]]
            XCTAssertEqual(body?["alert_event_ids"], [5, 8])
            return (200, Data(#"{"ok":1,"cleared_count":1,"skipped_count":1,"not_found_ids":[8]}"#.utf8))
        }
        let response = try await api().clearArchive(userID: "user", ids: [0, -1, 5, 8])
        XCTAssertEqual(response.cleared_count, 1)
        XCTAssertEqual(response.skipped_count, 1)
        XCTAssertEqual(response.not_found_ids, [8])
    }

    func testPartialReadKeepsFailedItemsAndFailureMessage() async {
        let mock = AlertsAPIMock()
        mock.items = [AlertItem(id: 1), AlertItem(id: 2)]
        mock.failReadIDs = [2]
        let model = AlertFeedViewModel(api: mock)
        model.configure(userID: "user")
        await model.refresh()
        let successful = await model.markSelectedRead([1, 2])
        XCTAssertEqual(successful, [1])
        XCTAssertEqual(model.alerts.map(\.id), [2])
        XCTAssertTrue(model.message?.contains("1건 실패") == true)
        XCTAssertFalse(model.isMutating)
        mock.failReadIDs = []
        let retry = await model.markRead(2)
        XCTAssertTrue(retry)
        XCTAssertTrue(model.alerts.isEmpty)
    }

    func testRefreshFailureKeepsVisibleData() async {
        let mock = AlertsAPIMock()
        mock.items = [AlertItem(id: 1)]
        let model = AlertFeedViewModel(api: mock)
        model.configure(userID: "user")
        await model.refresh()
        mock.failFetch = true
        await model.refresh()
        XCTAssertEqual(model.alerts.map(\.id), [1])
        XCTAssertNotNil(model.errorMessage)
        XCTAssertFalse(model.isRefreshing)
    }

    func testPreviousAccountResponseCannotOverwriteNewSession() async {
        let mock = AlertsAPIMock()
        var continuation: CheckedContinuation<[AlertItem], Error>?
        let started = expectation(description: "Previous account request")
        mock.fetch = { account in
            if account == "old" {
                return try await withCheckedThrowingContinuation {
                    continuation = $0
                    started.fulfill()
                }
            }
            return [AlertItem(id: 2)]
        }
        let model = AlertFeedViewModel(api: mock)
        model.configure(userID: "old")
        let oldRequest = Task { await model.refresh() }
        await fulfillment(of: [started], timeout: 1)
        model.configure(userID: "new")
        await model.refresh()
        continuation?.resume(returning: [AlertItem(id: 1)])
        await oldRequest.value
        XCTAssertEqual(model.alerts.map(\.id), [2])
        XCTAssertFalse(model.isRefreshing)
    }

    func testArchiveGroupSortMatchesAndroid() {
        let groups: [String: [String: [AlertItem]]] = ["기타": [:], "M4": [:], "M1": [:], "M2 PRO": [:]]
        XCTAssertEqual(AlertFeedViewModel.sortedChips(groups.keys), ["M1", "M4", "M2 PRO", "기타"])
        let screens: [String: [AlertItem]] = ["기타": [], "15": [], "13": [], "unknown": []]
        XCTAssertEqual(AlertFeedViewModel.sortedScreens(screens.keys), ["13", "15", "unknown", "기타"])
    }

    func testArchiveClearUsesOriginalAlertIDWhileTradeKeepsArchiveID() async {
        var archived = AlertItem(id: 1101)
        archived.alert_event_id = 101
        archived.read_archive_event_id = 1101
        let mock = AlertsAPIMock()
        mock.archiveGroups = ["M1": ["13": [archived]]]
        let model = AlertFeedViewModel(api: mock)
        model.configure(userID: "user")
        await model.refreshArchive()
        XCTAssertEqual(model.visibleArchiveIDs, [101])
        XCTAssertEqual(archived.archiveIdentity, 1101)
        let success = await model.clearArchive(ids: model.visibleArchiveIDs)
        XCTAssertTrue(success)
        XCTAssertEqual(mock.clearedIDs, [101])
    }

    func testPollingStopsWhenScreenLeaves() async throws {
        let polling = AlertPollingService(intervalNanoseconds: 1_000_000)
        var count = 0
        polling.start { count += 1 }
        try await Task.sleep(nanoseconds: 10_000_000)
        XCTAssertGreaterThan(count, 0)
        polling.stop()
        let stoppedAt = count
        try await Task.sleep(nanoseconds: 5_000_000)
        XCTAssertFalse(polling.isRunning)
        XCTAssertEqual(count, stoppedAt)
    }

}

@MainActor
private final class AlertsAPIMock: AlertsAPIProtocol {
    var items: [AlertItem] = []
    var failReadIDs: Set<Int> = []
    var failFetch = false
    var archiveGroups: [String: [String: [AlertItem]]] = [:]
    var clearedIDs: Set<Int>?
    var fetch: ((String) async throws -> [AlertItem])?

    func alerts(userID: String) async throws -> [AlertItem] {
        if let fetch { return try await fetch(userID) }
        if failFetch { throw APIClientError.network(URLError(.notConnectedToInternet)) }
        return items
    }
    func archive(userID: String) async throws -> [String: [String: [AlertItem]]] { archiveGroups }
    func markRead(id: Int, userID: String) async throws {
        if failReadIDs.contains(id) { throw APIClientError.httpStatus(500) }
        items.removeAll { $0.eventID == id }
    }
    func markAllRead(userID: String) async throws -> AlertMutationResponse {
        items = []
        return try JSONDecoder().decode(AlertMutationResponse.self, from: Data(#"{"ok":true,"updated_count":1}"#.utf8))
    }
    func clearArchive(userID: String, ids: Set<Int>?) async throws -> AlertMutationResponse {
        clearedIDs = ids
        return try JSONDecoder().decode(AlertMutationResponse.self, from: Data(#"{"ok":true,"cleared_count":1}"#.utf8))
    }
}
