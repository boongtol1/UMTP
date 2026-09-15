import Foundation

protocol ResaleTradeAPIProtocol {
    func start(userId: String, reference: String?, alertId: Int?, fromArchive: Bool) async throws -> TradeResponse
    func save(userId: String, row: ResaleTradeRow, mode: TradeMode, updates: [String: TradeValue]) async throws -> TradeResponse
    func history(userId: String, completed: Bool) async throws -> TradeResponse
    func delete(userId: String, ids: Set<Int>?) async throws -> TradeResponse
}

struct ResaleTradeAPI: ResaleTradeAPIProtocol {
    let client: APIClient
    init(client: APIClient = .shared) { self.client = client }

    func start(userId: String, reference: String?, alertId: Int?, fromArchive: Bool) async throws -> TradeResponse {
        var body: [String: TradeValue] = ["user_id": .string(userId)]
        let path: String
        if let alertId, alertId > 0 {
            path = fromArchive ? "trade-journeys/start-from-read-archive" : "trade-journeys/start-from-alert"
            body[fromArchive ? "read_archive_event_id" : "alert_event_id"] = .whole(alertId)
        } else {
            path = "trade-journeys/start-from-url"
            body["url"] = .string(reference ?? "")
        }
        let response: TradeResponse = try await client.send(path: path, body: body)
        return try response.checked()
    }

    func save(userId: String, row: ResaleTradeRow, mode: TradeMode, updates: [String: TradeValue]) async throws -> TradeResponse {
        let response: TradeResponse
        if let id = row.id, id > 0 {
            response = try await client.send(path: "users/\(APIClient.pathComponent(userId))/resale-trade-journeys/\(id)/\(mode.endpoint)", method: "PATCH", body: ["updates": TradeValue.object(updates)])
        } else {
            var body: [String: TradeValue] = ["user_id": .string(userId), "source": .string(row["source"].isEmpty ? "joongna" : row["source"]), "updates": .object(updates)]
            if !row["product_id"].isEmpty { body["product_id"] = .string(row["product_id"]) }
            if !row["url"].isEmpty { body["url"] = .string(row["url"]) }
            if mode == .resale, updates["current_stage"]?.text.isEmpty == false {
                // Legacy resale upsert splits resale/sold fields into separate writes,
                // then derives a stage again without the caller's explicit stage.
                // Obtain the identity first and send all resale changes in one PATCH.
                // Retrying the same user/source/product upsert reuses its existing ID.
                body["updates"] = .object([:])
                let prepared: TradeResponse = try await client.send(path: "resale-trades/after-purchase/upsert", body: body)
                guard let preparedRow = try prepared.checked().row, let id = preparedRow.id, id > 0 else {
                    throw TradeError.missingRow
                }
                do {
                    let saved = try await save(userId: userId, row: preparedRow, mode: .resale, updates: updates)
                    guard saved.row != nil else { throw TradeError.missingRow }
                    return saved
                } catch is CancellationError {
                    throw CancellationError()
                } catch {
                    // A record may now exist, while the PATCH result is unknown.
                    // Keep the caller's draft and report no overall save success.
                    throw TradeError.resaleSaveUnconfirmed
                }
            }
            response = try await client.send(path: "resale-trades/after-\(mode.endpoint)/upsert", body: body)
        }
        return try response.checked()
    }

    func history(userId: String, completed: Bool) async throws -> TradeResponse {
        let response: TradeResponse = try await client.get(path: "users/\(APIClient.pathComponent(userId))/resale-trade-journeys/\(completed ? "completed" : "purchased")", query: [URLQueryItem(name: "limit", value: "200")])
        return try response.checked()
    }

    func delete(userId: String, ids: Set<Int>?) async throws -> TradeResponse {
        let response: TradeResponse
        if let ids {
            response = try await client.send(path: "users/\(APIClient.pathComponent(userId))/resale-trade-journeys/completed/delete-selected", method: "PATCH", body: ["journey_ids": ids.sorted()])
        } else {
            response = try await client.send(path: "users/\(APIClient.pathComponent(userId))/resale-trade-journeys/completed/delete-all", method: "PATCH")
        }
        return try response.checked()
    }
}
