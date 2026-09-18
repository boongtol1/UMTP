import SwiftUI

private enum SettingsDestination: Hashable {
    case product(String)
    case chip(String, String)
    case combinations(String, String, Int)
}

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = SettingsViewModel()
    @State private var path: [SettingsDestination] = []
    @State private var navigationUserID: String?

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    Text("User: \(appState.userId ?? "")").font(.footnote).foregroundStyle(.secondary)
                    SettingsRefreshStatus(viewModel: viewModel)
                }
                Section("제품 종류 선택") {
                    if viewModel.isLoading { ProgressView("설정을 불러오는 중...") }
                    ForEach(viewModel.products, id: \.self) { product in
                        NavigationLink(product, value: SettingsDestination.product(product))
                    }
                    if !viewModel.isLoading && viewModel.units.isEmpty {
                        Text("설정 데이터를 불러오지 못했습니다. 상단 새로고침을 눌러 다시 시도해주세요.")
                            .foregroundStyle(.secondary)
                    }
                }
                NotificationSettingsView()
                Section {
                    Button("로그아웃") { appState.logout() }.disabled(viewModel.isBusy)
                }
            }
            .navigationTitle("실리콘 Mac 설정")
            .modifier(SettingsRefreshModifier(viewModel: viewModel))
            .navigationDestination(for: SettingsDestination.self) { destination in
                switch destination {
                case .product(let product):
                    List {
                        SettingsRefreshStatus(viewModel: viewModel)
                        Section("칩 선택") {
                            ForEach(viewModel.chips(product: product), id: \.self) { chip in
                                NavigationLink(chip, value: !MacUnit.hasBuiltInDisplay(product)
                                               ? SettingsDestination.combinations(product, chip, 0)
                                               : SettingsDestination.chip(product, chip))
                            }
                        }
                    }
                    .navigationTitle("\(product) 설정")
                    .modifier(SettingsRefreshModifier(viewModel: viewModel))
                case .chip(let product, let chip):
                    List {
                        SettingsRefreshStatus(viewModel: viewModel)
                        Section("화면 크기 선택") {
                            ForEach(viewModel.screens(product: product, chip: chip), id: \.self) { screen in
                                NavigationLink("\(screen)인치", value: SettingsDestination.combinations(product, chip, screen))
                            }
                        }
                    }
                    .navigationTitle("\(chip) \(product) 선택")
                    .modifier(SettingsRefreshModifier(viewModel: viewModel))
                case .combinations(let product, let chip, let screen):
                    SettingsCombinationsView(viewModel: viewModel, userID: appState.userId ?? "",
                                             product: product, chip: chip, screen: screen)
                }
            }
        }
        .task(id: appState.userId) {
            // Tab reappearance restarts this task. Keep the current destination
            // and its bulk draft until the account actually changes.
            if navigationUserID != appState.userId {
                path = []
                navigationUserID = appState.userId
            }
            if let userID = appState.userId { await viewModel.load(userID: userID) }
        }
        .alert("설정", isPresented: Binding(get: { viewModel.message != nil }, set: { if !$0 { viewModel.message = nil } })) {
            Button("확인") { viewModel.message = nil }
        } message: {
            Text(viewModel.message ?? "")
        }
    }
}

private struct SettingsRefreshModifier: ViewModifier {
    @ObservedObject var viewModel: SettingsViewModel
    func body(content: Content) -> some View {
        content
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await viewModel.refresh() }
                    } label: {
                        if viewModel.isRefreshing { ProgressView() }
                        else { Image(systemName: "arrow.clockwise") }
                    }
                    .accessibilityLabel("새로고침")
                    .disabled(viewModel.isBusy)
                }
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("완료") {
                        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                    }
                }
            }
            .refreshable { await viewModel.refresh() }
    }
}

private struct SettingsRefreshStatus: View {
    @ObservedObject var viewModel: SettingsViewModel
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let status = viewModel.refreshStatus {
                Text(status).foregroundStyle(.tint)
                if let last = viewModel.lastRefresh { Text(last).foregroundStyle(.secondary) }
            }
            Text("새로고침하면 지금부터 새로 올라오는 매물을 다시 조회합니다.")
                .foregroundStyle(.secondary)
        }.font(.caption)
    }
}

private struct SettingsCombinationsView: View {
    @ObservedObject var viewModel: SettingsViewModel
    let userID: String
    let product: String
    let chip: String
    let screen: Int
    @State private var productScope = false
    @State private var initializedBulkDefaults = false
    @State private var bulkPriority = WatchPriority.normal
    @State private var gapInput = ""
    @State private var minimumInput = ""
    @State private var maximumInput = ""
    @State private var pendingChange: SettingsBulkChange?
    @State private var inputError: String?
    private var scope: SettingsScope {
        SettingsScope(product: product, chip: productScope ? nil : chip,
                      screen: productScope || !MacUnit.hasBuiltInDisplay(product) ? nil : screen)
    }
    private var scopedItems: [UserFairPriceItem] { viewModel.scopedSettings(scope) }
    private var enabledOverrides: [UserFairPriceItem] { scopedItems.filter(\.has_user_override) }
    private var hasBelow: Bool { scopedItems.contains { $0.direction == .below } }
    private var hasAbove: Bool { scopedItems.contains { $0.direction == .above } }
    private var bulkDefaultPriority: WatchPriority {
        let priorities = Set(enabledOverrides.map { WatchPriority(serverValue: $0.priority) })
        return priorities.count == 1 ? priorities.first! : .normal
    }
    private var bulkDefaultMinimum: String {
        let minimums = Set(scopedItems.filter { $0.direction == .below }.map(\.minimumPrice))
        return minimums.count == 1 ? minimums.first!.map(String.init) ?? "" : ""
    }
    private var bulkDefaultMaximum: String {
        let maximums = Set(scopedItems.filter { $0.direction == .above }.map(\.maximumPrice))
        return maximums.count == 1 ? maximums.first!.map(String.init) ?? "" : ""
    }
    private var visibleUnits: [MacUnit] {
        viewModel.units.filter { $0.product_type == product && $0.chip == chip && $0.screen_inch == screen }
    }

    var body: some View {
        Form {
            Section {
                SettingsRefreshStatus(viewModel: viewModel)
                if !viewModel.dirtyKeys.isEmpty {
                    Text("입력 중인 값은 새로고침과 탭 이동 후에도 유지됩니다. 각 항목의 저장을 눌러 반영해주세요.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            bulkSection
            ForEach(visibleUnits) { unit in
                Section("\(unit.ram_gb)GB / \(unit.ssd_gb)GB") {
                    SettingsUnitCard(viewModel: viewModel, unit: unit, userID: userID)
                }
            }
            if visibleUnits.isEmpty {
                Text("설정 데이터를 불러오지 못했습니다. 상단 새로고침을 눌러 다시 시도해주세요.")
                    .foregroundStyle(.secondary)
            }
        }
        .scrollDismissesKeyboard(.interactively)
        .navigationTitle(scopeTitle)
        .modifier(SettingsRefreshModifier(viewModel: viewModel))
        .onAppear {
            guard !initializedBulkDefaults else { return }
            initializedBulkDefaults = true
            updateBulkDefaults()
        }
        .onChange(of: productScope) { _, _ in updateBulkDefaults() }
        // Only the changed server aggregate resets its matching bulk input.
        // Saving a keyword or refreshing an unchanged scope must not erase
        // a pending bulk percentage, priority or price-bound edit.
        .onChange(of: bulkDefaultPriority) { _, value in bulkPriority = value }
        .onChange(of: bulkDefaultMinimum) { _, value in minimumInput = value }
        .onChange(of: bulkDefaultMaximum) { _, value in maximumInput = value }
        .alert("일괄 적용", isPresented: Binding(get: { pendingChange != nil }, set: { if !$0 { pendingChange = nil } })) {
            Button("취소", role: .cancel) { pendingChange = nil }
            Button("확인") {
                guard let change = pendingChange else { return }
                pendingChange = nil
                let targetScope = scope
                Task { await viewModel.apply(change, scope: targetScope) }
            }
        } message: {
            Text("\(scope.label) 범위에 \(pendingChange?.label ?? "")하시겠습니까?"
                 + (pendingChange == .resetMarket ? "\n기존 알림 방향과 차이 % 설정은 유지됩니다." : ""))
        }
    }

    private var scopeTitle: String { !MacUnit.hasBuiltInDisplay(product) ? "\(chip) \(product) 설정" : "\(chip) \(product) \(screen)인치 설정" }

    private var bulkSection: some View {
        Section("일괄 설정") {
            Picker("적용 범위", selection: $productScope) {
                Text(!MacUnit.hasBuiltInDisplay(product) ? "현재 칩" : "현재 칩/인치").tag(false)
                Text("제품 전체").tag(true)
            }.pickerStyle(.segmented)
            Text("\(scope.label) 범위에 적용됩니다.").font(.caption).foregroundStyle(.secondary)
            Toggle("전체 알림", isOn: Binding(
                get: { !enabledOverrides.isEmpty && enabledOverrides.allSatisfy(\.enabled) },
                set: { pendingChange = .alerts($0) }
            ))
            Toggle("조건 변경 후보 알림", isOn: Binding(
                get: { !enabledOverrides.isEmpty && enabledOverrides.allSatisfy(\.condition_change_candidate_notice_enabled) },
                set: { pendingChange = .candidate($0) }
            ))
            Text(SettingsUnitCard.candidateExplanation).font(.caption).foregroundStyle(.secondary)
            Picker("알림 속도", selection: $bulkPriority) {
                ForEach(WatchPriority.allCases, id: \.self) { Text($0.label).tag($0) }
            }.pickerStyle(.segmented)
                .accessibilityIdentifier("settings.bulk.priority")
            Text(bulkPriority.explanation).font(.caption).foregroundStyle(.secondary)
            Button("전체 알림 속도 적용") { pendingChange = .priority(bulkPriority) }
            HStack {
                TextField("시장가와의 차이 %", text: $gapInput).keyboardType(.decimalPad)
                Button("+/−") { gapInput = gapInput.hasPrefix("-") ? String(gapInput.dropFirst()) : "-" + gapInput }
            }
            Button("전체 차이 % 적용") {
                guard let gap = Double(gapInput), gap.isFinite, (-100...100).contains(gap) else {
                    inputError = SettingsInputError.percentage.localizedDescription; return
                }
                inputError = nil; pendingChange = .gap(gap)
            }
            TextField("최소 가격 (원)", text: $minimumInput).keyboardType(.numberPad)
            Text(hasBelow ? "이하 알림 항목에 최소 가격으로 적용됩니다." : "현재 범위에는 이하 알림 항목이 없습니다.")
                .font(.caption).foregroundStyle(.secondary)
            Button("전체 최소 가격 적용") { confirmBound(minimum: true) }.disabled(!hasBelow)
            TextField("최대 가격 (원)", text: $maximumInput).keyboardType(.numberPad)
            Text(hasAbove ? "이상 알림 항목에 최대 가격으로 적용됩니다." : "현재 범위에는 이상 알림 항목이 없습니다.")
                .font(.caption).foregroundStyle(.secondary)
            Button("전체 최대 가격 적용") { confirmBound(minimum: false) }.disabled(!hasAbove)
            Button("시스템 기준 시장가로 초기화") { pendingChange = .resetMarket }
            if let inputError { Text(inputError).foregroundStyle(.red).font(.caption) }
            if viewModel.isApplyingBulk { ProgressView("일괄 적용 중...") }
        }.disabled(viewModel.isBusy)
    }

    private func confirmBound(minimum: Bool) {
        guard let value = Int(minimum ? minimumInput : maximumInput), value >= 0, value <= Int(Int32.max) else {
            inputError = SettingsInputError.bound.localizedDescription; return
        }
        inputError = nil; pendingChange = minimum ? .minimum(value) : .maximum(value)
    }
    private func updateBulkDefaults() {
        bulkPriority = bulkDefaultPriority
        minimumInput = bulkDefaultMinimum
        maximumInput = bulkDefaultMaximum
    }
}

private struct SettingsUnitCard: View {
    @ObservedObject var viewModel: SettingsViewModel
    let unit: MacUnit
    let userID: String
    static let candidateExplanation = "조건을 변경하면 최근 7일 안에 분석된 매물도 새 기준으로 다시 확인해요. 이전 기준에는 안 맞았지만 새 기준에는 맞는 매물은 조건 변경 후보로 알려드려요. 최근 7일은 매물 등록일이 아니라, 시스템이 매물을 확인한 시점부터 저장 시점까지를 기준으로 계산해요."
    private var item: UserFairPriceItem? { viewModel.item(for: unit) }
    private var draft: SettingDraft { viewModel.draft(for: unit) }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Toggle("알림 받기", isOn: binding(\.enabled))
                if let item, let id = item.ruleID {
                    Button {
                        Task { await viewModel.refreshRule(item) }
                    } label: {
                        if viewModel.refreshingRules.contains(id) { ProgressView() }
                        else { Label("새로고침", systemImage: "arrow.clockwise") }
                    }
                    .buttonStyle(.bordered).font(.caption)
                    .disabled(!item.enabled || !item.has_user_override || viewModel.isBusy)
                }
            }
            if let id = item?.ruleID, let label = viewModel.ruleRefreshLabels[id] {
                Text(label).font(.caption).foregroundStyle(.secondary)
            }
            currentValues
            Divider()
            searchAndPriority
            priceInputs
            directionAndBounds
            Toggle("조건 변경 후보 알림 받기", isOn: binding(\.candidateNotice))
            Text(Self.candidateExplanation).font(.caption).foregroundStyle(.secondary)
            Button {
                Task { await viewModel.save(unit) }
            } label: {
                HStack {
                    Spacer()
                    if viewModel.savingKey == unit.id { ProgressView() }
                    else { Text("저장") }
                    Spacer()
                }
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("settings.save.\(unit.id)")
        }
        .padding(.vertical, 8)
        .disabled(viewModel.isBusy)
    }

    private var currentValues: some View {
        VStack(alignment: .leading, spacing: 8) {
            LabeledContent("시스템 기준 시장가", value: SettingsPriceMath.money(item?.system_fair_price_krw))
            LabeledContent(SettingsPriceMath.marketLabel(userID), value: SettingsPriceMath.money(item?.effective_fair_price_krw))
            let target = item?.effective_target_buy_price_krw ?? SettingsPriceMath.target(market: item?.effective_fair_price_krw, gap: item?.effective_alert_drop_rate_percent)
            LabeledContent("알림 기준 가격", value: SettingsPriceMath.money(target))
            LabeledContent("시장가와의 차이 (%)", value: SettingsPriceMath.percent(SettingsPriceMath.gap(market: item?.effective_fair_price_krw, target: target)))
            LabeledContent("추천 검색어", value: item?.recommended_search_keyword ?? "-")
        }.font(.footnote)
    }

    private var searchAndPriority: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("커스텀 검색어").font(.caption).foregroundStyle(.secondary)
            TextField(item?.recommended_search_keyword ?? "예: \(unit.chip) \(unit.product_type)", text: binding(\.keyword))
                .textInputAutocapitalization(.never).autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)
            Text("알림 속도").font(.caption).foregroundStyle(.secondary)
            Picker("알림 속도", selection: binding(\.priority)) {
                ForEach(WatchPriority.allCases, id: \.self) { Text($0.label).tag($0) }
            }.pickerStyle(.segmented)
            Text(draft.priority.explanation).font(.caption).foregroundStyle(.secondary)
        }
    }

    private var priceInputs: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(SettingsPriceMath.marketLabel(userID)) (원)").font(.caption).foregroundStyle(.secondary)
            TextField("시장가 (원)", text: Binding(get: { draft.marketText }, set: { text in viewModel.edit(unit) { $0.changeMarket(text) } }))
                .keyboardType(.numberPad).textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("settings.market.\(unit.id)")
            Text("알림 기준 가격 (원)").font(.caption).foregroundStyle(.secondary)
            TextField("알림 기준 가격 (원)", text: Binding(get: { draft.targetText }, set: { text in viewModel.edit(unit) { $0.changeTarget(text) } }))
                .keyboardType(.numberPad).textFieldStyle(.roundedBorder)
            Text("시장가와의 차이 (%)").font(.caption).foregroundStyle(.secondary)
            HStack {
                TextField("예: 20 또는 -15.5", text: Binding(get: { draft.gapText }, set: { text in viewModel.edit(unit) { $0.changeGap(text) } }))
                    .keyboardType(.decimalPad).textFieldStyle(.roundedBorder)
                Button("+/−") {
                    let value = draft.gapText.hasPrefix("-") ? String(draft.gapText.dropFirst()) : "-" + draft.gapText
                    viewModel.edit(unit) { $0.changeGap(value) }
                }.buttonStyle(.bordered)
            }
            Text("계산식: (시장가 − 알림 기준 가격) / 시장가 × 100").font(.caption).foregroundStyle(.secondary)
            Text("이 제품이 보통 이 정도 가격이라고 생각하는 금액을 입력하세요. 시장가보다 낮거나 높은 가격에서 알림을 받도록 설정할 수 있습니다.")
                .font(.caption).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("settings.market.guidance.\(unit.id)")
        }
    }

    private var directionAndBounds: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("알림 방향").font(.caption).foregroundStyle(.secondary)
            Picker("알림 방향", selection: binding(\.direction)) {
                ForEach(AlertPriceDirection.allCases, id: \.self) { Text($0.label).tag($0) }
            }.pickerStyle(.segmented)
            Text(draft.direction == .below ? "이 가격 이하이면 알림을 받습니다." : "이 가격 이상이면 알림을 받습니다.")
                .font(.caption).foregroundStyle(.secondary)
            let above = draft.direction == .above
            Text(above ? "최대 가격 (원)" : "최소 가격 (원)").font(.caption).foregroundStyle(.secondary)
            TextField(above ? "예: 900000" : "예: 300000", text: above ? binding(\.maximumText) : binding(\.minimumText))
                .keyboardType(.numberPad).textFieldStyle(.roundedBorder)
            Text(above ? "이 가격 이하인 매물만 알림을 받습니다." : "이 가격 이상인 매물만 알림을 받습니다.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private func binding<Value>(_ keyPath: WritableKeyPath<SettingDraft, Value>) -> Binding<Value> {
        Binding(get: { viewModel.draft(for: unit)[keyPath: keyPath] }, set: { value in viewModel.edit(unit) { $0[keyPath: keyPath] = value } })
    }
}
