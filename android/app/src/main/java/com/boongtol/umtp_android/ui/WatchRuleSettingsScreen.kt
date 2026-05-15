package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.boongtol.umtp_android.network.WatchRuleItem
import com.boongtol.umtp_android.network.WatchRuleUpsertRequest
import java.text.NumberFormat
import java.util.Locale

private const val DEFAULT_PRODUCT_TYPE = "MacBook Air"
private const val DEFAULT_POLL_INTERVAL_SECONDS = 60

@Composable
fun WatchRuleSettingsScreen(
    userId: String,
    recommendedKeywords: List<String>,
    watchRules: List<WatchRuleItem>,
    isSaving: Boolean,
    isRequestingNow: Boolean,
    lastServerDropRatePercent: Double?,
    onFetchRecommendedKeywords: (productType: String, chip: String, ramGb: Int, ssdGb: Int) -> Unit,
    onUpsertWatchRule: (WatchRuleUpsertRequest) -> Unit,
    onRequestPollNow: (userId: String, searchKeyword: String) -> Unit,
    onRefreshWatchRules: () -> Unit,
) {
    val chipOptions = listOf("M1", "M2", "M3", "M4", "M5")
    val screenOptions = listOf(13, 15)
    val ramOptions = listOf(8, 16, 24, 32)
    val ssdOptions = listOf(256, 512, 1024, 2048)

    var chip by remember { mutableStateOf("M1") }
    var screenInch by remember { mutableStateOf(13) }
    var ramGb by remember { mutableStateOf(8) }
    var ssdGb by remember { mutableStateOf(256) }
    var searchKeyword by remember { mutableStateOf("") }
    var fairPriceText by remember { mutableStateOf("") }
    var targetPriceText by remember { mutableStateOf("") }
    var enabled by remember { mutableStateOf(true) }

    val fairPrice = fairPriceText.toIntOrNull()
    val targetPrice = targetPriceText.toIntOrNull()
    val localDropRate =
        if (fairPrice != null && fairPrice > 0 && targetPrice != null) {
            ((fairPrice - targetPrice).toDouble() / fairPrice.toDouble()) * 100.0
        } else {
            null
        }

    val friendlyTargetPriceText = targetPrice?.let {
        "${formatKrwAsManwonOrKrw(it)} 이하로 뜨면 알림"
    }

    Column(
        modifier = Modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("맥북 감시 조건 설정", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text("사용자: $userId", style = MaterialTheme.typography.bodySmall)

        HorizontalDivider()

        Text("어떤 맥북을 찾을지", style = MaterialTheme.typography.labelLarge)
        Text("제품: MacBook Air", style = MaterialTheme.typography.bodyMedium)

        Text("칩", style = MaterialTheme.typography.labelLarge)
        StringOptionChipRow(options = chipOptions, selected = chip, onSelect = { chip = it })

        Text("화면 크기", style = MaterialTheme.typography.labelLarge)
        IntOptionChipRow(options = screenOptions, selected = screenInch, onSelect = { screenInch = it })

        Text("RAM (GB)", style = MaterialTheme.typography.labelLarge)
        IntOptionChipRow(options = ramOptions, selected = ramGb, onSelect = { ramGb = it })

        Text("SSD (GB)", style = MaterialTheme.typography.labelLarge)
        IntOptionChipRow(options = ssdOptions, selected = ssdGb, onSelect = { ssdGb = it })

        HorizontalDivider()

        OutlinedTextField(
            value = searchKeyword,
            onValueChange = { searchKeyword = it },
            label = { Text("검색어") },
            placeholder = { Text("예: 맥북 m1, m1맥북에어") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Text(
            "검색어는 넓게 입력해도 돼요. 최종 알림은 실제 스펙과 가격을 다시 확인한 뒤 보내요.",
            style = MaterialTheme.typography.bodySmall
        )

        Button(
            onClick = {
                onFetchRecommendedKeywords(
                    DEFAULT_PRODUCT_TYPE,
                    chip,
                    ramGb,
                    ssdGb
                )
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("추천 검색어 불러오기")
        }

        if (recommendedKeywords.isNotEmpty()) {
            Text("추천 검색어", style = MaterialTheme.typography.labelLarge)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(recommendedKeywords) { keyword ->
                    FilterChip(
                        selected = searchKeyword.trim() == keyword,
                        onClick = { searchKeyword = keyword },
                        label = { Text(keyword) }
                    )
                }
            }
        }

        HorizontalDivider()

        OutlinedTextField(
            value = fairPriceText,
            onValueChange = { if (it.all(Char::isDigit)) fairPriceText = it },
            label = { Text("내 기준 적정 가격") },
            placeholder = { Text("예: 800000") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Text(
            "이 모델이 보통 이 정도면 적당하다고 생각하는 가격이에요.",
            style = MaterialTheme.typography.bodySmall
        )

        OutlinedTextField(
            value = targetPriceText,
            onValueChange = { if (it.all(Char::isDigit)) targetPriceText = it },
            label = { Text("알림 받을 가격") },
            placeholder = { Text("예: 650000") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Text(
            "이 가격 이하로 뜨면 알려드려요.",
            style = MaterialTheme.typography.bodySmall
        )

        friendlyTargetPriceText?.let {
            Text(it, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
        }
        if (localDropRate != null) {
            Text(
                "내 기준보다 약 ${"%.2f".format(localDropRate)}% 저렴할 때 알림",
                style = MaterialTheme.typography.bodyMedium
            )
        }
        if (fairPrice != null && targetPrice != null && fairPrice > 0 && targetPrice > fairPrice) {
            Text(
                "알림 받을 가격이 공정가보다 높아요. 저장은 가능하지만 추천하지 않아요.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }

        lastServerDropRatePercent?.let {
            Text(
                text = "서버 계산 기준: 약 ${"%.2f".format(it)}% 저렴할 때 알림",
                style = MaterialTheme.typography.bodySmall
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("이 조건으로 감시하기")
            Switch(checked = enabled, onCheckedChange = { enabled = it })
        }

        Button(
            onClick = {
                onUpsertWatchRule(
                    WatchRuleUpsertRequest(
                        user_id = userId,
                        product_type = DEFAULT_PRODUCT_TYPE,
                        chip = chip,
                        screen_inch = screenInch,
                        ram_gb = ramGb,
                        ssd_gb = ssdGb,
                        search_keyword = searchKeyword.trim().ifEmpty { null },
                        enabled = enabled,
                        poll_interval_seconds = DEFAULT_POLL_INTERVAL_SECONDS,
                        target_price_krw = targetPrice,
                        fair_price_krw = fairPrice,
                    )
                )
            },
            enabled = !isSaving,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (isSaving) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
            } else {
                Text("감시 조건 저장")
            }
        }

        Button(
            onClick = {
                onRequestPollNow(userId, searchKeyword.trim())
            },
            enabled = !isRequestingNow,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (isRequestingNow) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
            } else {
                Text("지금 바로 검색")
            }
        }

        HorizontalDivider()

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("저장된 감시 조건", style = MaterialTheme.typography.titleMedium)
            Button(onClick = onRefreshWatchRules) {
                Text("새로고침")
            }
        }

        if (watchRules.isEmpty()) {
            Text("저장된 감시 조건이 아직 없어요.", style = MaterialTheme.typography.bodySmall)
        } else {
            watchRules.forEach { rule ->
                val specLabel = buildString {
                    append(rule.chip ?: "-")
                    append(" ")
                    append(rule.product_type ?: "MacBook Air")
                    append(" ")
                    append(rule.ram_gb ?: "-")
                    append("/")
                    append(rule.ssd_gb ?: "-")
                    if (rule.screen_inch != null) {
                        append(" (")
                        append(rule.screen_inch)
                        append("인치)")
                    }
                }

                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp)
                ) {
                    Text(specLabel, fontWeight = FontWeight.SemiBold)
                    Text("검색어: ${rule.search_keyword ?: "-"}", style = MaterialTheme.typography.bodySmall)
                    val targetLabel = rule.target_price_krw?.let { formatKrw(it) + " 이하 알림" } ?: "알림 가격 미설정"
                    Text(targetLabel, style = MaterialTheme.typography.bodySmall)
                    Text(
                        if (rule.enabled == true) "상태: 켜짐" else "상태: 꺼짐",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                HorizontalDivider()
            }
        }
    }
}

@Composable
private fun IntOptionChipRow(
    options: List<Int>,
    selected: Int,
    onSelect: (Int) -> Unit
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(options) { option ->
            FilterChip(
                selected = option == selected,
                onClick = { onSelect(option) },
                label = { Text(option.toString()) }
            )
        }
    }
}

@Composable
private fun StringOptionChipRow(
    options: List<String>,
    selected: String,
    onSelect: (String) -> Unit
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(options) { option ->
            FilterChip(
                selected = option == selected,
                onClick = { onSelect(option) },
                label = { Text(option) }
            )
        }
    }
}

private fun formatKrw(value: Int): String {
    val formatter = NumberFormat.getNumberInstance(Locale.KOREA)
    return "${formatter.format(value)}원"
}

private fun formatKrwAsManwonOrKrw(value: Int): String {
    if (value > 0 && value % 10000 == 0) {
        return "${value / 10000}만원"
    }
    return formatKrw(value)
}
