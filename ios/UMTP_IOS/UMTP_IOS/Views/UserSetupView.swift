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
                    Text(viewModel.isSubmitting ? "등록 중..." : "등록")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!viewModel.canSubmit)
        }
        .padding()
    }
}
