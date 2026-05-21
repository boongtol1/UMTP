import Foundation
import UIKit

protocol UserAPIProtocol {
    func register(userId: String) async throws -> RegisterUserResult
}

struct RegisterUserResult {
    let userId: String
}

final class UserAPI: UserAPIProtocol {
    static let shared = UserAPI()

    private let apiClient: APIClient
    private let defaults: UserDefaults
    private let fallbackDeviceIdKey = "umtp_ios_fallback_device_id"

    init(apiClient: APIClient = .shared, defaults: UserDefaults = .standard) {
        self.apiClient = apiClient
        self.defaults = defaults
    }

    func register(userId: String) async throws -> RegisterUserResult {
        let trimmedUserId = userId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmedUserId.count >= 2 else {
            throw UserAPIError.invalidInput
        }

        let request = RegisterUserRequest(
            user_id: trimmedUserId,
            device_id: resolveDeviceId(),
            platform: "ios"
        )

        do {
            let response = try await apiClient.postJSON(
                path: "users/register",
                body: request,
                responseType: RegisterUserResponseDTO.self
            )

            guard response.ok else {
                throw UserAPIError.registrationFailed
            }

            let resolvedUserId = (response.user_id ?? trimmedUserId)
                .trimmingCharacters(in: .whitespacesAndNewlines)
            guard !resolvedUserId.isEmpty else {
                throw UserAPIError.invalidServerResponse
            }

            return RegisterUserResult(userId: resolvedUserId)
        } catch let error as APIClientError {
            throw UserAPIError.fromAPIClientError(error)
        } catch let error as UserAPIError {
            throw error
        } catch {
            throw UserAPIError.unknown
        }
    }

    private func resolveDeviceId() -> String {
        if let identifierForVendor = UIDevice.current.identifierForVendor?.uuidString,
           !identifierForVendor.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return identifierForVendor
        }

        if let storedFallback = defaults.string(forKey: fallbackDeviceIdKey)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
           !storedFallback.isEmpty {
            return storedFallback
        }

        let generatedFallback = UUID().uuidString
        defaults.set(generatedFallback, forKey: fallbackDeviceIdKey)
        // TODO(Stage2): Keychain 기반 영구 UUID 저장으로 대체
        return generatedFallback
    }
}

enum UserAPIError: Error {
    case invalidInput
    case registrationFailed
    case invalidServerResponse
    case network
    case timeout
    case unknown

    var userMessage: String {
        switch self {
        case .invalidInput:
            return "사용자 ID는 2자 이상 입력해 주세요."
        case .registrationFailed:
            return "사용자 등록에 실패했어요."
        case .invalidServerResponse:
            return "서버 응답을 확인하지 못했어요. 잠시 후 다시 시도해 주세요."
        case .network:
            return "네트워크 연결을 확인해 주세요."
        case .timeout:
            return "요청 시간이 초과됐어요. 잠시 후 다시 시도해 주세요."
        case .unknown:
            return "일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요."
        }
    }

    static func fromAPIClientError(_ error: APIClientError) -> UserAPIError {
        switch error {
        case .network(let urlError):
            return urlError.code == .timedOut ? .timeout : .network
        case .httpStatus:
            return .registrationFailed
        case .invalidResponse, .decodingFailed:
            return .invalidServerResponse
        case .unknown:
            return .unknown
        }
    }
}

private struct RegisterUserRequest: Encodable {
    let user_id: String
    let device_id: String
    let platform: String
}

private struct RegisterUserResponseDTO: Decodable {
    let ok: Bool
    let user_id: String?
    let message: String?
    let reason: String?
}

