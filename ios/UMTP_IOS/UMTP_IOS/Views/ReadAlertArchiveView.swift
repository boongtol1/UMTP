import SwiftUI

struct ReadAlertArchiveView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var viewModel: AlertFeedViewModel
    @State private var selectedAlert: AlertItem?
    @State private var selectedIDs: Set<Int> = []
    @State private var isSelecting = false
    @State private var clearRequest: ArchiveClearRequest?
    let onStartTrade: (AlertItem, Bool) -> Void

    init(viewModel: AlertFeedViewModel? = nil, onStartTrade: @escaping (AlertItem, Bool) -> Void = { _, _ in }) {
        _viewModel = StateObject(wrappedValue: viewModel ?? AlertFeedViewModel())
        self.onStartTrade = onStartTrade
    }

    var body: some View {
        NavigationStack {
            List {
                AlertStatusView(isRefreshing: viewModel.isRefreshingArchive, error: viewModel.archiveErrorMessage,
                                message: viewModel.message, lastRefresh: nil) {
                    Task { await viewModel.refreshArchive() }
                }
                if viewModel.visibleArchiveIDs.isEmpty && !viewModel.isRefreshingArchive {
                    Text("읽음 처리된 알림이 없습니다.").foregroundStyle(.secondary)
                }
                ForEach(AlertFeedViewModel.sortedChips(viewModel.groups.keys), id: \.self) { chip in
                    let screenGroups = viewModel.groups[chip] ?? [:]
                    ForEach(AlertFeedViewModel.sortedScreens(screenGroups.keys), id: \.self) { screen in
                        Section("\(chip) · \(screen == "기타" ? "기타" : "\(screen)인치")") {
                            ForEach(screenGroups[screen] ?? [], id: \.archiveIdentity) { alert in
                                AlertCardView(
                                    alert: alert, archive: true, isSelecting: isSelecting,
                                    isSelected: selectedIDs.contains(alert.eventID), isBusy: viewModel.isMutating,
                                    onOpen: { open(alert) }, onStartTrade: { onStartTrade(alert, true) }
                                )
                            }
                        }
                    }
                }
            }
            .navigationTitle("읽음 알림 보관함")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable { await viewModel.refreshArchive() }
            .navigationDestination(item: $selectedAlert) { alert in
                AlertDetailView(alert: alert, archive: true, viewModel: viewModel)
            }
            .toolbar {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Menu {
                        Button(isSelecting ? "선택 해제" : "선택") {
                            isSelecting.toggle()
                            if !isSelecting { selectedIDs = [] }
                        }.disabled(viewModel.visibleArchiveIDs.isEmpty || viewModel.isMutating)
                        if isSelecting {
                            Button(selectedIDs == viewModel.visibleArchiveIDs ? "전체 해제" : "전체 선택") {
                                selectedIDs = selectedIDs == viewModel.visibleArchiveIDs ? [] : viewModel.visibleArchiveIDs
                            }.disabled(viewModel.isMutating)
                            Button("선택 비우기 (\(selectedIDs.count)건)", role: .destructive) {
                                clearRequest = .selected(selectedIDs)
                            }.disabled(selectedIDs.isEmpty || viewModel.isMutating)
                        }
                        Button("전체 비우기", role: .destructive) { clearRequest = .all }
                            .disabled(viewModel.visibleArchiveIDs.isEmpty || viewModel.isMutating)
                    } label: { Label("보관함 관리", systemImage: "ellipsis.circle") }
                    Button { Task { await viewModel.refreshArchive() } } label: {
                        Label("새로고침", systemImage: "arrow.clockwise")
                    }.disabled(viewModel.isRefreshingArchive)
                }
            }
            .confirmationDialog(
                clearRequest?.title ?? "보관함 비우기",
                isPresented: Binding(get: { clearRequest != nil }, set: { if !$0 { clearRequest = nil } }),
                titleVisibility: .visible, presenting: clearRequest
            ) { request in
                Button(request.title, role: .destructive) {
                    Task {
                        if await viewModel.clearArchive(ids: request.ids) {
                            selectedIDs.formIntersection(viewModel.visibleArchiveIDs)
                            if selectedIDs.isEmpty { isSelecting = false }
                        }
                    }
                }
                Button("취소", role: .cancel) { clearRequest = nil }
            } message: { _ in
                Text("비운 알림은 보관함에서 숨겨져요. 거래 기록은 유지돼요.")
            }
        }
        .task(id: appState.userId) {
            viewModel.configure(userID: appState.userId ?? "")
            await viewModel.refreshArchive()
        }
        .onAppear {
            viewModel.configure(userID: appState.userId ?? "")
            Task { await viewModel.refreshArchive() }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { Task { await viewModel.refreshArchive() } }
        }
        .onChange(of: viewModel.groups) { _, _ in selectedIDs.formIntersection(viewModel.visibleArchiveIDs) }
        .onReceive(NotificationCenter.default.publisher(for: .umtpSettingsDidChange)) { _ in
            Task { await viewModel.refreshArchive() }
        }
    }

    private func open(_ alert: AlertItem) {
        if isSelecting {
            guard alert.eventID > 0, !viewModel.isMutating else { return }
            if selectedIDs.contains(alert.eventID) { selectedIDs.remove(alert.eventID) }
            else { selectedIDs.insert(alert.eventID) }
        } else { selectedAlert = alert }
    }
}

private enum ArchiveClearRequest {
    case all
    case selected(Set<Int>)
    var ids: Set<Int>? {
        if case .selected(let ids) = self { return ids }
        return nil
    }
    var title: String {
        if case .selected(let ids) = self { return "선택 \(ids.count)건 비우기" }
        return "전체 비우기"
    }
}
