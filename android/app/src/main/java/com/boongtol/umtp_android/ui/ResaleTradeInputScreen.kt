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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
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

private val AUTO_DISABLED_FIELDS = listOf(
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
    "image_urls",
    "body_text",
    "product_type",
    "chip",
    "screen_inch",
    "ram_gb",
    "ssd_gb",
    "fair_price_krw",
    "discount_rate_percent",
    "expected_profit_krw",
    "risk_score",
    "reason_tags",
    "created_at",
    "updated_at",
    "total_cost_krw",
    "gross_profit_krw",
    "net_profit_krw",
    "roi_percent",
    "purchase_speed_minutes",
    "sale_duration_hours",
    "total_holding_time_hours",
    "profit_per_day_krw",
    "response_time_minutes",
    "first_inquiry_delay_minutes",
)

private val PURCHASE_INPUT_FIELDS = listOf(
    "contacted_at",
    "seller_response_at",
    "purchase_contact_record",
    "purchase_conversation_text",
    "purchased_at",
    "purchase_method",
    "purchase_location",
    "purchase_price_krw",
    "transport_cost_krw",
    "shipping_cost_krw",
    "payment_method",
    "money_sent_at",
    "purchase_account_number",
    "inspection_notes",
    "final_result_notes",
    "current_stage",
)

private val RESALE_INPUT_FIELDS = listOf(
    "resale_listing_created_at",
    "resale_platform",
    "resale_url",
    "resale_product_id",
    "initial_resale_price_krw",
    "resale_listing_price_krw",
    "minimum_accept_price_krw",
    "resale_contact_record",
    "resale_conversation_text",
    "buyer_nickname",
    "sale_method",
    "sale_location",
    "sold_at",
    "sale_price_krw",
    "money_received_at",
    "resale_account_number",
    "sale_platform",
    "final_shipping_cost_krw",
    "platform_fee_krw",
    "refund_or_claim",
    "final_result_notes",
    "current_stage",
)

private val ALL_MANUAL_FIELDS = (PURCHASE_INPUT_FIELDS + RESALE_INPUT_FIELDS).distinct()

private val INT_INPUT_FIELDS = setOf(
    "purchase_price_krw",
    "transport_cost_krw",
    "shipping_cost_krw",
    "resale_listing_price_krw",
    "minimum_accept_price_krw",
    "initial_resale_price_krw",
    "sale_price_krw",
    "final_shipping_cost_krw",
    "platform_fee_krw",
)

private val BOOL_INPUT_FIELDS = emptySet<String>()

private fun parseInputValue(field: String, rawValue: String): Any? {
    val normalized = rawValue.trim()
    if (normalized.isEmpty()) {
        return null
    }

    if (field in INT_INPUT_FIELDS) {
        return normalized.replace(",", "").toIntOrNull()
    }

    if (field in BOOL_INPUT_FIELDS) {
        return when (normalized.lowercase()) {
            "1", "true", "yes", "y", "on" -> true
            "0", "false", "no", "n", "off" -> false
            else -> normalized
        }
    }

    return normalized
}

private fun buildManualUpdates(fields: List<String>, values: Map<String, String>): Map<String, Any?> {
    val updates = mutableMapOf<String, Any?>()
    fields.forEach { field ->
        val parsed = parseInputValue(field, values[field] ?: "")
        if (parsed != null) {
            updates[field] = parsed
        }
    }
    return updates
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

private fun buildJourneyValueMap(row: ResaleTradeJourneyRow?): Map<String, String> {
    if (row == null) {
        return emptyMap()
    }

    val jsonObject = Gson().toJsonTree(row).asJsonObject
    val result = mutableMapOf<String, String>()
    jsonObject.entrySet().forEach { (key, element) ->
        val value = formatStoredElement(element)
        if (value != null) {
            result[key] = value
        }
    }
    return result
}

@Composable
private fun ReadOnlyFieldCard(
    rowValues: Map<String, String>,
) {
    Text(text = "자동채움 정보", style = MaterialTheme.typography.titleMedium)

    val visibleReadonlyFields = AUTO_DISABLED_FIELDS
        .filter { key -> !rowValues[key].isNullOrBlank() }

    if (visibleReadonlyFields.isEmpty()) {
        Text(text = "source + product_id 조회 후 자동채움 정보를 표시합니다.")
        return
    }

    visibleReadonlyFields.forEach { key ->
        OutlinedTextField(
            value = rowValues[key] ?: "",
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            enabled = false,
            label = { Text("$key (자동채움)") },
            singleLine = !key.endsWith("_text"),
        )
    }
}

@Composable
private fun EditableFieldList(
    fields: List<String>,
    values: MutableMap<String, String>,
    isSubmitting: Boolean,
) {
    fields.forEach { key ->
        OutlinedTextField(
            value = values[key] ?: "",
            onValueChange = { values[key] = it },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting,
            label = { Text(key) },
            singleLine = !key.endsWith("_text"),
        )
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

    val manualInputs = remember { mutableStateMapOf<String, String>() }
    val journeyValueMap = remember(selectedJourney) { buildJourneyValueMap(selectedJourney) }

    LaunchedEffect(selectedJourney?.id) {
        manualInputs.clear()
        ALL_MANUAL_FIELDS.forEach { field ->
            journeyValueMap[field]?.let { manualInputs[field] = it }
        }
    }

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
            text = "source + product_id 조회 후 자동채움 정보를 확인하고, 필요한 값만 입력해 저장합니다.",
            style = MaterialTheme.typography.bodySmall,
        )

        Text(text = "source + product_id 조회", style = MaterialTheme.typography.titleMedium)

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

        ReadOnlyFieldCard(
            rowValues = journeyValueMap,
        )

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = inputMode == ResaleInputMode.PURCHASE,
                onClick = { inputMode = ResaleInputMode.PURCHASE },
                label = { Text("구매 후 기록") },
            )
            FilterChip(
                selected = inputMode == ResaleInputMode.RESALE,
                onClick = { inputMode = ResaleInputMode.RESALE },
                label = { Text("되팔이 후 기록") },
            )
        }

        if (inputMode == ResaleInputMode.PURCHASE) {
            Text(text = "구매 후 기록 입력", style = MaterialTheme.typography.titleMedium)
            EditableFieldList(
                fields = PURCHASE_INPUT_FIELDS,
                values = manualInputs,
                isSubmitting = isSubmitting,
            )

            Button(
                onClick = {
                    onSubmitPurchase(buildManualUpdates(PURCHASE_INPUT_FIELDS, manualInputs))
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
            Text(text = "되팔이 후 기록 입력", style = MaterialTheme.typography.titleMedium)
            EditableFieldList(
                fields = RESALE_INPUT_FIELDS,
                values = manualInputs,
                isSubmitting = isSubmitting,
            )

            Button(
                onClick = {
                    val updates = buildManualUpdates(RESALE_INPUT_FIELDS, manualInputs)
                    onSubmitResale(updates)
                },
                enabled = !isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("되팔이 후 기록 저장")
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
