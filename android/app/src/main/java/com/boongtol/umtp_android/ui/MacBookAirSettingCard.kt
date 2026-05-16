package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.boongtol.umtp_android.network.MacBookAirUnit
import com.boongtol.umtp_android.network.UserFairPriceItem
import java.text.NumberFormat
import java.util.*
import kotlin.math.roundToInt

@Composable
fun MacBookAirSettingCard(
    unit: MacBookAirUnit,
    userSetting: UserFairPriceItem?,
    isSaving: Boolean,
    onSave: (
        fairPrice: Int,
        desiredPrice: Int,
        alertPriceDirection: String,
        enabled: Boolean,
        searchKeyword: String?
    ) -> Unit
) {
    var fairPriceText by remember(userSetting) { 
        mutableStateOf(userSetting?.user_fair_price_krw?.toString() ?: userSetting?.system_fair_price_krw?.toString() ?: "") 
    }
    var enabled by remember(userSetting) { mutableStateOf(userSetting?.enabled ?: false) }
    var searchKeywordText by remember(userSetting) {
        mutableStateOf(userSetting?.custom_search_keyword ?: userSetting?.effective_search_keyword ?: "")
    }
    var desiredPriceText by remember(userSetting) {
        val fair = userSetting?.user_fair_price_krw ?: userSetting?.effective_fair_price_krw
        val dropRate = userSetting?.user_alert_drop_rate_percent ?: userSetting?.effective_alert_drop_rate_percent
        val initialDesiredPrice = calculateDesiredPrice(fair, dropRate)
        mutableStateOf(initialDesiredPrice?.toString() ?: "")
    }
    var alertPriceDirection by remember(userSetting) {
        mutableStateOf(
            normalizeAlertPriceDirection(
                userSetting?.user_alert_price_direction ?: userSetting?.effective_alert_price_direction
            )
        )
    }

    val numberFormat = NumberFormat.getNumberInstance(Locale.KOREA)
    val fairPriceInput = fairPriceText.toIntOrNull()
    val desiredPriceInput = desiredPriceText.toIntOrNull()
    val computedDropRate = calculateDropRatePercent(fairPriceInput, desiredPriceInput)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${unit.ram_gb}GB / ${unit.ssd_gb}GB",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Switch(
                    checked = enabled,
                    onCheckedChange = { enabled = it }
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            HorizontalDivider()

            Spacer(modifier = Modifier.height(8.dp))

            InfoRow(label = "시스템 공정가", value = "${numberFormat.format(userSetting?.system_fair_price_krw ?: 0)}원")
            InfoRow(
                label = "적용 공정가", 
                value = "${numberFormat.format(userSetting?.effective_fair_price_krw ?: 0)}원", 
                valueColor = if (userSetting?.has_user_override == true) Color(0xFF388E3C) else Color.Unspecified
            )
            InfoRow(label = "알림 기준", value = formatDropRateForDisplay(userSetting?.effective_alert_drop_rate_percent))
            InfoRow(label = "추천 검색어", value = userSetting?.recommended_search_keyword ?: "-")

            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = searchKeywordText,
                onValueChange = { searchKeywordText = it },
                label = { Text("커스텀 검색어", fontSize = 12.sp) },
                placeholder = { Text(userSetting?.recommended_search_keyword ?: "예: m1맥북에어", fontSize = 12.sp) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = fairPriceText,
                    onValueChange = { if (it.all { char -> char.isDigit() }) fairPriceText = it },
                    label = { Text("공정가 (원)", fontSize = 12.sp) },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true
                )
                OutlinedTextField(
                    value = desiredPriceText,
                    onValueChange = { if (it.all { char -> char.isDigit() }) desiredPriceText = it },
                    label = { Text("내가 사고 싶은 가격 (원)", fontSize = 12.sp) },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = if (computedDropRate != null) {
                    "차이비율(자동 계산): ${formatDropRateForDisplay(computedDropRate)}"
                } else {
                    "차이비율(자동 계산): -"
                },
                style = MaterialTheme.typography.bodySmall
            )

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "알림 방향",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(
                        selected = alertPriceDirection == BELOW_OR_EQUAL,
                        onClick = { alertPriceDirection = BELOW_OR_EQUAL }
                    )
                    Text("이하 알림")
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(
                        selected = alertPriceDirection == ABOVE_OR_EQUAL,
                        onClick = { alertPriceDirection = ABOVE_OR_EQUAL }
                    )
                    Text("이상 알림")
                }
            }
            Text(
                text = if (alertPriceDirection == ABOVE_OR_EQUAL) {
                    "이 가격 이상이면 알림을 받습니다."
                } else {
                    "이 가격 이하이면 알림을 받습니다."
                },
                style = MaterialTheme.typography.bodySmall
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = {
                    val price = fairPriceText.toIntOrNull() ?: 0
                    val desiredPrice = desiredPriceText.toIntOrNull() ?: 0
                    if (price > 0 && desiredPrice > 0) {
                        onSave(
                            price,
                            desiredPrice,
                            alertPriceDirection,
                            enabled,
                            searchKeywordText.trim().ifEmpty { null },
                        )
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSaving
            ) {
                if (isSaving) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp, color = Color.White)
                } else {
                    Text("저장")
                }
            }
        }
    }
}

private fun formatDropRateForDisplay(value: Double?): String {
    if (value == null) {
        return "-"
    }
    return "${"%.2f".format(value)}%"
}

private fun calculateDropRatePercent(fairPrice: Int?, desiredPrice: Int?): Double? {
    if (fairPrice == null || desiredPrice == null || fairPrice <= 0) {
        return null
    }
    return ((fairPrice - desiredPrice).toDouble() / fairPrice.toDouble()) * 100.0
}

private fun calculateDesiredPrice(fairPrice: Int?, dropRate: Double?): Int? {
    if (fairPrice == null || fairPrice <= 0 || dropRate == null) {
        return null
    }
    val desired = fairPrice.toDouble() * (1.0 - (dropRate / 100.0))
    return desired.roundToInt().coerceAtLeast(0)
}

private fun normalizeAlertPriceDirection(raw: String?): String {
    return when (raw?.trim()?.uppercase()) {
        ABOVE_OR_EQUAL -> ABOVE_OR_EQUAL
        else -> BELOW_OR_EQUAL
    }
}

private const val BELOW_OR_EQUAL = "BELOW_OR_EQUAL"
private const val ABOVE_OR_EQUAL = "ABOVE_OR_EQUAL"

@Composable
private fun InfoRow(label: String, value: String, valueColor: Color = Color.Unspecified) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = label, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
        Text(text = value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = valueColor)
    }
}
