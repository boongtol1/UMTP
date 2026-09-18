import Foundation

struct MacUnit: Codable, Equatable, Hashable, Identifiable {
    var product_type: String
    var chip: String
    var screen_inch: Int
    var ram_gb: Int
    var ssd_gb: Int
    var id: String { "\(product_type)|\(chip)|\(screen_inch)|\(ram_gb)|\(ssd_gb)" }
    static func productOrder(_ value: String) -> Int {
        ["MacBook Air": 1, "Mac mini": 2, "MacBook Pro": 3, "iMac": 4][value] ?? 99
    }
    static func chipOrder(_ value: String) -> Int {
        let chips = ["M1", "M1 PRO", "M1 MAX", "M2", "M2 PRO", "M2 MAX",
                     "M3", "M3 PRO", "M3 MAX", "M4", "M4 PRO", "M4 MAX",
                     "M5", "M5 PRO", "M5 MAX"]
        return chips.firstIndex(of: value.uppercased()) ?? 99
    }
}

enum WatchPriority: String, CaseIterable, Codable {
    case fast = "FAST", normal = "NORMAL", low = "LOW"
    init(serverValue: String?) {
        self = Self(rawValue: serverValue?.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() ?? "") ?? .normal
    }
    var label: String { switch self { case .fast: "빠름"; case .normal: "보통"; case .low: "절전" } }
    var explanation: String { switch self { case .fast: "더 자주 확인해요"; case .normal: "일반적인 속도"; case .low: "천천히 확인해요" } }
}

enum AlertPriceDirection: String, CaseIterable, Codable {
    case below = "BELOW_OR_EQUAL", above = "ABOVE_OR_EQUAL"
    init(serverValue: String?) {
        self = Self(rawValue: serverValue?.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() ?? "") ?? .below
    }
    var label: String { self == .below ? "이하 알림" : "이상 알림" }
}

struct UserFairPriceItem: Decodable, Equatable, Identifiable {
    var unit: MacUnit
    var ruleID: Int64?
    var system_fair_price_krw: Int?
    var system_min_price_krw: Int?
    var system_max_price_krw: Int?
    var user_fair_price_krw: Int?
    var user_target_buy_price_krw: Int?
    var user_min_price_krw: Int?
    var user_max_price_krw: Int?
    var effective_fair_price_krw: Int?
    var effective_target_buy_price_krw: Int?
    var effective_min_price_krw: Int?
    var effective_max_price_krw: Int?
    var poll_interval_seconds: Int?
    var system_alert_drop_rate_percent: Double?
    var user_alert_drop_rate_percent: Double?
    var effective_alert_drop_rate_percent: Double?
    var system_alert_price_direction: String?
    var user_alert_price_direction: String?
    var effective_alert_price_direction: String?
    var custom_search_keyword: String?
    var recommended_search_keyword: String?
    var effective_search_keyword: String?
    var priority: String?
    var saved_at: String?
    var last_polled_at: String?
    var last_poll_requested_at: String?
    var enabled = false
    var condition_change_candidate_notice_enabled = false
    var has_user_override = false
    var force_poll: Bool?
    var id: String { unit.id }
    var marketPrice: Int? { user_fair_price_krw ?? effective_fair_price_krw ?? system_fair_price_krw }
    var dropRate: Double { user_alert_drop_rate_percent ?? effective_alert_drop_rate_percent ?? system_alert_drop_rate_percent ?? 20 }
    var direction: AlertPriceDirection { AlertPriceDirection(serverValue: user_alert_price_direction ?? effective_alert_price_direction ?? system_alert_price_direction) }
    var minimumPrice: Int? { user_min_price_krw ?? effective_min_price_krw ?? system_min_price_krw }
    var maximumPrice: Int? { user_max_price_krw ?? effective_max_price_krw ?? system_max_price_krw }
    init(unit: MacUnit) { self.unit = unit }

    init(from decoder: Decoder) throws {
        let data = try decoder.container(keyedBy: SettingsJSONKey.self)
        unit = MacUnit(product_type: try data.requiredString("product_type"), chip: try data.requiredString("chip"),
                       screen_inch: try data.requiredInt("screen_inch"), ram_gb: try data.requiredInt("ram_gb"), ssd_gb: try data.requiredInt("ssd_gb"))
        ruleID = try data.optionalInt("id").map(Int64.init)
        system_fair_price_krw = try data.optionalInt("system_fair_price_krw")
        system_min_price_krw = try data.optionalInt("system_min_price_krw")
        system_max_price_krw = try data.optionalInt("system_max_price_krw")
        user_fair_price_krw = try data.optionalInt("user_fair_price_krw")
        user_target_buy_price_krw = try data.optionalInt("user_target_buy_price_krw")
        user_min_price_krw = try data.optionalInt("user_min_price_krw")
        user_max_price_krw = try data.optionalInt("user_max_price_krw")
        effective_fair_price_krw = try data.optionalInt("effective_fair_price_krw")
        effective_target_buy_price_krw = try data.optionalInt("effective_target_buy_price_krw")
        effective_min_price_krw = try data.optionalInt("effective_min_price_krw")
        effective_max_price_krw = try data.optionalInt("effective_max_price_krw")
        poll_interval_seconds = try data.optionalInt("poll_interval_seconds")
        system_alert_drop_rate_percent = try data.optionalDouble("system_alert_drop_rate_percent")
        user_alert_drop_rate_percent = try data.optionalDouble("user_alert_drop_rate_percent")
        effective_alert_drop_rate_percent = try data.optionalDouble("effective_alert_drop_rate_percent")
        system_alert_price_direction = try data.optionalString("system_alert_price_direction")
        user_alert_price_direction = try data.optionalString("user_alert_price_direction")
        effective_alert_price_direction = try data.optionalString("effective_alert_price_direction")
        custom_search_keyword = try data.optionalString("custom_search_keyword")
        recommended_search_keyword = try data.optionalString("recommended_search_keyword")
        effective_search_keyword = try data.optionalString("effective_search_keyword")
        priority = try data.optionalString("priority")
        saved_at = try data.optionalString("saved_at")
        last_polled_at = try data.optionalString("last_polled_at")
        last_poll_requested_at = try data.optionalString("last_poll_requested_at")
        enabled = try data.optionalBool("enabled") ?? false
        condition_change_candidate_notice_enabled = try data.optionalBool("condition_change_candidate_notice_enabled") ?? false
        has_user_override = try data.optionalBool("has_user_override") ?? false
        force_poll = try data.optionalBool("force_poll")
    }
}

struct MacUnitsResponse: Decodable {
    let ok: Bool
    let units: [MacUnit]
    init(from decoder: Decoder) throws {
        let data = try decoder.container(keyedBy: SettingsJSONKey.self)
        ok = try data.optionalBool("ok") ?? false
        units = try data.decodeIfPresent([MacUnit].self, forKey: SettingsJSONKey("units")) ?? []
    }
}

struct FairPricesResponse: Decodable {
    let ok: Bool
    let items: [UserFairPriceItem]
    init(from decoder: Decoder) throws {
        let data = try decoder.container(keyedBy: SettingsJSONKey.self)
        ok = try data.optionalBool("ok") ?? false
        items = try data.decodeIfPresent([UserFairPriceItem].self, forKey: SettingsJSONKey("items")) ?? []
    }
}

struct SettingsOperationResponse: Decodable {
    var ok: Bool
    var immediate_poll_requested: Bool?
    var missed_candidate_count: Int?
    init(ok: Bool, immediatePollRequested: Bool? = nil) { self.ok = ok; immediate_poll_requested = immediatePollRequested }
    init(from decoder: Decoder) throws {
        let data = try decoder.container(keyedBy: SettingsJSONKey.self)
        ok = try data.optionalBool("ok") ?? false
        immediate_poll_requested = try data.optionalBool("immediate_poll_requested")
        missed_candidate_count = try data.optionalInt("missed_candidate_count")
    }
}

struct FairPriceUpsertRequest: Encodable, Equatable {
    var user_id: String
    var product_type: String
    var chip: String
    var screen_inch: Int
    var ram_gb: Int
    var ssd_gb: Int
    var fair_price_krw: Int
    var alert_drop_rate_percent: Double
    var alert_price_direction: String
    var min_price_krw: Int?
    var max_price_krw: Int?
    var enabled: Bool
    var condition_change_candidate_notice_enabled: Bool
    var search_keyword: String?
    var poll_interval_seconds: Int
    var priority: String
}

enum SettingsInputError: LocalizedError {
    case price, percentage, bound, keyword, emptyScope, server, incomplete
    var errorDescription: String? {
        switch self {
        case .price: "시장가는 1원 이상, 알림 기준 가격은 0원 이상이어야 합니다."
        case .percentage: "시장가와의 차이는 -100 ~ 100% 범위로 입력해주세요."
        case .bound: "최소/최대 가격은 0원 이상의 숫자로 입력해주세요."
        case .keyword: "검색어는 255자 이내로 입력해주세요."
        case .emptyScope: "적용할 설정이 없습니다. 새로고침 후 다시 시도해주세요."
        case .server: "설정을 저장하지 못했어요. 잠시 후 다시 시도해주세요."
        case .incomplete: "설정 데이터를 불러오지 못했습니다. 다시 시도해주세요."
        }
    }
}

enum SettingsPriceMath {
    static func gap(market: Int?, target: Int?) -> Double? {
        guard let market, market > 0, let target else { return nil }
        var ratio = (Decimal(market) - Decimal(target)) / Decimal(market)
        var roundedRatio = Decimal()
        NSDecimalRound(&roundedRatio, &ratio, 8, .plain)
        var percent = roundedRatio * 100
        var rounded = Decimal()
        NSDecimalRound(&rounded, &percent, 2, .plain)
        return NSDecimalNumber(decimal: rounded).doubleValue
    }
    static func target(market: Int?, gap: Double?) -> Int? {
        guard let market, market > 0, let gap, gap.isFinite else { return nil }
        let value = (Double(market) * (1 - gap / 100)).rounded()
        guard value.isFinite, value >= 0, value < Double(Int.max) else { return nil }
        return Int(value)
    }
    static func money(_ value: Int?) -> String {
        guard let value else { return "정보 없음" }
        return value.formatted(.number.locale(Locale(identifier: "ko_KR"))) + "원"
    }
    static func percent(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "정보 없음" }
        return String(format: "%.2f%%", locale: Locale(identifier: "ko_KR"), value)
    }
    static func marketLabel(_ userID: String) -> String {
        let id = userID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !id.isEmpty else { return "사용자가 생각한 시장가" }
        let label = id.count > 12 ? String(id.prefix(5)) + "…" + String(id.suffix(6)) : id
        return "\(label)님이 생각한 시장가"
    }
}

private struct SettingsJSONKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init(_ value: String) { stringValue = value }
    init?(stringValue: String) { self.init(stringValue) }
    init?(intValue: Int) { return nil }
}

private extension KeyedDecodingContainer where Key == SettingsJSONKey {
    func optionalString(_ key: String) throws -> String? { try decodeIfPresent(String.self, forKey: SettingsJSONKey(key)) }
    func requiredString(_ key: String) throws -> String { try decode(String.self, forKey: SettingsJSONKey(key)) }
    func requiredInt(_ key: String) throws -> Int {
        guard let value = try optionalInt(key) else {
            throw DecodingError.keyNotFound(SettingsJSONKey(key), .init(codingPath: codingPath, debugDescription: "Required setting field"))
        }
        return value
    }
    func optionalInt(_ name: String) throws -> Int? {
        let key = SettingsJSONKey(name)
        guard contains(key), try !decodeNil(forKey: key) else { return nil }
        if let value = try? decode(Int.self, forKey: key) { return value }
        if let value = try? decode(String.self, forKey: key), let number = Int(value) { return number }
        throw DecodingError.typeMismatch(Int.self, .init(codingPath: codingPath + [key], debugDescription: "Invalid integer"))
    }
    func optionalDouble(_ name: String) throws -> Double? {
        let key = SettingsJSONKey(name)
        guard contains(key), try !decodeNil(forKey: key) else { return nil }
        if let value = try? decode(Double.self, forKey: key), value.isFinite { return value }
        if let value = try? decode(String.self, forKey: key), let number = Double(value), number.isFinite { return number }
        throw DecodingError.typeMismatch(Double.self, .init(codingPath: codingPath + [key], debugDescription: "Invalid number"))
    }
    func optionalBool(_ name: String) throws -> Bool? {
        let key = SettingsJSONKey(name)
        guard contains(key), try !decodeNil(forKey: key) else { return nil }
        if let value = try? decode(Bool.self, forKey: key) { return value }
        if let value = try? decode(Int.self, forKey: key), value == 0 || value == 1 { return value == 1 }
        if let value = try? decode(String.self, forKey: key) {
            switch value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
            case "1", "true", "yes", "y", "on": return true
            case "0", "false", "no", "n", "off": return false
            default: break
            }
        }
        throw DecodingError.typeMismatch(Bool.self, .init(codingPath: codingPath + [key], debugDescription: "Invalid boolean"))
    }
}
