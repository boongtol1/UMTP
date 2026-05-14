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
import androidx.compose.ui.text.input.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.boongtol.umtp_android.network.WatchRuleUpsertRequest

private const val DEFAULT_PRODUCT_TYPE = "MacBook Air"
private const val DEFAULT_SCREEN_INCH = 13
private const val DEFAULT_POLL_INTERVAL_SECONDS = 60

@Composable
fun WatchRuleSettingsScreen(
    userId: String,
    recommendedKeywords: List<String>,
    isSaving: Boolean,
    isRequestingNow: Boolean,
    lastServerDropRatePercent: Double?,
    onFetchRecommendedKeywords: (productType: String, chip: String, ramGb: Int, ssdGb: Int) -> Unit,
    onUpsertWatchRule: (WatchRuleUpsertRequest) -> Unit,
    onRequestPollNow: (userId: String, searchKeyword: String) -> Unit
) {
    val chipOptions = listOf("M1", "M2", "M3", "M4", "M5")
    val ramOptions = listOf(8, 16, 24, 32)
    val ssdOptions = listOf(256, 512, 1024, 2048)

    var chip by remember { mutableStateOf("M1") }
    var ramGb by remember { mutableStateOf(8) }
    var ssdGb by remember { mutableStateOf(256) }
    var searchKeyword by remember { mutableStateOf("") }
    var fairPriceText by remember { mutableStateOf("") }
    var targetPriceText by remember { mutableStateOf("") }
    var enabled by remember { mutableStateOf(true) }

    val fairPrice = fairPriceText.toIntOrNull()
    val targetPrice = targetPriceText.toIntOrNull()
    val localDropRateText = if (fairPrice != null && fairPrice > 0 && targetPrice != null) {
        val ratio = ((fairPrice - targetPrice).toDouble() / fairPrice.toDouble()) * 100.0
        "약 ${"%.2f".format(ratio)}% 저렴하면 알림"
    } else {
        null
    }

    Column(
        modifier = Modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("감시 조건 설정", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text("User: $userId", style = MaterialTheme.typography.bodySmall)

        HorizontalDivider()

        Text("제품", style = MaterialTheme.typography.labelLarge)
        Text("MacBook Air", style = MaterialTheme.typography.bodyMedium)

        Text("칩", style = MaterialTheme.typography.labelLarge)
        IntOptionChipRow(
            options = chipOptions,
            selected = chip,
            onSelect = { chip = it }
        )

        Text("RAM (GB)", style = MaterialTheme.typography.labelLarge)
        IntOptionChipRow(
            options = ramOptions,
            selected = ramGb,
            onSelect = { ramGb = it }
        )

        Text("SSD (GB)", style = MaterialTheme.typography.labelLarge)
        IntOptionChipRow(
            options = ssdOptions,
            selected = ssdGb,
            onSelect = { ssdGb = it }
        )

        OutlinedTextField(
            value = searchKeyword,
            onValueChange = { searchKeyword = it },
            label = { Text("검색어 (예: 맥북 m1)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
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

        OutlinedTextField(
            value = fairPriceText,
            onValueChange = { if (it.all(Char::isDigit)) fairPriceText = it },
            label = { Text("공정가 (원)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = targetPriceText,
            onValueChange = { if (it.all(Char::isDigit)) targetPriceText = it },
            label = { Text("알림 받을 가격 (원)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        localDropRateText?.let {
            Text(it, style = MaterialTheme.typography.bodyMedium)
        }

        lastServerDropRatePercent?.let {
            Text(
                text = "서버 계산 저평가율: ${"%.2f".format(it)}%",
                style = MaterialTheme.typography.bodySmall
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("enabled")
            Switch(checked = enabled, onCheckedChange = { enabled = it })
        }

        Button(
            onClick = {
                onUpsertWatchRule(
                    WatchRuleUpsertRequest(
                        user_id = userId,
                        product_type = DEFAULT_PRODUCT_TYPE,
                        chip = chip,
                        screen_inch = DEFAULT_SCREEN_INCH,
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
                Text("저장")
            }
        }

        Button(
            onClick = {
                val normalizedKeyword = searchKeyword.trim()
                if (normalizedKeyword.isNotEmpty()) {
                    onRequestPollNow(userId, normalizedKeyword)
                }
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
private fun IntOptionChipRow(
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
