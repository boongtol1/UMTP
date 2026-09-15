import XCTest
@testable import UMTP_IOS

@MainActor
final class DNSParityTests: XCTestCase {
    private struct Reply: Decodable { let ok: Bool }
    // Recovery requires HTTPS. Keep these mocked requests independent of the
    // app's optional HTTP loopback build setting; no transport contacts this host.
    private let baseURL = "https://api.example.invalid"

    private func success(_ request: URLRequest, status: Int = 200) -> (Data, URLResponse) {
        (Data(#"{"ok":true}"#.utf8),
         HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }

    func testSuccessfulSystemDNSDoesNotConfigureFallback() async throws {
        var configured: [DNSRecovery.Resolver] = []
        let recovery = DNSRecovery(configure: { configured.append($0) })
        var requests = 0
        let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { request in
            requests += 1
            return self.success(request)
        })
        let reply: Reply = try await client.get(path: "alerts")
        XCTAssertTrue(reply.ok)
        XCTAssertEqual(requests, 1)
        XCTAssertTrue(configured.isEmpty)
    }

    func testPreflightMutationRecoveryPreservesOriginalHTTPSRequest() async throws {
        var configured: [DNSRecovery.Resolver] = []
        let recovery = DNSRecovery(configure: { configured.append($0) })
        var requests: [URLRequest] = []
        let client = APIClient(baseURLString: "https://umtp.duckdns.org/api", dnsRecovery: recovery,
            transport: { request in
                requests.append(request)
                if requests.count == 1 {
                    throw DNSTransportFailure(underlying: URLError(.cannotFindHost), progress: .notStarted)
                }
                return self.success(request)
            })
        let _: Reply = try await client.send(path: "users/fixture/settings", method: "PATCH", body: ["enabled": true],
            query: [.init(name: "user_id", value: "test/한글")])
        XCTAssertEqual(requests.count, 2)
        XCTAssertEqual(requests[0], requests[1])
        XCTAssertEqual(requests[1].url?.scheme, "https")
        XCTAssertEqual(requests[1].url?.host, "umtp.duckdns.org")
        XCTAssertEqual(requests[1].httpMethod, "PATCH")
        XCTAssertNotNil(requests[1].httpBody)
        XCTAssertNil(requests[1].value(forHTTPHeaderField: "Host"))
        XCTAssertEqual(configured, [DNSRecovery.resolvers[0]])
    }

    func testCloudflareThenGoogleAndProcessWideMonotonicFallback() async throws {
        var configured: [DNSRecovery.Resolver] = []
        let recovery = DNSRecovery(configure: { configured.append($0) })
        var calls = 0
        let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { request in
            calls += 1
            if calls < 3 { throw URLError(.dnsLookupFailed) }
            return self.success(request)
        })
        let _: Reply = try await client.get(path: "alerts")
        XCTAssertEqual(calls, 3)
        XCTAssertEqual(configured, DNSRecovery.resolvers)
        let _: Reply = try await client.get(path: "alerts")
        XCTAssertEqual(calls, 4)
        XCTAssertEqual(configured.count, 2)
    }

    func testAllDNSFailuresAreBoundedAndKeepSafeNetworkError() async {
        var configured: [DNSRecovery.Resolver] = []
        let recovery = DNSRecovery(configure: { configured.append($0) })
        var calls = 0
        let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { _ in
            calls += 1
            throw URLError(.cannotFindHost)
        })
        do { let _: Reply = try await client.get(path: "alerts"); XCTFail("Expected unresolved DNS") }
        catch { XCTAssertTrue(error is APIClientError) }
        XCTAssertEqual(calls, 3)
        XCTAssertEqual(configured.count, 2)
        // The shared context is already Google: a later failure cannot downgrade it.
        do { let _: Reply = try await client.get(path: "alerts"); XCTFail("Expected unresolved DNS") }
        catch { XCTAssertTrue(error is APIClientError) }
        XCTAssertEqual(calls, 4)
        XCTAssertEqual(configured.count, 2)
    }

    func testOnlyHTTPSBaseHostOrDuckDNSAreEligible() {
        for (url, allowed) in [
            ("https://api.example.org/alerts", true),
            ("https://other.duckdns.org/alerts", true),
            ("https://notduckdns.org/alerts", false),
            ("https://duckdns.org.attacker.invalid/alerts", false),
            ("https://other.example.org/alerts", false),
            ("http://api.example.org/alerts", false),
            ("http://127.0.0.1:18765/alerts", false)
        ] {
            XCTAssertEqual(DNSRecovery.canRecover(request: URLRequest(url: URL(string: url)!),
                baseHost: "API.EXAMPLE.ORG", error: URLError(.cannotFindHost), progress: .notStarted), allowed, url)
        }
    }

    func testTimeoutDisconnectTLSAndHTTPFailuresAreNeverRetried() async {
        for code in [URLError.Code.timedOut, .networkConnectionLost, .cannotConnectToHost,
                     .notConnectedToInternet, .secureConnectionFailed, .serverCertificateUntrusted] {
            var calls = 0
            let recovery = DNSRecovery(configure: { _ in XCTFail("Must not change DNS for \(code)") })
            let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { _ in
                calls += 1
                throw DNSTransportFailure(underlying: URLError(code), progress: .notStarted)
            })
            do { let _: Reply = try await client.send(path: "trades", method: "POST"); XCTFail("Expected error") }
            catch { XCTAssertTrue(error is APIClientError) }
            XCTAssertEqual(calls, 1)
        }
        var calls = 0
        let recovery = DNSRecovery(configure: { _ in XCTFail("HTTP errors must not configure DNS") })
        let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { request in
            calls += 1
            return self.success(request, status: 503)
        })
        do { let _: Reply = try await client.send(path: "trades", method: "POST"); XCTFail("Expected HTTP failure") }
        catch { guard case APIClientError.httpStatus(503) = error else { return XCTFail("Expected HTTP 503") } }
        XCTAssertEqual(calls, 1)
    }

    func testSentOrUncertainMutationIsNeverReplayedEvenOnDNSError() async {
        for progress in [DNSRequestProgress.started, .unknown] {
            var calls = 0
            let recovery = DNSRecovery(configure: { _ in XCTFail("Must not replay a possibly sent mutation") })
            let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { _ in
                calls += 1
                throw DNSTransportFailure(underlying: URLError(.cannotFindHost), progress: progress)
            })
            do { let _: Reply = try await client.send(path: "trades", method: "POST"); XCTFail("Expected DNS failure") }
            catch { XCTAssertTrue(error is APIClientError) }
            XCTAssertEqual(calls, 1)
        }
    }

    func testRedirectDNSFailureDoesNotReplayOriginalRequest() {
        var request = URLRequest(url: URL(string: "https://umtp.duckdns.org/trades")!)
        request.httpMethod = "POST"
        let error = URLError(.cannotFindHost, userInfo: [NSURLErrorFailingURLErrorKey: URL(string: "https://other.duckdns.org/trades")!])
        XCTAssertFalse(DNSRecovery.canRecover(request: request, baseHost: "umtp.duckdns.org",
            error: error, progress: .notStarted))
        request.httpMethod = "GET"
        XCTAssertFalse(DNSRecovery.canRecover(request: request, baseHost: "umtp.duckdns.org",
            error: URLError(.dnsLookupFailed), progress: .started))
    }

    func testCancellationDoesNotConfigureFallbackOrRetry() async {
        var calls = 0
        let recovery = DNSRecovery(configure: { _ in XCTFail("Cancellation must not configure DNS") })
        let client = APIClient(baseURLString: baseURL, dnsRecovery: recovery, transport: { _ in
            calls += 1
            throw URLError(.cancelled)
        })
        do { let _: Reply = try await client.get(path: "alerts"); XCTFail("Expected cancellation") }
        catch { XCTAssertTrue(error is CancellationError) }
        XCTAssertEqual(calls, 1)
    }
}
