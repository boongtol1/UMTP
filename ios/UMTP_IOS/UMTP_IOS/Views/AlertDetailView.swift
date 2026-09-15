import SwiftUI
import UIKit

struct AlertCardView: View {
    let alert: AlertItem
    var archive = false
    var isSelecting = false
    var isSelected = false
    var isBusy = false
    let onOpen: () -> Void
    let onStartTrade: () -> Void
    @State private var copyMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 10) {
                if !archive {
                    HStack {
                        Text("사기 가능성").font(.subheadline.weight(.semibold))
                        Spacer()
                        Text(alert.displayFraud).fontWeight(.bold)
                    }
                    .foregroundStyle(riskColor)
                    .padding(10)
                    .background(riskColor.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
                    if let url = alert.imageURL { AlertImageView(url: url) }
                }
                HStack(alignment: .top) {
                    if isSelecting {
                        Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(isSelected ? Color.accentColor : .secondary)
                            .accessibilityLabel(isSelected ? "선택됨" : "선택 안 됨")
                    }
                    Text(alert.displayTitle).font(.headline).lineLimit(2)
                    if !archive {
                        Spacer(minLength: 0)
                        Circle().fill(.red).frame(width: 7, height: 7).accessibilityLabel("읽지 않음")
                    }
                }
                if archive {
                    Text("가격: \(AlertDisplay.krw(alert.listing_price_krw ?? alert.alert_target_price_krw))")
                    Text("사기 가능성: \(alert.displayFraud)").foregroundStyle(riskColor)
                    if alert.isCandidateNotice { Text("참고용 후보").font(.caption).foregroundStyle(.secondary) }
                    Text("스펙: \(alert.displaySpec)").font(.caption).foregroundStyle(.secondary)
                    Text("읽음 시각: \(alert.read_at ?? "정보 없음")").font(.caption).foregroundStyle(.secondary)
                } else {
                    Text(alert.isCandidateNotice ? "참고 알림 · 조건 변경 사이 후보" :
                            (alert.isContentChange ? "\(alert.displayType) · " : "") + alert.displayCondition)
                        .font(.caption.weight(.semibold)).foregroundStyle(.blue)
                    if alert.isCandidateNotice {
                        Text(AlertDisplay.candidateNotice).font(.caption).foregroundStyle(.secondary)
                    }
                    Text("가격: \(AlertDisplay.krw(alert.listing_price_krw ?? alert.alert_target_price_krw))").fontWeight(.semibold)
                    Text("제품 분류: \(alert.displaySpec)").font(.subheadline)
                    Text("알림 기준 가격: \(AlertDisplay.krw(alert.alert_target_price_krw))").font(.subheadline)
                    Text("시장가와의 차이: \(AlertDisplay.percent(alert.price_gap_percent ?? alert.diff_ratio ?? alert.alert_drop_rate_percent))")
                        .font(.subheadline)
                    Text("출처: \(alert.source == "umtp_notice" ? "UMTP 참고 알림" : AlertDisplay.text(alert.source) ?? "정보 없음")")
                        .font(.caption).foregroundStyle(.secondary)
                    Text("링크: \(alert.resolvedURL != nil ? "열기 가능" : "정보 없음")")
                        .font(.caption).foregroundStyle(.secondary)
                    if let preview = alert.displayPreview {
                        Text(preview).font(.subheadline).foregroundStyle(.secondary).lineLimit(3)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .contentShape(Rectangle())
            .onTapGesture(perform: onOpen)
            .accessibilityElement(children: .combine)
            .accessibilityAddTraits(.isButton)
            .accessibilityIdentifier("alert.card.\(alert.eventID)")

            if !isSelecting {
                Button("거래 기록 시작", action: onStartTrade)
                    .buttonStyle(.borderedProminent)
                    .disabled(isBusy || (archive ? alert.archiveIdentity <= 0 && alert.eventID <= 0 : alert.eventID <= 0))
                    .frame(maxWidth: .infinity)
                HStack {
                    Button("URL 복사") { copy(alert.resolvedURLText, message: "URL을 복사했어요.") }
                        .disabled(alert.resolvedURLText == nil)
                    Spacer()
                    Button("이미지 URL 복사") { copy(AlertDisplay.text(alert.listing_image_url), message: "이미지 URL을 복사했어요.") }
                        .disabled(AlertDisplay.text(alert.listing_image_url) == nil)
                }
                .font(.caption).buttonStyle(.borderless)
                if let copyMessage { Text(copyMessage).font(.caption).foregroundStyle(.secondary) }
            }
            if !archive {
                HStack {
                    Text(AlertDisplay.text(alert.sort_date) ?? AlertDisplay.text(alert.created_at) ?? "시각 정보 없음")
                        .font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    Button("상세 보기", action: onOpen).font(.caption).buttonStyle(.borderless)
                }
            }
        }
        .padding(.vertical, 8)
    }

    private var riskColor: Color {
        switch alert.displayFraudLabel {
        case "높음", "위험": return .red
        case "주의": return .orange
        case "낮음": return .green
        default: return .secondary
        }
    }

    private func copy(_ value: String?, message: String) {
        guard let value else { return }
        UIPasteboard.general.string = value
        copyMessage = message
    }
}

struct AlertImageView: View {
    let url: URL
    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .empty: ProgressView().frame(maxWidth: .infinity, minHeight: 172)
            case .success(let image):
                image.resizable().scaledToFill().frame(maxWidth: .infinity).frame(height: 172).clipped()
            case .failure:
                Label("이미지를 불러오지 못했어요.", systemImage: "photo")
                    .font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, minHeight: 60)
            @unknown default: EmptyView()
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .accessibilityLabel("대표 이미지")
    }
}

struct AlertDetailView: View {
    let alert: AlertItem
    let archive: Bool
    @ObservedObject var viewModel: AlertFeedViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    @State private var linkError: String?

    var body: some View {
        List {
            Section {
                Text(alert.displayTitle).font(.title3.bold())
                if let url = alert.imageURL {
                    Button { open(url) } label: { AlertImageView(url: url) }.buttonStyle(.plain)
                }
            }
            ForEach(Array(alert.detailRows(archive: archive).enumerated()), id: \.offset) { _, row in
                VStack(alignment: .leading, spacing: 5) {
                    Text(row.0).font(.caption).foregroundStyle(.secondary)
                    if row.0 == "URL", let url = alert.resolvedURL {
                        Button(row.1) { open(url) }.multilineTextAlignment(.leading)
                    } else if row.0 == "대표 이미지", let url = alert.imageURL {
                        Button(row.1) { open(url) }.multilineTextAlignment(.leading)
                    } else {
                        Text(row.1).textSelection(.enabled)
                    }
                }
            }
            Section {
                if !archive {
                    if let error = viewModel.errorMessage { Text(error).foregroundStyle(.red) }
                    Button {
                        Task { if await viewModel.markRead(alert.eventID) { dismiss() } }
                    } label: {
                        HStack {
                            if viewModel.isMutating { ProgressView() }
                            Text("검토 완료")
                        }
                    }
                    .disabled(viewModel.isMutating || alert.eventID <= 0)
                    .accessibilityIdentifier("alert.review")
                }
                Button("매물 보러가기") { if let url = alert.resolvedURL { open(url) } }
                    .disabled(alert.resolvedURL == nil)
                if let linkError { Text(linkError).foregroundStyle(.red) }
            }
        }
        .navigationTitle(archive ? "읽음 알림 상세" : "거래 알림 상세")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("목록으로") { dismiss() } } }
    }

    private func open(_ url: URL) {
        openURL(url) { success in
            if !success { linkError = "링크를 열지 못했어요. URL을 복사해 브라우저에서 확인해 주세요." }
        }
    }
}

struct AlertStatusView: View {
    var isRefreshing: Bool
    var error: String?
    var message: String?
    var lastRefresh: Date?
    let retry: () -> Void

    var body: some View {
        if isRefreshing || error != nil || message != nil || lastRefresh != nil {
            Section {
                if isRefreshing { ProgressView("새로고침 중...") }
                if let error {
                    Text(error).font(.footnote).foregroundStyle(.red)
                    Button("다시 시도", action: retry)
                }
                if let message { Text(message).font(.footnote).foregroundStyle(.secondary) }
                if let lastRefresh {
                    Text("마지막 새로고침: \(lastRefresh.formatted(date: .omitted, time: .standard))")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
        }
    }
}
