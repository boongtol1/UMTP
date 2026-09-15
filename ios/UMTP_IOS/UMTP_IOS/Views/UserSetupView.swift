import SwiftUI

struct UserSetupView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = UserSetupViewModel(sessionService: .shared)

    var body: some View {
        VStack(spacing: 20) {
            Text("UMTP 시작하기")
                .font(.title2)
                .bold()

            Text("사용자 ID를 입력해 주세요")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            TextField("예: boongtol", text: $viewModel.userIdInput)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .disableAutocorrection(true)
                .disabled(viewModel.isSubmitting)
                .accessibilityIdentifier("registration.userId")

            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            Button {
                Task {
                    await viewModel.register(appState: appState)
                }
            } label: {
                HStack(spacing: 8) {
                    if viewModel.isSubmitting {
                        ProgressView()
                            .controlSize(.small)
                    }
                    Text(viewModel.isSubmitting ? "등록 중..." : "저장 및 시작")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!viewModel.canSubmit)
            .accessibilityIdentifier("registration.submit")
        }
        .padding()
    }
}
