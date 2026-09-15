import Foundation
import Security
import UIKit

/// Keeps the identifier used by existing registrations; never replaces it on logout.
final class DeviceIdentity {
    private let defaults: UserDefaults
    private let vendorID: () -> String?
    private let readKeychain: () -> String?
    private let writeKeychain: (String) -> Void
    nonisolated private static let service = "boongtol.UMTP-IOS.device-identity"
    nonisolated private static let account = "registration-device-id"

    init(defaults: UserDefaults = .standard,
         vendorID: @escaping () -> String? = { UIDevice.current.identifierForVendor?.uuidString },
         readKeychain: @escaping () -> String? = DeviceIdentity.read,
         writeKeychain: @escaping (String) -> Void = DeviceIdentity.write) {
        self.defaults = defaults
        self.vendorID = vendorID
        self.readKeychain = readKeychain
        self.writeKeychain = writeKeychain
    }

    func resolve() -> String {
        let pinned = clean(defaults.string(forKey: "umtp_ios_device_id"))
        let keychain = clean(readKeychain())
        // Stage1 preferred IDFV whenever available. Preserve that precedence on
        // the first upgrade; retain its legacy fallback when IDFV is unavailable.
        let resolved = pinned ?? keychain ?? clean(vendorID())
            ?? clean(defaults.string(forKey: "umtp_ios_fallback_device_id")) ?? UUID().uuidString
        defaults.set(resolved, forKey: "umtp_ios_device_id")
        writeKeychain(resolved)
        return resolved
    }

    private func clean(_ value: String?) -> String? {
        guard let value = value?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else { return nil }
        return value
    }

    nonisolated private static func read() -> String? {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service, kSecAttrAccount as String: account,
            kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    nonisolated private static func write(_ value: String) {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service, kSecAttrAccount as String: account]
        let attributes: [String: Any] = [kSecValueData as String: Data(value.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            SecItemAdd(query.merging(attributes) { _, new in new } as CFDictionary, nil)
        }
        // A temporary Keychain failure keeps the pinned UserDefaults identifier.
    }
}
