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
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.boongtol.umtp_android.network.AlertItem
import com.boongtol.umtp_android.network.TradeTypeFlags

@Composable
fun AlertFeedScreen(
    alerts: List<AlertItem>,
    onRefresh: () -> Unit,
) {
    var readIds by remember { mutableStateOf(setOf<Long>()) }
    var expandedIds by remember { mutableStateOf(setOf<Long>()) }
    val context = LocalContext.current

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
            TextButton(onClick = onRefresh) {
                Text("새로고침")
            }
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
                val isRead = readIds.contains(alert.id)
                val isExpanded = expandedIds.contains(alert.id)
                AlertCard(
                    alert = alert,
                    isRead = isRead,
                    isExpanded = isExpanded,
                    onToggleExpand = {
                        expandedIds = if (isExpanded) {
                            expandedIds - alert.id
                        } else {
                            expandedIds + alert.id
                        }
                    },
                    onOpenUrl = {
                        val resolvedUrl = resolveAlertUrl(alert)
                        if (!resolvedUrl.isNullOrBlank()) {
                            readIds = readIds + alert.id
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(resolvedUrl))
                            context.startActivity(intent)
                        }
                    },
                )
            }
        }
    }
}

@Composable
fun AlertCard(
    alert: AlertItem,
    isRead: Boolean,
    isExpanded: Boolean,
    onToggleExpand: () -> Unit,
    onOpenUrl: () -> Unit,
) {
    val resolvedUrl = resolveAlertUrl(alert)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onToggleExpand() },
        colors = CardDefaults.cardColors(
            containerColor = if (isRead) {
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            } else {
                MaterialTheme.colorScheme.surface
            },
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isRead) 0.dp else 2.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = alert.title?.ifBlank { "제목 없음" } ?: "제목 없음",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                if (!isRead) {
                    Surface(
                        modifier = Modifier
                            .padding(start = 8.dp)
                            .size(8.dp),
                        shape = MaterialTheme.shapes.small,
                        color = Color.Red,
                    ) {}
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                BadgeChip(label = resolveRiskLabel(alert), color = resolveRiskColor(alert))
                BadgeChip(label = resolveAlertConditionLabel(alert), color = Color(0xFF1565C0))
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "가격: ${formatKrwDisplay(alert.listing_price_krw)}",
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
                text = "시장가와의 차이: ${formatPercentDisplay(alert.price_gap_percent ?: alert.diff_ratio)}",
                style = MaterialTheme.typography.bodySmall,
            )

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = alert.analyzed_at ?: alert.created_at ?: "분석 시각 정보 없음",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray,
                )
                Text(
                    text = if (isExpanded) "상세 접기" else "상세 보기",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
            }

            if (isExpanded) {
                Spacer(modifier = Modifier.height(12.dp))
                HorizontalDivider()
                Spacer(modifier = Modifier.height(12.dp))

                DetailRow(label = "출처", value = alert.source ?: "정보 없음")
                DetailRow(label = "URL", value = resolvedUrl ?: "URL 정보 없음")
                DetailRow(label = "내가 생각한 시장가", value = formatKrwDisplay(alert.user_market_price_krw ?: alert.fair_price_krw))
                DetailRow(label = "알림 기준 가격", value = formatKrwDisplay(alert.alert_target_price_krw))
                DetailRow(label = "시장가와의 차이", value = formatPercentDisplay(alert.price_gap_percent ?: alert.diff_ratio))
                DetailRow(label = "알림 조건", value = resolveAlertConditionLabel(alert))
                DetailRow(label = "위험도", value = resolveRiskLabel(alert))
                DetailRow(label = "위험 점수", value = alert.risk_score?.toString() ?: "정보 없음")
                DetailRow(label = "위험 키워드", value = resolveRiskKeywordsText(alert))
                DetailRow(label = "본문 요약", value = alert.body_excerpt ?: "본문 정보 없음")
                DetailRow(label = "분석 시각", value = alert.analyzed_at ?: alert.created_at ?: "분석 시각 정보 없음")
                DetailRow(label = "교환/나눔/의심", value = resolveTradeFlagsText(alert.trade_type_flags))

                Spacer(modifier = Modifier.height(8.dp))

                Button(
                    onClick = onOpenUrl,
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
private fun DetailRow(label: String, value: String) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = Color.Gray,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
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

private fun resolveAlertConditionLabel(alert: AlertItem): String {
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
