import XCTest
@testable import UMTP_IOS

@MainActor
final class SettingsParityTests: XCTestCase {
    private let unit = MacUnit(product_type: "MacBook Air", chip: "M2", screen_inch: 13, ram_gb: 16, ssd_gb: 512)

    func testMacBookNeoCatalogAndSeedPricesPreserveOnlyTwoConfigurations() async {
        let neo = [256, 512].map { ssd -> UserFairPriceItem in
            var item = UserFairPriceItem(unit: MacUnit(product_type: "MacBook Neo", chip: "A18 Pro", screen_inch: 13, ram_gb: 8, ssd_gb: ssd))
            item.system_fair_price_krw = ssd == 256 ? 850_000 : 900_000
            item.recommended_search_keyword = "맥북 네오"
            return item
        }
        let api = SettingsTestAPI(items: Array(neo.reversed()) + [UserFairPriceItem(unit: unit)])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "neo-user")
        XCTAssertEqual(model.products, ["MacBook Air", "MacBook Neo"])
        XCTAssertEqual(model.chips(product: "MacBook Neo"), ["A18 Pro"])
        XCTAssertEqual(model.screens(product: "MacBook Neo", chip: "A18 Pro"), [13])
        XCTAssertEqual(model.units.filter { $0.product_type == "MacBook Neo" }.count, 2)
        XCTAssertEqual(model.draft(for: neo[0].unit).targetText, "680000")
        XCTAssertEqual(model.draft(for: neo[1].unit).targetText, "720000")
        XCTAssertLessThan(MacUnit.chipOrder("A18 Pro"), MacUnit.chipOrder("unknown"))
        await model.apply(.priority(.fast), scope: SettingsScope(product: "MacBook Neo", chip: nil, screen: nil))
        XCTAssertEqual(api.requests.count, 2)
        XCTAssertTrue(api.requests.allSatisfy { $0.product_type == "MacBook Neo" && $0.chip == "A18 Pro" && $0.ram_gb == 8 && $0.priority == "FAST" })
    }

    func testMacBookNeoSaveKeepsCanonicalChipAndStorage() async throws {
        let neo = MacUnit(product_type: "MacBook Neo", chip: "A18 Pro", screen_inch: 13, ram_gb: 8, ssd_gb: 512)
        var item = UserFairPriceItem(unit: neo)
        item.system_fair_price_krw = 900_000
        item.recommended_search_keyword = "맥북 네오"
        let api = SettingsTestAPI(items: [item])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "neo-user")
        model.edit(neo) { $0.enabled = true }
        let saved = await model.save(neo)
        XCTAssertTrue(saved)
        let request = try XCTUnwrap(api.requests.first)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "MacBook Neo")
        XCTAssertEqual(body["chip"] as? String, "A18 Pro")
        XCTAssertEqual(body["screen_inch"] as? Int, 13)
        XCTAssertEqual(body["ram_gb"] as? Int, 8)
        XCTAssertEqual(body["ssd_gb"] as? Int, 512)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 900_000)
        XCTAssertEqual(body["enabled"] as? Bool, true)
    }

    func testIMacCatalogUsesAllSeedCombinationsAndOnlyTwentyFourInches() async {
        let options: [(String, [Int])] = [("M4", [16, 24, 32]), ("M1", [8, 16]), ("M3", [8, 16, 24])]
        var units = options.flatMap { chip, memory in
            memory.flatMap { ram in
                [256, 512, 1024, 2048].map { ssd in
                    MacUnit(product_type: "iMac", chip: chip, screen_inch: 24, ram_gb: ram, ssd_gb: ssd)
                }
            }
        }
        XCTAssertEqual(units.count, 32)
        units += [unit, MacUnit(product_type: "Mac mini", chip: "M4", screen_inch: 0, ram_gb: 16, ssd_gb: 256),
                  MacUnit(product_type: "MacBook Pro", chip: "M3", screen_inch: 14, ram_gb: 8, ssd_gb: 512)]
        let model = SettingsViewModel(api: SettingsTestAPI(items: units.map { UserFairPriceItem(unit: $0) }))
        await model.load(userID: "u")
        XCTAssertEqual(model.products, ["MacBook Air", "Mac mini", "MacBook Pro", "iMac"])
        XCTAssertEqual(model.chips(product: "iMac"), ["M1", "M3", "M4"])
        for chip in ["M1", "M3", "M4"] {
            XCTAssertEqual(model.screens(product: "iMac", chip: chip), [24])
        }
    }

    func testIMacSaveUsesSeedPriceDisabledDefaultAndCanonicalSpecification() async throws {
        let imac = MacUnit(product_type: "iMac", chip: "M4", screen_inch: 24, ram_gb: 32, ssd_gb: 1024)
        var item = UserFairPriceItem(unit: imac)
        item.system_fair_price_krw = 2_650_000
        item.recommended_search_keyword = "m4 아이맥"
        // The settings API supplies the recommended keyword as the effective
        // keyword when this newly introduced unit has no user override.
        item.effective_search_keyword = item.recommended_search_keyword
        let api = SettingsTestAPI(items: [item])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "imac-user")
        XCTAssertFalse(model.draft(for: imac).enabled)
        XCTAssertEqual(model.draft(for: imac).targetText, "2120000")
        model.edit(imac) { $0.enabled = true; $0.priority = .fast }
        let saved = await model.save(imac)
        XCTAssertTrue(saved)
        let request = try XCTUnwrap(api.requests.first)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "iMac")
        XCTAssertEqual(body["chip"] as? String, "M4")
        XCTAssertEqual(body["screen_inch"] as? Int, 24)
        XCTAssertEqual(body["ram_gb"] as? Int, 32)
        XCTAssertEqual(body["ssd_gb"] as? Int, 1024)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 2_650_000)
        XCTAssertEqual(body["search_keyword"] as? String, "m4 아이맥")
        XCTAssertEqual(body["enabled"] as? Bool, true)
        XCTAssertEqual(body["priority"] as? String, "FAST")
    }

    func testIMacBulkChangesRespectChipAndProductScope() async {
        let units = [MacUnit(product_type: "iMac", chip: "M1", screen_inch: 24, ram_gb: 8, ssd_gb: 256),
                     MacUnit(product_type: "iMac", chip: "M4", screen_inch: 24, ram_gb: 16, ssd_gb: 256), unit]
        let api = SettingsTestAPI(items: units.map { unit in
            var item = UserFairPriceItem(unit: unit)
            item.system_fair_price_krw = 1_000_000
            return item
        })
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        await model.apply(.alerts(true), scope: SettingsScope(product: "iMac", chip: "M1", screen: 24))
        XCTAssertEqual(api.requests.count, 1)
        XCTAssertEqual(api.requests.first?.chip, "M1")
        XCTAssertEqual(api.requests.first?.enabled, true)
        api.requests = []
        await model.apply(.priority(.fast), scope: SettingsScope(product: "iMac", chip: nil, screen: nil))
        XCTAssertEqual(api.requests.count, 2)
        XCTAssertTrue(api.requests.allSatisfy { $0.product_type == "iMac" && $0.screen_inch == 24 && $0.priority == "FAST" })
    }

    func testMacStudioCatalogSortsUltraAndSkipsScreenSelection() async {
        let chips = ["M1 Max", "M1 Ultra", "M2 Max", "M2 Ultra", "M3 Ultra", "M4 Max"]
        let studios = chips.reversed().map { MacUnit(product_type: "Mac Studio", chip: $0, screen_inch: 0, ram_gb: 64, ssd_gb: 1024) }
        let model = SettingsViewModel(api: SettingsTestAPI(items: ([unit] + studios).map { UserFairPriceItem(unit: $0) }))
        await model.load(userID: "studio-user")
        XCTAssertEqual(model.products, ["MacBook Air", "Mac Studio"])
        XCTAssertEqual(model.chips(product: "Mac Studio"), chips)
        XCTAssertEqual(model.screens(product: "Mac Studio", chip: "M3 Ultra"), [])
        XCTAssertFalse(MacUnit.hasBuiltInDisplay("Mac Studio"))
        XCTAssertFalse(MacUnit.hasBuiltInDisplay("Mac mini"))
        XCTAssertTrue(MacUnit.hasBuiltInDisplay("MacBook Pro"))
        XCTAssertEqual(MacUnit.chipOrder("m3 ultra"), MacUnit.chipOrder("M3 Ultra"))
    }

    func testMacStudioSavePreserves512GBRAMAnd16TBStorage() async throws {
        let studio = MacUnit(product_type: "Mac Studio", chip: "M3 Ultra", screen_inch: 0, ram_gb: 512, ssd_gb: 16384)
        var item = UserFairPriceItem(unit: studio)
        item.system_fair_price_krw = 29_500_000
        item.effective_fair_price_krw = 29_500_000
        item.recommended_search_keyword = "m3ultra 맥스튜디오"
        let api = SettingsTestAPI(items: [item])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "studio-user")
        XCTAssertEqual(model.draft(for: studio).targetText, "23600000")
        model.edit(studio) { $0.enabled = true; $0.priority = .fast }
        let saved = await model.save(studio)
        XCTAssertTrue(saved)
        let request = try XCTUnwrap(api.requests.first)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "Mac Studio")
        XCTAssertEqual(body["chip"] as? String, "M3 Ultra")
        XCTAssertEqual(body["screen_inch"] as? Int, 0)
        XCTAssertEqual(body["ram_gb"] as? Int, 512)
        XCTAssertEqual(body["ssd_gb"] as? Int, 16384)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 29_500_000)
        XCTAssertEqual(body["priority"] as? String, "FAST")
    }

    func testMacStudioBulkScopeIsolatesChipsAndOtherProducts() async {
        let units = [
            MacUnit(product_type: "Mac Studio", chip: "M1 Max", screen_inch: 0, ram_gb: 32, ssd_gb: 512),
            MacUnit(product_type: "Mac Studio", chip: "M1 Max", screen_inch: 0, ram_gb: 64, ssd_gb: 1024),
            MacUnit(product_type: "Mac Studio", chip: "M3 Ultra", screen_inch: 0, ram_gb: 512, ssd_gb: 16384),
            MacUnit(product_type: "MacBook Pro", chip: "M1 Max", screen_inch: 14, ram_gb: 32, ssd_gb: 1024), unit,
        ]
        let items = units.map { unit in
            var item = UserFairPriceItem(unit: unit)
            item.system_fair_price_krw = 1_800_000
            item.enabled = true
            return item
        }
        let api = SettingsTestAPI(items: items)
        let model = SettingsViewModel(api: api)
        await model.load(userID: "studio-user")
        await model.apply(.alerts(false), scope: SettingsScope(product: "Mac Studio", chip: "M1 Max", screen: nil))
        XCTAssertEqual(api.requests.count, 2)
        XCTAssertTrue(api.requests.allSatisfy { $0.product_type == "Mac Studio" && $0.chip == "M1 Max" && $0.screen_inch == 0 })
        api.requests = []
        await model.apply(.priority(.fast), scope: SettingsScope(product: "Mac Studio", chip: nil, screen: nil))
        XCTAssertEqual(api.requests.count, 3)
        XCTAssertTrue(api.requests.allSatisfy { $0.product_type == "Mac Studio" && $0.priority == "FAST" })
    }

    func testMacBookProCatalogGroupsEverySiliconGenerationAndUsesServerScreenSizes() async {
        let expectedChips = ["M1", "M1 Pro", "M1 Max", "M2", "M2 Pro", "M2 Max",
                             "M3", "M3 Pro", "M3 Max", "M4", "M4 Pro", "M4 Max",
                             "M5", "M5 Pro", "M5 Max"]
        // Representative seed configurations deliberately arrive out of order.
        var units = expectedChips.reversed().flatMap { chip -> [MacUnit] in
            let screens = chip.contains(" ") ? [16, 14] : [chip == "M1" || chip == "M2" ? 13 : 14]
            let ram = chip.contains("Max") ? 64 : chip == "M3 Pro" ? 18 : ["M4 Pro", "M5 Pro"].contains(chip) ? 24 : 16
            let ssd = chip == "M5 Max" ? 2048 : 1024
            return screens.map { MacUnit(product_type: "MacBook Pro", chip: chip, screen_inch: $0, ram_gb: ram, ssd_gb: ssd) }
        }
        units += [unit, MacUnit(product_type: "Mac mini", chip: "M4", screen_inch: 0, ram_gb: 16, ssd_gb: 256)]
        let model = SettingsViewModel(api: SettingsTestAPI(items: units.map { UserFairPriceItem(unit: $0) }))
        await model.load(userID: "u")

        XCTAssertEqual(model.products, ["MacBook Air", "Mac mini", "MacBook Pro"])
        XCTAssertEqual(model.chips(product: "MacBook Pro"), expectedChips)
        XCTAssertEqual(model.screens(product: "MacBook Pro", chip: "M1"), [13])
        XCTAssertEqual(model.screens(product: "MacBook Pro", chip: "M2"), [13])
        XCTAssertEqual(model.screens(product: "MacBook Pro", chip: "M5"), [14])
        XCTAssertEqual(model.screens(product: "MacBook Pro", chip: "M3 Pro"), [14, 16])
        XCTAssertEqual(model.screens(product: "MacBook Pro", chip: "M5 Max"), [14, 16])
        XCTAssertEqual(model.chips(product: "MacBook Air"), ["M2"])
        XCTAssertEqual(MacUnit.chipOrder("m3 max"), MacUnit.chipOrder("M3 Max"))
        XCTAssertLessThan(MacUnit.chipOrder("M5 Max"), MacUnit.chipOrder("unknown"))
    }

    func testMacBookProSavePreservesMaxChipAndHighCapacitySeedSpecification() async throws {
        let pro = MacUnit(product_type: "MacBook Pro", chip: "M5 Max", screen_inch: 16, ram_gb: 128, ssd_gb: 8192)
        var item = UserFairPriceItem(unit: pro)
        item.system_fair_price_krw = 10_250_000
        item.effective_fair_price_krw = 10_250_000
        item.effective_alert_drop_rate_percent = 20
        item.recommended_search_keyword = "맥북프로 M5 Max"
        let api = SettingsTestAPI(items: [item])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "pro-user")
        XCTAssertEqual(model.draft(for: pro).targetText, "8200000")
        model.edit(pro) { $0.enabled = true; $0.priority = .fast }
        let saved = await model.save(pro)
        XCTAssertTrue(saved)
        let request = try XCTUnwrap(api.requests.first)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as? [String: Any])
        XCTAssertEqual(body["product_type"] as? String, "MacBook Pro")
        XCTAssertEqual(body["chip"] as? String, "M5 Max")
        XCTAssertEqual(body["screen_inch"] as? Int, 16)
        XCTAssertEqual(body["ram_gb"] as? Int, 128)
        XCTAssertEqual(body["ssd_gb"] as? Int, 8192)
        XCTAssertEqual(body["fair_price_krw"] as? Int, 10_250_000)
        XCTAssertEqual(body["alert_drop_rate_percent"] as? Double, 20)
        XCTAssertEqual(body["enabled"] as? Bool, true)
        XCTAssertEqual(body["priority"] as? String, "FAST")
    }

    func testMacBookProBulkScopeIsolatesScreenChipAndProduct() async {
        let units = [
            MacUnit(product_type: "MacBook Pro", chip: "M1 Pro", screen_inch: 14, ram_gb: 16, ssd_gb: 512),
            MacUnit(product_type: "MacBook Pro", chip: "M1 Pro", screen_inch: 16, ram_gb: 16, ssd_gb: 512),
            MacUnit(product_type: "MacBook Pro", chip: "M1 Max", screen_inch: 14, ram_gb: 32, ssd_gb: 1024),
            unit, MacUnit(product_type: "Mac mini", chip: "M2 Pro", screen_inch: 0, ram_gb: 16, ssd_gb: 512)
        ]
        let items = units.map { unit in
            var item = UserFairPriceItem(unit: unit)
            item.system_fair_price_krw = 1_200_000
            item.enabled = true
            return item
        }
        let api = SettingsTestAPI(items: items)
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        await model.apply(.alerts(false), scope: SettingsScope(product: "MacBook Pro", chip: "M1 Pro", screen: 14))
        XCTAssertEqual(api.requests.count, 1)
        XCTAssertEqual(api.requests.first?.screen_inch, 14)
        XCTAssertEqual(api.requests.first?.chip, "M1 Pro")
        XCTAssertEqual(api.requests.first?.enabled, false)
        api.requests = []
        await model.apply(.priority(.fast), scope: SettingsScope(product: "MacBook Pro", chip: nil, screen: nil))
        XCTAssertEqual(api.requests.count, 3)
        XCTAssertTrue(api.requests.allSatisfy { $0.product_type == "MacBook Pro" && $0.priority == "FAST" })
    }

    func testAndroidPriceFormulaAndNegativeGapRoundTrip() throws {
        XCTAssertEqual(SettingsPriceMath.gap(market: 900_000, target: 700_000), 22.22)
        XCTAssertEqual(SettingsPriceMath.gap(market: 1_000_000, target: 1_155_000), -15.5)
        XCTAssertEqual(SettingsPriceMath.target(market: 1_000_000, gap: -15.5), 1_155_000)
        XCTAssertNil(SettingsPriceMath.gap(market: 0, target: 100))
        XCTAssertNil(SettingsPriceMath.target(market: 1_000, gap: .infinity))
    }

    func testDraftTracksLastEditedPriceAndRejectsInvalidBounds() throws {
        var draft = SettingDraft(setting: nil)
        draft.changeMarket("1000000")
        draft.changeGap("-15.5")
        XCTAssertEqual(draft.targetText, "1155000")
        draft.changeMarket("2000000")
        XCTAssertEqual(draft.targetText, "2310000")
        draft.changeTarget("1600000")
        XCTAssertEqual(draft.gapText, "20.00")
        draft.changeMarket("1000000")
        XCTAssertEqual(draft.targetText, "1600000")
        XCTAssertEqual(draft.gapText, "-60.00")
        draft.minimumText = "invalid"
        XCTAssertThrowsError(try draft.request(userID: "user", unit: unit))
        draft.minimumText = "-1"
        XCTAssertThrowsError(try draft.request(userID: "user", unit: unit))
        draft.minimumText = "0"
        XCTAssertEqual(try draft.request(userID: "user", unit: unit).min_price_krw, 0)
        draft.changeTarget("3000000")
        XCTAssertThrowsError(try draft.request(userID: "user", unit: unit))
    }

    func testSaveMapsDirectionPriorityAndClearsOppositeBound() throws {
        var draft = SettingDraft(setting: nil)
        draft.changeMarket("1000000"); draft.changeTarget("800000")
        draft.minimumText = "300000"; draft.maximumText = "1400000"
        draft.priority = .fast; draft.candidateNotice = true; draft.enabled = true
        draft.keyword = "  m2 맥북에어  "
        let below = try draft.request(userID: "기존 사용자", unit: unit)
        XCTAssertEqual(below.min_price_krw, 300000)
        XCTAssertNil(below.max_price_krw)
        XCTAssertEqual(below.priority, "FAST")
        XCTAssertEqual(below.search_keyword, "m2 맥북에어")
        XCTAssertTrue(below.condition_change_candidate_notice_enabled)
        draft.direction = .above
        let above = try draft.request(userID: "기존 사용자", unit: unit)
        XCTAssertNil(above.min_price_krw)
        XCTAssertEqual(above.max_price_krw, 1400000)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(above)) as? [String: Any])
        XCTAssertEqual(json["alert_price_direction"] as? String, "ABOVE_OR_EQUAL")
        XCTAssertEqual(json["user_id"] as? String, "기존 사용자")
        XCTAssertNil(json["min_price_krw"])
    }

    func testZeroTargetEncodesServerCompatibleHundredPercentWithoutAllowingInvalidPrices() throws {
        var draft = SettingDraft(setting: nil)
        draft.changeMarket("1000000")
        draft.changeTarget("0")
        let request = try draft.request(userID: "existing-user", unit: unit)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as? [String: Any])
        XCTAssertEqual(json["fair_price_krw"] as? Int, 1000000)
        XCTAssertEqual(json["alert_drop_rate_percent"] as? Double, 100)
        XCTAssertEqual(SettingsPriceMath.target(market: request.fair_price_krw, gap: request.alert_drop_rate_percent), 0)

        draft.changeMarket("0")
        XCTAssertThrowsError(try draft.request(userID: "existing-user", unit: unit))
        draft.changeMarket("1000000")
        draft.changeTarget("-1")
        XCTAssertThrowsError(try draft.request(userID: "existing-user", unit: unit))
        draft.changeTarget("2000100")
        XCTAssertThrowsError(try draft.request(userID: "existing-user", unit: unit))
    }

    func testBulkHundredPercentCanBeReloadedAndIndividuallyEnabledWithoutChangingTarget() async throws {
        var item = exampleItem()
        item.enabled = false
        let api = SettingsTestAPI(items: [item])
        api.reflectSavedSettings = true
        let model = SettingsViewModel(api: api)
        await model.load(userID: "existing-user")
        await model.apply(.gap(100), scope: SettingsScope(product: "MacBook Air", chip: "M2", screen: 13))
        XCTAssertEqual(model.draft(for: unit).targetText, "0")
        XCTAssertEqual(model.draft(for: unit).gapText, "100.00")

        model.edit(unit) { $0.enabled = true; $0.keyword = "zero target remains editable" }
        let saved = await model.save(unit)
        XCTAssertTrue(saved)
        XCTAssertEqual(api.requests.count, 2)
        let request = try XCTUnwrap(api.requests.last)
        XCTAssertEqual(request.alert_drop_rate_percent, 100)
        XCTAssertEqual(request.fair_price_krw, 1000000)
        XCTAssertTrue(request.enabled)
        XCTAssertEqual(request.search_keyword, "zero target remains editable")
        XCTAssertEqual(model.draft(for: unit).targetText, "0")
        XCTAssertFalse(model.dirtyKeys.contains(unit.id))
    }

    func testServerTargetAmountWinsOverRoundedPercentageReconstruction() {
        var item = exampleItem()
        item.user_fair_price_krw = 900000
        item.user_alert_drop_rate_percent = 22.22
        item.user_target_buy_price_krw = 700000
        item.effective_target_buy_price_krw = 700020
        let draft = SettingDraft(setting: item)
        XCTAssertEqual(draft.targetText, "700000")
        XCTAssertEqual(draft.gapText, "22.22")
        item.user_target_buy_price_krw = nil
        item.effective_target_buy_price_krw = 700010
        XCTAssertEqual(SettingDraft(setting: item).targetText, "700010")
    }

    func testDecodesLegacyBooleanAndNumericShapesWithoutInventingValues() throws {
        let data = Data(#"""
        {"ok":"yes","items":[{"id":"77","product_type":"Mac mini","chip":"M4 Pro","screen_inch":0,"ram_gb":24,"ssd_gb":512,"enabled":1,"has_user_override":"on","condition_change_candidate_notice_enabled":"false","effective_fair_price_krw":"1200000","effective_alert_drop_rate_percent":"-15.5","priority":"fast","user_max_price_krw":null}]}
        """#.utf8)
        let response = try JSONDecoder().decode(FairPricesResponse.self, from: data)
        XCTAssertTrue(response.ok)
        let item = try XCTUnwrap(response.items.first)
        XCTAssertEqual(item.ruleID, 77)
        XCTAssertTrue(item.enabled)
        XCTAssertTrue(item.has_user_override)
        XCTAssertFalse(item.condition_change_candidate_notice_enabled)
        XCTAssertEqual(item.marketPrice, 1200000)
        XCTAssertEqual(item.dropRate, -15.5)
        XCTAssertNil(item.user_max_price_krw)
        XCTAssertEqual(WatchPriority(serverValue: item.priority), .fast)
        let invalid = Data(#"{"product_type":"Mac mini","chip":"M4","screen_inch":0,"ram_gb":16,"ssd_gb":256,"enabled":"perhaps"}"#.utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(UserFairPriceItem.self, from: invalid))
    }

    @MainActor
    func testBulkResetPreservesEveryUnrelatedSettingAndSkipsMissingSystemPrice() throws {
        var item = exampleItem()
        item.user_fair_price_krw = 900000
        item.system_fair_price_krw = 1000000
        item.user_alert_drop_rate_percent = -15
        item.user_alert_price_direction = "ABOVE_OR_EQUAL"
        item.user_max_price_krw = 1400000
        item.custom_search_keyword = "my keyword"
        item.priority = "LOW"
        item.poll_interval_seconds = 120
        item.condition_change_candidate_notice_enabled = true
        let request = try XCTUnwrap(SettingsViewModel.bulkRequest(.resetMarket, item: item, userID: "u"))
        XCTAssertEqual(request.fair_price_krw, 1000000)
        XCTAssertEqual(request.alert_drop_rate_percent, -15)
        XCTAssertEqual(request.alert_price_direction, "ABOVE_OR_EQUAL")
        XCTAssertEqual(request.max_price_krw, 1400000)
        XCTAssertNil(request.min_price_krw)
        XCTAssertEqual(request.priority, "LOW")
        XCTAssertEqual(request.poll_interval_seconds, 120)
        XCTAssertEqual(request.search_keyword, "my keyword")
        XCTAssertTrue(request.condition_change_candidate_notice_enabled)
        item.system_fair_price_krw = nil
        XCTAssertNil(try SettingsViewModel.bulkRequest(.resetMarket, item: item, userID: "u"))
        XCTAssertNil(try SettingsViewModel.bulkRequest(.minimum(500000), item: item, userID: "u"))
    }

    @MainActor
    func testMacMiniAndProductScopesDoNotTouchOtherProductsOrChips() throws {
        let mini = MacUnit(product_type: "Mac mini", chip: "M4", screen_inch: 0, ram_gb: 16, ssd_gb: 256)
        let otherChip = MacUnit(product_type: "Mac mini", chip: "M4 Pro", screen_inch: 0, ram_gb: 24, ssd_gb: 512)
        let current = SettingsScope(product: "Mac mini", chip: "M4", screen: nil)
        XCTAssertTrue(current.contains(mini))
        XCTAssertFalse(current.contains(otherChip))
        XCTAssertFalse(current.contains(unit))
        let allProduct = SettingsScope(product: "Mac mini", chip: nil, screen: nil)
        XCTAssertTrue(allProduct.contains(otherChip))
        XCTAssertFalse(allProduct.contains(unit))
    }

    @MainActor
    func testRefreshWritesSavedAtAndPreservesUnsavedDrafts() async throws {
        let api = SettingsTestAPI(items: [exampleItem()])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "existing-user")
        model.edit(unit) { $0.keyword = "unsaved keyword" }
        api.items[0].effective_fair_price_krw = 1200000
        await model.refresh()
        XCTAssertEqual(api.refreshCalls.count, 1)
        XCTAssertNil(api.refreshCalls[0])
        XCTAssertEqual(model.draft(for: unit).keyword, "unsaved keyword")
        XCTAssertEqual(model.item(for: unit)?.effective_fair_price_krw, 1200000)
        XCTAssertEqual(model.refreshStatus, "새로고침됨")
        XCTAssertNotNil(model.lastRefresh)
        XCTAssertTrue(model.dirtyKeys.contains(unit.id))
    }

    @MainActor
    func testFailedLoadKeepsPreviousSettingsAndDoesNotReportSuccess() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        api.failSettings = true
        await model.refresh()
        XCTAssertEqual(model.settings.count, 1)
        XCTAssertEqual(model.refreshStatus, "새로고침 실패")
        XCTAssertNotNil(model.message)
        XCTAssertFalse(model.isBusy)
    }

    @MainActor
    func testSaveFailureRetainsUserInputAndExistingData() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        model.edit(unit) { $0.keyword = "keep this" }
        api.failAtSave = 1
        let saved = await model.save(unit)
        XCTAssertFalse(saved)
        XCTAssertEqual(model.draft(for: unit).keyword, "keep this")
        XCTAssertTrue(model.dirtyKeys.contains(unit.id))
        XCTAssertEqual(model.settings.count, 1)
        XCTAssertFalse(model.isBusy)
    }

    @MainActor
    func testPartialBatchFailureReconcilesAndReportsExactCompletedCount() async {
        var second = exampleItem(); second.unit.ram_gb = 24
        var third = exampleItem(); third.unit.ram_gb = 32
        let api = SettingsTestAPI(items: [exampleItem(), second, third])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        api.failAtSave = 2
        await model.apply(.priority(.fast), scope: SettingsScope(product: "MacBook Air", chip: nil, screen: nil))
        XCTAssertEqual(api.requests.count, 2)
        XCTAssertEqual(api.settingsLoads, 2)
        XCTAssertTrue(model.message?.contains("1건 적용") == true)
        XCTAssertTrue(model.message?.contains("실패") == true)
        XCTAssertFalse(model.isBusy)
    }

    @MainActor
    func testDuplicateSaveDoesNotSendASecondRequest() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        api.pauseSave = true
        let first = Task { await model.save(unit) }
        while api.saveContinuation == nil { await Task.yield() }
        let second = await model.save(unit)
        XCTAssertFalse(second)
        XCTAssertEqual(api.requests.count, 1)
        api.saveContinuation?.resume()
        api.saveContinuation = nil
        _ = await first.value
        XCTAssertFalse(model.isBusy)
    }

    func testBulkChangeRebasesDirtyKeywordWithoutReenablingAlertsOnSave() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        api.reflectSavedSettings = true
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        model.edit(unit) { $0.keyword = "unsaved keyword" }
        await model.apply(.alerts(false), scope: SettingsScope(product: "MacBook Air", chip: nil, screen: nil))
        XCTAssertEqual(model.draft(for: unit).keyword, "unsaved keyword")
        XCTAssertFalse(model.draft(for: unit).enabled)
        XCTAssertTrue(model.dirtyKeys.contains(unit.id))
        let saved = await model.save(unit)
        XCTAssertTrue(saved)
        XCTAssertEqual(api.requests.last?.search_keyword, "unsaved keyword")
        XCTAssertEqual(api.requests.last?.enabled, false)
    }

    func testExplicitBatchPriorityWinsOverDraftAndPreservesIndependentInput() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        api.reflectSavedSettings = true
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        model.edit(unit) { $0.priority = .low; $0.keyword = "keep" }
        await model.apply(.priority(.fast), scope: SettingsScope(product: "MacBook Air", chip: nil, screen: nil))
        XCTAssertEqual(model.draft(for: unit).priority, .fast)
        XCTAssertEqual(model.draft(for: unit).keyword, "keep")
    }

    func testBatchPercentageRecomputesPendingMarketInputWithoutLosingIt() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        api.reflectSavedSettings = true
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        model.edit(unit) { $0.changeMarket("900000"); $0.keyword = "keep" }
        await model.apply(.gap(30), scope: SettingsScope(product: "MacBook Air", chip: nil, screen: nil))
        XCTAssertEqual(model.draft(for: unit).marketText, "900000")
        XCTAssertEqual(model.draft(for: unit).targetText, "630000")
        XCTAssertEqual(model.draft(for: unit).gapText, "30.00")
        XCTAssertEqual(model.draft(for: unit).keyword, "keep")
    }

    func testSuccessfulSaveSurvivesReloadFailureAndSubsequentBulkUpsert() async {
        var item = exampleItem()
        item.custom_search_keyword = "old keyword"
        let api = SettingsTestAPI(items: [item])
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        model.edit(unit) { $0.keyword = "new keyword" }
        api.failSettings = true
        let saved = await model.save(unit)
        XCTAssertTrue(saved)
        XCTAssertEqual(model.item(for: unit)?.custom_search_keyword, "new keyword")
        await model.apply(.priority(.fast), scope: SettingsScope(product: "MacBook Air", chip: nil, screen: nil))
        XCTAssertEqual(api.requests.last?.search_keyword, "new keyword")
        XCTAssertEqual(api.requests.last?.priority, "FAST")
    }

    func testMissingUserSettingsCannotOverwriteExistingServerRowWithDefaults() async {
        let api = SettingsTestAPI(items: [exampleItem()])
        api.failSettings = true
        let model = SettingsViewModel(api: api)
        await model.load(userID: "u")
        XCTAssertFalse(model.units.isEmpty)
        XCTAssertTrue(model.settings.isEmpty)
        model.edit(unit) { $0.changeMarket("1000000"); $0.changeTarget("800000") }
        let saved = await model.save(unit)
        XCTAssertFalse(saved)
        XCTAssertTrue(api.requests.isEmpty)
        api.failSettings = false
        await model.load(userID: "u")
        XCTAssertEqual(model.settings.count, 1, "목록만 불러온 경우 설정 재조회가 차단되지 않아야 합니다.")
    }

    @MainActor
    func testSettingsAPIUsesCorrectHTTPMethodsAndEscapedIdentity() async throws {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [SettingsTestURLProtocol.self]
        let session = URLSession(configuration: config)
        defer { session.invalidateAndCancel(); SettingsTestURLProtocol.handler = nil }
        let client = APIClient(baseURLString: "https://example.invalid", session: session)
        let api = SettingsAPI(client: client)
        var requests: [URLRequest] = []
        SettingsTestURLProtocol.handler = { request in
            requests.append(request)
            return Data(#"{"ok":true,"items":[]}"#.utf8)
        }
        _ = try await api.settings(userID: "한 글/?")
        try await api.refreshRules(userID: "한 글/?", ruleID: 42)
        XCTAssertEqual(requests.map(\.httpMethod), ["GET", "POST"])
        XCTAssertEqual(URLComponents(url: try XCTUnwrap(requests[0].url), resolvingAgainstBaseURL: false)?.queryItems?.first?.value, "한 글/?")
        XCTAssertTrue(requests[1].url?.absoluteString.contains("/rules/42/refresh") == true)
        XCTAssertTrue(requests[1].url?.absoluteString.contains("%2F%3F") == true)
        XCTAssertFalse(requests[1].url?.absoluteString.contains("%252F") == true)
    }

    private func exampleItem() -> UserFairPriceItem {
        var item = UserFairPriceItem(unit: unit)
        item.ruleID = 10; item.enabled = true; item.has_user_override = true
        item.effective_fair_price_krw = 1000000; item.effective_alert_drop_rate_percent = 20
        return item
    }
}

@MainActor
private final class SettingsTestAPI: SettingsAPIProtocol {
    var items: [UserFairPriceItem]
    var requests: [FairPriceUpsertRequest] = []
    var refreshCalls: [Int64?] = []
    var settingsLoads = 0
    var failSettings = false
    var failAtSave: Int?
    var pauseSave = false
    var reflectSavedSettings = false
    var saveContinuation: CheckedContinuation<Void, Never>?
    init(items: [UserFairPriceItem]) { self.items = items }
    func units() async throws -> [MacUnit] { items.map(\.unit) }
    func settings(userID: String) async throws -> [UserFairPriceItem] {
        settingsLoads += 1
        if failSettings { throw SettingsInputError.incomplete }
        return items
    }
    func save(_ request: FairPriceUpsertRequest) async throws -> SettingsOperationResponse {
        requests.append(request)
        if failAtSave == requests.count { throw SettingsInputError.server }
        if pauseSave { await withCheckedContinuation { saveContinuation = $0 } }
        if reflectSavedSettings, let index = items.firstIndex(where: {
            $0.unit.product_type == request.product_type && $0.unit.chip == request.chip &&
            $0.unit.screen_inch == request.screen_inch && $0.unit.ram_gb == request.ram_gb && $0.unit.ssd_gb == request.ssd_gb
        }) {
            items[index].user_fair_price_krw = request.fair_price_krw
            items[index].effective_fair_price_krw = request.fair_price_krw
            items[index].user_alert_drop_rate_percent = request.alert_drop_rate_percent
            items[index].effective_alert_drop_rate_percent = request.alert_drop_rate_percent
            items[index].user_target_buy_price_krw = SettingsPriceMath.target(market: request.fair_price_krw, gap: request.alert_drop_rate_percent)
            items[index].effective_target_buy_price_krw = items[index].user_target_buy_price_krw
            items[index].enabled = request.enabled
            items[index].condition_change_candidate_notice_enabled = request.condition_change_candidate_notice_enabled
            items[index].priority = request.priority
            items[index].custom_search_keyword = request.search_keyword
            items[index].user_min_price_krw = request.min_price_krw
            items[index].effective_min_price_krw = request.min_price_krw
            items[index].user_max_price_krw = request.max_price_krw
            items[index].effective_max_price_krw = request.max_price_krw
        }
        return SettingsOperationResponse(ok: true, immediatePollRequested: true)
    }
    func refreshRules(userID: String, ruleID: Int64?) async throws { refreshCalls.append(ruleID) }
}

private final class SettingsTestURLProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var handler: ((URLRequest) -> Data)?
    nonisolated override class func canInit(with request: URLRequest) -> Bool { true }
    nonisolated override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    nonisolated override func startLoading() {
        let data = Self.handler?(request) ?? Data()
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: ["Content-Type": "application/json"])!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }
    nonisolated override func stopLoading() {}
}
