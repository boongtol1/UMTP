package com.boongtol.umtp_android.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProductTypeListScreen(
    userId: String,
    productTypes: List<String>,
    isRefreshing: Boolean,
    refreshStatusMessage: String?,
    lastRefreshAtText: String?,
    onRefresh: () -> Unit,
    onProductTypeClick: (String) -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("실리콘 Mac 설정", fontSize = 18.sp)
                        Text("User: $userId", fontSize = 12.sp, color = MaterialTheme.colorScheme.secondary)
                    }
                },
                actions = {
                    IconButton(onClick = onRefresh, enabled = !isRefreshing) {
                        if (isRefreshing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(18.dp),
                                strokeWidth = 2.dp,
                            )
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "새로고침")
                        }
                    }
                },
            )
        }
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {
            if (isRefreshing) {
                Text(
                    text = "새로고침 중...",
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            } else if (!refreshStatusMessage.isNullOrBlank()) {
                Text(
                    text = refreshStatusMessage,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                if (!lastRefreshAtText.isNullOrBlank()) {
                    Text(
                        text = lastRefreshAtText,
                        modifier = Modifier.padding(horizontal = 16.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray,
                    )
                }
            }
            Text(
                text = "제품 종류 선택",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(16.dp),
                fontWeight = FontWeight.Bold,
            )

            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(productTypes) { productType ->
                    ListItem(
                        headlineContent = { Text(productType, fontWeight = FontWeight.Medium) },
                        trailingContent = { Icon(Icons.Default.KeyboardArrowRight, contentDescription = null) },
                        modifier = Modifier.clickable { onProductTypeClick(productType) },
                    )
                    HorizontalDivider(
                        modifier = Modifier.padding(horizontal = 16.dp),
                        thickness = 0.5.dp,
                        color = Color.LightGray,
                    )
                }
            }
        }
    }
}
