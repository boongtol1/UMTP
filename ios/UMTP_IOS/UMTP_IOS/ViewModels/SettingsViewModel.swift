import Combine
import Foundation

extension Notification.Name {
    static let umtpSettingsDidChange = Notification.Name("umtp.settingsDidChange")
}

struct SettingDraft: Equatable {
    var marketText: String
    var targetText: String
    var gapText: String
    var direction: AlertPriceDirection
    var minimumText: String
    var maximumText: String
    var enabled: Bool
    var candidateNotice: Bool
    var keyword: String
    var priority: WatchPriority
    var usesPercentage = false

    init(setting: UserFairPriceItem?) {
        let fair = setting?.marketPrice
        // Keep the server's saved won amount when available. Reconstructing it
        // from a rounded percentage can shift the amount on every edit cycle.
        let target = setting?.user_target_buy_price_krw ?? setting?.effective_target_buy_price_krw
            ?? SettingsPriceMath.target(market: fair, gap: setting?.dropRate)
        marketText = fair.map(String.init) ?? ""
        targetText = target.map(String.init) ?? ""
        gapText = SettingsPriceMath.gap(market: fair, target: target).map { String(format: "%.2f", locale: Locale(identifier: "en_US_POSIX"), $0) } ?? ""
        direction = setting?.direction ?? .below
        minimumText = setting?.minimumPrice.map(String.init) ?? ""
        maximumText = setting?.maximumPrice.map(String.init) ?? ""
        enabled = setting?.enabled ?? false
        candidateNotice = setting?.condition_change_candidate_notice_enabled ?? false
        keyword = setting?.custom_search_keyword ?? setting?.effective_search_keyword ?? ""
        priority = WatchPriority(serverValue: setting?.priority)
    }

    mutating func changeMarket(_ text: String) {
        marketText = text
        if usesPercentage {
            targetText = SettingsPriceMath.target(market: Int(text), gap: Double(gapText)).map(String.init) ?? ""
        } else {
            updateGap()
        }
    }
    mutating func changeTarget(_ text: String) {
        targetText = text; usesPercentage = false; updateGap()
    }
    mutating func changeGap(_ text: String) {
        gapText = text; usesPercentage = true
        targetText = SettingsPriceMath.target(market: Int(marketText), gap: Double(text)).map(String.init) ?? ""
    }
    private mutating func updateGap() {
        gapText = SettingsPriceMath.gap(market: Int(marketText), target: Int(targetText)).map { String(format: "%.2f", locale: Locale(identifier: "en_US_POSIX"), $0) } ?? ""
    }
    func request(userID: String, unit: MacUnit, interval: Int = 60) throws -> FairPriceUpsertRequest {
        // A 100% gap is valid in the server contract and produces a zero-won
        // target. Keep that setting editable after a bulk update or reload.
        guard let fair = Int(marketText), fair > 0, fair <= Int(Int32.max),
              let target = Int(targetText), target >= 0, target <= Int(Int32.max) else { throw SettingsInputError.price }
        guard let gap = SettingsPriceMath.gap(market: fair, target: target), gap.isFinite,
              (-100...100).contains(gap) else { throw SettingsInputError.percentage }
        let boundText = (direction == .below ? minimumText : maximumText).trimmingCharacters(in: .whitespacesAndNewlines)
        let bound = Int(boundText)
        guard boundText.isEmpty || (bound != nil && bound! >= 0 && bound! <= Int(Int32.max)) else { throw SettingsInputError.bound }
        let normalizedKeyword = keyword.trimmingCharacters(in: .whitespacesAndNewlines)
        guard normalizedKeyword.count <= 255 else { throw SettingsInputError.keyword }
        return FairPriceUpsertRequest(
            user_id: userID, product_type: unit.product_type, chip: unit.chip, screen_inch: unit.screen_inch,
            ram_gb: unit.ram_gb, ssd_gb: unit.ssd_gb, fair_price_krw: fair, alert_drop_rate_percent: gap,
            alert_price_direction: direction.rawValue, min_price_krw: direction == .below ? bound : nil,
            max_price_krw: direction == .above ? bound : nil, enabled: enabled,
            condition_change_candidate_notice_enabled: candidateNotice,
            search_keyword: normalizedKeyword.isEmpty ? nil : normalizedKeyword, poll_interval_seconds: max(1, interval),
            priority: priority.rawValue
        )
    }
}

struct SettingsScope: Equatable, Hashable {
    var product: String
    var chip: String?
    var screen: Int?
    func contains(_ unit: MacUnit) -> Bool {
        unit.product_type == product && (chip == nil || unit.chip == chip) && (screen == nil || unit.screen_inch == screen)
    }
    var label: String {
        [chip, product, screen.flatMap { $0 > 0 ? "\($0)인치" : nil }].compactMap { $0 }.joined(separator: " ")
    }
}

enum SettingsBulkChange: Equatable {
    case alerts(Bool), candidate(Bool), priority(WatchPriority), gap(Double), minimum(Int), maximum(Int), resetMarket
    var label: String {
        switch self {
        case .alerts(let enabled): enabled ? "전체 알림 켜기" : "전체 알림 끄기"
        case .candidate(let enabled): enabled ? "조건 변경 후보 알림 켜기" : "조건 변경 후보 알림 끄기"
        case .priority(let priority): "전체 알림 속도 \(priority.label) 적용"
        case .gap(let percent): "전체 차이 \(SettingsPriceMath.percent(percent)) 적용"
        case .minimum(let price): "전체 최소 가격 \(SettingsPriceMath.money(price)) 적용"
        case .maximum(let price): "전체 최대 가격 \(SettingsPriceMath.money(price)) 적용"
        case .resetMarket: "시스템 기준 시장가로 초기화"
        }
    }
}

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published private(set) var units: [MacUnit] = []
    @Published private(set) var settings: [UserFairPriceItem] = []
    @Published private(set) var drafts: [String: SettingDraft] = [:]
    @Published private(set) var dirtyKeys: Set<String> = []
    @Published private(set) var isLoading = false
    @Published private(set) var isRefreshing = false
    @Published private(set) var isApplyingBulk = false
    @Published private(set) var savingKey: String?
    @Published private(set) var refreshingRules: Set<Int64> = []
    @Published private(set) var refreshStatus: String?
    @Published private(set) var lastRefresh: String?
    @Published private(set) var ruleRefreshLabels: [Int64: String] = [:]
    @Published var message: String?
    private let api: any SettingsAPIProtocol
    private var userID: String?
    private var loadGeneration = 0
    var isBusy: Bool { isLoading || isRefreshing || isApplyingBulk || savingKey != nil || !refreshingRules.isEmpty }

    init(api: (any SettingsAPIProtocol)? = nil) { self.api = api ?? SettingsAPI() }

    var products: [String] {
        Array(Set(units.map(\.product_type))).sorted { (MacUnit.productOrder($0), $0) < (MacUnit.productOrder($1), $1) }
    }
    func chips(product: String) -> [String] {
        Array(Set(units.filter { $0.product_type == product }.map(\.chip))).sorted { (MacUnit.chipOrder($0), $0) < (MacUnit.chipOrder($1), $1) }
    }
    func screens(product: String, chip: String) -> [Int] {
        Array(Set(units.filter { $0.product_type == product && $0.chip == chip && $0.screen_inch > 0 }.map(\.screen_inch))).sorted()
    }
    func item(for unit: MacUnit) -> UserFairPriceItem? { settings.first { $0.id == unit.id } }
    func draft(for unit: MacUnit) -> SettingDraft { drafts[unit.id] ?? SettingDraft(setting: item(for: unit)) }
    func edit(_ unit: MacUnit, _ change: (inout SettingDraft) -> Void) {
        var value = draft(for: unit); change(&value); drafts[unit.id] = value; dirtyKeys.insert(unit.id)
    }
    func scopedSettings(_ scope: SettingsScope) -> [UserFairPriceItem] { settings.filter { scope.contains($0.unit) } }

    func load(userID nextID: String) async {
        if userID == nextID && ((!units.isEmpty && !settings.isEmpty) || isLoading) { return }
        loadGeneration += 1
        let generation = loadGeneration
        if userID != nextID {
            units = []; settings = []; drafts = [:]; dirtyKeys = []; ruleRefreshLabels = [:]
            refreshStatus = nil; lastRefresh = nil
        }
        userID = nextID
        isLoading = true
        var errors: [String] = []
        do {
            let value = try await api.units()
            guard generation == loadGeneration else { return }
            units = value
        } catch { errors.append(error.localizedDescription) }
        do {
            let value = try await api.settings(userID: nextID)
            guard generation == loadGeneration else { return }
            merge(value)
        } catch { errors.append(error.localizedDescription) }
        guard generation == loadGeneration else { return }
        isLoading = false
        if !errors.isEmpty { refreshStatus = "불러오기 실패"; message = errors.joined(separator: "\n") }
    }

    func refresh() async {
        guard let userID, !isBusy else { return }
        isRefreshing = true; refreshStatus = "새로고침 중..."
        defer { isRefreshing = false }
        var errors: [String] = []
        do { try await api.refreshRules(userID: userID, ruleID: nil) }
        catch { errors.append(error.localizedDescription) }
        do { units = try await api.units() }
        catch { errors.append(error.localizedDescription) }
        do { merge(try await api.settings(userID: userID)) }
        catch { errors.append(error.localizedDescription) }
        if errors.isEmpty {
            refreshStatus = "새로고침됨"; lastRefresh = Self.timeLabel()
            for item in settings where item.has_user_override && item.enabled {
                if let id = item.ruleID { ruleRefreshLabels[id] = lastRefresh }
            }
        } else {
            refreshStatus = "새로고침 실패"; message = errors.joined(separator: "\n")
        }
        NotificationCenter.default.post(name: .umtpSettingsDidChange, object: nil)
    }

    func refreshRule(_ item: UserFairPriceItem) async {
        guard let userID, let id = item.ruleID, id > 0, item.enabled, item.has_user_override, !isBusy else { return }
        refreshingRules.insert(id)
        defer { refreshingRules.remove(id) }
        do {
            try await api.refreshRules(userID: userID, ruleID: id)
            ruleRefreshLabels[id] = Self.timeLabel()
            merge(try await api.settings(userID: userID))
            NotificationCenter.default.post(name: .umtpSettingsDidChange, object: nil)
        } catch { ruleRefreshLabels[id] = "새로고침 실패"; message = error.localizedDescription }
    }

    @discardableResult
    func save(_ unit: MacUnit) async -> Bool {
        guard let userID, !isBusy else { return false }
        do {
            // The units endpoint is a catalog, not the user's saved settings.
            // Never overwrite an unknown existing row using empty draft defaults.
            guard let original = item(for: unit) else { throw SettingsInputError.incomplete }
            let request = try draft(for: unit).request(userID: userID, unit: unit, interval: original.poll_interval_seconds ?? 60)
            savingKey = unit.id
            defer { savingKey = nil }
            let response = try await api.save(request)
            guard response.ok else { throw SettingsInputError.server }
            dirtyKeys.remove(unit.id)
            applyConfirmed(request, to: original)
            message = request.enabled
                ? (response.immediate_poll_requested == true ? "저장 완료. 즉시 검색을 요청했어요." : "저장은 완료됐지만, 즉시 검색 요청은 보내지 못했어요. 잠시 후 다시 시도해 주세요.")
                : "저장 완료."
            do { merge(try await api.settings(userID: userID)) }
            catch { message = "저장은 완료됐지만 최신 설정을 불러오지 못했습니다. 새로고침해주세요." }
            NotificationCenter.default.post(name: .umtpSettingsDidChange, object: nil)
            return true
        } catch { message = error.localizedDescription; return false }
    }

    // Batch updates use the same full upsert contract as Android; each completed
    // request may change saved_at. Report partial success and reconcile afterward.
    func apply(_ change: SettingsBulkChange, scope: SettingsScope) async {
        guard let userID, !isBusy else { return }
        let source = scopedSettings(scope)
        guard !source.isEmpty else { message = SettingsInputError.emptyScope.localizedDescription; return }
        isApplyingBulk = true
        defer { isApplyingBulk = false }
        var completed = 0
        var skipped = 0
        var failure: Error?
        for item in source {
            do {
                guard let request = try Self.bulkRequest(change, item: item, userID: userID) else { skipped += 1; continue }
                let response = try await api.save(request)
                guard response.ok else { throw SettingsInputError.server }
                applyConfirmed(request, to: item, bulkChange: change)
                completed += 1
            } catch { failure = error; break }
        }
        do { merge(try await api.settings(userID: userID)) }
        catch { if failure == nil { failure = error } }
        if let failure {
            message = "\(completed)건 적용, \(skipped)건 건너뜀. 나머지 적용 또는 새로고침에 실패했습니다.\n\(failure.localizedDescription)"
        } else if completed == 0 {
            message = "적용할 항목이 없습니다. \(skipped)건은 방향 또는 시스템 시장가를 확인해주세요."
        } else {
            message = "\(change.label) 완료 (\(completed)건 적용, \(skipped)건 건너뜀)"
        }
        NotificationCenter.default.post(name: .umtpSettingsDidChange, object: nil)
    }

    static func bulkRequest(_ change: SettingsBulkChange, item: UserFairPriceItem, userID: String) throws -> FairPriceUpsertRequest? {
        var market = item.marketPrice
        var gap = item.dropRate
        var enabled = item.enabled
        var candidate = item.condition_change_candidate_notice_enabled
        var priority = WatchPriority(serverValue: item.priority)
        var bound = item.direction == .below ? item.minimumPrice : item.maximumPrice
        switch change {
        case .alerts(let value): enabled = value
        case .candidate(let value): candidate = value
        case .priority(let value): priority = value
        case .gap(let value): gap = value
        case .minimum(let value):
            guard item.direction == .below else { return nil }; bound = value
        case .maximum(let value):
            guard item.direction == .above else { return nil }; bound = value
        case .resetMarket: market = item.system_fair_price_krw
        }
        guard let market, market > 0 else { return nil }
        guard gap.isFinite, (-100...100).contains(gap) else { throw SettingsInputError.percentage }
        guard bound == nil || bound! >= 0 else { throw SettingsInputError.bound }
        let keyword = item.custom_search_keyword?.trimmingCharacters(in: .whitespacesAndNewlines)
        return FairPriceUpsertRequest(
            user_id: userID, product_type: item.unit.product_type, chip: item.unit.chip,
            screen_inch: item.unit.screen_inch, ram_gb: item.unit.ram_gb, ssd_gb: item.unit.ssd_gb,
            fair_price_krw: market, alert_drop_rate_percent: gap, alert_price_direction: item.direction.rawValue,
            min_price_krw: item.direction == .below ? bound : nil, max_price_krw: item.direction == .above ? bound : nil,
            enabled: enabled, condition_change_candidate_notice_enabled: candidate,
            search_keyword: keyword?.isEmpty == false ? keyword : nil,
            poll_interval_seconds: item.poll_interval_seconds ?? 60, priority: priority.rawValue
        )
    }

    private func merge(_ items: [UserFairPriceItem]) {
        let previous = Dictionary(uniqueKeysWithValues: settings.map { ($0.id, $0) })
        settings = items
        for item in items {
            if dirtyKeys.contains(item.id), let old = previous[item.id], let draft = drafts[item.id] {
                drafts[item.id] = Self.rebase(draft, from: old, onto: item)
            } else {
                drafts[item.id] = SettingDraft(setting: item)
            }
        }
    }

    /// A successful upsert is authoritative even if its follow-up GET fails.
    /// Keep a local confirmed baseline so a later full upsert cannot replay old values.
    private func applyConfirmed(_ request: FairPriceUpsertRequest, to old: UserFairPriceItem, bulkChange: SettingsBulkChange? = nil) {
        var updated = old
        updated.user_fair_price_krw = request.fair_price_krw
        updated.effective_fair_price_krw = request.fair_price_krw
        updated.user_alert_drop_rate_percent = request.alert_drop_rate_percent
        updated.effective_alert_drop_rate_percent = request.alert_drop_rate_percent
        updated.user_target_buy_price_krw = SettingsPriceMath.target(market: request.fair_price_krw, gap: request.alert_drop_rate_percent)
        updated.effective_target_buy_price_krw = updated.user_target_buy_price_krw
        updated.user_alert_price_direction = request.alert_price_direction
        updated.effective_alert_price_direction = request.alert_price_direction
        updated.user_min_price_krw = request.min_price_krw
        updated.effective_min_price_krw = request.min_price_krw
        updated.user_max_price_krw = request.max_price_krw
        updated.effective_max_price_krw = request.max_price_krw
        updated.enabled = request.enabled
        updated.condition_change_candidate_notice_enabled = request.condition_change_candidate_notice_enabled
        updated.custom_search_keyword = request.search_keyword
        updated.effective_search_keyword = request.search_keyword ?? old.recommended_search_keyword
        updated.priority = request.priority
        updated.poll_interval_seconds = request.poll_interval_seconds
        updated.has_user_override = true
        settings = settings.map { $0.id == old.id ? updated : $0 }

        if dirtyKeys.contains(old.id), let draft = drafts[old.id] {
            var rebased = Self.rebase(draft, from: old, onto: updated)
            // The user explicitly confirmed the batch change, so that field wins
            // over any draft edit; independent draft fields stay untouched.
            switch bulkChange {
            case .alerts: rebased.enabled = updated.enabled
            case .candidate: rebased.candidateNotice = updated.condition_change_candidate_notice_enabled
            case .priority: rebased.priority = WatchPriority(serverValue: updated.priority)
            case .gap:
                rebased.changeGap(String(format: "%.2f", locale: Locale(identifier: "en_US_POSIX"), request.alert_drop_rate_percent))
            case .minimum: rebased.minimumText = request.min_price_krw.map(String.init) ?? ""
            case .maximum: rebased.maximumText = request.max_price_krw.map(String.init) ?? ""
            case .resetMarket: rebased.changeMarket(String(request.fair_price_krw))
            case nil: break
            }
            drafts[old.id] = rebased
        } else {
            drafts[old.id] = SettingDraft(setting: updated)
        }
    }

    private static func rebase(_ draft: SettingDraft, from old: UserFairPriceItem, onto updated: UserFairPriceItem) -> SettingDraft {
        let baseline = SettingDraft(setting: old)
        var result = SettingDraft(setting: updated)
        func preserve<Value: Equatable>(_ key: WritableKeyPath<SettingDraft, Value>) {
            if draft[keyPath: key] != baseline[keyPath: key] { result[keyPath: key] = draft[keyPath: key] }
        }
        // Price inputs are coupled; retain their last-edited source as one draft.
        if draft.marketText != baseline.marketText || draft.targetText != baseline.targetText || draft.gapText != baseline.gapText {
            result.marketText = draft.marketText
            result.targetText = draft.targetText
            result.gapText = draft.gapText
            result.usesPercentage = draft.usesPercentage
        }
        preserve(\.direction); preserve(\.minimumText); preserve(\.maximumText)
        preserve(\.enabled); preserve(\.candidateNotice); preserve(\.keyword); preserve(\.priority)
        return result
    }
    private static func timeLabel() -> String {
        "마지막 새로고침: " + Date().formatted(.dateTime.hour(.twoDigits(amPM: .omitted)).minute(.twoDigits).locale(Locale(identifier: "ko_KR")))
    }
}
