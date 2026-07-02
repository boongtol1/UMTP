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

private fun formatWon(value: Int?): String {
    if (value == null) {
        return "-"
    }
    return "%,d".format(value)
}

private data class LabeledInputField(
    val key: String,
    val label: String,
    val helperText: String? = null,
    val trueLabel: String? = null,
    val falseLabel: String? = null,
)

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

private val PRODUCT_BASE_SPEC_FIELDS = listOf(
    LabeledInputField("product_type", "제품 기본 스펙 - 제품 유형"),
    LabeledInputField("chip", "제품 기본 스펙 - 칩"),
    LabeledInputField("screen_inch", "제품 기본 스펙 - 화면 크기(인치)"),
    LabeledInputField("ram_gb", "제품 기본 스펙 - RAM (GB)"),
    LabeledInputField("ssd_gb", "제품 기본 스펙 - SSD (GB)"),
)

private val EXACT_VERIFICATION_FIELDS = listOf(
    LabeledInputField("serial_number", "일련번호"),
    LabeledInputField("model_number", "정확한 모델번호"),
    LabeledInputField("cpu_core_count", "CPU 코어 수"),
    LabeledInputField("gpu_core_count", "GPU 코어 수"),
    LabeledInputField("battery_cycle_count", "배터리 사이클 수"),
    LabeledInputField("battery_health_percent", "배터리 성능 최대치 %"),
    LabeledInputField("applecare_status", "AppleCare 상태"),
    LabeledInputField(
        "activation_lock_off",
        "활성화 잠금 해제 확인",
        "이전 Apple ID 잠금 없음",
        trueLabel = "잠금 없음",
        falseLabel = "잠금 있음",
    ),
    LabeledInputField(
        "mdm_lock_none",
        "MDM 잠금 없음 확인",
        "회사/학교 관리 기기 아님",
        trueLabel = "MDM 없음",
        falseLabel = "MDM 있음",
    ),
)

private val EXACT_VERIFICATION_FIELD_KEYS = EXACT_VERIFICATION_FIELDS.map { it.key }

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
    "sale_platform",
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
    "final_shipping_cost_krw",
    "platform_fee_krw",
    "refund_or_claim",
    "final_result_notes",
    "current_stage",
)

private val ALL_MANUAL_FIELDS = (PURCHASE_INPUT_FIELDS + RESALE_INPUT_FIELDS + EXACT_VERIFICATION_FIELD_KEYS).distinct()

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
    "cpu_core_count",
    "gpu_core_count",
    "battery_cycle_count",
    "battery_health_percent",
)

private val BOOL_INPUT_FIELDS = setOf(
    "activation_lock_off",
    "mdm_lock_none",
)

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

private fun buildManualUpdates(
    fields: List<String>,
    values: Map<String, String>,
    baselineValues: Map<String, String> = emptyMap(),
): Map<String, Any?> {
    val updates = mutableMapOf<String, Any?>()
    fields.forEach { field ->
        val parsed = parseInputValue(field, values[field] ?: "")
        if (parsed != null) {
            val baselineParsed = parseInputValue(field, baselineValues[field] ?: "")
            if (baselineParsed == parsed) {
                return@forEach
            }
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
private fun ProductBaseSpecCard(
    rowValues: Map<String, String>,
) {
    Text(text = "제품 기본 스펙", style = MaterialTheme.typography.titleMedium)

    val visibleFields = PRODUCT_BASE_SPEC_FIELDS
        .filter { field -> !rowValues[field.key].isNullOrBlank() }

    if (visibleFields.isEmpty()) {
        Text(text = "자동 파싱된 제품 기본 스펙이 아직 없습니다.")
        return
    }

    visibleFields.forEach { field ->
        OutlinedTextField(
            value = rowValues[field.key] ?: "",
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            enabled = false,
            label = { Text(field.label) },
            singleLine = true,
        )
    }
}

@Composable
private fun ReadOnlyFieldCard(
    rowValues: Map<String, String>,
) {
    Text(text = "자동채움 정보", style = MaterialTheme.typography.titleMedium)

    val baseSpecKeys = PRODUCT_BASE_SPEC_FIELDS.map { it.key }.toSet()
    val hiddenIdentityKeys = setOf("source", "product_id")
    val visibleReadonlyFields = AUTO_DISABLED_FIELDS
        .filterNot { it in hiddenIdentityKeys }
        .filterNot { it in baseSpecKeys }
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
private fun ExactVerificationInputSection(
    values: MutableMap<String, String>,
    isSubmitting: Boolean,
) {
    Text(text = "정확 확인 정보", style = MaterialTheme.typography.titleMedium)
    Text(
        text = "판매자에게 직접 확인한 정보만 입력하세요. 모르는 경우 비워둘 수 있습니다.",
        style = MaterialTheme.typography.bodySmall,
    )
    Spacer(modifier = Modifier.height(4.dp))

    EXACT_VERIFICATION_FIELDS.forEach { field ->
        if (field.key in BOOL_INPUT_FIELDS) {
            val normalizedValue = parseInputValue(field.key, values[field.key] ?: "") as? Boolean
            Text(text = field.label, style = MaterialTheme.typography.bodyLarge)
            if (!field.helperText.isNullOrBlank()) {
                Text(text = field.helperText, style = MaterialTheme.typography.bodySmall)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                FilterChip(
                    selected = normalizedValue == true,
                    onClick = { values[field.key] = "true" },
                    enabled = !isSubmitting,
                    label = { Text(field.trueLabel ?: "예") },
                )
                FilterChip(
                    selected = normalizedValue == false,
                    onClick = { values[field.key] = "false" },
                    enabled = !isSubmitting,
                    label = { Text(field.falseLabel ?: "아니오") },
                )
                FilterChip(
                    selected = normalizedValue == null,
                    onClick = { values[field.key] = "" },
                    enabled = !isSubmitting,
                    label = { Text("미입력") },
                )
            }
            Spacer(modifier = Modifier.height(2.dp))
            return@forEach
        }

        OutlinedTextField(
            value = values[field.key] ?: "",
            onValueChange = { values[field.key] = it },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting,
            label = { Text(field.label) },
            singleLine = !field.key.endsWith("_text"),
            supportingText = {
                if (!field.helperText.isNullOrBlank()) {
                    Text(field.helperText)
                }
            },
        )
    }
}

private fun stageLabel(raw: String?): String {
    return when (raw?.trim()?.uppercase()) {
        "DISCOVERED" -> "발견됨"
        "INSPECTED" -> "구매/점검"
        "RESALE_LISTED" -> "재판매 등록"
        "SOLD" -> "판매 완료"
        "KEEP" -> "보유(KEEP)"
        null -> "-"
        else -> raw ?: "-"
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResaleTradeInputScreen(
    selectedJourney: ResaleTradeJourneyRow?,
    completedJourneys: List<ResaleTradeJourneyRow>,
    purchasedJourneys: List<ResaleTradeJourneyRow>,
    isSubmitting: Boolean,
    isLoadingCompleted: Boolean,
    isLoadingPurchased: Boolean,
    onStartFromUrl: (url: String) -> Unit,
    onSubmitPurchase: (updates: Map<String, Any?>) -> Unit,
    onSubmitResale: (updates: Map<String, Any?>) -> Unit,
    onSubmitSold: (updates: Map<String, Any?>) -> Unit,
    onLoadHistory: () -> Unit,
    onSelectPurchasedJourney: (ResaleTradeJourneyRow) -> Unit,
    onDeleteSelectedCompleted: (Set<Long>) -> Unit,
    onDeleteAllCompleted: () -> Unit,
) {
    var startUrl by remember { mutableStateOf("") }
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
            text = "URL, product_id 또는 알림 카드에서 거래 기록을 시작한 뒤, 필요한 값만 입력해 저장합니다.",
            style = MaterialTheme.typography.bodySmall,
        )

        Text(text = "URL 또는 product_id로 거래 기록 시작", style = MaterialTheme.typography.titleMedium)
        OutlinedTextField(
            value = startUrl,
            onValueChange = { startUrl = it },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isSubmitting,
            singleLine = true,
            label = { Text("중고나라 URL 또는 product_id") },
            placeholder = { Text("예: 228826879 또는 https://web.joongna.com/product/228826879") },
        )

        Button(
            onClick = {
                onStartFromUrl(startUrl)
            },
            enabled = !isSubmitting,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (isSubmitting) {
                CircularProgressIndicator(strokeWidth = 2.dp)
            } else {
                Text("거래 기록 시작")
            }
        }

        val sourceText = selectedJourney?.source?.takeIf { it.isNotBlank() } ?: "-"
        val productIdText = selectedJourney?.product_id?.takeIf { it.isNotBlank() } ?: "-"
        Text(
            text = "내부 식별값: ${sourceText} / ${productIdText}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        ProductBaseSpecCard(
            rowValues = journeyValueMap,
        )

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        ReadOnlyFieldCard(
            rowValues = journeyValueMap,
        )

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        ExactVerificationInputSection(
            values = manualInputs,
            isSubmitting = isSubmitting,
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
                    val updates = buildManualUpdates(
                        PURCHASE_INPUT_FIELDS,
                        manualInputs,
                        baselineValues = journeyValueMap,
                    ) + buildManualUpdates(
                        EXACT_VERIFICATION_FIELD_KEYS,
                        manualInputs,
                        baselineValues = journeyValueMap,
                    )
                    onSubmitPurchase(updates)
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
                    val updates = buildManualUpdates(
                        RESALE_INPUT_FIELDS,
                        manualInputs,
                        baselineValues = journeyValueMap,
                    ) + buildManualUpdates(
                        EXACT_VERIFICATION_FIELD_KEYS,
                        manualInputs,
                        baselineValues = journeyValueMap,
                    )
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
                onClick = onLoadHistory,
                enabled = !isLoadingCompleted && !isLoadingPurchased,
            ) {
                if (isLoadingCompleted || isLoadingPurchased) {
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

        if (completedJourneys.isEmpty()) {
            Text(text = "완료된 거래가 없습니다.")
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
                        "#${item.id} [${stageLabel(item.current_stage)}] ${item.title ?: "(제목없음)"} / ${formatWon(item.sale_price_krw)} / ROI ${item.roi_percent ?: "-"}%"
                    )
                },
            )
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        Text(text = "구매 거래 내역 (KEEP 포함)", style = MaterialTheme.typography.titleMedium)
        if (purchasedJourneys.isEmpty()) {
            Text(text = "구매 기록이 없습니다.")
        }
        purchasedJourneys.forEach { item ->
            val rowId = item.id ?: return@forEach
            val isSelectedJourney = selectedJourney?.id == rowId
            FilterChip(
                selected = isSelectedJourney,
                onClick = { onSelectPurchasedJourney(item) },
                label = {
                    Text(
                        "#${item.id} [${stageLabel(item.current_stage)}] ${item.title ?: "(제목없음)"} / 구매 ${formatWon(item.purchase_price_krw)}"
                    )
                },
            )
        }

        Spacer(modifier = Modifier.height(40.dp))
    }
}
