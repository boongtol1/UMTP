import SwiftUI
import UIKit

struct ResaleTradeView: View {
    @StateObject private var model: ResaleTradeViewModel
    @Environment(\.scenePhase) private var scenePhase
    private let alertId: Int?
    private let fromArchive: Bool
    private let initialReference: String?
    @State private var started = false
    @State private var pendingSelection: ResaleTradeRow?
    @State private var confirmSelection = false
    @State private var confirmStart = false
    @State private var confirmDelete = false
    @State private var deleteAll = false
    @FocusState private var focusedInput: String?

    init(userId: String, alertId: Int? = nil, fromArchive: Bool = false, reference: String? = nil) {
        _model = StateObject(wrappedValue: ResaleTradeViewModel(userId: userId))
        self.alertId = alertId
        self.fromArchive = fromArchive
        initialReference = reference
    }

    init(viewModel: ResaleTradeViewModel) {
        _model = StateObject(wrappedValue: viewModel)
        alertId = nil
        fromArchive = false
        initialReference = nil
    }

    var body: some View {
        Form {
            Section {
                Text("URL, product_id 또는 알림 카드에서 거래 기록을 시작한 뒤, 필요한 값만 입력해 저장합니다.")
                    .font(.footnote).foregroundStyle(.secondary)
                TextField("URL 또는 product_id", text: $model.reference)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                    .accessibilityIdentifier("trade.reference")
                    .focused($focusedInput, equals: "reference")
                    .frame(minHeight: 44)
                    .contentShape(Rectangle())
                    .simultaneousGesture(TapGesture().onEnded {
                        focusedInput = "reference"
                    })
                Button("거래 기록 시작") {
                    dismissInput()
                    if model.hasUnsavedChanges { confirmStart = true }
                    else { Task { await model.start() } }
                }.accessibilityIdentifier("trade.start")
            } header: { Text("URL 또는 product_id로 거래 기록 시작") }
                .disabled(model.isBusy)

            if model.isBusy { ProgressView("처리 중...") }
            if let error = model.errorMessage {
                Section {
                    Text(error).foregroundStyle(.red).accessibilityIdentifier("trade.error")
                    if model.canRetryStart {
                        Button("거래 기록 다시 불러오기") {
                            if model.hasUnsavedChanges { confirmStart = true }
                            else { Task { await model.start() } }
                        }
                            .accessibilityIdentifier("trade.retryStart")
                    }
                }
            }
            if let message = model.message { Text(message).foregroundStyle(.secondary) }

            if let row = model.selected {
                productInformation(row)
                Section {
                    Text("판매자에게 직접 확인한 정보만 입력하세요. 모르는 경우 비워둘 수 있습니다.")
                        .font(.footnote).foregroundStyle(.secondary)
                    ForEach(TradeField.verification) { field in
                        VStack(alignment: .leading, spacing: 8) { input(field) }
                            .id(field.id)
                    }
                } header: { Text("정확 확인 정보") }
                    .disabled(model.isBusy)

                Section {
                    Picker("기록 종류", selection: $model.mode) {
                        ForEach(TradeMode.allCases) { mode in Text(mode.rawValue).tag(mode) }
                    }.pickerStyle(.segmented)
                    ForEach(model.mode == .purchase ? TradeField.purchase : TradeField.resale) { field in
                        // A field and its optional date action form one stable Form row.
                        // Flattened, variable-count rows can lose their responder during a draft update.
                        VStack(alignment: .leading, spacing: 8) { input(field) }
                            .id(field.id)
                    }
                    Button(model.mode == .purchase ? "구매 후 기록 저장" : "되팔이 후 기록 저장") {
                        dismissInput()
                        Task { await model.save() }
                    }.accessibilityIdentifier("trade.save")
                } header: { Text(model.mode.rawValue + " 입력") }
                    .disabled(model.isBusy)
            }

            Section {
                Button { Task { await model.loadHistory() } } label: {
                    if model.isLoading { ProgressView("목록 새로고침 중...") } else { Label("목록 새로고침", systemImage: "arrow.clockwise") }
                }.disabled(model.isLoading || model.isBusy)
                if let error = model.completedError { Text(error).foregroundStyle(.red) }
                if model.completed.isEmpty && model.completedError == nil && !model.isLoading { Text("완료된 거래가 없습니다.").foregroundStyle(.secondary) }
                ForEach(model.completed) { row in
                    HStack {
                        historyButton(row, completed: true)
                        if let id = row.id {
                            Button {
                                if model.selectedForDeletion.contains(id) { model.selectedForDeletion.remove(id) }
                                else { model.selectedForDeletion.insert(id) }
                            } label: {
                                Image(systemName: model.selectedForDeletion.contains(id) ? "checkmark.circle.fill" : "circle")
                            }.buttonStyle(.borderless).accessibilityLabel("삭제 선택: \(row.title)")
                        }
                    }.disabled(model.isBusy)
                }
                HStack {
                    Button("선택 삭제", role: .destructive) { deleteAll = false; confirmDelete = true }
                        .buttonStyle(.borderless)
                        .disabled(model.selectedForDeletion.isEmpty || model.isBusy)
                    Spacer()
                    Button("전체 삭제", role: .destructive) { deleteAll = true; confirmDelete = true }
                        .buttonStyle(.borderless)
                        .disabled(model.completed.isEmpty || model.completedError != nil || model.isBusy)
                }
            } header: { Text("완료된 거래") } footer: { Text("최근 200건을 표시합니다. 전체 삭제는 서버의 완료된 거래 전체에 적용됩니다.") }

            Section {
                if let error = model.purchasedError { Text(error).foregroundStyle(.red) }
                if model.purchased.isEmpty && model.purchasedError == nil && !model.isLoading { Text("구매 기록이 없습니다.").foregroundStyle(.secondary) }
                ForEach(model.purchased) { row in historyButton(row, completed: false).disabled(model.isBusy) }
            } header: { Text("구매 거래 내역 (KEEP 포함)") } footer: { Text("최근 200건을 표시합니다.") }
        }
        .navigationTitle("거래 기록")
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            if focusedInput == "reference" {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("완료") { dismissInput() }
                        .accessibilityIdentifier("trade.keyboard.done")
                }
            }
        }
        .refreshable { await model.loadHistory() }
        .task {
            guard !started else { return }
            started = true
            if let initialReference { model.reference = initialReference }
            if alertId != nil || initialReference != nil { await model.start(alertId: alertId, fromArchive: fromArchive) }
            else { await model.loadHistory() }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active && started { Task { await model.loadHistory() } }
        }
        .alert("입력한 변경사항을 버릴까요?", isPresented: $confirmSelection) {
            Button("취소", role: .cancel) {}
            Button("변경사항 버리기", role: .destructive) { model.select(pendingSelection) }
        } message: { Text("다른 거래를 열면 아직 저장하지 않은 입력이 사라집니다.") }
        .alert("새 거래를 시작할까요?", isPresented: $confirmStart) {
            Button("취소", role: .cancel) {}
            Button("거래 기록 시작", role: .destructive) { Task { await model.start() } }
        } message: { Text("현재 거래의 저장하지 않은 입력이 사라집니다.") }
        .alert(deleteAll ? "완료된 거래 전체 삭제" : "선택한 거래 삭제", isPresented: $confirmDelete) {
            Button("취소", role: .cancel) {}
            Button("삭제", role: .destructive) { Task { await model.deleteCompleted(all: deleteAll) } }
        } message: { Text(deleteAll ? "서버에 저장된 완료 거래 전체를 삭제합니다. 되돌릴 수 없습니다. 구매 중인 거래는 유지됩니다." : "선택한 완료 거래 \(model.selectedForDeletion.count)건을 삭제합니다. 되돌릴 수 없습니다.") }
    }

    @ViewBuilder
    private func productInformation(_ row: ResaleTradeRow) -> some View {
        Section("제품 기본 스펙") {
            if let url = row.imageURL {
                AsyncImage(url: url) { image in image.resizable().scaledToFit() } placeholder: { Image(systemName: "photo") }
                    .frame(maxWidth: .infinity, maxHeight: 180)
            }
            Text(row.title).font(.headline)
            ForEach([TradeField("product_type", "제품 유형"), TradeField("chip", "칩"), TradeField("screen_inch", "화면 크기(인치)"), TradeField("ram_gb", "RAM (GB)"), TradeField("ssd_gb", "SSD (GB)")]) { field in
                LabeledContent(field.label, value: row[field.id].isEmpty ? "-" : row[field.id])
            }
            if let url = URL(string: row["url"]), ["http", "https"].contains(url.scheme?.lowercased() ?? "") {
                Link("매물 원문 열기", destination: url)
            }
            Button("선택 해제") { requestSelection(nil) }.disabled(model.isBusy)
        }
        Section("자동으로 채워진 정보") {
            DisclosureGroup("매물 및 거래 정보") {
                VStack(alignment: .leading, spacing: 3) {
                    Text("이미지 URL 목록").font(.caption).foregroundStyle(.secondary)
                    Text(row["image_urls"].isEmpty ? "-" : row["image_urls"]).textSelection(.enabled)
                }
                ForEach([TradeField("id", "거래 번호"), TradeField("user_id", "사용자 ID"), TradeField("source", "출처"), TradeField("product_id", "매물 번호"), TradeField("url", "매물 URL"), TradeField("listing_price_krw", "등록 가격 (원)"), TradeField("seller_nickname", "판매자"), TradeField("seller_location", "판매자 위치"), TradeField("body_text", "본문"), TradeField("fair_price_krw", "적정 가격 (원)"), TradeField("discount_rate_percent", "시장가와의 차이 (%)"), TradeField("total_cost_krw", "총 구매 비용 (원)"), TradeField("created_at", "생성 시각"), TradeField("updated_at", "수정 시각")]) { field in
                    VStack(alignment: .leading, spacing: 3) {
                        Text(field.label).font(.caption).foregroundStyle(.secondary)
                        Text(row[field.id].isEmpty ? "-" : row[field.id]).textSelection(.enabled)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func input(_ field: TradeField) -> some View {
        let binding = Binding<String>(get: { model.inputs[field.id] ?? "" }, set: { value in
            guard (model.inputs[field.id] ?? "") != value else { return }
            model.inputs[field.id] = value
        })
        if TradeField.boolean.contains(field.id) {
            Picker(field.label, selection: Binding<String>(get: {
                guard let value = TradeValue.string(binding.wrappedValue).boolValue else { return "" }
                return value ? "true" : "false"
            }, set: { binding.wrappedValue = $0 })) {
                Text(model.selected?[field.id].isEmpty == false ? "미입력 (기존 값 유지)" : "미입력").tag("")
                Text(field.id == "activation_lock_off" ? "잠금 없음" : "MDM 없음").tag("true")
                Text(field.id == "activation_lock_off" ? "잠금 있음" : "MDM 있음").tag("false")
            }
        } else if field.id == "current_stage" {
            Picker(field.label, selection: binding) {
                Text("미입력").tag("")
                Text("발견됨").tag("DISCOVERED")
                Text("구매/점검").tag("INSPECTED")
                Text("재판매 등록").tag("RESALE_LISTED")
                Text("판매 완료").tag("SOLD")
                Text("보유(KEEP)").tag("KEEP")
            }
        } else {
            VStack(alignment: .leading, spacing: 4) {
                Text(field.label).font(.caption).foregroundStyle(.secondary)
                TradeTextInput(field: field, text: binding)
            }
            if TradeField.dates.contains(field.id) {
                Button("\(field.label): 현재 시각 입력") {
                    binding.wrappedValue = ResaleTradeViewModel.timestampForEntry(Date())
                }.font(.caption).buttonStyle(.borderless)
                    .accessibilityIdentifier("trade.now.\(field.id)")
            }
        }
    }

    private func historyButton(_ row: ResaleTradeRow, completed: Bool) -> some View {
        Button {
            requestSelection(model.selected?.id == row.id ? nil : row)
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(row.title).foregroundStyle(.primary)
                Text("#\(row.id.map(String.init) ?? "-") · \(row.stageLabel) · \(row.amount(completed ? "sale_price_krw" : "purchase_price_krw"))")
                    .font(.caption).foregroundStyle(.secondary)
                if model.selected?.id == row.id { Text("선택됨").font(.caption) }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }.buttonStyle(.borderless)
    }

    private func requestSelection(_ row: ResaleTradeRow?) {
        dismissInput()
        if model.hasUnsavedChanges { pendingSelection = row; confirmSelection = true }
        else { model.select(row) }
    }

    private func dismissInput() {
        focusedInput = nil
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}

/// A focused editor stays inside one stable Form row as its draft changes.
private struct TradeTextInput: View {
    let field: TradeField
    @Binding var text: String
    @FocusState private var isFocused: Bool

    var body: some View {
        editor
            .focused($isFocused)
            .textFieldStyle(.roundedBorder)
            .textInputAutocapitalization(.never).autocorrectionDisabled()
            .keyboardType(TradeField.numeric.contains(field.id) ? .numberPad
                : (TradeField.dates.contains(field.id) ? .numbersAndPunctuation : .default))
            .accessibilityIdentifier("trade.field.\(field.id)")
            .accessibilityLabel(field.label)
            .frame(minHeight: 44, alignment: .leading)
            .contentShape(Rectangle())
            .simultaneousGesture(TapGesture().onEnded { isFocused = true })
            .toolbar {
                if isFocused {
                    ToolbarItemGroup(placement: .keyboard) {
                        Spacer()
                        Button("완료") {
                            isFocused = false
                            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                        }
                        .accessibilityIdentifier("trade.keyboard.done")
                    }
                }
            }
    }

    @ViewBuilder
    private var editor: some View {
        if field.id == "body_text" || field.id == "inspection_notes" {
            TextField(field.label, text: $text, axis: .vertical)
        } else {
            TextField(TradeField.dates.contains(field.id) ? "YYYY-MM-DD HH:mm" : field.label, text: $text)
                .submitLabel(.done)
                .onSubmit { isFocused = false }
        }
    }
}
