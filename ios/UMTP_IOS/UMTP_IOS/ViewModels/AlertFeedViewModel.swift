import Combine
import Foundation

@MainActor
final class AlertFeedViewModel: ObservableObject {
    @Published private(set) var alerts: [AlertItem] = []

    private let pollingService: AlertPollingService

    init(pollingService: AlertPollingService) {
        self.pollingService = pollingService
    }

    func onAppear() {
        // TODO(Stage2): 서버 연동
        pollingService.start()
    }

    func onDisappear() {
        pollingService.stop()
    }
}
