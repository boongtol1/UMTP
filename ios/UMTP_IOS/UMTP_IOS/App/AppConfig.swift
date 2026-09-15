import Foundation

enum AppConfig {
    static var apiBaseURL: String {
        #if DEBUG
        // UI integration tests use a real loopback HTTP server. Release builds
        // always use the service URL and cannot be redirected by launch arguments.
        if let value = ProcessInfo.processInfo.environment["UMTP_TEST_BASE_URL"],
           let url = URL(string: value), ["127.0.0.1", "localhost", "::1"].contains(url.host ?? "") {
            return value
        }
        #endif
        return "https://umtp.duckdns.org"
    }
    static let requestTimeout: TimeInterval = 30
}
