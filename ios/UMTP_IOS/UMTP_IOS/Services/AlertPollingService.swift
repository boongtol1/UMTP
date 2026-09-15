import Foundation

@MainActor
final class AlertPollingService {
    private(set) var isRunning = false
    private var task: Task<Void, Never>?
    private let intervalNanoseconds: UInt64

    init(intervalNanoseconds: UInt64 = 10_000_000_000) {
        self.intervalNanoseconds = intervalNanoseconds
    }

    deinit { task?.cancel() }

    func start(action: @escaping @MainActor () async -> Void) {
        guard !isRunning else { return }
        isRunning = true
        let interval = intervalNanoseconds
        task = Task {
            while !Task.isCancelled {
                await action()
                do { try await Task.sleep(nanoseconds: interval) }
                catch { break }
            }
        }
    }

    func stop() {
        task?.cancel()
        task = nil
        isRunning = false
    }
}
