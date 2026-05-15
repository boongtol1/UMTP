import Foundation

final class APIClient {
    static let shared = APIClient()

    private init() {}

    // TODO(Stage2): API 구현
    // TODO(Stage2): 서버 연동
    func requestPlaceholder(endpoint: String) async throws -> Data {
        throw URLError(.badURL)
    }
}
