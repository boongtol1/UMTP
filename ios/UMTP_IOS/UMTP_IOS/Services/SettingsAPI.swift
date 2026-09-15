import Foundation

@MainActor
protocol SettingsAPIProtocol {
    func units() async throws -> [MacUnit]
    func settings(userID: String) async throws -> [UserFairPriceItem]
    func save(_ request: FairPriceUpsertRequest) async throws -> SettingsOperationResponse
    func refreshRules(userID: String, ruleID: Int64?) async throws
}

@MainActor
struct SettingsAPI: SettingsAPIProtocol {
    private let client: APIClient
    init(client: APIClient? = nil) { self.client = client ?? .shared }
    func units() async throws -> [MacUnit] {
        let response: MacUnitsResponse = try await client.get(path: "macbook-air-units")
        guard response.ok else { throw SettingsInputError.incomplete }
        return response.units
    }
    func settings(userID: String) async throws -> [UserFairPriceItem] {
        let response: FairPricesResponse = try await client.get(path: "user-fair-prices", query: [URLQueryItem(name: "user_id", value: userID)])
        guard response.ok else { throw SettingsInputError.incomplete }
        return response.items
    }
    func save(_ request: FairPriceUpsertRequest) async throws -> SettingsOperationResponse {
        let response: SettingsOperationResponse = try await client.send(path: "user-fair-prices/upsert", body: request)
        guard response.ok else { throw SettingsInputError.server }
        return response
    }
    func refreshRules(userID: String, ruleID: Int64?) async throws {
        let id = APIClient.pathComponent(userID)
        let path = ruleID.map { "users/\(id)/rules/\($0)/refresh" } ?? "users/\(id)/rules/refresh"
        let response: SettingsOperationResponse = try await client.send(path: path, method: "POST")
        guard response.ok else { throw SettingsInputError.incomplete }
    }
}
