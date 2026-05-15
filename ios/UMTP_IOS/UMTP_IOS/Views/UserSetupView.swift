import SwiftUI

struct UserSetupView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = UserSetupViewModel(sessionService: .shared)

    var body: some View {
        VStack(spacing: 16) {
            Text("사용자 설정")
                .font(.title2)
                .bold()

            TextField("user_id 입력", text: $viewModel.userIdInput)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .disableAutocorrection(true)

            Button("저장") {
                viewModel.save(appState: appState)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!viewModel.canSave)
        }
        .padding()
        .onAppear {
            if viewModel.userIdInput.isEmpty {
                viewModel.userIdInput = appState.userId ?? ""
            }
        }
    }
}
