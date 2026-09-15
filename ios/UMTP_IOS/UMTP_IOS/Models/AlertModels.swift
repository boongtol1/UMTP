import Foundation

/// Server keys deliberately match Android and the backend. No old alert cache exists to migrate.
struct AlertItem: Decodable, Hashable, Identifiable {
    var id: Int = 0
    var alert_event_id: Int?
    var read_archive_event_id: Int?
    var user_id: String?
    var title: String?
    var message: String?
    var source: String?
    var listing_image_url: String?
    var product_url: String?
    var url: String?
    var sort_date: String?
    var alert_price_direction: String?
    var alert_condition_label: String?
    var alert_type_label: String?
    var product_type: String?
    var chip: String?
    var risk_level: String?
    var formatted_risk_label: String?
    var fraud_probability_label: String?
    var formatted_fraud_probability_label: String?
    var fraud_probability_text: String?
    var fraud_model_version: String?
    var fraud_scored_at: String?
    var fraud_probability_label_v1: String?
    var fraud_probability_v1_text: String?
    var fraud_model_version_v1: String?
    var fraud_scored_at_v1: String?
    var fraud_probability_label_v2: String?
    var fraud_probability_v2_text: String?
    var fraud_model_version_v2: String?
    var fraud_scored_at_v2: String?
    var fraud_probability_label_v3: String?
    var fraud_probability_v3_text: String?
    var fraud_model_version_v3: String?
    var fraud_scored_at_v3: String?
    var fraud_probability_delta_v2_minus_v1_text: String?
    var fraud_probability_delta_v3_minus_v2_text: String?
    var fraud_probability_comparison_text: String?
    var body_excerpt: String?
    var body_text: String?
    var trigger_reason: String?
    var refresh_notice_text: String?
    var special_notes_text: String?
    var analyzed_at: String?
    var created_at: String?
    var read_at: String?
    var read_archive_cleared_at: String?
    var listing_price_krw: Double?
    var fair_price_krw: Double?
    var user_market_price_krw: Double?
    var alert_target_price_krw: Double?
    var diff_ratio: Double?
    var price_gap_percent: Double?
    var alert_drop_rate_percent: Double?
    var screen_inch: Double?
    var ram_gb: Double?
    var ssd_gb: Double?
    var risk_score: Double?
    var fraud_probability: Double?
    var fraud_probability_v1: Double?
    var fraud_probability_v2: Double?
    var fraud_probability_v3: Double?
    var fraud_probability_delta_v2_minus_v1: Double?
    var fraud_probability_delta_v3_minus_v2: Double?
    var used_refresh_info: Bool?
    var is_read: Bool?
    var is_read_archive_cleared: Bool?
    var is_alert_target: Bool?
    var is_condition_change_candidate_notice: Bool?
    var risk_keywords: [String]?
    var trade_type_flags: TradeTypeFlags?

    init(id: Int = 0) { self.id = id }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AlertCodingKey.self)
        id = try c.alertInt("id") ?? 0
        alert_event_id = try c.alertInt("alert_event_id")
        read_archive_event_id = try c.alertInt("read_archive_event_id")
        user_id = try c.alertValue("user_id", as: String.self)
        title = try c.alertValue("title", as: String.self)
        message = try c.alertValue("message", as: String.self)
        source = try c.alertValue("source", as: String.self)
        listing_image_url = try c.alertValue("listing_image_url", as: String.self)
        product_url = try c.alertValue("product_url", as: String.self)
        url = try c.alertValue("url", as: String.self)
        sort_date = try c.alertValue("sort_date", as: String.self)
        alert_price_direction = try c.alertValue("alert_price_direction", as: String.self)
        alert_condition_label = try c.alertValue("alert_condition_label", as: String.self)
        alert_type_label = try c.alertValue("alert_type_label", as: String.self)
        product_type = try c.alertValue("product_type", as: String.self)
        chip = try c.alertValue("chip", as: String.self)
        risk_level = try c.alertValue("risk_level", as: String.self)
        formatted_risk_label = try c.alertValue("formatted_risk_label", as: String.self)
        fraud_probability_label = try c.alertValue("fraud_probability_label", as: String.self)
        formatted_fraud_probability_label = try c.alertValue("formatted_fraud_probability_label", as: String.self)
        fraud_probability_text = try c.alertValue("fraud_probability_text", as: String.self)
        fraud_model_version = try c.alertValue("fraud_model_version", as: String.self)
        fraud_scored_at = try c.alertValue("fraud_scored_at", as: String.self)
        fraud_probability_label_v1 = try c.alertValue("fraud_probability_label_v1", as: String.self)
        fraud_probability_v1_text = try c.alertValue("fraud_probability_v1_text", as: String.self)
        fraud_model_version_v1 = try c.alertValue("fraud_model_version_v1", as: String.self)
        fraud_scored_at_v1 = try c.alertValue("fraud_scored_at_v1", as: String.self)
        fraud_probability_label_v2 = try c.alertValue("fraud_probability_label_v2", as: String.self)
        fraud_probability_v2_text = try c.alertValue("fraud_probability_v2_text", as: String.self)
        fraud_model_version_v2 = try c.alertValue("fraud_model_version_v2", as: String.self)
        fraud_scored_at_v2 = try c.alertValue("fraud_scored_at_v2", as: String.self)
        fraud_probability_label_v3 = try c.alertValue("fraud_probability_label_v3", as: String.self)
        fraud_probability_v3_text = try c.alertValue("fraud_probability_v3_text", as: String.self)
        fraud_model_version_v3 = try c.alertValue("fraud_model_version_v3", as: String.self)
        fraud_scored_at_v3 = try c.alertValue("fraud_scored_at_v3", as: String.self)
        fraud_probability_delta_v2_minus_v1_text = try c.alertValue("fraud_probability_delta_v2_minus_v1_text", as: String.self)
        fraud_probability_delta_v3_minus_v2_text = try c.alertValue("fraud_probability_delta_v3_minus_v2_text", as: String.self)
        fraud_probability_comparison_text = try c.alertValue("fraud_probability_comparison_text", as: String.self)
        body_excerpt = try c.alertValue("body_excerpt", as: String.self)
        body_text = try c.alertValue("body_text", as: String.self)
        trigger_reason = try c.alertValue("trigger_reason", as: String.self)
        refresh_notice_text = try c.alertValue("refresh_notice_text", as: String.self)
        special_notes_text = try c.alertValue("special_notes_text", as: String.self)
        analyzed_at = try c.alertValue("analyzed_at", as: String.self)
        created_at = try c.alertValue("created_at", as: String.self)
        read_at = try c.alertValue("read_at", as: String.self)
        read_archive_cleared_at = try c.alertValue("read_archive_cleared_at", as: String.self)
        listing_price_krw = try c.alertDouble("listing_price_krw")
        fair_price_krw = try c.alertDouble("fair_price_krw")
        user_market_price_krw = try c.alertDouble("user_market_price_krw")
        alert_target_price_krw = try c.alertDouble("alert_target_price_krw")
        diff_ratio = try c.alertDouble("diff_ratio")
        price_gap_percent = try c.alertDouble("price_gap_percent")
        alert_drop_rate_percent = try c.alertDouble("alert_drop_rate_percent")
        screen_inch = try c.alertDouble("screen_inch")
        ram_gb = try c.alertDouble("ram_gb")
        ssd_gb = try c.alertDouble("ssd_gb")
        risk_score = try c.alertDouble("risk_score")
        fraud_probability = try c.alertDouble("fraud_probability")
        fraud_probability_v1 = try c.alertDouble("fraud_probability_v1")
        fraud_probability_v2 = try c.alertDouble("fraud_probability_v2")
        fraud_probability_v3 = try c.alertDouble("fraud_probability_v3")
        fraud_probability_delta_v2_minus_v1 = try c.alertDouble("fraud_probability_delta_v2_minus_v1")
        fraud_probability_delta_v3_minus_v2 = try c.alertDouble("fraud_probability_delta_v3_minus_v2")
        used_refresh_info = try c.alertBool("used_refresh_info")
        is_read = try c.alertBool("is_read")
        is_read_archive_cleared = try c.alertBool("is_read_archive_cleared")
        is_alert_target = try c.alertBool("is_alert_target")
        is_condition_change_candidate_notice = try c.alertBool("is_condition_change_candidate_notice")
        risk_keywords = try c.alertValue("risk_keywords", as: [String].self)
        trade_type_flags = try c.alertValue("trade_type_flags", as: TradeTypeFlags.self)
    }

    var eventID: Int { alert_event_id ?? id }
    var archiveIdentity: Int { read_archive_event_id ?? id }
}

struct TradeTypeFlags: Decodable, Hashable {
    var is_exchange = false
    var is_free = false
    var is_suspicious = false

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AlertCodingKey.self)
        is_exchange = try c.alertBool("is_exchange") ?? false
        is_free = try c.alertBool("is_free") ?? false
        is_suspicious = try c.alertBool("is_suspicious") ?? false
    }
}

struct AlertsResponse: Decodable {
    let items: [AlertItem]
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AlertCodingKey.self)
        try c.alertRequireSuccess()
        items = try c.alertValue("items", as: [AlertItem].self) ?? []
    }
}

struct GroupedReadAlertsResponse: Decodable {
    let groups: [String: [String: [AlertItem]]]
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AlertCodingKey.self)
        try c.alertRequireSuccess()
        groups = try c.alertValue("groups", as: [String: [String: [AlertItem]]].self) ?? [:]
    }
}

struct AlertMutationResponse: Decodable {
    let updated_count: Int?
    let cleared_count: Int?
    let skipped_count: Int?
    let not_found_ids: [Int]
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AlertCodingKey.self)
        try c.alertRequireSuccess()
        updated_count = try c.alertInt("updated_count")
        cleared_count = try c.alertInt("cleared_count")
        skipped_count = try c.alertInt("skipped_count")
        not_found_ids = try c.alertValue("not_found_ids", as: [Int].self) ?? []
    }
}

private struct AlertCodingKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init(_ value: String) { stringValue = value }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}

private extension KeyedDecodingContainer where Key == AlertCodingKey {
    func alertRequireSuccess() throws {
        guard try alertBool("ok") == true else {
            throw DecodingError.dataCorrupted(.init(codingPath: codingPath, debugDescription: "Expected explicit successful response"))
        }
    }

    func alertValue<T: Decodable>(_ key: String, as type: T.Type) throws -> T? {
        try decodeIfPresent(type, forKey: AlertCodingKey(key))
    }

    func alertDouble(_ key: String) throws -> Double? {
        let k = AlertCodingKey(key)
        guard contains(k), try !decodeNil(forKey: k) else { return nil }
        if let number = try? decode(Double.self, forKey: k), number.isFinite { return number }
        if let text = try? decode(String.self, forKey: k), let number = Double(text), number.isFinite { return number }
        throw DecodingError.dataCorruptedError(forKey: k, in: self, debugDescription: "Expected a finite number")
    }

    func alertInt(_ key: String) throws -> Int? {
        let k = AlertCodingKey(key)
        guard contains(k), try !decodeNil(forKey: k) else { return nil }
        // Read integers before Double to retain BIGINT precision above 2^53.
        if let value = try? decode(Int.self, forKey: k) { return value }
        if let value = try? decode(String.self, forKey: k), let integer = Int(value) { return integer }
        guard let number = try alertDouble(key) else { return nil }
        guard number.rounded(.towardZero) == number, let value = Int(exactly: number) else {
            throw DecodingError.dataCorruptedError(forKey: AlertCodingKey(key), in: self, debugDescription: "Expected an integer")
        }
        return value
    }

    func alertBool(_ key: String) throws -> Bool? {
        let k = AlertCodingKey(key)
        guard contains(k), try !decodeNil(forKey: k) else { return nil }
        if let value = try? decode(Bool.self, forKey: k) { return value }
        if let value = try? decode(Int.self, forKey: k), value == 0 || value == 1 { return value == 1 }
        if let value = try? decode(String.self, forKey: k) {
            switch value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
            case "true", "1", "yes", "y", "on": return true
            case "false", "0", "no", "n", "off": return false
            default: break
            }
        }
        throw DecodingError.dataCorruptedError(forKey: k, in: self, debugDescription: "Expected boolean, 0/1, or boolean string")
    }
}
