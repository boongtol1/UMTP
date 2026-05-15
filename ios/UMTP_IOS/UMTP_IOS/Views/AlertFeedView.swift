import SwiftUI

struct AlertFeedView: View {
    @StateObject private var viewModel = AlertFeedViewModel()

    var body: some View {
        NavigationStack {
            List {
                if viewModel.alerts.isEmpty {
                    Text("아직 알림이 없습니다")
                        .foregroundStyle(.secondary)
                    Text("샘플 알림 리스트가 여기에 표시됩니다")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(viewModel.alerts) { alert in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(alert.title).bold()
                            Text(alert.message)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle("알림")
        }
        .onAppear { viewModel.onAppear() }
        .onDisappear { viewModel.onDisappear() }
    }
}
