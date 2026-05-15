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
    onSave: (fairPrice: Int, dropRate: Int, enabled: Boolean) -> Unit
) {
    var fairPriceText by remember(userSetting) { 
        mutableStateOf(userSetting?.user_fair_price_krw?.toString() ?: userSetting?.system_fair_price_krw?.toString() ?: "") 
    }
    var dropRateText by remember(userSetting) { 
        mutableStateOf(
            formatDropRateForInput(
                userSetting?.user_alert_drop_rate_percent ?: userSetting?.system_alert_drop_rate_percent
            )
        )
    }
    var enabled by remember(userSetting) { mutableStateOf(userSetting?.enabled ?: false) }

    val numberFormat = NumberFormat.getNumberInstance(Locale.KOREA)

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

            Spacer(modifier = Modifier.height(16.dp))

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
                    value = dropRateText,
                    onValueChange = { if (it.all { char -> char.isDigit() }) dropRateText = it },
                    label = { Text("차이비율 (%)", fontSize = 12.sp) },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = {
                    val price = fairPriceText.toIntOrNull() ?: 0
                    val rate = dropRateText.toIntOrNull() ?: 0
                    if (price > 0 && rate in 0..100) {
                        onSave(price, rate, enabled)
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

private fun formatDropRateForInput(value: Double?): String {
    if (value == null) {
        return ""
    }
    return value.roundToInt().toString()
}

private fun formatDropRateForDisplay(value: Double?): String {
    if (value == null) {
        return "0%"
    }
    val rounded = value.roundToInt()
    return "$rounded%"
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
