import Combine
import Foundation

@MainActor
final class ResaleTradeViewModel: ObservableObject {
    @Published var reference = ""
    @Published var mode: TradeMode = .purchase
    @Published var inputs: [String: String] = [:]
    @Published var selectedForDeletion = Set<Int>()
    @Published private(set) var selected: ResaleTradeRow?
    @Published private(set) var completed: [ResaleTradeRow] = []
    @Published private(set) var purchased: [ResaleTradeRow] = []
    @Published private(set) var isBusy = false
    @Published private(set) var isLoading = false
    @Published private(set) var completedError: String?
    @Published private(set) var purchasedError: String?
    @Published private(set) var errorMessage: String?
    @Published private(set) var message: String?
    let userId: String
    private let api: any ResaleTradeAPIProtocol
    private var reloadHistoryWhenFinished = false
    private var pendingStart: StartRequest?

    private struct StartRequest {
        let reference: String?
        let alertID: Int?
        let fromArchive: Bool
    }

    var canRetryStart: Bool { pendingStart != nil && errorMessage != nil && !isBusy }

    static func timestampForEntry(_ date: Date) -> String {
        // The backend normalizes offset-aware values to UTC. Include Z instead of an ambiguous local time.
        ISO8601DateFormatter().string(from: date)
    }

    init(userId: String, api: (any ResaleTradeAPIProtocol)? = nil) {
        self.userId = userId
        self.api = api ?? ResaleTradeAPI()
    }

    var hasUnsavedChanges: Bool {
        guard let selected else { return false }
        return TradeField.all.contains { (inputs[$0.id] ?? "") != selected[$0.id] }
    }

    func select(_ row: ResaleTradeRow?) {
        guard !isBusy else { return }
        pendingStart = nil
        applySelection(row)
        errorMessage = nil
        message = nil
    }

    private func applySelection(_ row: ResaleTradeRow?) {
        selected = row
        inputs = [:]
        if let row {
            for field in TradeField.all { inputs[field.id] = row[field.id] }
        }
    }

    func start(alertId: Int? = nil, fromArchive: Bool = false) async {
        guard !isBusy else { return }
        let trimmed = reference.trimmingCharacters(in: .whitespacesAndNewlines)
        let request: StartRequest
        if let alertId, alertId > 0 {
            // A newly tapped alert is an explicit navigation intent. Discard an older reference
            // so a failed alert request can also retry its own identity without stale input.
            reference = ""
            request = StartRequest(reference: nil, alertID: alertId, fromArchive: fromArchive)
        } else if !trimmed.isEmpty {
            // User-entered input on the form takes priority over a previously failed route.
            request = StartRequest(reference: trimmed, alertID: nil, fromArchive: false)
        } else if let pendingStart {
            request = pendingStart
        } else {
            errorMessage = "URL 또는 product_id를 입력해 주세요."
            return
        }
        pendingStart = request
        isBusy = true
        errorMessage = nil
        message = nil
        defer { isBusy = false }
        do {
            let response = try await api.start(userId: userId, reference: request.reference,
                                               alertId: request.alertID, fromArchive: request.fromArchive).checked()
            try Task.checkCancellation()
            guard let row = response.row else { throw TradeError.missingRow }
            applySelection(row)
            pendingStart = nil
            message = response.existing ? "기존 거래 기록 열기" : "거래 기록 시작"
            await loadHistory()
        } catch is CancellationError {
        } catch { errorMessage = error.localizedDescription }
    }

    func save() async {
        guard !isBusy else { return }
        guard var row = selected, row.id.map({ $0 > 0 }) == true || !row["product_id"].isEmpty || !row["url"].isEmpty else {
            errorMessage = "먼저 거래 기록 시작(알림/읽음 보관함/URL)을 진행해 주세요."
            return
        }
        isBusy = true
        pendingStart = nil
        errorMessage = nil
        message = nil
        defer { isBusy = false }
        var verificationSaved = false
        do {
            let fields = mode == .purchase ? TradeField.purchase : TradeField.resale
            var updates = try TradeField.changes(fields: fields, inputs: inputs, baseline: row)
            let verification = try TradeField.changes(fields: TradeField.verification, inputs: inputs, baseline: row)
            if mode == .resale && !verification.isEmpty {
                // The backend resale whitelist does not accept verification fields.
                var verificationUpdates = verification
                if row.id != nil, !row["current_stage"].isEmpty {
                    verificationUpdates["current_stage"] = .string(row["current_stage"])
                }
                let result = try await api.save(userId: userId, row: row, mode: .purchase, updates: verificationUpdates).checked()
                guard let updated = result.row else { throw TradeError.missingRow }
                row = updated
                selected = updated
                verificationSaved = true
            } else {
                updates.merge(verification) { _, new in new }
            }
            if mode == .purchase, updates["current_stage"] == nil,
               ["KEEP", "RESALE_LISTED", "SOLD"].contains(row["current_stage"]) {
                // Editing a purchase detail must not silently undo a later stage.
                updates["current_stage"] = .string(row["current_stage"])
            }
            let result = try await api.save(userId: userId, row: row, mode: mode, updates: updates).checked()
            guard let updated = result.row else { throw TradeError.missingRow }
            // Keep the draft if the other mode has unsaved edits.
            let retained = inputs
            let otherFields = mode == .purchase ? TradeField.resale : TradeField.purchase
            let editedOther = otherFields.filter { !fields.map(\.id).contains($0.id) && retained[$0.id] != row[$0.id] }
            applySelection(updated)
            for field in editedOther { inputs[field.id] = retained[field.id] }
            message = mode == .purchase ? "구매 후 입력이 저장되었습니다." : "되팔이 후 입력이 저장되었습니다."
            await loadHistory()
        } catch is CancellationError {
        } catch {
            errorMessage = verificationSaved ? TradeError.partialSave.localizedDescription : error.localizedDescription
        }
    }

    func loadHistory() async {
        guard !isLoading else { reloadHistoryWhenFinished = true; return }
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await api.history(userId: userId, completed: true).checked()
            try Task.checkCancellation()
            completed = response.items.filter { ($0.id ?? 0) > 0 }
            selectedForDeletion.formIntersection(Set(completed.compactMap(\.id)))
            completedError = nil
        } catch is CancellationError { return
        } catch { completedError = error.localizedDescription }
        do {
            let response = try await api.history(userId: userId, completed: false).checked()
            try Task.checkCancellation()
            purchased = response.items.filter { ($0.id ?? 0) > 0 }
            purchasedError = nil
        } catch is CancellationError {
        } catch { purchasedError = error.localizedDescription }
        if reloadHistoryWhenFinished && !Task.isCancelled {
            reloadHistoryWhenFinished = false
            isLoading = false
            await loadHistory()
        }
    }

    func deleteCompleted(all: Bool) async {
        guard !isBusy else { return }
        let ids = selectedForDeletion.intersection(Set(completed.compactMap(\.id)))
        guard all || !ids.isEmpty else { return }
        isBusy = true
        errorMessage = nil
        message = nil
        defer { isBusy = false }
        do {
            let response = try await api.delete(userId: userId, ids: all ? nil : ids).checked()
            let deletedIDs = all ? Set(completed.compactMap(\.id)) : ids
            if let selectedId = selected?.id, deletedIDs.contains(selectedId) { applySelection(nil) }
            selectedForDeletion.subtract(deletedIDs)
            message = "완료된 거래 \(response.deletedCount)건을 삭제했습니다."
            await loadHistory()
        } catch is CancellationError {
        } catch { errorMessage = error.localizedDescription }
    }
}
