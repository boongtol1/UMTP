package com.boongtol.umtp_android.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DoneAll
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.boongtol.umtp_android.network.AlertItem
import com.boongtol.umtp_android.network.TradeTypeFlags

@Composable
fun AlertFeedScreen(
    alerts: List<AlertItem>,
    isRefreshing: Boolean = false,
    isMarkingAllRead: Boolean = false,
    refreshStatusMessage: String? = null,
    lastRefreshAtText: String? = null,
    onRefresh: () -> Unit,
    onMarkAlertRead: (Long, (Boolean) -> Unit) -> Unit = { _, callback -> callback(false) },
    onMarkAllAsRead: () -> Unit = {},
    initialTargetAlertId: String? = null,
    onTargetAlertFound: () -> Unit = {},
) {
    var selectedAlert by remember { mutableStateOf<AlertItem?>(null) }
    val context = LocalContext.current

    LaunchedEffect(initialTargetAlertId, alerts) {
        if (initialTargetAlertId != null && alerts.isNotEmpty()) {
            val targetId = initialTargetAlertId.toLongOrNull()
            if (targetId != null) {
                val targetAlert = alerts.firstOrNull { it.id == targetId }
                if (targetAlert != null) {
                    selectedAlert = targetAlert
                    onTargetAlertFound()
                }
            }
        }
    }

    if (selectedAlert != null) {
        AlertDetailScreen(
            alert = selectedAlert!!,
            onBack = {
                selectedAlert = null
            },
            onMarkReviewed = { alertId, completion ->
                onMarkAlertRead(alertId) { success ->
                    if (success) {
                        onRefresh()
                        selectedAlert = null
                    }
                    completion(success)
                }
            },
            onOpenUrl = { alert ->
                val resolvedUrl = resolveAlertUrl(alert)
                if (!resolvedUrl.isNullOrBlank()) {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(resolvedUrl))
                    context.startActivity(intent)
                }
            },
            onOpenImageUrl = { alert ->
                val imageUrl = resolveAlertImageUrl(alert)
                if (!imageUrl.isNullOrBlank()) {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(imageUrl))
                    context.startActivity(intent)
                }
            },
        )
        return
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "거래 알림 피드",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(
                    onClick = onMarkAllAsRead,
                    enabled = !isMarkingAllRead && alerts.isNotEmpty(),
                ) {
                    if (isMarkingAllRead) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Default.DoneAll, contentDescription = "모두 읽음")
                    }
                }
                IconButton(
                    onClick = onRefresh,
                    enabled = !isRefreshing,
                ) {
                    if (isRefreshing) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Default.Refresh, contentDescription = "새로고침")
                    }
                }
            }
        }
        if (isRefreshing) {
            Text(
                text = "새로고침 중...",
                modifier = Modifier.padding(horizontal = 16.dp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(modifier = Modifier.height(4.dp))
        } else if (!refreshStatusMessage.isNullOrBlank()) {
            Text(
                text = refreshStatusMessage,
                modifier = Modifier.padding(horizontal = 16.dp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )
            if (!lastRefreshAtText.isNullOrBlank()) {
                Text(
                    text = lastRefreshAtText,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 2.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray,
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
        }

        if (alerts.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(text = "알림이 없습니다.", color = Color.Gray)
            }
            return@Column
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(alerts) { alert ->
                AlertCard(
                    alert = alert,
                    onOpenDetails = {
                        selectedAlert = alert
                    },
                )
            }
        }
    }
}

@Composable
fun AlertCard(
    alert: AlertItem,
    onOpenDetails: () -> Unit,
) {
    val listingImageUrl = alert.listing_image_url?.takeIf { it.isNotBlank() }
    val isReferenceNotice = isConditionChangeCandidateNotice(alert)
    val resolvedUrl = resolveAlertUrl(alert)
    val titleText = resolveAlertTitle(alert)
    val bodyPreview = resolveAlertBodyPreview(alert)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenDetails() },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            if (listingImageUrl != null) {
                AsyncImage(
                    model = listingImageUrl,
                    contentDescription = "대표 이미지",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(172.dp)
                        .clip(MaterialTheme.shapes.medium),
                    contentScale = ContentScale.Crop,
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = titleText,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Surface(
                    modifier = Modifier
                        .padding(start = 8.dp)
                        .size(8.dp),
                    shape = MaterialTheme.shapes.small,
                    color = Color.Red,
                ) {}
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (isReferenceNotice) {
                    BadgeChip(label = "참고 알림", color = Color(0xFF8D6E63))
                    BadgeChip(label = "조건 변경 사이 후보", color = Color(0xFF6D4C41))
                } else {
                    BadgeChip(label = resolveRiskLabel(alert), color = resolveRiskColor(alert))
                    BadgeChip(label = resolveAlertConditionLabel(alert), color = Color(0xFF1565C0))
                }
            }
            if (isReferenceNotice) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "정식 알림 기준은 저장 이후 매물이며, 이 항목은 참고용 후보입니다.",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray,
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "가격: ${formatKrwDisplay(resolveListingPriceForDisplay(alert))}",
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = "제품 분류: ${buildSpecSummary(alert)}",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )
            Text(
                text = "알림 기준 가격: ${formatKrwDisplay(alert.alert_target_price_krw)}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                text = "시장가와의 차이: ${formatPercentDisplay(resolveAlertGapPercent(alert))}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                text = "출처: ${resolveAlertSourceText(alert)}",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )
            Text(
                text = "링크: ${if (!resolvedUrl.isNullOrBlank()) "열기 가능" else "정보 없음"}",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )
            if (!bodyPreview.isNullOrBlank()) {
                Text(
                    text = "본문 요약: $bodyPreview",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.Gray,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(
                text = "계산식: (내가 생각한 시장가 - 등록 가격) / 내가 생각한 시장가 × 100",
                style = MaterialTheme.typography.labelSmall,
                color = Color.Gray,
            )

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = resolveSortDateText(alert) ?: resolveCreatedAtText(alert) ?: "시각 정보 없음",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray,
                )
                Text(
                    text = "상세 보기",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

@Composable
private fun AlertDetailScreen(
    alert: AlertItem,
    onBack: () -> Unit,
    onMarkReviewed: (Long, (Boolean) -> Unit) -> Unit,
    onOpenUrl: (AlertItem) -> Unit,
    onOpenImageUrl: (AlertItem) -> Unit,
) {
    val resolvedUrl = resolveAlertUrl(alert)
    val listingImageUrl = alert.listing_image_url?.takeIf { it.isNotBlank() }
    var isMarkingReviewed by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "거래 알림 상세",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "목록으로",
                modifier = Modifier.clickable { onBack() },
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
            )
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                Text(
                    text = resolveAlertTitle(alert),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.height(8.dp))
                HorizontalDivider()
                Spacer(modifier = Modifier.height(8.dp))
                if (listingImageUrl != null) {
                    AsyncImage(
                        model = listingImageUrl,
                        contentDescription = "대표 이미지",
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                            .clip(MaterialTheme.shapes.medium)
                            .clickable { onOpenImageUrl(alert) },
                        contentScale = ContentScale.Crop,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }

            items(buildAlertDetailRows(alert, resolvedUrl, listingImageUrl)) { row ->
                val isUrlRow = row.first == "URL" && !resolvedUrl.isNullOrBlank()
                val isImageRow = row.first == "대표 이미지" && !listingImageUrl.isNullOrBlank()
                val isLinkRow = isUrlRow || isImageRow
                val rowClickHandler = when {
                    isUrlRow -> ({ onOpenUrl(alert) })
                    isImageRow -> ({ onOpenImageUrl(alert) })
                    else -> null
                }
                DetailRow(
                    label = row.first,
                    value = row.second,
                    isLink = isLinkRow,
                    onClick = rowClickHandler,
                )
            }

            item {
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        if (isMarkingReviewed) {
                            return@Button
                        }
                        isMarkingReviewed = true
                        onMarkReviewed(alert.id) {
                            isMarkingReviewed = false
                        }
                    },
                    enabled = !isMarkingReviewed,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (isMarkingReviewed) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Text("검토 완료")
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = { onOpenUrl(alert) },
                    enabled = !resolvedUrl.isNullOrBlank(),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("매물 보러가기")
                }
            }
        }
    }
}

@Composable
private fun DetailRow(
    label: String,
    value: String,
    isLink: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    val valueModifier = if (isLink && onClick != null) {
        Modifier.clickable { onClick() }
    } else {
        Modifier
    }
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = Color.Gray,
        )
        Text(
            text = value,
            modifier = valueModifier,
            style = MaterialTheme.typography.bodyMedium,
            color = if (isLink) MaterialTheme.colorScheme.primary else Color.Unspecified,
        )
        Spacer(modifier = Modifier.height(8.dp))
    }
}

@Composable
private fun BadgeChip(label: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.12f),
        shape = MaterialTheme.shapes.small,
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelSmall,
            color = color,
            fontWeight = FontWeight.Bold,
        )
    }
}

private fun resolveAlertUrl(alert: AlertItem): String? {
    return alert.product_url?.takeIf { it.isNotBlank() } ?: alert.url?.takeIf { it.isNotBlank() }
}

private fun resolveAlertImageUrl(alert: AlertItem): String? {
    return alert.listing_image_url?.takeIf { it.isNotBlank() }
}

private fun resolveAlertTitle(alert: AlertItem): String {
    val title = alert.title?.trim()
    if (!title.isNullOrEmpty()) {
        return title
    }
    val fallbackMessage = alert.message?.trim()
    if (!fallbackMessage.isNullOrEmpty()) {
        return fallbackMessage
    }
    return "제목 없음"
}

private fun resolveListingPriceForDisplay(alert: AlertItem): Int? {
    return alert.listing_price_krw ?: alert.alert_target_price_krw
}

private fun resolveAlertGapPercent(alert: AlertItem): Double? {
    return alert.price_gap_percent ?: alert.diff_ratio ?: alert.alert_drop_rate_percent
}

private fun resolveAlertSourceText(alert: AlertItem): String {
    val source = alert.source?.trim().orEmpty()
    if (source.isEmpty()) {
        return "정보 없음"
    }
    return if (source == "umtp_notice") {
        "UMTP 참고 알림"
    } else {
        source
    }
}

private fun resolveAlertBodyPreview(alert: AlertItem): String? {
    val excerpt = alert.body_excerpt?.trim()
    if (!excerpt.isNullOrEmpty()) {
        return excerpt
    }
    val fullText = alert.body_text?.trim()
    if (!fullText.isNullOrEmpty()) {
        return fullText
    }
    return null
}

private fun resolveSortDateText(alert: AlertItem): String? {
    return alert.sort_date?.takeIf { it.isNotBlank() }
}

private fun resolveCreatedAtText(alert: AlertItem): String? {
    return alert.created_at?.takeIf { it.isNotBlank() }
}

private fun resolveAlertConditionLabel(alert: AlertItem): String {
    if (isConditionChangeCandidateNotice(alert)) {
        return "조건 변경 사이 후보"
    }
    alert.alert_condition_label?.let {
        if (it.isNotBlank()) {
            return it
        }
    }
    return if ((alert.alert_price_direction ?: "").uppercase() == "ABOVE_OR_EQUAL") {
        "이 가격 이상이면 알림"
    } else {
        "이 가격 이하이면 알림"
    }
}

private fun resolveRiskLabel(alert: AlertItem): String {
    alert.formatted_risk_label?.let {
        if (it.isNotBlank()) {
            return it
        }
    }
    return when ((alert.risk_level ?: "").uppercase()) {
        "LOW", "NONE" -> "낮음"
        "MEDIUM" -> "주의"
        "HIGH", "EXCLUDE" -> "위험"
        else -> "정보 없음"
    }
}

private fun resolveRiskColor(alert: AlertItem): Color {
    return when (resolveRiskLabel(alert)) {
        "위험" -> Color(0xFFD32F2F)
        "주의" -> Color(0xFFF57C00)
        "낮음" -> Color(0xFF2E7D32)
        else -> Color(0xFF455A64)
    }
}

private fun resolveRiskKeywordsText(alert: AlertItem): String {
    val keywords = alert.risk_keywords ?: emptyList()
    if (keywords.isEmpty()) {
        return "특이사항 없음"
    }
    return keywords.joinToString(", ")
}

private fun resolveBodyText(alert: AlertItem): String {
    val fullText = alert.body_text?.trim()
    if (!fullText.isNullOrEmpty()) {
        return fullText
    }
    val excerpt = alert.body_excerpt?.trim()
    if (!excerpt.isNullOrEmpty()) {
        return excerpt
    }
    return "본문 내용 없음"
}

private fun resolveTradeFlagsText(flags: TradeTypeFlags?): String {
    if (flags == null) {
        return "정보 없음"
    }

    val labels = mutableListOf<String>()
    if (flags.is_exchange) {
        labels += "교환"
    }
    if (flags.is_free) {
        labels += "나눔"
    }
    if (flags.is_suspicious) {
        labels += "허위/의심"
    }
    if (labels.isEmpty()) {
        return "특이사항 없음"
    }
    return labels.joinToString(", ")
}

private fun resolveProductTypeText(alert: AlertItem): String {
    return alert.product_type?.takeIf { it.isNotBlank() } ?: "분류 정보 없음"
}

private fun resolveChipText(alert: AlertItem): String {
    return alert.chip?.takeIf { it.isNotBlank() } ?: "정보 없음"
}

private fun resolveScreenInchText(alert: AlertItem): String {
    val inch = alert.screen_inch
    if (inch == null || inch <= 0) {
        return "정보 없음"
    }
    return "${inch}인치"
}

private fun resolveRamText(alert: AlertItem): String {
    val ram = alert.ram_gb
    if (ram == null || ram <= 0) {
        return "정보 없음"
    }
    return "${ram}GB"
}

private fun resolveSsdText(alert: AlertItem): String {
    val ssd = alert.ssd_gb
    if (ssd == null || ssd <= 0) {
        return "정보 없음"
    }
    return "${ssd}GB"
}

private fun resolveSpecialNotesText(alert: AlertItem): String {
    val notes = mutableListOf<String>()
    val riskLabel = resolveRiskLabel(alert)
    if (riskLabel == "주의" || riskLabel == "위험") {
        notes += "위험도 $riskLabel"
    }

    val tradeFlagsText = resolveTradeFlagsText(alert.trade_type_flags)
    if (tradeFlagsText != "특이사항 없음" && tradeFlagsText != "정보 없음") {
        notes += "거래 유형: $tradeFlagsText"
    }

    val riskKeywordsText = resolveRiskKeywordsText(alert)
    if (riskKeywordsText != "특이사항 없음") {
        notes += "위험 키워드: $riskKeywordsText"
    }

    if (notes.isEmpty()) {
        return "특이사항 없음"
    }
    return notes.joinToString(" / ")
}

private fun buildAlertDetailRows(
    alert: AlertItem,
    resolvedUrl: String?,
    listingImageUrl: String?,
): List<Pair<String, String>> {
    return listOf(
        "알림 유형" to if (isConditionChangeCandidateNotice(alert)) "참고 알림 (조건 변경 사이 후보)" else "정식 알림",
        "참고 안내" to if (isConditionChangeCandidateNotice(alert)) {
            "정식 알림 기준은 저장 이후 매물이며, 이 항목은 참고용 후보입니다."
        } else {
            "-"
        },
        "출처" to resolveAlertSourceText(alert),
        "URL" to (resolvedUrl ?: "URL 정보 없음"),
        "대표 이미지" to (listingImageUrl ?: "이미지 없음"),
        "제품 분류" to resolveProductTypeText(alert),
        "칩" to resolveChipText(alert),
        "화면 크기" to resolveScreenInchText(alert),
        "RAM" to resolveRamText(alert),
        "SSD" to resolveSsdText(alert),
        "등록 가격" to formatKrwDisplay(resolveListingPriceForDisplay(alert)),
        "내가 생각한 시장가" to formatKrwDisplay(alert.user_market_price_krw ?: alert.fair_price_krw),
        "알림 기준 가격" to formatKrwDisplay(alert.alert_target_price_krw),
        "시장가와의 차이" to formatPercentDisplay(resolveAlertGapPercent(alert)),
        "설정 차이율" to formatPercentDisplay(alert.alert_drop_rate_percent),
        "차이율 계산식" to "(내가 생각한 시장가 - 등록 가격) / 내가 생각한 시장가 × 100",
        "알림 조건" to resolveAlertConditionLabel(alert),
        "위험도" to resolveRiskLabel(alert),
        "위험 점수" to (alert.risk_score?.toString() ?: "정보 없음"),
        "위험 키워드" to resolveRiskKeywordsText(alert),
        "본문 내용" to resolveBodyText(alert),
        "매물 등록 시각" to (resolveSortDateText(alert) ?: "정보 없음"),
        "알림 생성 시각" to (resolveCreatedAtText(alert) ?: "정보 없음"),
        "분석 시각" to (alert.analyzed_at ?: alert.created_at ?: "분석 시각 정보 없음"),
        "교환/나눔/의심" to resolveTradeFlagsText(alert.trade_type_flags),
        "특이사항" to resolveSpecialNotesText(alert),
    )
}

private fun buildSpecSummary(alert: AlertItem): String {
    val tokens = mutableListOf<String>()
    alert.product_type?.takeIf { it.isNotBlank() }?.let { tokens += it }
    alert.chip?.takeIf { it.isNotBlank() }?.let { tokens += it }
    alert.screen_inch?.let { tokens += "${it}인치" }
    alert.ram_gb?.let { tokens += "${it}GB" }
    alert.ssd_gb?.let { tokens += "${it}GB SSD" }

    if (tokens.isEmpty()) {
        return "분류 정보 없음"
    }
    return tokens.joinToString(" · ")
}

private fun isConditionChangeCandidateNotice(alert: AlertItem): Boolean {
    if (alert.is_condition_change_candidate_notice) {
        return true
    }
    if (!alert.is_alert_target) {
        return true
    }
    return (alert.trigger_reason ?: "").trim().lowercase() == "condition_change_candidate_notice"
}
