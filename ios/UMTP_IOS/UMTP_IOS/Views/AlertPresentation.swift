import Foundation

enum AlertDisplay {
    static let refreshNotice = "끌올된 정보를 사용한 알림입니다"
    static let candidateNotice = "정식 알림 기준은 저장 이후 매물이며, 이 항목은 참고용 후보입니다."
    static let changedReasons: Set<String> = ["content_changed", "title_changed", "price_changed", "body_changed", "self_check_changed"]

    static func text(_ value: String?) -> String? {
        guard let value = value?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else { return nil }
        return value
    }

    static func webURL(_ value: String?) -> URL? {
        guard let raw = text(value), let url = URL(string: raw),
              ["https", "http"].contains(url.scheme?.lowercased() ?? ""), url.host != nil else { return nil }
        return url
    }

    static func krw(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "정보 없음" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.locale = Locale(identifier: "ko_KR")
        formatter.maximumFractionDigits = 0
        return "\(formatter.string(from: NSNumber(value: value.rounded(.towardZero))) ?? "")원"
    }

    static func percent(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "정보 없음" }
        return String(format: "%.2f%%", value)
    }

    static func number(_ value: Double?, suffix: String) -> String {
        guard let value, value > 0 else { return "정보 없음" }
        return value.formatted(.number.precision(.fractionLength(0...2))) + suffix
    }

    static func fraudLabel(probability: Double?, explicit: String?) -> String {
        if let probability {
            return probability >= 0.65 ? "높음" : probability >= 0.25 ? "주의" : "낮음"
        }
        switch explicit?.uppercased() {
        case "LOW": return "낮음"
        case "MEDIUM": return "주의"
        case "HIGH": return "높음"
        default: return "정보 없음"
        }
    }

    static func fraud(probability: Double?, label: String, explicit: String?) -> String {
        if let explicit = text(explicit), explicit != "정보 없음" { return explicit }
        guard let probability else { return label }
        let percent = String(format: "%.0f%%", probability * 100)
        return label == "정보 없음" ? percent : "\(label) (\(percent))"
    }
}
extension AlertItem {
    var displayTitle: String { AlertDisplay.text(title) ?? AlertDisplay.text(message) ?? "제목 없음" }
    var resolvedURLText: String? { AlertDisplay.text(product_url) ?? AlertDisplay.text(url) }
    var resolvedURL: URL? { AlertDisplay.webURL(resolvedURLText) }
    var imageURL: URL? { AlertDisplay.webURL(listing_image_url) }
    var isCandidateNotice: Bool {
        is_condition_change_candidate_notice == true || is_alert_target == false ||
            trigger_reason?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "condition_change_candidate_notice"
    }
    var isContentChange: Bool {
        AlertDisplay.changedReasons.contains(trigger_reason?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? "")
    }
    var displayType: String {
        AlertDisplay.text(alert_type_label) ?? (isCandidateNotice ? "참고 알림 (조건 변경 사이 후보)" : isContentChange ? "내용 변경 알림" : "정식 알림")
    }
    var displayCondition: String {
        if isCandidateNotice { return "조건 변경 사이 후보" }
        if let explicit = AlertDisplay.text(alert_condition_label),
           !(isContentChange && ["내용변경알림", "내용 변경 알림"].contains(explicit)) { return explicit }
        return alert_price_direction?.uppercased() == "ABOVE_OR_EQUAL" ? "이 가격 이상이면 알림" : "이 가격 이하이면 알림"
    }
    var displayFraudLabel: String {
        if let explicit = AlertDisplay.text(formatted_fraud_probability_label), explicit != "정보 없음" { return explicit }
        return AlertDisplay.fraudLabel(probability: fraud_probability, explicit: fraud_probability_label)
    }
    var displayFraud: String {
        AlertDisplay.fraud(probability: fraud_probability, label: displayFraudLabel, explicit: fraud_probability_text)
    }
    var displayBody: String { AlertDisplay.text(body_text) ?? AlertDisplay.text(body_excerpt) ?? "본문 내용 없음" }
    var usesRefreshInfo: Bool {
        used_refresh_info == true || AlertDisplay.text(refresh_notice_text) != nil ||
            ["sort_date_changed", "refresh_key_changed"].contains(trigger_reason?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? "") ||
            [message, body_excerpt, body_text, special_notes_text].contains { $0?.contains(AlertDisplay.refreshNotice) == true }
    }
    var displayPreview: String? {
        let body = AlertDisplay.text(body_excerpt) ?? AlertDisplay.text(body_text)
        guard usesRefreshInfo else { return body }
        let notice = AlertDisplay.text(refresh_notice_text) ?? AlertDisplay.refreshNotice
        guard let body else { return notice }
        return body.contains(notice) ? body : notice + "\n" + body
    }
    var displayTradeFlags: String {
        guard let flags = trade_type_flags else { return "정보 없음" }
        let labels = [(flags.is_exchange, "교환"), (flags.is_free, "나눔"), (flags.is_suspicious, "허위/의심")]
            .filter { $0.0 }.map { $0.1 }
        return labels.isEmpty ? "특이사항 없음" : labels.joined(separator: ", ")
    }
    var displayKeywords: String {
        guard let keywords = risk_keywords, !keywords.isEmpty else { return "특이사항 없음" }
        return keywords.joined(separator: ", ")
    }
    var displayNotes: String {
        if let explicit = AlertDisplay.text(special_notes_text) { return explicit }
        var notes: [String] = []
        if usesRefreshInfo { notes.append(AlertDisplay.text(refresh_notice_text) ?? AlertDisplay.refreshNotice) }
        if ["주의", "높음", "위험"].contains(displayFraudLabel) { notes.append("사기 가능성 \(displayFraudLabel)") }
        if !["특이사항 없음", "정보 없음"].contains(displayTradeFlags) { notes.append("거래 유형: \(displayTradeFlags)") }
        if displayKeywords != "특이사항 없음" { notes.append("위험 키워드: \(displayKeywords)") }
        return notes.isEmpty ? "특이사항 없음" : notes.joined(separator: " / ")
    }
    var displaySpec: String {
        var parts = [AlertDisplay.text(product_type), AlertDisplay.text(chip)].compactMap { $0 }
        if let screen_inch, screen_inch > 0 { parts.append(AlertDisplay.number(screen_inch, suffix: "인치")) }
        if let ram_gb, ram_gb > 0 { parts.append(AlertDisplay.number(ram_gb, suffix: "GB")) }
        if let ssd_gb, ssd_gb > 0 { parts.append(AlertDisplay.number(ssd_gb, suffix: "GB SSD")) }
        return parts.isEmpty ? "분류 정보 없음" : parts.joined(separator: " · ")
    }

    func detailRows(archive: Bool) -> [(String, String)] {
        let score = fraud_probability.map { "\(Int(min(100, max(0, ($0 * 100).rounded()))))점" } ?? "정보 없음"
        var rows: [(String, String)] = [
            ("알림 유형", displayType),
            ("참고 안내", isCandidateNotice ? AlertDisplay.candidateNotice : "-"),
            ("출처", source == "umtp_notice" ? "UMTP 참고 알림" : AlertDisplay.text(source) ?? "정보 없음"),
            ("URL", resolvedURLText ?? "URL 정보 없음"),
            ("대표 이미지", AlertDisplay.text(listing_image_url) ?? "이미지 없음"),
            ("제품 분류", AlertDisplay.text(product_type) ?? "분류 정보 없음"),
            ("칩", AlertDisplay.text(chip) ?? "정보 없음"),
            ("화면 크기", AlertDisplay.number(screen_inch, suffix: "인치")),
            ("RAM", AlertDisplay.number(ram_gb, suffix: "GB")),
            ("SSD", AlertDisplay.number(ssd_gb, suffix: "GB")),
            ("등록 가격", AlertDisplay.krw(listing_price_krw ?? alert_target_price_krw)),
            ("내가 생각한 시장가", AlertDisplay.krw(user_market_price_krw ?? fair_price_krw)),
            ("알림 기준 가격", AlertDisplay.krw(alert_target_price_krw)),
            ("시장가와의 차이", AlertDisplay.percent(price_gap_percent ?? diff_ratio ?? alert_drop_rate_percent)),
            ("설정 차이율", AlertDisplay.percent(alert_drop_rate_percent)),
            ("알림 조건", displayCondition), ("사기 가능성", displayFraud),
            ("위험도", displayFraudLabel), ("위험 점수", score),
            ("위험 키워드", displayKeywords), ("본문 내용", displayBody),
            ("매물 등록 시각", AlertDisplay.text(sort_date) ?? "정보 없음"),
            ("알림 생성 시각", AlertDisplay.text(created_at) ?? "정보 없음"),
            ("분석 시각", AlertDisplay.text(analyzed_at) ?? AlertDisplay.text(created_at) ?? "분석 시각 정보 없음"),
            ("교환/나눔/의심", displayTradeFlags), ("특이사항", displayNotes)
        ]
        if archive { rows.insert(("읽음 시각", read_at ?? "정보 없음"), at: 2) }
        let versions = [
            ("V1", fraud_probability_v1, fraud_probability_label_v1, fraud_probability_v1_text, fraud_model_version_v1, fraud_scored_at_v1),
            ("V2", fraud_probability_v2, fraud_probability_label_v2, fraud_probability_v2_text, fraud_model_version_v2, fraud_scored_at_v2),
            ("V3", fraud_probability_v3, fraud_probability_label_v3, fraud_probability_v3_text, fraud_model_version_v3, fraud_scored_at_v3)
        ]
        for (version, probability, label, explicit, model, scored) in versions {
            if probability != nil || explicit != nil || label != nil {
                rows.append(("사기 가능성 \(version)", AlertDisplay.fraud(probability: probability, label: AlertDisplay.fraudLabel(probability: probability, explicit: label), explicit: explicit)))
            }
            if let model = AlertDisplay.text(model) { rows.append(("\(version) 모델", model)) }
            if let scored = AlertDisplay.text(scored) { rows.append(("\(version) 평가 시각", scored)) }
        }
        if let comparison = AlertDisplay.text(fraud_probability_comparison_text) { rows.append(("사기 모델 비교", comparison)) }
        if let delta = AlertDisplay.text(fraud_probability_delta_v2_minus_v1_text) { rows.append(("V2 - V1", delta)) }
        else if let delta = fraud_probability_delta_v2_minus_v1 { rows.append(("V2 - V1", AlertDisplay.percent(delta * 100))) }
        if let delta = AlertDisplay.text(fraud_probability_delta_v3_minus_v2_text) { rows.append(("V3 - V2", delta)) }
        else if let delta = fraud_probability_delta_v3_minus_v2 { rows.append(("V3 - V2", AlertDisplay.percent(delta * 100))) }
        if let model = AlertDisplay.text(fraud_model_version) { rows.append(("사기 평가 모델", model)) }
        if let scored = AlertDisplay.text(fraud_scored_at) { rows.append(("사기 평가 시각", scored)) }
        return rows
    }
}
