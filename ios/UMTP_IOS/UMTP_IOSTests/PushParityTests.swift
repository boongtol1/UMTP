import XCTest
@testable import UMTP_IOS

@MainActor
final class PushParityTests: XCTestCase {
    func testNotificationRouteAcceptsOnlyPositiveIntegerIDs() {
        XCTAssertEqual(PushRoute.alertID(from: ["alert_id": "123"]), 123)
        XCTAssertEqual(PushRoute.alertID(from: ["alert_id": 123]), 123)
        XCTAssertNil(PushRoute.alertID(from: ["alert_id": true]))
        XCTAssertNil(PushRoute.alertID(from: ["alert_id": "-1"]))
        XCTAssertNil(PushRoute.alertID(from: ["alert_id": 2.5]))
        XCTAssertNil(PushRoute.alertID(from: ["alert_id": "https://untrusted.invalid"]))
        XCTAssertNil(PushRoute.alertID(from: [:]))
    }

    func testTokenRegistersOncePerUserAndRotationRetriesFailures() async {
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        var calls: [String] = []
        var fail = true
        let registry = PushTokenRegistration(defaults: defaults) { user, token in
            calls.append(user + token)
            if fail { throw APIClientError.httpStatus(503) }
        }
        let a = String(repeating: "a", count: 25)
        let b = String(repeating: "b", count: 25)
        await registry.register(user: "one", token: a)
        XCTAssertNotNil(registry.lastError)
        XCTAssertNil(defaults.string(forKey: "umtp_ios_push_registered_token"))
        fail = false
        await registry.register(user: "one", token: a)
        await registry.register(user: "one", token: a)
        XCTAssertEqual(calls.count, 2)
        await registry.register(user: "one", token: b)
        await registry.register(user: "two", token: b)
        XCTAssertEqual(calls.count, 4)
        XCTAssertNil(registry.lastError)
        registry.clear()
        XCTAssertNil(defaults.string(forKey: "umtp_ios_push_registered_user"))
    }

    func testLogoutCannotPersistInFlightRegistrationAndQueuedNewUserRuns() async {
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        var resume: CheckedContinuation<Void, Never>?
        var calls = 0
        let registry = PushTokenRegistration(defaults: defaults) { _, _ in
            calls += 1
            if calls == 1 { await withCheckedContinuation { resume = $0 } }
        }
        let task = Task { await registry.register(user: "old", token: String(repeating: "a", count: 25)) }
        while resume == nil { await Task.yield() }
        registry.clear()
        await registry.register(user: "new", token: String(repeating: "b", count: 25))
        resume?.resume()
        await task.value
        XCTAssertEqual(calls, 2)
        XCTAssertEqual(defaults.string(forKey: "umtp_ios_push_registered_user"), "new")
    }

    func testTokenRotationDuringFetchIsCoalescedAndFetchedAgain() async {
        let queue = PushTokenFetchQueue()
        var resume: CheckedContinuation<Void, Never>?
        var calls = 0
        let operation = {
            calls += 1
            if calls == 1 { await withCheckedContinuation { resume = $0 } }
        }
        let task = Task { await queue.run(operation) }
        while resume == nil { await Task.yield() }
        await queue.run(operation)
        await queue.run(operation)
        resume?.resume()
        await task.value
        XCTAssertEqual(calls, 2, "Rotation or a new session during an in-flight fetch must be retried, without parallel requests")
        await queue.run(operation)
        XCTAssertEqual(calls, 3)
    }
}
