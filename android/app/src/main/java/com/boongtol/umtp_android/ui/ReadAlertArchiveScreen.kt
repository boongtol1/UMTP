package com.boongtol.umtp_android.ui

import android.content.Intent
import android.net.Uri
import android.widget.Toast
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.boongtol.umtp_android.network.AlertItem
import com.boongtol.umtp_android.network.TradeTypeFlags
import kotlin.math.roundToInt

@Composable
fun ReadAlertArchiveScreen(
    groupedAlerts: Map<String, Map<String, List<AlertItem>>>,
    isRefreshing: Boolean = false,
    isClearingAll: Boolean = false,
    isClearingSelected: Boolean = false,
    refreshStatusMessage: String? = null,
    onRefresh: () -> Unit,
    onClearAll: () -> Unit = {},
    onClearSelected: (List<Long>) -> Unit = {},
    onStartTradeJourney: (AlertItem, (Boolean) -> Unit) -> Unit = { _, callback -> callback(false) },
) {
    val context = LocalContext.current
    val clipboardManager = LocalClipboardManager.current
    var selectedAlert by remember { mutableStateOf<AlertItem?>(null) }
    var isSelectionMode by remember { mutableStateOf(false) }
    var selectedAlertIds by remember { mutableStateOf<Set<Long>>(emptySet()) }
    val visibleAlertIds = remember(groupedAlerts) { collectVisibleReadArchiveAlertIds(groupedAlerts) }

    LaunchedEffect(visibleAlertIds) {
        selectedAlertIds = selectedAlertIds.filterTo(mutableSetOf()) { it in visibleAlertIds }
        if (selectedAlertIds.isEmpty()) {
            isSelectionMode = false
        }
    }

    if (selectedAlert != null) {
        ReadAlertArchiveDetailScreen(
            alert = selectedAlert!!,
            onBack = { selectedAlert = null },
            onOpenUrl = { alert ->
                val url = resolveReadArchiveUrl(alert)
                if (!url.isNullOrBlank()) {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                }
            },
            onOpenImageUrl = { alert ->
                val imageUrl = resolveReadArchiveImageUrl(alert)
                if (!imageUrl.isNullOrBlank()) {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(imageUrl)))
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
                text = "읽음 알림 보관함",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(
                    onClick = {
                        isSelectionMode = !isSelectionMode
                        if (!isSelectionMode) {
                            selectedAlertIds = emptySet()
                        }
                    },
                    enabled = groupedAlerts.isNotEmpty(),
                ) {
                    Text(if (isSelectionMode) "선택 해제" else "선택")
                }
                if (isSelectionMode) {
                    val isAllVisibleSelected = visibleAlertIds.isNotEmpty() &&
                        selectedAlertIds.size == visibleAlertIds.size &&
                        selectedAlertIds.containsAll(visibleAlertIds)
                    TextButton(
                        onClick = {
                            selectedAlertIds = if (isAllVisibleSelected) {
                                emptySet()
                            } else {
                                visibleAlertIds
                            }
                        },
                        enabled = visibleAlertIds.isNotEmpty(),
                    ) {
                        Text(if (isAllVisibleSelected) "전체 해제" else "전체 선택")
                    }
                }
                TextButton(
                    onClick = {
                        onClearSelected(selectedAlertIds.toList())
                    },
                    enabled = isSelectionMode && selectedAlertIds.isNotEmpty() && !isClearingSelected,
                ) {
                    if (isClearingSelected) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Text("선택 비우기")
                    }
                }
                TextButton(
                    onClick = {
                        onClearAll()
                        selectedAlertIds = emptySet()
                        isSelectionMode = false
                    },
                    enabled = groupedAlerts.isNotEmpty() && !isClearingAll,
                ) {
                    if (isClearingAll) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Text("전체 비우기")
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
            Spacer(modifier = Modifier.height(4.dp))
        }

        if (groupedAlerts.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(text = "읽음 처리된 알림이 없습니다.", color = Color.Gray)
            }
            return@Column
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            val sortedChipKeys = groupedAlerts.keys.sortedWith(compareBy(::chipSortGroupOrder, { it }))
            for (chipKey in sortedChipKeys) {
                val screenGroups = groupedAlerts[chipKey].orEmpty()
                item(key = "chip-$chipKey") {
                    Text(
                        text = chipKey,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                }

                val sortedScreenKeys = screenGroups.keys.sortedWith(compareBy(::screenSortGroupOrder, { it }))
                for (screenKey in sortedScreenKeys) {
                    val label = if (screenKey == "기타") "기타" else "${screenKey}인치"
                    item(key = "chip-$chipKey-screen-$screenKey") {
                        Text(
                            text = label,
                            style = MaterialTheme.typography.titleMedium,
                            color = Color.Gray,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }

                    items(
                        items = screenGroups[screenKey].orEmpty(),
                        key = { alert -> "${chipKey}-${screenKey}-${alert.id}" },
                    ) { alert ->
                        val isSelected = selectedAlertIds.contains(alert.id)
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    if (isSelectionMode) {
                                        selectedAlertIds = if (isSelected) {
                                            selectedAlertIds - alert.id
                                        } else {
                                            selectedAlertIds + alert.id
                                        }
                                    } else {
                                        selectedAlert = alert
                                    }
                                },
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                if (isSelectionMode) {
                                    Checkbox(
                                        checked = isSelected,
                                        onCheckedChange = { checked ->
                                            selectedAlertIds = if (checked) {
                                                selectedAlertIds + alert.id
                                            } else {
                                                selectedAlertIds - alert.id
                                            }
                                        },
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                }
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = resolveReadArchiveTitle(alert),
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.SemiBold,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "가격: ${formatKrwDisplay(resolveReadArchiveListingPrice(alert))}",
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                    Text(
                                        text = "사기 가능성: ${resolveReadArchiveFraudProbabilityText(alert)}",
                                        style = MaterialTheme.typography.bodySmall,
                                        fontWeight = FontWeight.SemiBold,
                                        color = resolveReadArchiveFraudRiskColor(alert),
                                    )
                                    if (isConditionChangeCandidateNotice(alert)) {
                                        Text(
                                            text = "참고용 후보",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = Color.Gray,
                                        )
                                    }
                                    Text(
                                        text = "스펙: ${buildReadArchiveSpecSummary(alert)}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = Color.Gray,
                                    )
                                    Text(
                                        text = "읽음 시각: ${alert.read_at ?: "정보 없음"}",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = Color.Gray,
                                    )
                                    if (!isSelectionMode) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        ) {
                                            Button(
                                                onClick = {
                                                    onStartTradeJourney(alert) {}
                                                },
                                                modifier = Modifier.weight(1f),
                                                enabled = alert.read_archive_event_id != null || alert.id > 0L,
                                            ) {
                                                Text("거래 기록 시작")
                                            }
                                        }
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        ) {
                                            val resolvedUrl = resolveReadArchiveUrl(alert)
                                            val resolvedImageUrl = resolveReadArchiveImageUrl(alert)
                                            Button(
                                                onClick = {
                                                    if (!resolvedUrl.isNullOrBlank()) {
                                                        clipboardManager.setText(AnnotatedString(resolvedUrl))
                                                        Toast.makeText(context, "URL을 복사했어요.", Toast.LENGTH_SHORT).show()
                                                    }
                                                },
                                                modifier = Modifier.weight(1f),
                                                enabled = !resolvedUrl.isNullOrBlank(),
                                            ) {
                                                Text("URL 복사")
                                            }
                                            Button(
                                                onClick = {
                                                    if (!resolvedImageUrl.isNullOrBlank()) {
                                                        clipboardManager.setText(AnnotatedString(resolvedImageUrl))
                                                        Toast.makeText(context, "이미지 URL을 복사했어요.", Toast.LENGTH_SHORT).show()
                                                    }
                                                },
                                                modifier = Modifier.weight(1f),
                                                enabled = !resolvedImageUrl.isNullOrBlank(),
                                            ) {
                                                Text("이미지 URL 복사")
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun collectVisibleReadArchiveAlertIds(groupedAlerts: Map<String, Map<String, List<AlertItem>>>): Set<Long> {
    val ids = mutableSetOf<Long>()
    groupedAlerts.values.forEach { screenGroups ->
        screenGroups.values.forEach { alerts ->
            alerts.forEach { alert ->
                if (alert.id > 0L) {
                    ids.add(alert.id)
                }
            }
        }
    }
    return ids
}

@Composable
private fun ReadAlertArchiveDetailScreen(
    alert: AlertItem,
    onBack: () -> Unit,
    onOpenUrl: (AlertItem) -> Unit,
    onOpenImageUrl: (AlertItem) -> Unit,
) {
    val resolvedUrl = resolveReadArchiveUrl(alert)
    val listingImageUrl = alert.listing_image_url?.takeIf { it.isNotBlank() }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "읽음 알림 상세",
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
                    text = resolveReadArchiveTitle(alert),
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

            items(buildReadArchiveDetailRows(alert, resolvedUrl)) { row ->
                val isUrlRow = row.first == "URL" && !resolvedUrl.isNullOrBlank()
                val isImageRow = row.first == "대표 이미지" && !listingImageUrl.isNullOrBlank()
                val isLinkRow = isUrlRow || isImageRow
                Column(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = row.first,
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray,
                    )
                    Text(
                        text = row.second,
                        modifier = if (isLinkRow) {
                            Modifier.clickable {
                                if (isImageRow) {
                                    onOpenImageUrl(alert)
                                } else {
                                    onOpenUrl(alert)
                                }
                            }
                        } else {
                            Modifier
                        },
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (isLinkRow) MaterialTheme.colorScheme.primary else Color.Unspecified,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }

            item {
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

private fun resolveReadArchiveUrl(alert: AlertItem): String? {
    return alert.product_url?.takeIf { it.isNotBlank() } ?: alert.url?.takeIf { it.isNotBlank() }
}

private fun resolveReadArchiveImageUrl(alert: AlertItem): String? {
    return alert.listing_image_url?.takeIf { it.isNotBlank() }
}

private fun resolveReadArchiveTitle(alert: AlertItem): String {
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

private fun resolveReadArchiveListingPrice(alert: AlertItem): Int? {
    return (alert.listing_price_krw ?: alert.alert_target_price_krw)?.toInt()
}

private fun resolveReadArchiveGapPercent(alert: AlertItem): Double? {
    return alert.price_gap_percent ?: alert.diff_ratio ?: alert.alert_drop_rate_percent
}

private fun resolveReadArchiveSortDate(alert: AlertItem): String {
    return alert.sort_date?.takeIf { it.isNotBlank() } ?: "정보 없음"
}

private fun buildReadArchiveSpecSummary(alert: AlertItem): String {
    val tokens = mutableListOf<String>()
    alert.product_type?.takeIf { it.isNotBlank() }?.let { tokens += it }
    alert.chip?.takeIf { it.isNotBlank() }?.let { tokens += it }
    alert.screen_inch?.let { inch -> if (inch > 0.0) tokens += "${inch}인치" }
    alert.ram_gb?.let { ram -> if (ram > 0.0) tokens += "${ram}GB" }
    alert.ssd_gb?.let { ssd -> if (ssd > 0.0) tokens += "${ssd}GB SSD" }

    if (tokens.isEmpty()) {
        return "분류 정보 없음"
    }
    return tokens.joinToString(" · ")
}

private fun buildReadArchiveDetailRows(alert: AlertItem, resolvedUrl: String?): List<Pair<String, String>> {
    val riskLabel = resolveReadArchiveRiskLabel(alert)
    val riskKeywordsText = resolveReadArchiveRiskKeywordsText(alert)
    val tradeFlagsText = resolveReadArchiveTradeFlagsText(alert.trade_type_flags)

    return listOf(
        "알림 유형" to resolveReadArchiveAlertTypeLabel(alert),
        "출처" to (alert.source?.takeIf { it.isNotBlank() } ?: "정보 없음"),
        "URL" to (resolvedUrl ?: "URL 정보 없음"),
        "대표 이미지" to (alert.listing_image_url?.takeIf { it.isNotBlank() } ?: "이미지 없음"),
        "제품 분류" to (alert.product_type?.takeIf { it.isNotBlank() } ?: "분류 정보 없음"),
        "칩" to (alert.chip?.takeIf { it.isNotBlank() } ?: "정보 없음"),
        "화면 크기" to (if ((alert.screen_inch ?: 0.0) > 0.0) "${alert.screen_inch}인치" else "정보 없음"),
        "RAM" to (if ((alert.ram_gb ?: 0.0) > 0.0) "${alert.ram_gb}GB" else "정보 없음"),
        "SSD" to (if ((alert.ssd_gb ?: 0.0) > 0.0) "${alert.ssd_gb}GB" else "정보 없음"),
        "등록 가격" to formatKrwDisplay(resolveReadArchiveListingPrice(alert)),
        "내가 생각한 시장가" to formatKrwDisplay((alert.user_market_price_krw ?: alert.fair_price_krw)?.toInt()),
        "알림 기준 가격" to formatKrwDisplay(alert.alert_target_price_krw?.toInt()),
        "시장가와의 차이" to formatPercentDisplay(resolveReadArchiveGapPercent(alert)),
        "설정 차이율" to formatPercentDisplay(alert.alert_drop_rate_percent),
        "알림 조건" to resolveReadArchiveConditionLabel(alert),
        "사기 가능성" to resolveReadArchiveFraudProbabilityText(alert),
        "위험도" to riskLabel,
        "위험 점수" to resolveReadArchiveFraudRiskScore(alert),
        "위험 키워드" to riskKeywordsText,
        "본문 내용" to resolveReadArchiveBodyText(alert),
        "매물 등록 시각" to resolveReadArchiveSortDate(alert),
        "알림 생성 시각" to (alert.created_at ?: "정보 없음"),
        "분석 시각" to (alert.analyzed_at ?: alert.created_at ?: "분석 시각 정보 없음"),
        "교환/나눔/의심" to tradeFlagsText,
        "특이사항" to resolveReadArchiveSpecialNotesText(riskLabel, riskKeywordsText, tradeFlagsText),
    )
}

private fun resolveReadArchiveConditionLabel(alert: AlertItem): String {
    if (isConditionChangeCandidateNotice(alert)) {
        return "조건 변경 사이 후보"
    }
    val staleContentTypeLabels = setOf("내용변경알림", "내용 변경 알림")
    val explicit = alert.alert_condition_label?.takeIf { it.isNotBlank() }
    if (explicit != null) {
        if (!isContentChangeAlertForReadArchive(alert) || !staleContentTypeLabels.contains(explicit.trim())) {
            return explicit
        }
    }
    return if ((alert.alert_price_direction ?: "").uppercase() == "ABOVE_OR_EQUAL") {
        "이 가격 이상이면 알림"
    } else {
        "이 가격 이하이면 알림"
    }
}

private fun resolveReadArchiveRiskLabel(alert: AlertItem): String {
    return resolveReadArchiveFraudProbabilityLabel(alert)
}

private fun resolveReadArchiveFraudRiskColor(alert: AlertItem): Color {
    return when (resolveReadArchiveRiskLabel(alert)) {
        "높음", "위험" -> Color(0xFFD32F2F)
        "주의" -> Color(0xFFF57C00)
        "낮음" -> Color(0xFF2E7D32)
        else -> Color.Gray
    }
}

private fun resolveReadArchiveRiskKeywordsText(alert: AlertItem): String {
    val keywords = alert.risk_keywords ?: emptyList()
    if (keywords.isEmpty()) {
        return "특이사항 없음"
    }
    return keywords.joinToString(", ")
}

private fun resolveReadArchiveFraudProbabilityText(alert: AlertItem): String {
    val explicitText = alert.fraud_probability_text?.trim()
    if (!explicitText.isNullOrEmpty() && explicitText != "정보 없음") {
        return explicitText
    }

    val probability = alert.fraud_probability
    val label = resolveReadArchiveFraudProbabilityLabel(alert)
    if (probability == null) {
        return label
    }

    val percentText = "${"%.0f".format(probability * 100)}%"
    return if (label == "정보 없음") {
        percentText
    } else {
        "$label ($percentText)"
    }
}

private fun resolveReadArchiveFraudProbabilityLabel(alert: AlertItem): String {
    val explicit = alert.formatted_fraud_probability_label?.takeIf {
        it.isNotBlank() && it != "정보 없음"
    }
    if (explicit != null) {
        return explicit
    }
    alert.fraud_probability?.let { probability ->
        return when {
            probability >= 0.65 -> "높음"
            probability >= 0.25 -> "주의"
            else -> "낮음"
        }
    }
    return when ((alert.fraud_probability_label ?: "").uppercase()) {
        "LOW" -> "낮음"
        "MEDIUM" -> "주의"
        "HIGH" -> "높음"
        else -> "정보 없음"
    }
}

private fun resolveReadArchiveFraudRiskScore(alert: AlertItem): String {
    val probability = alert.fraud_probability ?: return "정보 없음"
    val score = (probability * 100).roundToInt().coerceIn(0, 100)
    return "${score}점"
}

private fun resolveReadArchiveBodyText(alert: AlertItem): String {
    val body = alert.body_text?.trim()
    if (!body.isNullOrEmpty()) {
        return body
    }
    val excerpt = alert.body_excerpt?.trim()
    if (!excerpt.isNullOrEmpty()) {
        return excerpt
    }
    return "본문 내용 없음"
}

private fun resolveReadArchiveTradeFlagsText(flags: TradeTypeFlags?): String {
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

private fun resolveReadArchiveSpecialNotesText(
    riskLabel: String,
    riskKeywordsText: String,
    tradeFlagsText: String,
): String {
    val notes = mutableListOf<String>()
    if (riskLabel == "주의" || riskLabel == "높음" || riskLabel == "위험") {
        notes += "사기 가능성 $riskLabel"
    }
    if (tradeFlagsText != "특이사항 없음" && tradeFlagsText != "정보 없음") {
        notes += "거래 유형: $tradeFlagsText"
    }
    if (riskKeywordsText != "특이사항 없음") {
        notes += "위험 키워드: $riskKeywordsText"
    }
    if (notes.isEmpty()) {
        return "특이사항 없음"
    }
    return notes.joinToString(" / ")
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

private fun isContentChangeAlertForReadArchive(alert: AlertItem): Boolean {
    return contentChangeTriggerReasonsForReadArchive.contains((alert.trigger_reason ?: "").trim().lowercase())
}

private fun resolveReadArchiveAlertTypeLabel(alert: AlertItem): String {
    alert.alert_type_label?.let { label ->
        if (label.isNotBlank()) {
            return label
        }
    }
    if (isConditionChangeCandidateNotice(alert)) {
        return "참고 알림 (조건 변경 사이 후보)"
    }
    if (isContentChangeAlertForReadArchive(alert)) {
        return "내용 변경 알림"
    }
    return "정식 알림"
}

private val contentChangeTriggerReasonsForReadArchive = setOf(
    "content_changed",
    "title_changed",
    "price_changed",
    "body_changed",
    "self_check_changed",
)

private fun chipSortGroupOrder(chip: String): Int {
    return when (chip.uppercase()) {
        "M1" -> 1
        "M2" -> 2
        "M3" -> 3
        "M4" -> 4
        "M5" -> 5
        "기타" -> 99
        else -> 50
    }
}

private fun screenSortGroupOrder(screen: String): Int {
    return if (screen == "기타") {
        99
    } else {
        screen.toIntOrNull() ?: 50
    }
}
