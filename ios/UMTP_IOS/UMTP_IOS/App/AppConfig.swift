import Foundation

enum AppConfig {
    static var apiBaseURL: String {
        #if DEBUG
        // XCTest launches keep the existing process-local loopback override.
        if let value = loopbackFixtureURL(ProcessInfo.processInfo.environment["UMTP_TEST_BASE_URL"]) {
            return value
        }
        #if targetEnvironment(simulator)
        // An OS notification cold-launch does not inherit XCTest's environment.
        // Only an explicitly configured Debug Simulator build can use this value.
        if let value = loopbackFixtureURL(Bundle.main.object(forInfoDictionaryKey: "UMTPParityFixtureURL") as? String) {
            return value
        }
        #endif
        #endif
        return "https://umtp.duckdns.org"
    }

    static func loopbackFixtureURL(_ value: String?) -> String? {
        guard let value, value == value.trimmingCharacters(in: .whitespacesAndNewlines),
              let components = URLComponents(string: value), components.url != nil,
              ["http", "https"].contains(components.scheme?.lowercased() ?? ""),
              ["127.0.0.1", "localhost", "::1", "[::1]"].contains(components.host?.lowercased() ?? ""),
              components.user == nil, components.password == nil,
              components.query == nil, components.fragment == nil,
              components.port.map({ (1...65535).contains($0) }) ?? true else { return nil }
        return value
    }

    static let requestTimeout: TimeInterval = 30
}
