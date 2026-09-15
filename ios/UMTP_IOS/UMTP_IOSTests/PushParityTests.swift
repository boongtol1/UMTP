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

    func testUnconfiguredLogoutCreatesNoDeletionButPreservesExistingCleanup() async {
        let suite = UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        var calls = 0
        let deletion = PushTokenDeletion(defaults: defaults) { calls += 1 }

        deletion.requireDeletion(isConfigured: false)
        XCTAssertFalse(deletion.isPending)
        XCTAssertNil(defaults.object(forKey: "umtp_ios_push_token_deletion_pending"))
        let noCleanupNeeded = await deletion.completePendingDeletion(isConfigured: false)
        XCTAssertTrue(noCleanupNeeded)
        XCTAssertEqual(calls, 0)

        deletion.requireDeletion(isConfigured: true)
        deletion.requireDeletion(isConfigured: false)
        let unavailable = await deletion.completePendingDeletion(isConfigured: false)
        XCTAssertFalse(unavailable, "Existing cleanup must still block SDK token activation")
        XCTAssertTrue(deletion.isPending)
        XCTAssertTrue(defaults.bool(forKey: "umtp_ios_push_token_deletion_pending"))
        XCTAssertEqual(calls, 0, "A missing Firebase configuration must never invoke its SDK")

        let configuredAgain = await deletion.completePendingDeletion(isConfigured: true)
        XCTAssertTrue(configuredAgain)
        XCTAssertEqual(calls, 1)
        XCTAssertFalse(deletion.isPending)
    }

    func testTokenDeletionFailureStaysPendingUntilRetrySucceeds() async {
        let suite = UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        var calls = 0
        let deletion = PushTokenDeletion(defaults: defaults) {
            calls += 1
            if calls == 1 { throw APIClientError.httpStatus(503) }
        }

        let initiallyReady = await deletion.completePendingDeletion()
        XCTAssertTrue(initiallyReady)
        XCTAssertEqual(calls, 0)
        deletion.requireDeletion()
        XCTAssertTrue(defaults.bool(forKey: "umtp_ios_push_token_deletion_pending"))

        let failed = await deletion.completePendingDeletion()
        XCTAssertFalse(failed, "A failed deletion must keep token activation blocked")
        XCTAssertTrue(deletion.isPending)
        XCTAssertNotNil(deletion.lastError)
        XCTAssertTrue(defaults.bool(forKey: "umtp_ios_push_token_deletion_pending"))

        let retried = await deletion.completePendingDeletion()
        XCTAssertTrue(retried)
        XCTAssertFalse(deletion.isPending)
        XCTAssertNil(deletion.lastError)
        XCTAssertNil(defaults.object(forKey: "umtp_ios_push_token_deletion_pending"))
        let alreadyReady = await deletion.completePendingDeletion()
        XCTAssertTrue(alreadyReady)
        XCTAssertEqual(calls, 2, "A confirmed deletion must not be repeated on each foreground activation")
    }

    func testPendingTokenDeletionSurvivesCoordinatorRecreation() async {
        let suite = UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        var calls = 0
        let original = PushTokenDeletion(defaults: defaults) {
            calls += 1
            throw APIClientError.httpStatus(503)
        }
        original.requireDeletion()

        // Recreate before any SDK call, as if the process ended immediately after logout.
        let restored = PushTokenDeletion(defaults: UserDefaults(suiteName: suite)!) {
            calls += 1
            throw APIClientError.httpStatus(503)
        }
        XCTAssertTrue(restored.isPending)
        XCTAssertEqual(calls, 0)
        let failed = await restored.completePendingDeletion()
        XCTAssertFalse(failed)

        // A failed attempt must also survive another restart and permit a later retry.
        let retried = PushTokenDeletion(defaults: UserDefaults(suiteName: suite)!) { calls += 1 }
        XCTAssertTrue(retried.isPending)
        let completed = await retried.completePendingDeletion()
        XCTAssertTrue(completed)
        XCTAssertEqual(calls, 2)
        let completedAfterRestart = PushTokenDeletion(defaults: UserDefaults(suiteName: suite)!) {}
        XCTAssertFalse(completedAfterRestart.isPending)
    }

    func testConcurrentCleanupAndRepeatedLogoutShareOneDeletion() async {
        let suite = UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        var finish: CheckedContinuation<Void, Never>?
        var calls = 0
        let deletion = PushTokenDeletion(defaults: defaults) {
            calls += 1
            if calls == 1 { await withCheckedContinuation { finish = $0 } }
        }
        deletion.requireDeletion()
        let logout = Task { await deletion.completePendingDeletion() }
        while finish == nil { await Task.yield() }

        var joined = 0
        let activation = Task {
            joined += 1
            return await deletion.completePendingDeletion()
        }
        while joined < 1 { await Task.yield() }
        deletion.requireDeletion()
        deletion.requireDeletion()
        let repeatedLogout = Task {
            joined += 1
            return await deletion.completePendingDeletion()
        }
        while joined < 2 { await Task.yield() }
        XCTAssertTrue(deletion.isPending)
        XCTAssertEqual(calls, 1, "Logout and activation must await the same in-flight SDK deletion")

        finish?.resume()
        let logoutCompleted = await logout.value
        let activationCompleted = await activation.value
        let repeatedLogoutCompleted = await repeatedLogout.value
        XCTAssertTrue(logoutCompleted)
        XCTAssertTrue(activationCompleted)
        XCTAssertTrue(repeatedLogoutCompleted)
        XCTAssertFalse(deletion.isPending)
        XCTAssertEqual(calls, 1)

        deletion.requireDeletion()
        let nextSessionLogout = await deletion.completePendingDeletion()
        XCTAssertTrue(nextSessionLogout)
        XCTAssertEqual(calls, 2, "A later session's logout must start a fresh deletion")
    }

    func testDeletionWaitsForTokenFetchAlreadyInProgress() async {
        let suite = UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let queue = PushTokenFetchQueue()
        var finishFetch: CheckedContinuation<Void, Never>?
        var events: [String] = []
        let fetch = Task {
            await queue.run {
                events.append("fetch started")
                await withCheckedContinuation { finishFetch = $0 }
                events.append("fetch finished")
            }
        }
        while finishFetch == nil { await Task.yield() }
        var waitingForFetch = false
        let deletion = PushTokenDeletion(defaults: defaults, waitForFetches: {
            waitingForFetch = true
            await queue.waitUntilIdle()
        }, deleteToken: { events.append("token deleted") })
        deletion.requireDeletion()
        let cleanup = Task { await deletion.completePendingDeletion() }
        while !waitingForFetch { await Task.yield() }
        XCTAssertEqual(events, ["fetch started"])
        XCTAssertTrue(deletion.isPending)

        finishFetch?.resume()
        await fetch.value
        let completed = await cleanup.value
        XCTAssertTrue(completed)
        XCTAssertEqual(events, ["fetch started", "fetch finished", "token deleted"])
    }
}
