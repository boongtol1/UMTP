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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.boongtol.umtp_android.network.ResaleTradeJourneyRow
import com.google.gson.Gson
import com.google.gson.JsonElement

private enum class ResaleInputMode {
    PURCHASE,
    RESALE,
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

private fun formatWon(value: Int?): String {
    if (value == null) {
        return "-"
    }
    return "%,d".format(value)
}

private val RESALE_JOURNEY_ALL_COLUMNS = listOf(
    "id",
    "user_id",
    "source",
    "product_id",
    "url",
    "url_digest",
    "title",
    "listing_created_at",
    "discovered_at",
    "listing_price_krw",
    "seller_nickname",
    "seller_shop_id",
    "seller_location",
    "image_urls",
    "body_text",
    "product_type",
    "chip",
    "screen_inch",
    "ram_gb",
    "ssd_gb",
    "color",
    "keyboard_layout",
    "fair_price_krw",
    "discount_rate_percent",
    "expected_profit_krw",
    "risk_score",
    "reason_tags",
    "contacted_at",
    "seller_response_at",
    "response_time_minutes",
    "seller_answer_text",
    "negotiable",
    "seller_tone",
    "suspicious_points",
    "confirmed_price_krw",
    "decision_at",
    "decision_result",
    "decision_reason",
    "target_purchase_price_krw",
    "expected_sale_price_krw",
    "expected_net_profit_krw",
    "expected_sale_duration_days",
    "purchased_at",
    "purchase_price_krw",
    "purchase_method",
    "purchase_location",
    "transport_cost_krw",
    "shipping_cost_krw",
    "total_cost_krw",
    "payment_method",
    "serial_number",
    "model_number",
    "applecare_status",
    "activation_lock_off",
    "mdm_lock_none",
    "cpu_core_count",
    "gpu_core_count",
    "battery_health_percent",
    "battery_cycle_count",
    "battery_condition",
    "truetone_ok",
    "display_condition",
    "keyboard_condition",
    "trackpad_condition",
    "speaker_condition",
    "camera_condition",
    "wifi_bluetooth_ok",
    "exterior_grade",
    "included_items",
    "repair_suspected",
    "inspection_notes",
    "cleaned_at",
    "photo_taken_at",
    "resale_title",
    "resale_body_text",
    "resale_photo_count",
    "resale_listing_price_krw",
    "minimum_accept_price_krw",
    "resale_platform",
    "resale_strategy_notes",
    "resale_listing_created_at",
    "resale_url",
    "resale_product_id",
    "initial_resale_price_krw",
    "upload_time_slot",
    "view_count",
    "favorite_count",
    "inquiry_count",
    "first_inquiry_at",
    "first_inquiry_delay_minutes",
    "negotiation_count",
    "price_drop_count",
    "price_drop_history",
    "buyer_questions",
    "common_objections",
    "sold_at",
    "sale_price_krw",
    "buyer_nickname",
    "sale_method",
    "sale_location",
    "sale_platform",
    "final_shipping_cost_krw",
    "platform_fee_krw",
    "refund_or_claim",
    "gross_profit_krw",
    "net_profit_krw",
    "roi_percent",
    "purchase_speed_minutes",
    "sale_duration_hours",
    "total_holding_time_hours",
    "profit_per_day_krw",
    "final_result_notes",
    "current_stage",
    "created_at",
    "updated_at",
)

private fun buildAdditionalColumnUpdates(values: Map<String, String>): Map<String, Any?> {
    return RESALE_JOURNEY_ALL_COLUMNS
        .mapNotNull { key ->
            val text = values[key]?.toOptionalText() ?: return@mapNotNull null
            key to text
        }
        .toMap()
}

private fun formatStoredElement(element: JsonElement): String? {
    if (element.isJsonNull) {
        return null
    }
    if (element.isJsonPrimitive) {
        val primitive = element.asJsonPrimitive
        val value = if (primitive.isString) primitive.asString else primitive.toString()
        val normalized = value.trim()
        return if (normalized.isEmpty()) null else normalized
    }
    val normalized = element.toString().trim()
    return if (normalized.isEmpty() || normalized == "[]" || normalized == "{}") null else normalized
}

private fun buildStoredJourneyRows(row: ResaleTradeJourneyRow?): List<Pair<String, String>> {
    if (row == null) {
        return emptyList()
    }
    val jsonObject = Gson().toJsonTree(row).asJsonObject
    return RESALE_JOURNEY_ALL_COLUMNS.mapNotNull { key ->
        val element = jsonObject.get(key) ?: return@mapNotNull null
        val text = formatStoredElement(element) ?: return@mapNotNull null
        key to text
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResaleTradeInputScreen(
    selectedJourney: ResaleTradeJourneyRow?,
    completedJourneys: List<ResaleTradeJourneyRow>,
    isSubmitting: Boolean,
    isLoadingCompleted: Boolean,
    onCreateFromProduct: (source: String, productId: String) -> Unit,
    onSubmitPurchase: (updates: Map<String, Any?>) -> Unit,
    onSubmitResale: (updates: Map<String, Any?>) -> Unit,
    onSubmitSold: (updates: Map<String, Any?>) -> Unit,
    onLoadCompleted: () -> Unit,
    onDeleteSelectedCompleted: (Set<Long>) -> Unit,
    onDeleteAllCompleted: () -> Unit,
) {
    var selectedSource by remember { mutableStateOf("joongna") }
    var customSource by remember { mutableStateOf("") }
    var productId by remember { mutableStateOf("") }

    var inputMode by remember { mutableStateOf(ResaleInputMode.PURCHASE) }
    var showAdvancedPurchase by remember { mutableStateOf(false) }

    var purchasePriceKrw by remember { mutableStateOf("") }
    var purchasedAt by remember { mutableStateOf("") }
    var batteryHealthPercent by remember { mutableStateOf("") }
    var batteryCycleCount by remember { mutableStateOf("") }
    var exteriorGrade by remember { mutableStateOf("") }
    var includedItems by remember { mutableStateOf("") }
    var inspectionNotes by remember { mutableStateOf("") }

    var truetoneOk by remember { mutableStateOf("") }
    var purchaseMethod by remember { mutableStateOf("") }
    var purchaseLocation by remember { mutableStateOf("") }
    var transportCostKrw by remember { mutableStateOf("") }
    var shippingCostKrw by remember { mutableStateOf("") }
    var paymentMethod by remember { mutableStateOf("") }
    var serialNumber by remember { mutableStateOf("") }
    var modelNumber by remember { mutableStateOf("") }
    var applecareStatus by remember { mutableStateOf("") }
    var activationLockOff by remember { mutableStateOf("") }
    var mdmLockNone by remember { mutableStateOf("") }
    var batteryCondition by remember { mutableStateOf("") }
    var displayCondition by remember { mutableStateOf("") }
    var keyboardCondition by remember { mutableStateOf("") }
    var trackpadCondition by remember { mutableStateOf("") }
    var speakerCondition by remember { mutableStateOf("") }
    var cameraCondition by remember { mutableStateOf("") }
    var wifiBluetoothOk by remember { mutableStateOf("") }
    var repairSuspected by remember { mutableStateOf("") }

    var resaleListingPriceKrw by remember { mutableStateOf("") }
    var resalePlatform by remember { mutableStateOf("") }
    var resaleUrl by remember { mutableStateOf("") }
    var resaleListingCreatedAt by remember { mutableStateOf("") }
    var soldAt by remember { mutableStateOf("") }
    var salePriceKrw by remember { mutableStateOf("") }
    var finalShippingCostKrw by remember { mutableStateOf("") }
    var platformFeeKrw by remember { mutableStateOf("") }
    var finalResultNotes by remember { mutableStateOf("") }

    var showAdditionalInputs by remember { mutableStateOf(false) }
    val additionalFieldValues = remember { mutableStateMapOf<String, String>() }

    var selectedCompletedIds by remember { mutableStateOf(setOf<Long>()) }

    val sourceOptions = listOf("joongna", "bunjang", "daangn", "기타")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "거래 기록",
            style = MaterialTheme.typography.titleLarge,
        )
        Text(
            text = "상품번호만 입력하면 기존 UMTP 기록에서 최대한 자동으로 채웁니다.",
            style = MaterialTheme.typography.bodySmall,
        )

        Text(text = "상품번호로 거래 기록 만들기", style = MaterialTheme.typography.titleMedium)

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            sourceOptions.forEach { option ->
                FilterChip(
                    selected = selectedSource == option,
                    onClick = { selectedSource = option },
                    label = { Text(option) },
                )
            }
        }

        if (selectedSource == "기타") {
            OutlinedTextField(
                value = customSource,
                onValueChange = { customSource = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("기타 source") },
                placeholder = { Text("예: naver-cafe") },
            )
        }

        OutlinedTextField(
            value = productId,
            onValueChange = { productId = it },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting,
            singleLine = true,
            label = { Text("product_id") },
            placeholder = { Text("예: 228826879") },
        )

        Button(
            onClick = {
                val sourceValue = if (selectedSource == "기타") customSource.toOptionalText() else selectedSource
                onCreateFromProduct(sourceValue ?: "", productId)
            },
            enabled = !isSubmitting,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (isSubmitting) {
                CircularProgressIndicator(strokeWidth = 2.dp)
            } else {
                Text("자동으로 불러오기")
            }
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        val storedRows = buildStoredJourneyRows(selectedJourney)
        Text(text = "저장값 조회 (실제 저장된 값만)", style = MaterialTheme.typography.titleMedium)
        if (storedRows.isEmpty()) {
            Text(text = "저장된 값이 없습니다.")
        } else {
            storedRows.forEach { (key, value) ->
                Text(text = "$key: $value")
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = inputMode == ResaleInputMode.PURCHASE,
                onClick = { inputMode = ResaleInputMode.PURCHASE },
                label = { Text("구매 후 기록하기") },
            )
            FilterChip(
                selected = inputMode == ResaleInputMode.RESALE,
                onClick = { inputMode = ResaleInputMode.RESALE },
                label = { Text("되팔이 후 기록하기") },
            )
        }

        FilterChip(
            selected = showAdditionalInputs,
            onClick = { showAdditionalInputs = !showAdditionalInputs },
            label = { Text(if (showAdditionalInputs) "추가 컬럼 입력 접기" else "추가 컬럼 입력 열기") },
        )

        if (showAdditionalInputs) {
            Text(
                text = "전체 컬럼을 개별 입력칸으로 입력합니다. 빈칸은 전송되지 않습니다.",
                style = MaterialTheme.typography.bodySmall,
            )
            RESALE_JOURNEY_ALL_COLUMNS.forEach { key ->
                OutlinedTextField(
                    value = additionalFieldValues[key] ?: "",
                    onValueChange = { additionalFieldValues[key] = it },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !isSubmitting,
                    label = { Text(key) },
                    singleLine = !key.endsWith("_text"),
                )
            }
        }

        if (inputMode == ResaleInputMode.PURCHASE) {
            OutlinedTextField(
                value = purchasePriceKrw,
                onValueChange = { purchasePriceKrw = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("purchase_price_krw") },
            )
            OutlinedTextField(
                value = purchasedAt,
                onValueChange = { purchasedAt = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("purchased_at") },
                placeholder = { Text("YYYY-MM-DD HH:MM") },
            )
            OutlinedTextField(
                value = batteryHealthPercent,
                onValueChange = { batteryHealthPercent = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("battery_health_percent") },
            )
            OutlinedTextField(
                value = batteryCycleCount,
                onValueChange = { batteryCycleCount = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("battery_cycle_count") },
            )
            OutlinedTextField(
                value = exteriorGrade,
                onValueChange = { exteriorGrade = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                singleLine = true,
                label = { Text("exterior_grade") },
            )
            OutlinedTextField(
                value = includedItems,
                onValueChange = { includedItems = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                label = { Text("included_items") },
            )
            OutlinedTextField(
                value = inspectionNotes,
                onValueChange = { inspectionNotes = it },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSubmitting,
                label = { Text("inspection_notes") },
            )

            FilterChip(
                selected = showAdvancedPurchase,
                onClick = { showAdvancedPurchase = !showAdvancedPurchase },
                label = { Text(if (showAdvancedPurchase) "고급 입력 접기" else "고급 입력 열기") },
            )

            if (showAdvancedPurchase) {
                OutlinedTextField(value = truetoneOk, onValueChange = { truetoneOk = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("truetone_ok (true/false)") })
                OutlinedTextField(value = purchaseMethod, onValueChange = { purchaseMethod = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("purchase_method") })
                OutlinedTextField(value = purchaseLocation, onValueChange = { purchaseLocation = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("purchase_location") })
                OutlinedTextField(value = transportCostKrw, onValueChange = { transportCostKrw = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("transport_cost_krw") })
                OutlinedTextField(value = shippingCostKrw, onValueChange = { shippingCostKrw = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("shipping_cost_krw") })
                OutlinedTextField(value = paymentMethod, onValueChange = { paymentMethod = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("payment_method") })
                OutlinedTextField(value = serialNumber, onValueChange = { serialNumber = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("serial_number") })
                OutlinedTextField(value = modelNumber, onValueChange = { modelNumber = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("model_number") })
                OutlinedTextField(value = applecareStatus, onValueChange = { applecareStatus = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("applecare_status") })
                OutlinedTextField(value = activationLockOff, onValueChange = { activationLockOff = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("activation_lock_off (true/false)") })
                OutlinedTextField(value = mdmLockNone, onValueChange = { mdmLockNone = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("mdm_lock_none (true/false)") })
                OutlinedTextField(value = batteryCondition, onValueChange = { batteryCondition = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("battery_condition") })
                OutlinedTextField(value = displayCondition, onValueChange = { displayCondition = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("display_condition") })
                OutlinedTextField(value = keyboardCondition, onValueChange = { keyboardCondition = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("keyboard_condition") })
                OutlinedTextField(value = trackpadCondition, onValueChange = { trackpadCondition = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("trackpad_condition") })
                OutlinedTextField(value = speakerCondition, onValueChange = { speakerCondition = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("speaker_condition") })
                OutlinedTextField(value = cameraCondition, onValueChange = { cameraCondition = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("camera_condition") })
                OutlinedTextField(value = wifiBluetoothOk, onValueChange = { wifiBluetoothOk = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("wifi_bluetooth_ok (true/false)") })
                OutlinedTextField(value = repairSuspected, onValueChange = { repairSuspected = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("repair_suspected (true/false)") })
            }

            Button(
                onClick = {
                    val mergedUpdates = mutableMapOf<String, Any?>()
                    mergedUpdates.putAll(buildAdditionalColumnUpdates(additionalFieldValues))
                    mergedUpdates.putAll(
                        mapOf(
                            "purchase_price_krw" to purchasePriceKrw.toOptionalInt(),
                            "purchased_at" to purchasedAt.toOptionalText(),
                            "battery_health_percent" to batteryHealthPercent.toOptionalInt(),
                            "battery_cycle_count" to batteryCycleCount.toOptionalInt(),
                            "exterior_grade" to exteriorGrade.toOptionalText(),
                            "included_items" to includedItems.toOptionalText(),
                            "inspection_notes" to inspectionNotes.toOptionalText(),
                            "truetone_ok" to truetoneOk.toOptionalText(),
                            "purchase_method" to purchaseMethod.toOptionalText(),
                            "purchase_location" to purchaseLocation.toOptionalText(),
                            "transport_cost_krw" to transportCostKrw.toOptionalInt(),
                            "shipping_cost_krw" to shippingCostKrw.toOptionalInt(),
                            "payment_method" to paymentMethod.toOptionalText(),
                            "serial_number" to serialNumber.toOptionalText(),
                            "model_number" to modelNumber.toOptionalText(),
                            "applecare_status" to applecareStatus.toOptionalText(),
                            "activation_lock_off" to activationLockOff.toOptionalText(),
                            "mdm_lock_none" to mdmLockNone.toOptionalText(),
                            "battery_condition" to batteryCondition.toOptionalText(),
                            "display_condition" to displayCondition.toOptionalText(),
                            "keyboard_condition" to keyboardCondition.toOptionalText(),
                            "trackpad_condition" to trackpadCondition.toOptionalText(),
                            "speaker_condition" to speakerCondition.toOptionalText(),
                            "camera_condition" to cameraCondition.toOptionalText(),
                            "wifi_bluetooth_ok" to wifiBluetoothOk.toOptionalText(),
                            "repair_suspected" to repairSuspected.toOptionalText(),
                        )
                    )

                    onSubmitPurchase(
                        mergedUpdates
                    )
                },
                enabled = !isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("구매 후 기록 저장")
                }
            }
        } else {
            OutlinedTextField(value = resaleListingPriceKrw, onValueChange = { resaleListingPriceKrw = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("resale_listing_price_krw") })
            OutlinedTextField(value = resalePlatform, onValueChange = { resalePlatform = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("resale_platform") })
            OutlinedTextField(value = resaleUrl, onValueChange = { resaleUrl = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("resale_url") })
            OutlinedTextField(value = resaleListingCreatedAt, onValueChange = { resaleListingCreatedAt = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("resale_listing_created_at") }, placeholder = { Text("YYYY-MM-DD HH:MM") })

            Button(
                onClick = {
                    val mergedUpdates = mutableMapOf<String, Any?>()
                    mergedUpdates.putAll(buildAdditionalColumnUpdates(additionalFieldValues))
                    mergedUpdates.putAll(
                        mapOf(
                            "resale_listing_price_krw" to resaleListingPriceKrw.toOptionalInt(),
                            "resale_platform" to resalePlatform.toOptionalText(),
                            "resale_url" to resaleUrl.toOptionalText(),
                            "resale_listing_created_at" to resaleListingCreatedAt.toOptionalText(),
                        )
                    )

                    onSubmitResale(
                        mergedUpdates
                    )
                },
                enabled = !isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("되팔이 후 기록 저장")
            }

            OutlinedTextField(value = soldAt, onValueChange = { soldAt = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("sold_at") }, placeholder = { Text("YYYY-MM-DD HH:MM") })
            OutlinedTextField(value = salePriceKrw, onValueChange = { salePriceKrw = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("sale_price_krw") })
            OutlinedTextField(value = finalShippingCostKrw, onValueChange = { finalShippingCostKrw = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("final_shipping_cost_krw") })
            OutlinedTextField(value = platformFeeKrw, onValueChange = { platformFeeKrw = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, singleLine = true, label = { Text("platform_fee_krw") })
            OutlinedTextField(value = finalResultNotes, onValueChange = { finalResultNotes = it }, modifier = Modifier.fillMaxWidth(), enabled = !isSubmitting, label = { Text("final_result_notes") })

            Button(
                onClick = {
                    val mergedUpdates = mutableMapOf<String, Any?>()
                    mergedUpdates.putAll(buildAdditionalColumnUpdates(additionalFieldValues))
                    mergedUpdates.putAll(
                        mapOf(
                            "sold_at" to soldAt.toOptionalText(),
                            "sale_price_krw" to salePriceKrw.toOptionalInt(),
                            "final_shipping_cost_krw" to finalShippingCostKrw.toOptionalInt(),
                            "platform_fee_krw" to platformFeeKrw.toOptionalInt(),
                            "final_result_notes" to finalResultNotes.toOptionalText(),
                        )
                    )

                    onSubmitSold(
                        mergedUpdates
                    )
                },
                enabled = !isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("판매 완료 저장")
                }
            }
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        Text(text = "완료된 거래", style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = onLoadCompleted,
                enabled = !isLoadingCompleted,
            ) {
                if (isLoadingCompleted) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("목록 새로고침")
                }
            }
            Button(
                onClick = { onDeleteSelectedCompleted(selectedCompletedIds) },
                enabled = selectedCompletedIds.isNotEmpty(),
            ) {
                Text("선택 삭제")
            }
            Button(onClick = onDeleteAllCompleted) {
                Text("전체 삭제")
            }
        }

        completedJourneys.forEach { item ->
            val itemId = item.id ?: return@forEach
            val selected = selectedCompletedIds.contains(itemId)
            FilterChip(
                selected = selected,
                onClick = {
                    selectedCompletedIds = if (selected) {
                        selectedCompletedIds - itemId
                    } else {
                        selectedCompletedIds + itemId
                    }
                },
                label = {
                    Text(
                        "#${item.id} ${item.title ?: "(제목없음)"} / ${formatWon(item.sale_price_krw)} / ROI ${item.roi_percent ?: "-"}%"
                    )
                },
            )
        }

        Spacer(modifier = Modifier.height(40.dp))
    }
}
