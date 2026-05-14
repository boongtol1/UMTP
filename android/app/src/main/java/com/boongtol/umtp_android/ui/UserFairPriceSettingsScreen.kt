package com.boongtol.umtp_android.ui

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UserFairPriceSettingsScreen(
    viewModel: MacBookAirSettingsViewModel,
    onBack: () -> Unit
) {
    val items by viewModel.items.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val toastMessage by viewModel.toastMessage.collectAsState()
    val savingItemKey by viewModel.savingItemKey.collectAsState()
    
    val context = LocalContext.current

    LaunchedEffect(toastMessage) {
        toastMessage?.let {
            Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
            viewModel.clearToastMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Column {
                        Text(text = "MacBook Air 설정", fontSize = 18.sp)
                        Text(text = "User ID: ${viewModel.userId}", fontSize = 12.sp, color = MaterialTheme.colorScheme.secondary)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .padding(paddingValues = innerPadding)
                .fillMaxSize()
        ) {
            if (isLoading && items.isEmpty()) {
                CircularProgressIndicator(modifier = Modifier.align(alignment = Alignment.Center))
            } else if (errorMessage != null && items.isEmpty()) {
                Column(
                    modifier = Modifier.align(alignment = Alignment.Center),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(text = errorMessage!!, color = Color.Red)
                    Button(onClick = { viewModel.loadItems() }) {
                        Text(text = "다시 시도")
                    }
                }
            } else {
                val groupedItems = items.groupBy { it.chip }
                
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(all = 16.dp)
                ) {
                    groupedItems.forEach { (chip, chipItems) ->
                        item {
                            ChipHeader(chip = chip)
                        }
                        
                        val screenGroups = chipItems.groupBy { it.screen_inch }
                        screenGroups.forEach { (screen, screenItems) ->
                            item {
                                ScreenHeader(screen = screen)
                            }
                            
                            items(items = screenItems) { item ->
                                val itemKey = "${item.chip}-${item.screen_inch}-${item.ram_gb}-${item.ssd_gb}"
                                MacBookAirUnitCard(
                                    item = item,
                                    isSaving = savingItemKey == itemKey,
                                    onSave = { fairPrice, dropRate, enabled ->
                                        viewModel.upsertItem(item, fairPrice, dropRate, enabled)
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ChipHeader(chip: String) {
    Text(
        text = chip,
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .fillMaxWidth()
            .background(color = MaterialTheme.colorScheme.primaryContainer)
            .padding(all = 8.dp)
    )
}

@Composable
fun ScreenHeader(screen: Int) {
    Text(
        text = "${screen}인치",
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .padding(top = 16.dp, bottom = 8.dp)
    )
}
