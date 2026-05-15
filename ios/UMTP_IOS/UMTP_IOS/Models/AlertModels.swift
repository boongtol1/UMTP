import Foundation

struct AlertItem: Codable, Equatable, Identifiable {
    let id: String
    let title: String
    let message: String
    let createdAt: String
}
