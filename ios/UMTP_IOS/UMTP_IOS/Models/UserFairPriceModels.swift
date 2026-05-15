import Foundation

struct UserFairPriceItem: Codable, Equatable, Identifiable {
    let id: String
    let symbol: String
    let fairPrice: Double
}
