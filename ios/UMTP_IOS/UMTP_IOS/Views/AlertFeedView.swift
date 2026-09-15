import SwiftUI

struct AlertFeedView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var viewModel: AlertFeedViewModel
    @State private var selectedAlert: AlertItem?
    @State private var selectedIsArchive = false
    @State private var isSelecting = false
    @State private var selectedIDs: Set<Int> = []
    @State private var confirmingReadAll = false
    @State private var isRouting = false
    let onStartTrade: (AlertItem, Bool) -> Void

    init(viewModel: AlertFeedViewModel? = nil, onStartTrade: @escaping (AlertItem, Bool) -> Void = { _, _ in }) {
        _viewModel = StateObject(wrappedValue: viewModel ?? AlertFeedViewModel())
        self.onStartTrade = onStartTrade
    }

    var body: some View {
        NavigationStack {
            List {
                AlertStatusView(isRefreshing: viewModel.isRefreshing, error: viewModel.errorMessage,
                                message: viewModel.message, lastRefresh: viewModel.lastRefresh) {
                    Task { await viewModel.refresh(); await routePendingAlert() }
                }
                if viewModel.alerts.isEmpty && !viewModel.isRefreshing {
                    Text("알림이 없습니다.").foregroundStyle(.secondary)
                }
                ForEach(viewModel.alerts) { alert in
                    AlertCardView(
                        alert: alert, isSelecting: isSelecting,
                        isSelected: selectedIDs.contains(alert.eventID), isBusy: viewModel.isMutating,
                        onOpen: { open(alert) }, onStartTrade: { onStartTrade(alert, false) }
                    )
                }
            }
            .navigationTitle("거래 알림 피드")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable { await viewModel.refresh(); await routePendingAlert() }
            .navigationDestination(item: $selectedAlert) { alert in
                AlertDetailView(alert: alert, archive: selectedIsArchive, viewModel: viewModel)
            }
            .toolbar {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Menu {
                        Button(isSelecting ? "선택 해제" : "선택") {
                            isSelecting.toggle()
                            if !isSelecting { selectedIDs = [] }
                        }.disabled(viewModel.alerts.isEmpty || viewModel.isMutating)
                        if isSelecting {
                            Button(selectedIDs == visibleIDs ? "전체 해제" : "전체 선택") {
                                selectedIDs = selectedIDs == visibleIDs ? [] : visibleIDs
                            }.disabled(viewModel.isMutating)
                            Button("선택 읽음 (\(selectedIDs.count)건)") {
                                let ids = selectedIDs
                                Task {
                                    let successful = await viewModel.markSelectedRead(ids)
                                    selectedIDs.subtract(successful)
                                    if selectedIDs.isEmpty { isSelecting = false }
                                }
                            }.disabled(selectedIDs.isEmpty || viewModel.isMutating)
                        }
                        Button("모두 읽음") { confirmingReadAll = true }
                            .disabled(viewModel.alerts.isEmpty || viewModel.isMutating)
                    } label: { Label("알림 관리", systemImage: "ellipsis.circle") }
                    Button {
                        Task { await viewModel.refresh(); await routePendingAlert() }
                    } label: { Label("새로고침", systemImage: "arrow.clockwise") }
                        .disabled(viewModel.isRefreshing)
                }
            }
            .confirmationDialog("모든 알림을 읽음 처리할까요?", isPresented: $confirmingReadAll, titleVisibility: .visible) {
                Button("모두 읽음") { Task { await viewModel.markAllRead() } }
                Button("취소", role: .cancel) {}
            } message: { Text("읽음 처리한 알림은 읽음 보관함에서 다시 확인할 수 있어요.") }
        }
        .task(id: appState.userId) {
            viewModel.configure(userID: appState.userId ?? "")
            await viewModel.refresh()
            if scenePhase == .active { viewModel.onAppear() }
            await routePendingAlert()
        }
        .onAppear {
            viewModel.configure(userID: appState.userId ?? "")
            if scenePhase == .active { viewModel.onAppear() }
        }
        .onDisappear { viewModel.onDisappear() }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                viewModel.onAppear()
                Task { await viewModel.refresh(); await routePendingAlert() }
            } else { viewModel.onDisappear() }
        }
        .onChange(of: appState.pendingAlertID) { _, id in
            guard id != nil else { return }
            Task { await viewModel.refresh(); await routePendingAlert() }
        }
        .onChange(of: viewModel.lastRefresh) { _, _ in Task { await routePendingAlert() } }
        .onChange(of: viewModel.isRefreshingArchive) { _, loading in
            if !loading { Task { await routePendingAlert() } }
        }
        .onChange(of: viewModel.alerts) { _, _ in
            selectedIDs.formIntersection(visibleIDs)
            if let id = appState.pendingAlertID, let target = viewModel.alerts.first(where: { $0.eventID == id || $0.id == id }) {
                selectedIsArchive = false
                selectedAlert = target
                appState.pendingAlertID = nil
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .umtpSettingsDidChange)) { _ in
            Task { await viewModel.refresh() }
        }
        .onReceive(NotificationCenter.default.publisher(for: .umtpRemoteAlertsDidChange)) { _ in
            Task { await viewModel.refresh(); await routePendingAlert() }
        }
    }

    private var visibleIDs: Set<Int> { Set(viewModel.alerts.map(\.eventID).filter { $0 > 0 }) }

    private func open(_ alert: AlertItem) {
        if isSelecting {
            guard alert.eventID > 0, !viewModel.isMutating else { return }
            if selectedIDs.contains(alert.eventID) { selectedIDs.remove(alert.eventID) }
            else { selectedIDs.insert(alert.eventID) }
        } else {
            selectedIsArchive = false
            selectedAlert = alert
        }
    }

    private func routePendingAlert() async {
        guard let id = appState.pendingAlertID, !isRouting,
              !viewModel.isRefreshing, !viewModel.isRefreshingArchive,
              viewModel.lastRefresh != nil else { return }
        isRouting = true
        defer { isRouting = false }
        if let alert = viewModel.alerts.first(where: { $0.eventID == id || $0.id == id }) {
            selectedIsArchive = false
            selectedAlert = alert
            appState.pendingAlertID = nil
            return
        }
        await viewModel.refreshArchive()
        guard appState.pendingAlertID == id else { return }
        if let alert = viewModel.groups.values.flatMap({ $0.values.flatMap { $0 } })
            .first(where: { $0.eventID == id || $0.id == id }) {
            selectedIsArchive = true
            selectedAlert = alert
            appState.pendingAlertID = nil
        } else if viewModel.errorMessage == nil && viewModel.archiveErrorMessage == nil {
            viewModel.message = "이 알림은 더 이상 표시할 수 없어요. 알림 피드와 읽음 보관함을 확인해 주세요."
            appState.pendingAlertID = nil
        }
    }
}
