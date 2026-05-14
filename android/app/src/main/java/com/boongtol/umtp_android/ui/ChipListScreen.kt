package com.boongtol.umtp_android.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChipListScreen(
    userId: String,
    chips: List<String>,
    onChipClick: (String) -> Unit,
    onLogout: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Column {
                        Text("MacBook Air 설정", fontSize = 18.sp)
                        Text("User: $userId", fontSize = 12.sp, color = MaterialTheme.colorScheme.secondary)
                    }
                },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = "Logout")
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {
            Text(
                text = "칩 선택",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(16.dp),
                fontWeight = FontWeight.Bold
            )
            
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(chips) { chip ->
                    ListItem(
                        headlineContent = { Text(chip, fontWeight = FontWeight.Medium) },
                        trailingContent = { Icon(Icons.Default.KeyboardArrowRight, contentDescription = null) },
                        modifier = Modifier.clickable { onChipClick(chip) }
                    )
                    HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp), thickness = 0.5.dp, color = Color.LightGray)
                }
            }
        }
    }
}
