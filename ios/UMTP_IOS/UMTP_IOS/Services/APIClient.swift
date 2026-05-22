import Foundation

final class APIClient {
    static let shared = APIClient()

    private let baseURL: URL?
    private let session: URLSession

    init(
        baseURLString: String = AppConfig.apiBaseURL,
        timeout: TimeInterval = AppConfig.requestTimeout,
        session: URLSession? = nil
    ) {
        self.baseURL = URL(string: baseURLString)
        if let session {
            self.session = session
        } else {
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = timeout
            configuration.timeoutIntervalForResource = timeout
            self.session = URLSession(configuration: configuration)
        }
    }

    func postJSON<RequestBody: Encodable, ResponseBody: Decodable>(
        path: String,
        body: RequestBody,
        responseType: ResponseBody.Type
    ) async throws -> ResponseBody {
        let url = try buildURL(path: path)

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIClientError.invalidResponse
            }
            guard (200..<300).contains(httpResponse.statusCode) else {
                throw APIClientError.httpStatus(httpResponse.statusCode)
            }

            do {
                return try JSONDecoder().decode(ResponseBody.self, from: data)
            } catch {
                throw APIClientError.decodingFailed
            }
        } catch let error as APIClientError {
            throw error
        } catch let error as URLError {
            throw APIClientError.network(error)
        } catch {
            throw APIClientError.unknown
        }
    }

    private func buildURL(path: String) throws -> URL {
        guard let baseURL else {
            throw APIClientError.invalidBaseURL
        }
        let trimmedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if trimmedPath.isEmpty {
            return baseURL
        }
        return baseURL.appendingPathComponent(trimmedPath)
    }
}

enum APIClientError: Error {
    case invalidBaseURL
    case invalidResponse
    case httpStatus(Int)
    case decodingFailed
    case network(URLError)
    case unknown
}
