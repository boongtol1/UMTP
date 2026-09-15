import Combine
import Foundation

@MainActor
final class AlertFeedViewModel: ObservableObject {
    @Published private(set) var alerts: [AlertItem] = []
    @Published private(set) var groups: [String: [String: [AlertItem]]] = [:]
    @Published private(set) var isRefreshing = false
    @Published private(set) var isRefreshingArchive = false
    @Published private(set) var isMutating = false
    @Published private(set) var lastRefresh: Date?
    @Published var message: String?
    @Published var errorMessage: String?
    @Published var archiveErrorMessage: String?

    private let api: AlertsAPIProtocol
    private let pollingService: AlertPollingService
    private var userID = ""
    private var generation = 0
    private var revision = 0
    private var refreshAgain = false
    private var archiveRefreshAgain = false

    init(api: AlertsAPIProtocol? = nil, pollingService: AlertPollingService? = nil) {
        self.api = api ?? AlertsAPI()
        self.pollingService = pollingService ?? AlertPollingService()
    }

    func configure(userID: String) {
        guard self.userID != userID else { return }
        pollingService.stop()
        generation += 1
        revision += 1
        self.userID = userID
        alerts = []
        groups = [:]
        errorMessage = nil
        archiveErrorMessage = nil
        message = nil
        lastRefresh = nil
        isRefreshing = false
        isRefreshingArchive = false
        isMutating = false
        refreshAgain = false
        archiveRefreshAgain = false
    }

    func onAppear() {
        guard !userID.isEmpty else { return }
        pollingService.start { [weak self] in await self?.refresh() }
    }

    func onDisappear() { pollingService.stop() }

    func refresh() async {
        guard !userID.isEmpty else { return }
        if isRefreshing { refreshAgain = true; return }
        let account = userID
        let token = generation
        isRefreshing = true
        defer { if generation == token { isRefreshing = false } }
        repeat {
            refreshAgain = false
            let version = revision
            do {
                let items = try await api.alerts(userID: account)
                guard generation == token, !Task.isCancelled else { return }
                if revision == version {
                    alerts = items
                    errorMessage = nil
                    lastRefresh = Date()
                } else {
                    refreshAgain = true
                }
            } catch {
                guard generation == token, !Task.isCancelled else { return }
                errorMessage = error.localizedDescription
            }
        } while refreshAgain && generation == token && !Task.isCancelled
    }

    func refreshArchive() async {
        guard !userID.isEmpty else { return }
        if isRefreshingArchive { archiveRefreshAgain = true; return }
        let account = userID
        let token = generation
        isRefreshingArchive = true
        defer { if generation == token { isRefreshingArchive = false } }
        repeat {
            archiveRefreshAgain = false
            let version = revision
            do {
                let result = try await api.archive(userID: account)
                guard generation == token, !Task.isCancelled else { return }
                if revision == version {
                    groups = result
                    archiveErrorMessage = nil
                } else {
                    archiveRefreshAgain = true
                }
            } catch {
                guard generation == token, !Task.isCancelled else { return }
                archiveErrorMessage = error.localizedDescription
            }
        } while archiveRefreshAgain && generation == token && !Task.isCancelled
    }

    @discardableResult
    func markRead(_ id: Int) async -> Bool {
        let successful = await markSelectedRead([id])
        return successful.contains(id)
    }

    /// Return successes so a partially failed selection can remain selected for retry.
    func markSelectedRead(_ ids: Set<Int>) async -> Set<Int> {
        guard !isMutating, !userID.isEmpty else { return [] }
        let targets = ids.filter { $0 > 0 }.sorted()
        guard !targets.isEmpty else { return [] }
        isMutating = true
        errorMessage = nil
        let token = generation
        let account = userID
        defer { if generation == token { isMutating = false } }
        var successful: Set<Int> = []
        var failures = 0
        for id in targets {
            guard generation == token, !Task.isCancelled else { return successful }
            do {
                try await api.markRead(id: id, userID: account)
                guard generation == token else { return successful }
                revision += 1
                successful.insert(id)
                alerts.removeAll { $0.eventID == id }
            } catch {
                guard generation == token, !Task.isCancelled else { return successful }
                failures += 1
                errorMessage = error.localizedDescription
            }
        }
        message = failures == 0
            ? "\(successful.count)건 읽음 처리했어요."
            : "\(successful.count)건 읽음, \(failures)건 실패했어요. 실패 항목을 다시 시도해 주세요."
        await refresh()
        await refreshArchive()
        return successful
    }

    func markAllRead() async {
        guard !isMutating, !userID.isEmpty else { return }
        isMutating = true
        errorMessage = nil
        let token = generation
        let account = userID
        defer { if generation == token { isMutating = false } }
        do {
            let response = try await api.markAllRead(userID: account)
            guard generation == token else { return }
            revision += 1
            alerts = []
            message = "모두 읽음 처리 완료 (\(response.updated_count ?? 0)건)"
            await refresh()
            await refreshArchive()
        } catch {
            guard generation == token, !Task.isCancelled else { return }
            errorMessage = error.localizedDescription
        }
    }

    @discardableResult
    func clearArchive(ids: Set<Int>?) async -> Bool {
        guard !isMutating, !userID.isEmpty else { return false }
        isMutating = true
        archiveErrorMessage = nil
        let token = generation
        let account = userID
        defer { if generation == token { isMutating = false } }
        do {
            let response = try await api.clearArchive(userID: account, ids: ids)
            guard generation == token else { return false }
            revision += 1
            let skipped = response.skipped_count ?? 0
            let missing = response.not_found_ids.count
            message = "보관함 비우기 완료 (\(response.cleared_count ?? 0)건)"
            if skipped > 0 || missing > 0 {
                message! += " · \(skipped)건 건너뜀, \(missing)건 찾지 못함"
            }
            await refreshArchive()
            return true
        } catch {
            guard generation == token, !Task.isCancelled else { return false }
            archiveErrorMessage = error.localizedDescription
            return false
        }
    }

    var visibleArchiveIDs: Set<Int> {
        Set(groups.values.flatMap { $0.values.flatMap { $0 } }.map(\.eventID).filter { $0 > 0 })
    }

    static func sortedChips(_ keys: Dictionary<String, [String: [AlertItem]]>.Keys) -> [String] {
        let order = ["M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "기타": 99]
        return keys.sorted {
            let a = order[$0.uppercased()] ?? 50
            let b = order[$1.uppercased()] ?? 50
            return a == b ? $0 < $1 : a < b
        }
    }

    static func sortedScreens(_ keys: Dictionary<String, [AlertItem]>.Keys) -> [String] {
        keys.sorted {
            let a = $0 == "기타" ? 99 : (Int($0) ?? 50)
            let b = $1 == "기타" ? 99 : (Int($1) ?? 50)
            return a == b ? $0 < $1 : a < b
        }
    }
}
