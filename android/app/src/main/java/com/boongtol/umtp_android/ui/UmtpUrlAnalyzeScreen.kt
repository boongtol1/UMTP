package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.boongtol.umtp_android.network.AnalyzeUrlRequest
import com.boongtol.umtp_android.network.UmtpApiClient
import kotlinx.coroutines.launch

import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UmtpUrlAnalyzeScreen() {
    var url by remember { mutableStateOf("") }
    var resultText by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(value = false) }
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(text = "UMTP URL 분석 테스트") }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .padding(all = 16.dp)
                .fillMaxSize()
                .verticalScroll(state = rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            OutlinedTextField(
                value = url,
                onValueChange = { url = it },
                label = { Text(text = "중고나라 매물 URL 입력") },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(text = "https://web.joongna.com/product/...") }
            )

            Spacer(modifier = Modifier.height(height = 16.dp))

            Button(
                onClick = {
                    if (url.isBlank()) {
                        resultText = "URL을 입력해주세요."
                        return@Button
                    }
                    scope.launch {
                        isLoading = true
                        resultText = "분석 요청 중..."
                        resultText = try {
                            val response = UmtpApiClient.apiService.analyzeUrl(
                                AnalyzeUrlRequest(user_id = "test_user", url = url)
                            )
                            formatResponse(response)
                        } catch (e: Exception) {
                            "에러 발생: ${e.localizedMessage}"
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(size = 24.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(width = 8.dp))
                    Text(text = "분석 중...")
                } else {
                    Text(text = "분석 요청")
                }
            }

            Spacer(modifier = Modifier.height(height = 24.dp))

            Text(
                text = "분석 결과",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.align(alignment = Alignment.Start)
            )

            Spacer(modifier = Modifier.height(height = 8.dp))

            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = MaterialTheme.shapes.medium
            ) {
                Text(
                    text = resultText,
                    modifier = Modifier.padding(all = 16.dp),
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                    fontSize = 14.sp
                )
            }

            Spacer(modifier = Modifier.height(height = 32.dp))

            Divider(modifier = Modifier.padding(vertical = 8.dp))

            NotificationPermissionSection()
        }
    }
}

private fun formatResponse(response: com.boongtol.umtp_android.network.AnalyzeUrlResponse): String {
    val sb = StringBuilder()
    sb.append("성공 여부: ${response.ok}\n")
    response.status?.let { sb.append("상태: $it\n") }
    response.message?.let { sb.append("메시지: $it\n") }
    response.title?.let { sb.append("제목: $it\n") }
    response.listing_price_krw?.let { sb.append("등록 가격: $it 원\n") }
    response.fair_price_krw?.let { sb.append("적정 가격: $it 원\n") }
    response.diff_ratio?.let { sb.append("가격 차이: ${String.format(Locale.getDefault(), "%.1f", it * 100)}%\n") }
    response.is_alert_target?.let { sb.append("알림 대상: $it\n") }
    response.risk_level?.let { sb.append("위험도: $it\n") }
    response.trade_type?.let { sb.append("거래 방식: $it\n") }
    response.reason?.let { sb.append("이유: $it\n") }
    
    if (sb.isEmpty()) {
        return "응답 데이터가 비어 있습니다."
    }
    return sb.toString()
}
