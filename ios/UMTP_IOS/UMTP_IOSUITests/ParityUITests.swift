import XCTest

@MainActor
final class ParityUITests: XCTestCase {
    func testRegistrationValidation() {
        let app = XCUIApplication()
        app.launchArguments = ["-umtp_user_id", " "]
        app.launch()
        let input = app.textFields["registration.userId"]
        XCTAssertTrue(input.waitForExistence(timeout: 10))
        let submit = app.buttons["registration.submit"]
        XCTAssertFalse(submit.isEnabled)
        input.tap()
        input.typeText("a")
        XCTAssertFalse(submit.isEnabled)
        input.typeText("b")
        XCTAssertTrue(submit.isEnabled)
    }
}
