import Foundation

final class APIClient {
    static let shared = APIClient()
    private let baseURL: URL?
    private let session: URLSession
    private let dnsRecovery: DNSRecovery
    private let transport: DNSRecovery.Transport?

    init(baseURLString: String = AppConfig.apiBaseURL,
         timeout: TimeInterval = AppConfig.requestTimeout, session: URLSession? = nil,
         dnsRecovery: DNSRecovery? = nil, transport: DNSRecovery.Transport? = nil) {
        let url = URL(string: baseURLString)
        self.baseURL = url?.host != nil && ["https", "http"].contains(url?.scheme ?? "") ? url : nil
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = timeout
        configuration.timeoutIntervalForResource = timeout
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        self.session = session ?? URLSession(configuration: configuration)
        self.dnsRecovery = dnsRecovery ?? .shared
        self.transport = transport
    }

    func get<Response: Decodable>(path: String, query: [URLQueryItem] = []) async throws -> Response {
        try await execute(path: path, method: "GET", query: query, body: nil)
    }

    func send<Body: Encodable, Response: Decodable>(path: String, method: String = "POST",
        body: Body, query: [URLQueryItem] = []) async throws -> Response {
        try await execute(path: path, method: method, query: query, body: JSONEncoder().encode(body))
    }

    func send<Response: Decodable>(path: String, method: String,
        query: [URLQueryItem] = []) async throws -> Response {
        try await execute(path: path, method: method, query: query, body: nil)
    }

    func postJSON<RequestBody: Encodable, ResponseBody: Decodable>(path: String,
        body: RequestBody, responseType: ResponseBody.Type) async throws -> ResponseBody {
        try await send(path: path, body: body)
    }

    // Encode one identifier before interpolating it into a route.
    static func pathComponent(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: .alphanumerics.union(CharacterSet(charactersIn: "-._~"))) ?? ""
    }

    private func execute<Response: Decodable>(path: String, method: String,
        query: [URLQueryItem], body: Data?) async throws -> Response {
        guard let baseURL,
              var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw APIClientError.invalidBaseURL
        }
        let prefix = components.percentEncodedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.percentEncodedPath = (prefix.isEmpty ? "" : "/" + prefix)
            + "/" + path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.queryItems = query.isEmpty ? nil : query
        guard let url = components.url else { throw APIClientError.invalidBaseURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        do {
            try Task.checkCancellation()
            let (data, response) = try await dnsRecovery.data(for: request, baseHost: baseURL.host,
                transport: transport ?? { [session] request in try await DNSRecovery.load(request, session: session) })
            try Task.checkCancellation()
            guard let response = response as? HTTPURLResponse else { throw APIClientError.invalidResponse }
            guard (200..<300).contains(response.statusCode) else {
                throw APIClientError.httpStatus(response.statusCode)
            }
            // HTTP 200 can still carry a domain failure.
            if let envelope = try? JSONDecoder().decode(ResultEnvelope.self, from: data), envelope.ok == false {
                throw APIClientError.serverRejected(envelope.reason ?? "")
            }
            do { return try JSONDecoder().decode(Response.self, from: data) }
            catch { throw APIClientError.decodingFailed }
        } catch is CancellationError { throw CancellationError() }
        catch let error as APIClientError { throw error }
        catch let error as URLError {
            if error.code == .cancelled { throw CancellationError() }
            throw APIClientError.network(error)
        } catch { throw APIClientError.unknown }
    }

    private struct ResultEnvelope: Decodable { let ok: Bool?; let reason: String? }
}

enum APIClientError: Error, LocalizedError {
    case invalidBaseURL, invalidResponse, httpStatus(Int), decodingFailed, network(URLError), serverRejected(String), unknown

    var errorDescription: String? {
        switch self {
        case .network(let error) where error.code == .timedOut:
            return "요청 시간이 초과됐어요. 잠시 후 다시 시도해 주세요."
        case .network: return "네트워크 연결을 확인해 주세요."
        case .httpStatus(401), .httpStatus(403): return "사용자 정보를 확인하지 못했어요. 다시 시도해 주세요."
        case .httpStatus(404): return "요청한 항목을 찾을 수 없어요. 새로고침 후 다시 시도해 주세요."
        case .serverRejected(let reason):
            switch reason {
            case "user_id_already_registered", "user_id_already_exists", "user_device_mismatch", "user_id_device_mismatch":
                return "이미 다른 기기에 등록된 사용자 ID예요."
            case "device_already_registered", "device_id_already_registered":
                return "이 기기에 등록된 사용자 ID가 있어요. 앱을 다시 실행해 주세요."
            case "invalid_user_id": return "사용자 ID를 확인해 주세요."
            case "user_not_found": return "등록된 사용자 정보를 찾을 수 없어요."
            default: return "요청을 처리하지 못했어요. 입력을 확인한 뒤 다시 시도해 주세요."
            }
        case .invalidResponse, .decodingFailed: return "서버 응답을 확인하지 못했어요. 잠시 후 다시 시도해 주세요."
        default: return "일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요."
        }
    }
}
