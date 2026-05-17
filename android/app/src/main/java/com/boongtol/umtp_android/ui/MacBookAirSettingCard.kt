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
import kotlin.math.roundToInt

@Composable
fun MacBookAirSettingCard(
    userId: String?,
    unit: MacBookAirUnit,
    userSetting: UserFairPriceItem?,
    isSaving: Boolean,
    onSave: (
        fairPrice: Int,
        desiredPrice: Int,
        alertPriceDirection: String,
        enabled: Boolean,
        searchKeyword: String?,
        boundPrice: Int?
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
            normalizeAlertDirection(
                userSetting?.user_alert_price_direction ?: userSetting?.effective_alert_price_direction
            )
        )
    }
    var minPriceText by remember(userSetting) {
        mutableStateOf(userSetting?.user_min_price_krw?.toString() ?: "")
    }
    var maxPriceText by remember(userSetting) {
        mutableStateOf(userSetting?.user_max_price_krw?.toString() ?: "")
    }

    val marketPriceLabel = buildMarketPriceLabel(userId)
    val fairPriceInput = fairPriceText.toIntOrNull()
    val desiredPriceInput = desiredPriceText.toIntOrNull()
    val computedGapPercent = computeMarketPriceGapPercent(fairPriceInput, desiredPriceInput)
    val effectiveFairPrice = userSetting?.effective_fair_price_krw
    val effectiveTargetPrice = userSetting?.effective_target_buy_price_krw ?: calculateDesiredPrice(
        effectiveFairPrice,
        userSetting?.effective_alert_drop_rate_percent,
    )
    val effectiveGapPercent = computeMarketPriceGapPercent(effectiveFairPrice, effectiveTargetPrice)
    val isAboveDirection = alertPriceDirection == ABOVE_OR_EQUAL_DIRECTION
    val boundPriceText = if (isAboveDirection) maxPriceText else minPriceText
    val boundPriceInput = boundPriceText.toIntOrNull()

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

            InfoRow(label = "시스템 기준 시장가", value = formatKrwDisplay(userSetting?.system_fair_price_krw))
            InfoRow(
                label = marketPriceLabel,
                value = formatKrwDisplay(userSetting?.effective_fair_price_krw),
                valueColor = if (userSetting?.has_user_override == true) Color(0xFF388E3C) else Color.Unspecified
            )
            InfoRow(
                label = "알림 기준 가격",
                value = formatKrwDisplay(
                    userSetting?.effective_target_buy_price_krw ?: calculateDesiredPrice(
                        userSetting?.effective_fair_price_krw,
                        userSetting?.effective_alert_drop_rate_percent,
                    )
                ),
            )
            InfoRow(
                label = "시장가와의 차이(%)",
                value = formatPercentDisplay(effectiveGapPercent),
            )
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
                    onValueChange = {
                        if (it.all { char -> char.isDigit() }) {
                            fairPriceText = normalizePriceTextInput(it)
                        }
                    },
                    label = { Text("$marketPriceLabel (원)", fontSize = 12.sp) },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true
                )
                OutlinedTextField(
                    value = desiredPriceText,
                    onValueChange = {
                        if (it.all { char -> char.isDigit() }) {
                            desiredPriceText = normalizePriceTextInput(it)
                        }
                    },
                    label = { Text("알림 기준 가격 (원)", fontSize = 12.sp) },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = if (computedGapPercent != null) {
                    "시장가와의 차이(%): ${formatPercentDisplay(computedGapPercent)}"
                } else {
                    "시장가와의 차이(%): 정보 없음"
                },
                style = MaterialTheme.typography.bodySmall
            )
            Text(
                text = "시장가보다 몇 % 낮거나 높은 가격에서 알림을 받을지 자동 계산합니다.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )
            Text(
                text = "차이가 매우 크면 100%를 넘어갈 수 있어요.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )
            Text(
                text = "알림 기준 가격은 시장가와 차이를 바탕으로 자동 계산됩니다.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
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
                        selected = alertPriceDirection == BELOW_OR_EQUAL_DIRECTION,
                        onClick = { alertPriceDirection = BELOW_OR_EQUAL_DIRECTION }
                    )
                    Text("이하 알림")
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(
                        selected = alertPriceDirection == ABOVE_OR_EQUAL_DIRECTION,
                        onClick = { alertPriceDirection = ABOVE_OR_EQUAL_DIRECTION }
                    )
                    Text("이상 알림")
                }
            }
            Text(
                text = if (isAboveDirection) {
                    "이 가격 이상이면 알림을 받습니다."
                } else {
                    "이 가격 이하이면 알림을 받습니다."
                },
                style = MaterialTheme.typography.bodySmall
            )

            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = boundPriceText,
                onValueChange = {
                    if (it.all { char -> char.isDigit() }) {
                        if (isAboveDirection) {
                            maxPriceText = normalizePriceTextInput(it)
                        } else {
                            minPriceText = normalizePriceTextInput(it)
                        }
                    }
                },
                label = {
                    Text(
                        if (isAboveDirection) "최대 가격 (원)" else "최소 가격 (원)",
                        fontSize = 12.sp
                    )
                },
                placeholder = {
                    Text(
                        if (isAboveDirection) "예: 900000" else "예: 300000",
                        fontSize = 12.sp
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true
            )
            Text(
                text = if (isAboveDirection) {
                    "이 가격 이하인 매물만 알림을 받습니다."
                } else {
                    "이 가격 이상인 매물만 알림을 받습니다."
                },
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "시장가 설정 안내: 이 제품이 보통 이 정도 가격이라고 생각하는 금액을 입력하세요.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
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
                            boundPriceInput,
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

private fun calculateDesiredPrice(fairPrice: Int?, dropRate: Double?): Int? {
    if (fairPrice == null || fairPrice <= 0 || dropRate == null) {
        return null
    }
    val desired = fairPrice.toDouble() * (1.0 - (dropRate / 100.0))
    return desired.roundToInt().coerceAtLeast(0)
}

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
