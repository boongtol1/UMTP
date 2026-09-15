import Foundation

/// Trade rows contain nullable MySQL numbers, boolean integers and JSON image strings.
/// Preserve every returned field when displaying a row; write only validated changed fields.
enum TradeValue: Codable, Equatable {
    case string(String), whole(Int), number(Double), bool(Bool), object([String: TradeValue]), array([TradeValue]), null

    init(from decoder: Decoder) throws {
        let box = try decoder.singleValueContainer()
        if box.decodeNil() { self = .null }
        else if let value = try? box.decode(Bool.self) { self = .bool(value) }
        else if let value = try? box.decode(Int.self) { self = .whole(value) }
        else if let value = try? box.decode(Double.self) { self = .number(value) }
        else if let value = try? box.decode(String.self) { self = .string(value) }
        else if let value = try? box.decode([String: TradeValue].self) { self = .object(value) }
        else { self = .array(try box.decode([TradeValue].self)) }
    }

    func encode(to encoder: Encoder) throws {
        var box = encoder.singleValueContainer()
        switch self {
        case .string(let value): try box.encode(value)
        case .whole(let value): try box.encode(value)
        case .number(let value): try box.encode(value)
        case .bool(let value): try box.encode(value)
        case .object(let value): try box.encode(value)
        case .array(let value): try box.encode(value)
        case .null: try box.encodeNil()
        }
    }

    var text: String {
        switch self {
        case .string(let value): return value
        case .whole(let value): return String(value)
        case .number(let value):
            guard value.isFinite else { return "" }
            return value.rounded() == value ? String(format: "%.0f", value) : String(value)
        case .bool(let value): return value ? "true" : "false"
        case .null: return ""
        case .object, .array:
            return (try? JSONEncoder().encode(self)).flatMap { String(data: $0, encoding: .utf8) } ?? ""
        }
    }

    var boolValue: Bool? {
        switch text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "true", "1", "yes", "y", "on": return true
        case "false", "0", "no", "n", "off": return false
        default: return nil
        }
    }

    var integer: Int? {
        if let integer = Int(text) { return integer }
        guard let number = Double(text), number.isFinite, number.rounded() == number,
              number >= Double(Int.min), number < Double(Int.max) else { return nil }
        return Int(number)
    }

    var imageURLs: [URL] {
        switch self {
        case .string(let text):
            if let data = text.data(using: .utf8), let value = try? JSONDecoder().decode(TradeValue.self, from: data), value != self {
                return value.imageURLs
            }
            guard let url = URL(string: text), url.host?.isEmpty == false,
                  ["https", "http"].contains(url.scheme?.lowercased() ?? "") else { return [] }
            return [url]
        case .array(let values): return values.flatMap(\.imageURLs)
        case .object(let values):
            // Match Android's image-field priority before inspecting wrapper containers.
            // A listing/click URL must not displace a supplied representative image.
            for key in ["image_url", "imageUrl", "thumbnail_url", "thumbnailUrl", "thumbnail"] {
                let images = values[key]?.imageURLs ?? []
                if !images.isEmpty { return images }
            }
            return values.keys.sorted().flatMap { values[$0]?.imageURLs ?? [] }
        default: return []
        }
    }
}

struct ResaleTradeRow: Codable, Equatable, Identifiable {
    var values: [String: TradeValue]
    init(values: [String: TradeValue] = [:]) { self.values = values }
    init(from decoder: Decoder) throws { values = try decoder.singleValueContainer().decode([String: TradeValue].self) }
    func encode(to encoder: Encoder) throws {
        var box = encoder.singleValueContainer()
        try box.encode(values)
    }
    var id: Int? { values["id"]?.integer }
    subscript(_ key: String) -> String { values[key]?.text ?? "" }
    var title: String { self["title"].isEmpty ? "(제목없음)" : self["title"] }
    var imageURL: URL? { values["image_urls"]?.imageURLs.first }
    var stageLabel: String {
        switch self["current_stage"].uppercased() {
        case "DISCOVERED": return "발견됨"
        case "INSPECTED": return "구매/점검"
        case "RESALE_LISTED": return "재판매 등록"
        case "SOLD": return "판매 완료"
        case "KEEP": return "보유(KEEP)"
        default: return self["current_stage"].isEmpty ? "-" : self["current_stage"]
        }
    }
    func amount(_ key: String) -> String {
        guard let amount = values[key]?.integer else { return "-" }
        return amount.formatted(.number.locale(Locale(identifier: "ko_KR"))) + "원"
    }
}

struct TradeResponse: Decodable {
    let values: [String: TradeValue]
    init(from decoder: Decoder) throws { values = try decoder.singleValueContainer().decode([String: TradeValue].self) }
    var ok: Bool { values["ok"]?.boolValue == true }
    var existing: Bool { values["existing"]?.boolValue == true }
    var reason: String { values["reason"]?.text ?? "" }
    var deletedCount: Int { values["deleted_count"]?.integer ?? 0 }
    var row: ResaleTradeRow? {
        guard case .object(var row) = values["row"] else { return nil }
        for key in ["id", "source", "product_id", "current_stage"] where row[key] == nil || row[key] == .null {
            row[key] = values[key]
        }
        if row["id"] == nil || row["id"] == .null { row["id"] = values["trade_journey_id"] }
        return ResaleTradeRow(values: row)
    }
    var items: [ResaleTradeRow] {
        guard case .array(let items) = values["items"] else { return [] }
        return items.compactMap { if case .object(let row) = $0 { return ResaleTradeRow(values: row) }; return nil }
    }
    func checked() throws -> TradeResponse {
        guard ok else { throw TradeError.server(reason) }
        return self
    }
}

enum TradeMode: String, CaseIterable, Identifiable {
    case purchase = "구매 후 기록", resale = "되팔이 후 기록"
    var id: String { rawValue }
    var endpoint: String { self == .purchase ? "purchase" : "resale" }
}

struct TradeField: Identifiable {
    let id: String
    let label: String
    init(_ id: String, _ label: String) { self.id = id; self.label = label }

    static let verification = [
        TradeField("serial_number", "일련번호"), TradeField("model_number", "정확한 모델번호"),
        TradeField("battery_cycle_count", "배터리 사이클 수"), TradeField("battery_health_percent", "배터리 성능 최대치 %"),
        TradeField("activation_lock_off", "활성화 잠금 해제 확인"), TradeField("mdm_lock_none", "MDM 잠금 없음 확인")
    ]
    static let purchase = [
        TradeField("title", "제목"), TradeField("listing_price_krw", "등록 가격 (원)"),
        TradeField("seller_nickname", "판매자 닉네임"), TradeField("body_text", "본문 내용"),
        TradeField("fair_price_krw", "적정 가격 (원)"), TradeField("seller_location", "판매자 위치"),
        TradeField("contacted_at", "연락 시각"), TradeField("seller_response_at", "판매자 응답 시각"),
        TradeField("purchased_at", "구매 시각"), TradeField("purchase_method", "구매 방법"),
        TradeField("purchase_location", "구매 장소"), TradeField("purchase_price_krw", "구매 가격 (원)"),
        TradeField("transport_cost_krw", "교통비 (원)"), TradeField("shipping_cost_krw", "배송비 (원)"),
        TradeField("payment_method", "결제 수단"), TradeField("sale_platform", "구매 플랫폼"),
        TradeField("inspection_notes", "제품 점검 메모"), TradeField("current_stage", "현재 단계")
    ]
    static let resale = [
        TradeField("resale_platform", "재판매 플랫폼"), TradeField("resale_url", "재판매 URL"),
        TradeField("resale_listing_price_krw", "재판매 등록가 (원)"), TradeField("buyer_nickname", "구매자 닉네임"),
        TradeField("sale_method", "판매 방법"), TradeField("sale_location", "판매 장소"),
        TradeField("sold_at", "판매 시각"), TradeField("sale_price_krw", "판매 가격 (원)"),
        TradeField("current_stage", "현재 단계")
    ]
    static let numeric = Set(["listing_price_krw", "fair_price_krw", "purchase_price_krw", "transport_cost_krw", "shipping_cost_krw", "resale_listing_price_krw", "sale_price_krw", "battery_cycle_count", "battery_health_percent"])
    static let boolean = Set(["activation_lock_off", "mdm_lock_none"])
    static let dates = Set(["contacted_at", "seller_response_at", "purchased_at", "sold_at"])
    static let all = purchase + resale + verification

    static func parse(_ key: String, text: String) throws -> TradeValue? {
        let text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return nil }
        let label = all.first { $0.id == key }?.label ?? "입력값"
        if numeric.contains(key) {
            guard let integer = Int(text.replacingOccurrences(of: ",", with: "")), integer >= 0,
                  integer <= Int(Int32.max), key != "battery_health_percent" || integer <= 100 else {
                throw TradeError.validation("\(label)을 올바른 정수로 입력해 주세요.")
            }
            return .number(Double(integer))
        }
        if boolean.contains(key) {
            guard let value = TradeValue.string(text).boolValue else { throw TradeError.validation("\(label)을 선택해 주세요.") }
            return .bool(value)
        }
        if dates.contains(key), !validDate(text) { throw TradeError.validation("\(label)은 YYYY-MM-DD HH:mm 형식으로 입력해 주세요.") }
        if key == "current_stage", !["DISCOVERED", "INSPECTED", "RESALE_LISTED", "SOLD", "KEEP"].contains(text.uppercased()) {
            throw TradeError.validation("현재 단계를 목록에서 선택해 주세요.")
        }
        if key == "resale_url" {
            guard text.rangeOfCharacter(from: .whitespacesAndNewlines) == nil,
                  let url = URL(string: text), url.host?.isEmpty == false,
                  ["http", "https"].contains(url.scheme?.lowercased() ?? "") else {
                throw TradeError.validation("재판매 URL은 http 또는 https 주소로 입력해 주세요.")
            }
            return .string(text)
        }
        return .string(key == "current_stage" ? text.uppercased() : text)
    }

    static func validDate(_ text: String) -> Bool {
        // ISO8601DateFormatter normalizes impossible dates such as February 30.
        // Validate calendar/time components before accepting an offset-aware value.
        let day = String(text.prefix(10))
        let calendar = DateFormatter()
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)
        calendar.dateFormat = day.contains("/") ? "yyyy/MM/dd" : "yyyy-MM-dd"
        calendar.isLenient = false
        guard let date = calendar.date(from: day), calendar.string(from: date) == day else { return false }
        if text.count > 10 {
            let pattern = #"[T ]([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?"#
            guard let regex = try? NSRegularExpression(pattern: pattern),
                  let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) else { return false }
            let source = text as NSString
            for (index, maximum) in [(1, 23), (2, 59), (3, 59)] where match.range(at: index).location != NSNotFound {
                guard let component = Int(source.substring(with: match.range(at: index))), component <= maximum else { return false }
            }
        }
        for format in ["yyyy-MM-dd", "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm", "yyyy-MM-dd'T'HH:mm", "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ss.SSS", "yyyy/MM/dd HH:mm:ss", "yyyy/MM/dd HH:mm"] {
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = format
            formatter.isLenient = false
            if let value = formatter.date(from: text), formatter.string(from: value) == text { return true }
        }
        let formatter = ISO8601DateFormatter()
        if text.dropFirst(10).first == " " {
            // Python's datetime.fromisoformat also accepts the SQL-style separator
            // with a UTC offset. Keep the strict date/time checks above for both forms.
            formatter.formatOptions.insert(.withSpaceBetweenDateAndTime)
        }
        if formatter.date(from: text) != nil { return true }
        formatter.formatOptions.insert(.withFractionalSeconds)
        return formatter.date(from: text) != nil
    }

    static func changes(fields: [TradeField], inputs: [String: String], baseline: ResaleTradeRow) throws -> [String: TradeValue] {
        var result: [String: TradeValue] = [:]
        for field in fields {
            let raw = inputs[field.id] ?? ""
            if raw == baseline[field.id] { continue }
            guard let value = try parse(field.id, text: raw) else { continue }
            let old = try? parse(field.id, text: baseline[field.id])
            if value != old { result[field.id] = value }
        }
        return result
    }
}

enum TradeError: LocalizedError {
    case server(String), missingRow, validation(String), partialSave, resaleSaveUnconfirmed
    var errorDescription: String? {
        switch self {
        case .validation(let message): return message
        case .missingRow: return "서버에서 거래 기록을 받지 못했습니다. 다시 시도해 주세요."
        case .partialSave: return "정확 확인 정보는 저장되었지만 되팔이 기록 저장에 실패했습니다. 입력을 확인하고 다시 저장해 주세요."
        case .resaleSaveUnconfirmed: return "거래 기록은 준비되었지만 되팔이 입력의 저장 완료를 확인하지 못했습니다. 입력을 유지한 채 다시 저장해 주세요."
        case .server(let reason):
            if reason.contains("not_found") { return "거래 또는 알림 기록을 찾지 못했습니다. 목록을 새로고침해 주세요." }
            if reason.contains("user_not_registered") { return "등록된 사용자 정보를 확인할 수 없습니다. 다시 로그인해 주세요." }
            if reason.contains("invalid_url") || reason.contains("invalid_product_id") { return "URL 또는 product_id를 확인해 주세요." }
            return "거래 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."
        }
    }
}
