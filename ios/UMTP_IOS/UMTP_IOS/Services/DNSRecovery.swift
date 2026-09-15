import Foundation
import Network

enum DNSRequestProgress: Sendable {
    case notStarted, started, unknown
}

struct DNSTransportFailure: Error {
    let underlying: Error
    let progress: DNSRequestProgress
}

/// Native DNS recovery never substitutes an IP into the application request URL.
/// Apple's default PrivacyContext also affects URLSession and other app DNS lookups:
/// https://developer.apple.com/videos/play/wwdc2020/10047/ (12:07).
/// System encrypted-DNS policy takes precedence over these fallback resolvers.
@MainActor
final class DNSRecovery {
    struct Resolver: Equatable {
        let url: URL
        let addresses: [String]
    }

    typealias Transport = (URLRequest) async throws -> (Data, URLResponse)
    static let shared = DNSRecovery()
    static let resolvers = [
        Resolver(url: URL(string: "https://cloudflare-dns.com/dns-query")!, addresses: ["1.1.1.1", "1.0.0.1"]),
        Resolver(url: URL(string: "https://dns.google/dns-query")!, addresses: ["8.8.8.8", "8.8.4.4"])
    ]

    private let configure: (Resolver) -> Void
    private var installedResolverIndex: Int?

    /// Inject configuration and transport in tests: never change real app DNS there.
    init(configure: ((Resolver) -> Void)? = nil) {
        self.configure = configure ?? { resolver in
            let endpoints = resolver.addresses.map {
                NWEndpoint.hostPort(host: NWEndpoint.Host($0), port: 443)
            }
            let context = NWParameters.PrivacyContext.default
            context.requireEncryptedNameResolution(true,
                fallbackResolver: .https(resolver.url, serverAddresses: endpoints))
            context.flushCache()
        }
    }

    func data(for request: URLRequest, baseHost: String?, transport: Transport) async throws -> (Data, URLResponse) {
        var retries = 0
        while true {
            try Task.checkCancellation()
            let attemptedResolverIndex = installedResolverIndex
            do { return try await transport(request) }
            catch {
                let failure = error as? DNSTransportFailure
                let underlying = failure?.underlying ?? error
                guard retries < Self.resolvers.count,
                      Self.canRecover(request: request, baseHost: baseHost, error: underlying,
                                      progress: failure?.progress ?? .unknown) else { throw underlying }
                try Task.checkCancellation()

                if attemptedResolverIndex == installedResolverIndex {
                    let nextIndex = (installedResolverIndex ?? -1) + 1
                    guard Self.resolvers.indices.contains(nextIndex) else { throw underlying }
                    configure(Self.resolvers[nextIndex])
                    installedResolverIndex = nextIndex
                }
                // Another in-flight request may already have upgraded the app-wide
                // context. Reuse that setting; never race by downgrading to Cloudflare.
                // Keep the fallback for this process lifetime; new launches start with
                // system defaults. URLSession has no public per-task PrivacyContext.
                retries += 1
            }
        }
    }

    static func canRecover(request: URLRequest, baseHost: String?, error: Error,
                           progress: DNSRequestProgress) -> Bool {
        guard let error = error as? URLError,
              [.cannotFindHost, .dnsLookupFailed].contains(error.code),
              let url = request.url, url.scheme?.lowercased() == "https",
              let host = url.host?.lowercased(),
              host == baseHost?.lowercased() || host.hasSuffix(".duckdns.org") else { return false }
        // A redirect target failing DNS does not mean the original request was unsent.
        if let failedURL = error.userInfo[NSURLErrorFailingURLErrorKey] as? URL, failedURL != url { return false }
        if let failedString = error.userInfo[NSURLErrorFailingURLStringErrorKey] as? String,
           URL(string: failedString) != url { return false }
        switch progress {
        case .started: return false
        case .notStarted: return true
        case .unknown:
            // Without transaction metrics, never replay a possible mutation.
            return ["GET", "HEAD"].contains(request.httpMethod?.uppercased() ?? "GET")
        }
    }

    static func load(_ request: URLRequest, session: URLSession) async throws -> (Data, URLResponse) {
        let observer = DNSRequestObserver()
        do { return try await session.data(for: request, delegate: observer) }
        catch { throw DNSTransportFailure(underlying: error, progress: observer.progress) }
    }
}

/// Delegate callbacks run on URLSession's queue, not the UI actor. Missing metrics
/// are deliberately classified as unknown, rather than proof that a POST was unsent.
private final class DNSRequestObserver: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    nonisolated private let lock = NSLock()
    nonisolated(unsafe) private var observedMetrics = false
    nonisolated(unsafe) private var observedTransmission = false

    nonisolated var progress: DNSRequestProgress {
        lock.lock()
        defer { lock.unlock() }
        return observedTransmission ? .started : (observedMetrics ? .notStarted : .unknown)
    }

    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask,
                               didFinishCollecting metrics: URLSessionTaskMetrics) {
        lock.lock()
        defer { lock.unlock() }
        observedMetrics = !metrics.transactionMetrics.isEmpty
        observedTransmission = observedTransmission || task.countOfBytesSent > 0 || metrics.redirectCount > 0
            || metrics.transactionMetrics.contains {
                $0.requestStartDate != nil || $0.responseStartDate != nil
                    || $0.countOfRequestHeaderBytesSent > 0 || $0.countOfRequestBodyBytesSent > 0
            }
    }

    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask, didSendBodyData bytesSent: Int64,
                               totalBytesSent: Int64, totalBytesExpectedToSend: Int64) {
        lock.lock()
        observedTransmission = observedTransmission || bytesSent > 0 || totalBytesSent > 0
        lock.unlock()
    }

    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask,
                               willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
                               completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        lock.lock()
        observedTransmission = true
        lock.unlock()
        completionHandler(request)
    }
}
