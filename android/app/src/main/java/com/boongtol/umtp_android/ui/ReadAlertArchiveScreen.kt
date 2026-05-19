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
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.boongtol.umtp_android.network.AlertItem

@Composable
fun ReadAlertArchiveScreen(
    groupedAlerts: Map<String, Map<String, List<AlertItem>>>,
    isRefreshing: Boolean = false,
    refreshStatusMessage: String? = null,
    onRefresh: () -> Unit,
) {
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
                text = "읽음 알림 보관함",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
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
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    val url = resolveReadArchiveUrl(alert)
                                    if (!url.isNullOrBlank()) {
                                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                    }
                                },
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(
                                    text = alert.title?.ifBlank { "제목 없음" } ?: "제목 없음",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.SemiBold,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "가격: ${formatReadArchiveKrw(alert.listing_price_krw)}",
                                    style = MaterialTheme.typography.bodySmall,
                                )
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
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun resolveReadArchiveUrl(alert: AlertItem): String? {
    return alert.product_url?.takeIf { it.isNotBlank() } ?: alert.url?.takeIf { it.isNotBlank() }
}

private fun buildReadArchiveSpecSummary(alert: AlertItem): String {
    val tokens = mutableListOf<String>()
    alert.product_type?.takeIf { it.isNotBlank() }?.let { tokens += it }
    alert.chip?.takeIf { it.isNotBlank() }?.let { tokens += it }
    alert.screen_inch?.let { inch -> if (inch > 0) tokens += "${inch}인치" }
    alert.ram_gb?.let { ram -> if (ram > 0) tokens += "${ram}GB" }
    alert.ssd_gb?.let { ssd -> if (ssd > 0) tokens += "${ssd}GB SSD" }

    if (tokens.isEmpty()) {
        return "분류 정보 없음"
    }
    return tokens.joinToString(" · ")
}

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

private fun formatReadArchiveKrw(value: Int?): String {
    if (value == null) {
        return "정보 없음"
    }
    return "${String.format("%,d", value)}원"
}
