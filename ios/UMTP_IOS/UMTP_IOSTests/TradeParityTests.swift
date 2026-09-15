import XCTest
@testable import UMTP_IOS

@MainActor
final class TradeParityTests: XCTestCase {
    private func response(_ json: String) throws -> TradeResponse {
        try JSONDecoder().decode(TradeResponse.self, from: Data(json.utf8))
    }

    func testNullablePrefillAndTopLevelIdentity() throws {
        let draft = try response(#"{"ok":true,"existing":false,"id":null,"source":"joongna","product_id":"123","row":{"id":null,"title":"새 매물","activation_lock_off":0,"battery_health_percent":"95"}}"#)
        XCTAssertTrue(draft.ok)
        XCTAssertFalse(draft.existing)
        XCTAssertNil(draft.row?.id)
        XCTAssertEqual(draft.row?["product_id"], "123")
        XCTAssertEqual(draft.row?.values["activation_lock_off"]?.boolValue, false)
        XCTAssertEqual(draft.row?.values["battery_health_percent"]?.integer, 95)
        let existing = try response(#"{"ok":"yes","trade_journey_id":18,"row":{"id":null}}"#)
        XCTAssertEqual(existing.row?.id, 18)
        let largeID = try response(#"{"ok":true,"row":{"id":9007199254740993}}"#)
        XCTAssertEqual(largeID.row?.id, 9007199254740993)
    }

    func testImageFormatsAndUnsafeSchemes() throws {
        let object = try JSONDecoder().decode(TradeValue.self, from: Data(#"{"images":[{"url":"https://example.com/image.jpg"},"javascript:bad"]}"#.utf8))
        XCTAssertEqual(object.imageURLs.map(\.absoluteString), ["https://example.com/image.jpg"])
        XCTAssertEqual(TradeValue.string(#"["https://example.com/a.png"]"#).imageURLs.count, 1)
        XCTAssertTrue(TradeValue.string("file:///private/data").imageURLs.isEmpty)
    }

    func testKnownImageFieldsTakePriorityOverListingAndThumbnailURLs() throws {
        let object = try JSONDecoder().decode(TradeValue.self, from: Data(#"{"click_url":"https://example.com/listing/1","thumbnail_url":"https://example.com/thumb.jpg","image_url":"https://example.com/full.jpg"}"#.utf8))
        XCTAssertEqual(object.imageURLs.map(\.absoluteString), ["https://example.com/full.jpg"])
        let thumbnail = try JSONDecoder().decode(TradeValue.self, from: Data(#"{"click_url":"https://example.com/listing/1","image_url":null,"thumbnailUrl":"https://example.com/thumb.jpg"}"#.utf8))
        XCTAssertEqual(thumbnail.imageURLs.map(\.absoluteString), ["https://example.com/thumb.jpg"])
    }

    func testSparseChangesPreserveBlankAndUnchangedFields() throws {
        let baseline = ResaleTradeRow(values: ["purchase_price_krw": .number(200000), "seller_location": .string("서울"), "activation_lock_off": .number(0)])
        let changes = try TradeField.changes(fields: TradeField.purchase + TradeField.verification, inputs: ["purchase_price_krw": "200,000", "seller_location": "", "activation_lock_off": "false", "transport_cost_krw": "0"], baseline: baseline)
        XCTAssertEqual(changes, ["transport_cost_krw": .number(0)])
    }

    func testInvalidMoneyAndDatesAreNotSilentlyDropped() {
        XCTAssertThrowsError(try TradeField.parse("purchase_price_krw", text: "12.5"))
        XCTAssertThrowsError(try TradeField.parse("purchase_price_krw", text: "abc"))
        XCTAssertThrowsError(try TradeField.parse("battery_health_percent", text: "101"))
        XCTAssertThrowsError(try TradeField.parse("purchased_at", text: "2026-02-30 14:20"))
        XCTAssertNoThrow(try TradeField.parse("purchased_at", text: "2026-09-15 14:20"))
        XCTAssertNoThrow(try TradeField.parse("purchased_at", text: "2026-09-15T14:20:00+09:00"))
        XCTAssertThrowsError(try TradeField.parse("resale_url", text: "javascript:alert(1)"))
        XCTAssertThrowsError(try TradeField.parse("current_stage", text: "OTHER"))
    }

    func testResaleURLRequiresOneAbsoluteHTTPAddress() throws {
        for value in ["https://example.com/listing/123?item=1#photos", "http://example.com/a", "HTTPS://example.com/a"] {
            XCTAssertEqual(try TradeField.parse("resale_url", text: " \(value)\n"), .string(value))
        }
        for value in [#"["https://example.com/a"]"#, #"{"url":"https://example.com/a"}"#,
                      #""https://example.com/a""#, "//example.com/a", "/listing/123", "https:",
                      "https:///listing/123", "https://", "file:///private/data", "javascript:alert(1)",
                      "ftp://example.com/a", "https://example.com/a https://example.com/b",
                      "https://example.com/\nlisting/123"] {
            XCTAssertThrowsError(try TradeField.parse("resale_url", text: value), value)
        }
        XCTAssertNil(try TradeField.parse("resale_url", text: " \n"))
    }

    func testCurrentTimeEntryCarriesExplicitUTCOffset() {
        let value = ResaleTradeViewModel.timestampForEntry(Date(timeIntervalSince1970: 0))
        XCTAssertEqual(value, "1970-01-01T00:00:00Z")
        XCTAssertEqual(ISO8601DateFormatter().date(from: value), Date(timeIntervalSince1970: 0))
        XCTAssertNoThrow(try TradeField.parse("purchased_at", text: value))
    }

    func testServerSupportedDateOnlyAndISOTimeZoneInputs() {
        for value in ["2026-09-15", "2024-02-29", "2026-09-15T14:20",
                      "2026-09-15T14:20:00Z", "2026-09-15T14:20:00+09:00",
                      "2026-09-15T14:20:00+0900", "2026-09-15T14:20:00.123456Z"] {
            XCTAssertTrue(TradeField.validDate(value), "Expected server-compatible datetime: \(value)")
        }
        for value in ["2026-02-29", "2026-02-30", "2026-13-15", "2026-09-31",
                      "2026-02-30T14:20:00Z", "2026-09-15T25:20:00Z",
                      "2026-09-15T14:61:00Z", "2026-09-15T14:20:60Z"] {
            XCTAssertFalse(TradeField.validDate(value), "Impossible date must remain invalid: \(value)")
        }
    }

    func testSpaceSeparatedOffsetDatesPreserveValidInputAndRejectImpossibleComponents() throws {
        for value in ["2026-09-15 14:20:00+09:00", "2026-09-15 14:20:00+0900",
                      "2026-09-15 14:20:00Z", "2024-02-29 14:20:00.123456+09:00"] {
            XCTAssertEqual(try TradeField.parse("purchased_at", text: value), .string(value))
            XCTAssertEqual(try TradeField.parse("sold_at", text: value), .string(value))
        }
        for value in ["2026-02-30 14:20:00+09:00", "2026-02-29 14:20:00.123456Z",
                      "2026-09-15 25:20:00+09:00", "2026-09-15 14:61:00+0900",
                      "2026-09-15 14:20:60Z"] {
            XCTAssertThrowsError(try TradeField.parse("purchased_at", text: value), value)
        }
    }

    @MainActor
    func testMissingStartRowKeepsSelectedRecordAndInput() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true}"#))
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.select(ResaleTradeRow(values: ["id": .number(42), "title": .string("기존")]))
        model.inputs["title"] = "입력 유지"
        model.reference = "123"
        await model.start()
        XCTAssertEqual(model.selected?.id, 42)
        XCTAssertEqual(model.inputs["title"], "입력 유지")
        XCTAssertNotNil(model.errorMessage)
    }

    func testFailedArchiveStartRetriesOriginalIdentityWithoutReference() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{"id":7,"product_id":"123"}}"#))
        api.startFailures = 1
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.reference = "old-reference"
        await model.start(alertId: 1101, fromArchive: true)
        XCTAssertTrue(model.canRetryStart)
        XCTAssertTrue(model.reference.isEmpty)
        await model.start()
        XCTAssertEqual(api.startedAlertIDs, [1101, 1101])
        XCTAssertEqual(api.startedFromArchive, [true, true])
        XCTAssertEqual(model.selected?.id, 7)
        XCTAssertFalse(model.canRetryStart)
    }

    func testExplicitAlertRouteOverridesPreviousManualReference() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{"id":7,"product_id":"123"}}"#))
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.reference = "previous-product-id"
        await model.start(alertId: 101)
        XCTAssertEqual(api.startedAlertIDs, [101])
        XCTAssertEqual(api.startedReferences, [nil])
        XCTAssertTrue(model.reference.isEmpty)
    }

    func testManualReferenceOverridesFailedAlertStart() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{"id":8,"product_id":"456"}}"#))
        api.startFailures = 1
        let model = ResaleTradeViewModel(userId: "test", api: api)
        await model.start(alertId: 101)
        model.reference = " 456 "
        await model.start()
        XCTAssertEqual(api.startedAlertIDs, [101, nil])
        XCTAssertEqual(api.startedReferences, [nil, "456"])
        XCTAssertEqual(api.startedFromArchive, [false, false])
        XCTAssertEqual(model.selected?.id, 8)
    }

    @MainActor
    func testNewPrefillSaveAndFailedSaveKeepDraft() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"id":null,"product_id":"123","row":{"title":"매물"}}"#))
        api.saveResults = [try response(#"{"ok":false,"reason":"internal SQL detail"}"#)]
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.reference = "123"
        await model.start()
        model.inputs["purchase_price_krw"] = "100,000"
        await model.save()
        XCTAssertNil(api.savedRows.first?.id)
        XCTAssertEqual(api.savedRows.first?["product_id"], "123")
        XCTAssertEqual(api.savedUpdates.first?["purchase_price_krw"], .number(100000))
        XCTAssertEqual(model.inputs["purchase_price_krw"], "100,000")
        XCTAssertNotNil(model.errorMessage)
        XCTAssertFalse(model.errorMessage?.contains("SQL") ?? true)
    }

    @MainActor
    func testResaleVerificationUsesPurchaseWhitelistAndReportsPartialFailure() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{"id":7,"product_id":"123","activation_lock_off":false}}"#))
        api.saveResults = [try response(#"{"ok":true,"row":{"id":7,"product_id":"123","activation_lock_off":true}}"#), try response(#"{"ok":false,"reason":"db error"}"#)]
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.reference = "123"
        await model.start()
        model.mode = .resale
        model.inputs["activation_lock_off"] = "true"
        model.inputs["sale_price_krw"] = "300000"
        await model.save()
        XCTAssertEqual(api.savedModes, [.purchase, .resale])
        XCTAssertEqual(api.savedUpdates[0], ["activation_lock_off": .bool(true)])
        XCTAssertEqual(api.savedUpdates[1], ["sale_price_krw": .number(300000)])
        XCTAssertEqual(model.selected?.values["activation_lock_off"]?.boolValue, true)
        XCTAssertEqual(model.inputs["sale_price_krw"], "300000")
        XCTAssertEqual(model.errorMessage, TradeError.partialSave.localizedDescription)
    }

    func testResaleVerificationOnlyDoesNotSendEmptyPatchOrChangeStageAndKeepsPurchaseDraft() async throws {
        let original = try response(#"{"ok":true,"row":{"id":7,"product_id":"123","current_stage":"KEEP","sale_price_krw":300000,"sold_at":"2026-09-14","purchase_price_krw":200000,"activation_lock_off":false}}"#)
        let verified = try response(#"{"ok":true,"row":{"id":7,"product_id":"123","current_stage":"KEEP","sale_price_krw":300000,"sold_at":"2026-09-14","purchase_price_krw":200000,"activation_lock_off":true}}"#)
        let api = TradeMockAPI(start: original)
        // The second response models the unwanted server rederivation if a regression
        // sends an empty resale PATCH after the verification has already been saved.
        api.saveResults = [verified, try response(#"{"ok":true,"row":{"id":7,"current_stage":"SOLD","sale_price_krw":300000,"activation_lock_off":true}}"#)]
        api.purchasedResult = try response(#"{"ok":true,"items":[{"id":7,"current_stage":"KEEP"}]}"#)
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.select(try XCTUnwrap(original.row))
        model.mode = .resale
        model.inputs["activation_lock_off"] = "true"
        model.inputs["purchase_price_krw"] = "210000"

        await model.save()

        XCTAssertEqual(api.savedModes, [.purchase])
        XCTAssertEqual(api.savedUpdates, [["activation_lock_off": .bool(true), "current_stage": .string("KEEP")]])
        XCTAssertEqual(model.selected?.id, 7)
        XCTAssertEqual(model.selected?["current_stage"], "KEEP")
        XCTAssertEqual(model.selected?.values["activation_lock_off"]?.boolValue, true)
        XCTAssertEqual(model.selected?["purchase_price_krw"], "200000")
        XCTAssertEqual(model.inputs["purchase_price_krw"], "210000")
        XCTAssertEqual(model.inputs["sale_price_krw"], "300000")
        XCTAssertTrue(model.hasUnsavedChanges)
        XCTAssertEqual(model.purchased.first?.id, 7)
        XCTAssertEqual(model.message, "되팔이 후 입력이 저장되었습니다.")
        XCTAssertNil(model.errorMessage)
        XCTAssertFalse(model.isBusy)
    }

    func testExplicitEmptyResaleSaveStillUsesResaleEndpointWhenVerificationIsUnchanged() async throws {
        let original = try response(#"{"ok":true,"row":{"id":7,"product_id":"123","current_stage":"KEEP","sale_price_krw":300000,"activation_lock_off":true}}"#)
        let api = TradeMockAPI(start: original)
        api.saveResults = [try response(#"{"ok":true,"row":{"id":7,"product_id":"123","current_stage":"SOLD","sale_price_krw":300000,"activation_lock_off":true}}"#)]
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.select(try XCTUnwrap(original.row))
        model.mode = .resale

        await model.save()

        XCTAssertEqual(api.savedModes, [.resale])
        XCTAssertEqual(api.savedUpdates, [[:]])
        XCTAssertEqual(model.selected?["current_stage"], "SOLD")
        XCTAssertFalse(model.hasUnsavedChanges)
        XCTAssertEqual(model.message, "되팔이 후 입력이 저장되었습니다.")
        XCTAssertNil(model.errorMessage)
    }

    @MainActor
    func testHistoryFailuresAreIndependentAndSelectionDeleteIsScoped() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{}}"#))
        api.completedResult = try response(#"{"ok":false,"reason":"not_found"}"#)
        api.purchasedResult = try response(#"{"ok":true,"items":[{"id":8,"current_stage":"KEEP"}]}"#)
        let model = ResaleTradeViewModel(userId: "test", api: api)
        await model.loadHistory()
        XCTAssertNotNil(model.completedError)
        XCTAssertEqual(model.purchased.first?.id, 8)
        api.completedResult = try response(#"{"ok":true,"items":[{"id":7,"current_stage":"SOLD"}]}"#)
        await model.loadHistory()
        model.selectedForDeletion = [7, 8, 999]
        await model.deleteCompleted(all: false)
        XCTAssertEqual(api.deletedIDs, Set([7]))
    }

    func testZeroDeletedCountPreservesDraftWhenStaleCompletedRecordIsNowKeep() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{}}"#))
        api.completedResult = try response(#"{"ok":true,"items":[{"id":7,"current_stage":"SOLD","title":"원본"}]}"#)
        api.deleteResult = try response(#"{"ok":true,"deleted_count":0}"#)
        let model = ResaleTradeViewModel(userId: "test", api: api)
        await model.loadHistory()
        model.select(try XCTUnwrap(model.completed.first))
        model.inputs["title"] = "저장하지 않은 제목"
        model.selectedForDeletion = [7]
        api.completedResult = try response(#"{"ok":true,"items":[]}"#)
        api.purchasedResult = try response(#"{"ok":true,"items":[{"id":7,"current_stage":"KEEP"}]}"#)

        await model.deleteCompleted(all: false)

        XCTAssertEqual(api.deletedIDs, Set([7]))
        XCTAssertEqual(model.selected?.id, 7)
        XCTAssertEqual(model.inputs["title"], "저장하지 않은 제목")
        XCTAssertTrue(model.hasUnsavedChanges)
        XCTAssertEqual(model.purchased.first?["current_stage"], "KEEP")
        XCTAssertTrue(model.message?.hasPrefix("삭제된 완료 거래가 없습니다.") == true)
        XCTAssertTrue(model.message?.contains("최신 목록") == true)
    }

    func testPartialAndAllDeletionCountsDoNotProveWhichDraftWasDeleted() async throws {
        for all in [false, true] {
            for historyFails in [false, true] {
                let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{}}"#))
                api.completedResult = try response(#"{"ok":true,"items":[{"id":7,"current_stage":"SOLD","title":"원본"},{"id":8,"current_stage":"SOLD"}]}"#)
                api.deleteResult = try response(#"{"ok":true,"deleted_count":1}"#)
                let model = ResaleTradeViewModel(userId: "test", api: api)
                await model.loadHistory()
                model.select(try XCTUnwrap(model.completed.first))
                model.inputs["title"] = "입력 유지"
                model.selectedForDeletion = [7, 8]
                let history = try response(historyFails ? #"{"ok":false,"reason":"network"}"# : #"{"ok":true,"items":[]}"#)
                api.completedResult = history
                api.purchasedResult = history

                await model.deleteCompleted(all: all)

                XCTAssertEqual(api.deletedIDs, all ? nil : Set([7, 8]))
                XCTAssertEqual(model.selected?.id, 7)
                XCTAssertEqual(model.inputs["title"], "입력 유지")
                XCTAssertTrue(model.hasUnsavedChanges)
                XCTAssertTrue(model.message?.contains("입력은 유지") == true)
                XCTAssertEqual(model.completedError != nil, historyFails)
                XCTAssertEqual(model.purchasedError != nil, historyFails)
            }
        }
    }

    func testFullyConfirmedSelectedDeletionClearsDeletedRowAndDraft() async throws {
        let api = TradeMockAPI(start: try response(#"{"ok":true,"row":{}}"#))
        api.completedResult = try response(#"{"ok":true,"items":[{"id":7,"current_stage":"SOLD","title":"원본"},{"id":8,"current_stage":"SOLD"}]}"#)
        api.deleteResult = try response(#"{"ok":true,"deleted_count":2}"#)
        let model = ResaleTradeViewModel(userId: "test", api: api)
        await model.loadHistory()
        model.select(try XCTUnwrap(model.completed.first))
        model.inputs["title"] = "명시적으로 삭제할 기록의 입력"
        model.selectedForDeletion = [7, 8]
        api.completedResult = try response(#"{"ok":true,"items":[]}"#)

        await model.deleteCompleted(all: false)

        XCTAssertNil(model.selected)
        XCTAssertTrue(model.inputs.isEmpty)
        XCTAssertTrue(model.selectedForDeletion.isEmpty)
        XCTAssertEqual(model.message, "완료된 거래 2건을 삭제했습니다.")
    }

    func testUncertainDeletedDraftRetryPatchesOriginalIDAndNotFoundKeepsInputs() async throws {
        let api = makeHTTPAPI()
        defer { TradeTestURLProtocol.handler = nil }
        var writes: [String] = []
        TradeTestURLProtocol.handler = { request in
            if request.httpMethod == "GET" { return Data(#"{"ok":true,"items":[]}"#.utf8) }
            writes.append("\(request.httpMethod ?? "") \(request.url?.path ?? "")")
            if request.url?.path.hasSuffix("/completed/delete-all") == true {
                return Data(#"{"ok":true,"deleted_count":1}"#.utf8)
            }
            XCTAssertEqual(request.url?.path, "/users/test/resale-trade-journeys/7/purchase")
            XCTAssertEqual(TradeTestURLProtocol.body(request)["updates"], .object(["title": .string("입력 유지"), "current_stage": .string("SOLD")]))
            return Data(#"{"ok":false,"reason":"not_found"}"#.utf8)
        }
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.select(ResaleTradeRow(values: ["id": .whole(7), "product_id": .string("123"), "current_stage": .string("SOLD"), "title": .string("원본")]))
        model.inputs["title"] = "입력 유지"

        await model.deleteCompleted(all: true)
        XCTAssertEqual(model.selected?.id, 7)
        XCTAssertEqual(model.inputs["title"], "입력 유지")
        await model.save()

        XCTAssertEqual(writes, ["PATCH /users/test/resale-trade-journeys/completed/delete-all", "PATCH /users/test/resale-trade-journeys/7/purchase"])
        XCTAssertEqual(model.selected?.id, 7)
        XCTAssertEqual(model.inputs["title"], "입력 유지")
        XCTAssertTrue(model.hasUnsavedChanges)
        // The real transport rejects the HTTP-200 ok:false envelope before
        // the domain response is decoded; do not assert the mock API's error type.
        XCTAssertEqual(model.errorMessage, APIClientError.serverRejected("not_found").localizedDescription)
        XCTAssertNil(model.message)
    }

    func testAPIUsesUpsertForDraftAndPatchForSavedAndEncodedUserPath() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [TradeTestURLProtocol.self]
        let api = ResaleTradeAPI(client: APIClient(baseURLString: "https://example.com/", session: URLSession(configuration: configuration)))
        defer { TradeTestURLProtocol.handler = nil }
        TradeTestURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/resale-trades/after-purchase/upsert")
            return Data(#"{"ok":true,"row":{"id":7}}"#.utf8)
        }
        _ = try await api.save(userId: "a/b", row: ResaleTradeRow(values: ["product_id": .string("123")]), mode: .purchase, updates: [:])
        TradeTestURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertTrue(request.url?.absoluteString.contains("users/a%2Fb/resale-trade-journeys/7/resale") == true)
            return Data(#"{"ok":true,"row":{"id":7}}"#.utf8)
        }
        _ = try await api.save(userId: "a/b", row: ResaleTradeRow(values: ["id": .number(7)]), mode: .resale, updates: [:])
    }

    func testNewResaleExplicitStagePreparesIdentityThenPatchesAllChangesTogether() async throws {
        let api = makeHTTPAPI()
        defer { TradeTestURLProtocol.handler = nil }
        let scenarios: [[String: TradeValue]] = [
            ["current_stage": .string("KEEP"), "sale_price_krw": .whole(300000), "sold_at": .string("2026-09-15")],
            ["current_stage": .string("KEEP"), "resale_platform": .string("joongna")]
        ]
        for updates in scenarios {
            var requests: [String] = []
            TradeTestURLProtocol.handler = { request in
                let body = TradeTestURLProtocol.body(request)
                requests.append("\(request.httpMethod ?? "") \(request.url?.path ?? "")")
                if request.httpMethod == "POST" {
                    XCTAssertEqual(request.url?.path, "/resale-trades/after-purchase/upsert")
                    XCTAssertEqual(body, ["user_id": .string("a/b"), "source": .string("joongna"),
                                          "product_id": .string("123"), "url": .string("https://example.com/123"),
                                          "updates": .object([:])])
                    return Data(#"{"ok":true,"id":7,"row":{"id":null,"product_id":"123"}}"#.utf8)
                }
                XCTAssertEqual(request.httpMethod, "PATCH")
                XCTAssertTrue(request.url?.absoluteString.contains("users/a%2Fb/resale-trade-journeys/7/resale") == true)
                XCTAssertEqual(body, ["updates": .object(updates)])
                return Data(#"{"ok":true,"row":{"id":7,"current_stage":"KEEP"}}"#.utf8)
            }
            let result = try await api.save(userId: "a/b", row: ResaleTradeRow(values: [
                "product_id": .string("123"), "url": .string("https://example.com/123")
            ]), mode: .resale, updates: updates)
            XCTAssertEqual(result.row?["current_stage"], "KEEP")
            XCTAssertEqual(requests.count, 2)
        }
    }

    func testResaleWithoutExplicitStageStillUsesLegacyUpsert() async throws {
        let api = makeHTTPAPI()
        defer { TradeTestURLProtocol.handler = nil }
        var requests = 0
        TradeTestURLProtocol.handler = { request in
            requests += 1
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/resale-trades/after-resale/upsert")
            XCTAssertEqual(TradeTestURLProtocol.body(request)["updates"], .object(["sale_price_krw": .whole(300000)]))
            return Data(#"{"ok":true,"row":{"id":7,"current_stage":"SOLD"}}"#.utf8)
        }
        _ = try await api.save(userId: "test", row: ResaleTradeRow(values: ["product_id": .string("123")]),
                               mode: .resale, updates: ["sale_price_krw": .whole(300000)])
        XCTAssertEqual(requests, 1)
    }

    func testResalePreparationMustSucceedAndReturnAPositiveIDBeforePatch() async throws {
        let api = makeHTTPAPI()
        defer { TradeTestURLProtocol.handler = nil }
        for payload in [#"{"ok":false,"reason":"not_found"}"#, #"{"ok":true}"#,
                        #"{"ok":true,"row":{"id":null}}"#, #"{"ok":true,"row":{"id":0}}"#] {
            var requests = 0
            TradeTestURLProtocol.handler = { request in
                requests += 1
                XCTAssertEqual(request.httpMethod, "POST")
                return Data(payload.utf8)
            }
            do {
                _ = try await api.save(userId: "test", row: ResaleTradeRow(values: ["product_id": .string("123")]),
                                       mode: .resale, updates: ["current_stage": .string("KEEP")])
                XCTFail("Preparation without an acknowledged positive ID must not save")
            } catch {
                XCTAssertEqual(requests, 1)
            }
        }
    }

    func testPreparedResaleFailureKeepsDraftAndRetryUsesSameIdentity() async throws {
        let api = makeHTTPAPI()
        defer { TradeTestURLProtocol.handler = nil }
        var writes: [String] = []
        var patchAttempts = 0
        TradeTestURLProtocol.handler = { request in
            if request.httpMethod == "GET" { return Data(#"{"ok":true,"items":[]}"#.utf8) }
            writes.append("\(request.httpMethod ?? "") \(request.url?.path ?? "")")
            let body = TradeTestURLProtocol.body(request)
            if request.httpMethod == "POST" {
                XCTAssertEqual(body, ["user_id": .string("test"), "source": .string("joongna"),
                                      "product_id": .string("123"), "updates": .object([:])])
                return Data(#"{"ok":true,"row":{"id":7,"product_id":"123","current_stage":"DISCOVERED"}}"#.utf8)
            }
            patchAttempts += 1
            XCTAssertEqual(body, ["updates": .object(["current_stage": .string("KEEP"), "sale_price_krw": .whole(300000)])])
            if patchAttempts == 1 { return Data(#"{"ok":false,"reason":"save_failed"}"#.utf8) }
            return Data(#"{"ok":true,"row":{"id":7,"product_id":"123","current_stage":"KEEP","sale_price_krw":300000}}"#.utf8)
        }
        let model = ResaleTradeViewModel(userId: "test", api: api)
        model.select(ResaleTradeRow(values: ["product_id": .string("123"), "current_stage": .string("DISCOVERED")]))
        model.mode = .resale
        model.inputs["current_stage"] = "KEEP"
        model.inputs["sale_price_krw"] = "300000"
        await model.save()
        XCTAssertNil(model.selected?.id)
        XCTAssertNil(model.message)
        XCTAssertEqual(model.errorMessage, TradeError.resaleSaveUnconfirmed.localizedDescription)
        XCTAssertEqual(model.inputs["current_stage"], "KEEP")
        XCTAssertEqual(model.inputs["sale_price_krw"], "300000")
        await model.save()
        XCTAssertNil(model.errorMessage)
        XCTAssertEqual(model.selected?.id, 7)
        XCTAssertEqual(model.selected?["current_stage"], "KEEP")
        XCTAssertNotNil(model.message)
        XCTAssertEqual(writes, ["POST /resale-trades/after-purchase/upsert", "PATCH /users/test/resale-trade-journeys/7/resale",
                               "POST /resale-trades/after-purchase/upsert", "PATCH /users/test/resale-trade-journeys/7/resale"])
    }

    private func makeHTTPAPI() -> ResaleTradeAPI {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [TradeTestURLProtocol.self]
        return ResaleTradeAPI(client: APIClient(baseURLString: "https://example.com/", session: URLSession(configuration: configuration)))
    }
}

private final class TradeMockAPI: ResaleTradeAPIProtocol {
    let startResult: TradeResponse
    var saveResults: [TradeResponse] = []
    var savedRows: [ResaleTradeRow] = []
    var savedModes: [TradeMode] = []
    var savedUpdates: [[String: TradeValue]] = []
    var deletedIDs: Set<Int>?
    var deleteResult: TradeResponse?
    var completedResult: TradeResponse?
    var purchasedResult: TradeResponse?
    var startFailures = 0
    var startedAlertIDs: [Int?] = []
    var startedReferences: [String?] = []
    var startedFromArchive: [Bool] = []
    init(start: TradeResponse) { startResult = start }
    func start(userId: String, reference: String?, alertId: Int?, fromArchive: Bool) async throws -> TradeResponse {
        startedAlertIDs.append(alertId)
        startedReferences.append(reference)
        startedFromArchive.append(fromArchive)
        if startFailures > 0 {
            startFailures -= 1
            throw APIClientError.network(URLError(.notConnectedToInternet))
        }
        return startResult
    }
    func save(userId: String, row: ResaleTradeRow, mode: TradeMode, updates: [String: TradeValue]) async throws -> TradeResponse {
        savedRows.append(row); savedModes.append(mode); savedUpdates.append(updates)
        return saveResults.removeFirst()
    }
    func history(userId: String, completed: Bool) async throws -> TradeResponse {
        if let response = completed ? completedResult : purchasedResult { return response }
        return try JSONDecoder().decode(TradeResponse.self, from: Data(#"{"ok":true,"items":[]}"#.utf8))
    }
    func delete(userId: String, ids: Set<Int>?) async throws -> TradeResponse {
        deletedIDs = ids
        if let deleteResult { return deleteResult }
        return try JSONDecoder().decode(TradeResponse.self, from: Data(#"{"ok":true,"deleted_count":1}"#.utf8))
    }
}

private final class TradeTestURLProtocol: URLProtocol {
    static var handler: ((URLRequest) -> Data)?
    static func body(_ request: URLRequest) -> [String: TradeValue] {
        var data = request.httpBody
        if data == nil, let stream = request.httpBodyStream {
            stream.open()
            defer { stream.close() }
            var buffer = [UInt8](repeating: 0, count: 1024)
            var streamed = Data()
            while stream.hasBytesAvailable {
                let count = stream.read(&buffer, maxLength: buffer.count)
                guard count > 0 else { break }
                streamed.append(buffer, count: count)
            }
            data = streamed
        }
        guard let data, let result = try? JSONDecoder().decode([String: TradeValue].self, from: data) else {
            XCTFail("Expected a JSON request body")
            return [:]
        }
        return result
    }
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let data = Self.handler?(request) ?? Data()
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
