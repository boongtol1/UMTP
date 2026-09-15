import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var alerts = AlertFeedViewModel()
    @StateObject private var trade: ResaleTradeViewModel
    @State private var selectedTab = 0
    @State private var tradeRoute: TradeRoute?
    @State private var confirmTradeReplacement = false
    @State private var tradeBusyNotice = false

    init(userId: String) {
        _trade = StateObject(wrappedValue: ResaleTradeViewModel(userId: userId))
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            AlertFeedView(viewModel: alerts, onStartTrade: startTrade)
                .tabItem { Label("알림", systemImage: "bell") }.tag(0)
            ReadAlertArchiveView(viewModel: alerts, onStartTrade: startTrade)
                .tabItem { Label("읽음 보관함", systemImage: "archivebox") }.tag(1)
            NavigationStack {
                ResaleTradeView(viewModel: trade)
            }
            .tabItem { Label("거래 입력", systemImage: "square.and.pencil") }.tag(2)
            SettingsView()
                .tabItem { Label("설정", systemImage: "gearshape") }.tag(3)
        }
        .onChange(of: appState.pendingAlertID, initial: true) { _, id in
            if id != nil { selectedTab = 0 }
        }
        .onChange(of: selectedTab) { _, tab in
            if tab == 2 { Task { await trade.loadHistory() } }
        }
        // Continuing the draft is a navigation action, not just the system's
        // implicit popover dismissal. Keep both choices visible in an alert.
        .alert("작성 중인 거래 입력", isPresented: $confirmTradeReplacement) {
            Button("계속 작성", role: .cancel) { tradeRoute = nil; selectedTab = 2 }
                .accessibilityIdentifier("trade.draft.keep")
            Button("다른 거래 열기", role: .destructive) { openPendingTrade() }
                .accessibilityIdentifier("trade.draft.replace")
        } message: {
            Text("다른 매물을 열면 현재 거래의 저장하지 않은 입력이 사라집니다. 계속 작성하거나 다른 거래를 열어 주세요.")
        }
        .alert("거래 처리 중", isPresented: $tradeBusyNotice) {
            Button("확인", role: .cancel) {}
        } message: {
            Text("현재 거래의 처리가 끝난 뒤 다시 열어 주세요. 입력한 내용은 유지됩니다.")
        }
    }

    private func startTrade(_ item: AlertItem, fromArchive: Bool) {
        guard !trade.isBusy else { tradeBusyNotice = true; return }
        let archiveID = fromArchive ? item.read_archive_event_id.flatMap { $0 > 0 ? $0 : nil } : nil
        let id = archiveID ?? item.alert_event_id ?? item.id
        guard id > 0 else { return }
        tradeRoute = TradeRoute(alertID: id, fromArchive: archiveID != nil)
        if trade.hasUnsavedChanges { confirmTradeReplacement = true }
        else { openPendingTrade() }
    }

    private func openPendingTrade() {
        guard let route = tradeRoute else { return }
        guard !trade.isBusy else { tradeBusyNotice = true; return }
        tradeRoute = nil
        selectedTab = 2
        Task { await trade.start(alertId: route.alertID, fromArchive: route.fromArchive) }
    }

    private struct TradeRoute {
        let alertID: Int
        let fromArchive: Bool
    }
}
