package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

private enum class ResaleInputMode {
    AFTER_PURCHASE,
    AFTER_RESALE,
}

private fun String.toOptionalInt(): Int? {
    val normalized = trim().replace(",", "")
    if (normalized.isEmpty()) {
        return null
    }
    return normalized.toIntOrNull()
}

private fun String.toOptionalText(): String? {
    val normalized = trim()
    return if (normalized.isEmpty()) null else normalized
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResaleTradeInputScreen(
    isSubmitting: Boolean,
    onSubmitAfterPurchase: (productId: String?, url: String?, updates: Map<String, Any?>) -> Unit,
    onSubmitAfterResale: (productId: String?, url: String?, updates: Map<String, Any?>) -> Unit,
) {
    var inputMode by remember { mutableStateOf(ResaleInputMode.AFTER_PURCHASE) }

    var productId by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }

    var purchasedAt by remember { mutableStateOf("") }
    var purchasePriceKrw by remember { mutableStateOf("") }
    var purchaseMethod by remember { mutableStateOf("") }
    var purchaseLocation by remember { mutableStateOf("") }
    var cpuCoreCount by remember { mutableStateOf("") }
    var gpuCoreCount by remember { mutableStateOf("") }
    var batteryHealthPercent by remember { mutableStateOf("") }
    var batteryCycleCount by remember { mutableStateOf("") }
    var inspectionNotes by remember { mutableStateOf("") }
    var resaleListingCreatedAt by remember { mutableStateOf("") }
    var resaleListingPriceKrw by remember { mutableStateOf("") }
    var resaleUrl by remember { mutableStateOf("") }

    var soldAt by remember { mutableStateOf("") }
    var salePriceKrw by remember { mutableStateOf("") }
    var saleMethod by remember { mutableStateOf("") }
    var saleLocation by remember { mutableStateOf("") }
    var finalShippingCostKrw by remember { mutableStateOf("") }
    var platformFeeKrw by remember { mutableStateOf("") }
    var viewCount by remember { mutableStateOf("") }
    var inquiryCount by remember { mutableStateOf("") }
    var finalResultNotes by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "거래 입력",
            style = MaterialTheme.typography.titleLarge,
        )
        Text(
            text = "앱에서 바로 입력하면 서버 DB에 저장됩니다.",
            style = MaterialTheme.typography.bodySmall,
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = inputMode == ResaleInputMode.AFTER_PURCHASE,
                onClick = { inputMode = ResaleInputMode.AFTER_PURCHASE },
                label = { Text("구매 후 입력") },
            )
            FilterChip(
                selected = inputMode == ResaleInputMode.AFTER_RESALE,
                onClick = { inputMode = ResaleInputMode.AFTER_RESALE },
                label = { Text("되팔이 후 입력") },
            )
        }

        OutlinedTextField(
            value = productId,
            onValueChange = { productId = it },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting,
            singleLine = true,
            label = { Text("product_id (권장)") },
            placeholder = { Text("예: 123456789") },
        )
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting,
            singleLine = true,
            label = { Text("url (product_id 없을 때 필수)") },
            placeholder = { Text("https://web.joongna.com/product/...") },
        )

        if (inputMode == ResaleInputMode.AFTER_PURCHASE) {
            OutlinedTextField(
                value = purchasedAt,
                onValueChange = { purchasedAt = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("구매 시각") },
                placeholder = { Text("YYYY-MM-DD HH:MM") },
            )
            OutlinedTextField(
                value = purchasePriceKrw,
                onValueChange = { purchasePriceKrw = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("구매 금액(원)") },
            )
            OutlinedTextField(
                value = purchaseMethod,
                onValueChange = { purchaseMethod = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("구매 방식") },
                placeholder = { Text("직거래 / 택배") },
            )
            OutlinedTextField(
                value = purchaseLocation,
                onValueChange = { purchaseLocation = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("구매 장소") },
            )
            OutlinedTextField(
                value = cpuCoreCount,
                onValueChange = { cpuCoreCount = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("CPU 코어 수") },
            )
            OutlinedTextField(
                value = gpuCoreCount,
                onValueChange = { gpuCoreCount = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("GPU 코어 수") },
            )
            OutlinedTextField(
                value = batteryHealthPercent,
                onValueChange = { batteryHealthPercent = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("배터리 효율(%)") },
            )
            OutlinedTextField(
                value = batteryCycleCount,
                onValueChange = { batteryCycleCount = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("배터리 사이클") },
            )
            OutlinedTextField(
                value = inspectionNotes,
                onValueChange = { inspectionNotes = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                label = { Text("검수 메모") },
            )
            OutlinedTextField(
                value = resaleListingCreatedAt,
                onValueChange = { resaleListingCreatedAt = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("재판매 글 업로드 시각") },
                placeholder = { Text("YYYY-MM-DD HH:MM") },
            )
            OutlinedTextField(
                value = resaleListingPriceKrw,
                onValueChange = { resaleListingPriceKrw = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("재판매 시작가(원)") },
            )
            OutlinedTextField(
                value = resaleUrl,
                onValueChange = { resaleUrl = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("재판매 URL") },
            )

            Button(
                onClick = {
                    val updates = mapOf(
                        "purchased_at" to purchasedAt.toOptionalText(),
                        "purchase_price_krw" to purchasePriceKrw.toOptionalInt(),
                        "purchase_method" to purchaseMethod.toOptionalText(),
                        "purchase_location" to purchaseLocation.toOptionalText(),
                        "cpu_core_count" to cpuCoreCount.toOptionalInt(),
                        "gpu_core_count" to gpuCoreCount.toOptionalInt(),
                        "battery_health_percent" to batteryHealthPercent.toOptionalInt(),
                        "battery_cycle_count" to batteryCycleCount.toOptionalInt(),
                        "inspection_notes" to inspectionNotes.toOptionalText(),
                        "resale_listing_created_at" to resaleListingCreatedAt.toOptionalText(),
                        "resale_listing_price_krw" to resaleListingPriceKrw.toOptionalInt(),
                        "resale_url" to resaleUrl.toOptionalText(),
                    )
                    onSubmitAfterPurchase(
                        productId = productId.toOptionalText(),
                        url = url.toOptionalText(),
                        updates = updates,
                    )
                },
                enabled = !isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("구매 후 저장")
                }
            }
        } else {
            OutlinedTextField(
                value = soldAt,
                onValueChange = { soldAt = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("판매 완료 시각") },
                placeholder = { Text("YYYY-MM-DD HH:MM") },
            )
            OutlinedTextField(
                value = salePriceKrw,
                onValueChange = { salePriceKrw = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("최종 판매 금액(원)") },
            )
            OutlinedTextField(
                value = saleMethod,
                onValueChange = { saleMethod = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("판매 방식") },
                placeholder = { Text("직거래 / 택배") },
            )
            OutlinedTextField(
                value = saleLocation,
                onValueChange = { saleLocation = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("판매 장소") },
            )
            OutlinedTextField(
                value = finalShippingCostKrw,
                onValueChange = { finalShippingCostKrw = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("최종 배송비(원)") },
            )
            OutlinedTextField(
                value = platformFeeKrw,
                onValueChange = { platformFeeKrw = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("플랫폼 수수료(원)") },
            )
            OutlinedTextField(
                value = viewCount,
                onValueChange = { viewCount = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("조회수") },
            )
            OutlinedTextField(
                value = inquiryCount,
                onValueChange = { inquiryCount = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("문의수") },
            )
            OutlinedTextField(
                value = finalResultNotes,
                onValueChange = { finalResultNotes = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                label = { Text("최종 정산 메모") },
            )

            Button(
                onClick = {
                    val updates = mapOf(
                        "sold_at" to soldAt.toOptionalText(),
                        "sale_price_krw" to salePriceKrw.toOptionalInt(),
                        "sale_method" to saleMethod.toOptionalText(),
                        "sale_location" to saleLocation.toOptionalText(),
                        "final_shipping_cost_krw" to finalShippingCostKrw.toOptionalInt(),
                        "platform_fee_krw" to platformFeeKrw.toOptionalInt(),
                        "view_count" to viewCount.toOptionalInt(),
                        "inquiry_count" to inquiryCount.toOptionalInt(),
                        "final_result_notes" to finalResultNotes.toOptionalText(),
                    )
                    onSubmitAfterResale(
                        productId = productId.toOptionalText(),
                        url = url.toOptionalText(),
                        updates = updates,
                    )
                },
                enabled = !isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("되팔이 후 저장")
                }
            }
        }

        Spacer(modifier = Modifier.height(40.dp))
    }
}
