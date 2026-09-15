import Foundation

@MainActor
protocol AlertsAPIProtocol {
    func alerts(userID: String) async throws -> [AlertItem]
    func archive(userID: String) async throws -> [String: [String: [AlertItem]]]
    func markRead(id: Int, userID: String) async throws
    func markAllRead(userID: String) async throws -> AlertMutationResponse
    func clearArchive(userID: String, ids: Set<Int>?) async throws -> AlertMutationResponse
}

@MainActor
final class AlertsAPI: AlertsAPIProtocol {
    private let client: APIClient

    init(client: APIClient? = nil) { self.client = client ?? .shared }

    func alerts(userID: String) async throws -> [AlertItem] {
        let response: AlertsResponse = try await client.get(
            path: "alerts", query: userQuery(userID) + [URLQueryItem(name: "is_read", value: "0")]
        )
        // Stable tie order preserves the server order and the visible list position.
        return response.items.enumerated().sorted {
            let left = $0.element.created_at ?? ""
            let right = $1.element.created_at ?? ""
            return left == right ? $0.offset < $1.offset : left > right
        }.map(\.element)
    }

    func archive(userID: String) async throws -> [String: [String: [AlertItem]]] {
        let response: GroupedReadAlertsResponse = try await client.get(
            path: "alert-events/read/grouped", query: userQuery(userID)
        )
        return response.groups
    }

    func markRead(id: Int, userID: String) async throws {
        guard id > 0 else { throw APIClientError.serverRejected("알림 정보를 확인할 수 없습니다.") }
        let _: AlertMutationResponse = try await readRequest(path: "alert-events/\(id)/read", userID: userID)
    }

    func markAllRead(userID: String) async throws -> AlertMutationResponse {
        try await readRequest(path: "alert-events/read-all", userID: userID)
    }

    func clearArchive(userID: String, ids: Set<Int>?) async throws -> AlertMutationResponse {
        if let ids {
            let normalized = ids.filter { $0 > 0 }.sorted()
            guard !normalized.isEmpty else { throw APIClientError.serverRejected("선택된 읽음 알림이 없습니다.") }
            return try await client.send(
                path: "alert-events/read/archive/clear-selected", method: "PATCH",
                body: ClearArchiveRequest(alert_event_ids: normalized), query: userQuery(userID)
            )
        }
        return try await client.send(
            path: "alert-events/read/archive/clear-all", method: "PATCH", query: userQuery(userID)
        )
    }

    private func readRequest(path: String, userID: String) async throws -> AlertMutationResponse {
        do {
            return try await client.send(path: path, method: "PATCH", query: userQuery(userID))
        } catch APIClientError.httpStatus(let code) where [404, 405, 501].contains(code) {
            // Android supports older servers with POST read routes. Never retry ambiguous failures.
            return try await client.send(path: path, method: "POST", query: userQuery(userID))
        }
    }

    private func userQuery(_ id: String) -> [URLQueryItem] {
        [URLQueryItem(name: "user_id", value: id)]
    }

    private struct ClearArchiveRequest: Encodable { let alert_event_ids: [Int] }
}
