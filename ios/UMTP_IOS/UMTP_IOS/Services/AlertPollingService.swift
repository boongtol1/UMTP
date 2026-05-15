import Foundation

final class AlertPollingService {
    private(set) var isRunning = false

    // TODO(Stage2): 실제 alerts polling 구현
    func start() {
        isRunning = true
    }

    func stop() {
        isRunning = false
    }
}
