import SwiftUI

struct MainPlaceholderView: View {
    let userId: String

    var body: some View {
        VStack(spacing: 12) {
            Text("UMTP 메인 화면")
                .font(.title2)
                .bold()

            Text("\(userId)님으로 로그인됨")
                .foregroundStyle(.secondary)

            Text("Stage2에서 알림 피드/설정 기능이 추가될 예정입니다.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            // TODO(Stage2): Alert feed API 연결
            // TODO(Stage2): Settings 화면 구현
            // TODO(Stage2): Push notification/APNs 연동
        }
        .padding()
    }
}

