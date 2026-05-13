package com.boongtol.umtp_android.ui

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import com.boongtol.umtp_android.notification.UmtpNotificationListenerService

import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver

@Composable
fun NotificationPermissionSection(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    
    var isListenerEnabled by remember { mutableStateOf(isNotificationListenerEnabled(context)) }
    var isAppNotificationEnabled by remember { mutableStateOf(isAppNotificationEnabled(context)) }

    // Refresh when returning to the app
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                isListenerEnabled = isNotificationListenerEnabled(context)
                isAppNotificationEnabled = isAppNotificationEnabled(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }
    
    Column(modifier = modifier.fillMaxWidth()) {
        // A. Notification Listener Permission Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "A. 알림 접근 권한 (Notification Listener)",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Row {
                    Text(text = "상태: ", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = if (isListenerEnabled) "허용됨" else "필요함",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (isListenerEnabled) Color(0xFF2E7D32) else Color.Red
                    )
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "다른 앱(중고나라 등)의 알림을 자동으로 읽기 위해 필수적인 권한입니다. 앱 정보의 '허용된 권한'에는 표시되지 않을 수 있습니다.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Button(
                    onClick = {
                        context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(text = "알림 접근 권한 설정 열기")
                }
                
                if (!isListenerEnabled) {
                    Text(
                        text = "※ 권한을 켰는데 로그가 안 나오면 권한을 껐다가 다시 켠 뒤 앱을 재실행하세요.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // B. App Notification Permission Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "B. 앱 알림 표시 권한",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Row {
                    Text(text = "상태: ", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = if (isAppNotificationEnabled) "허용됨" else "필요함",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (isAppNotificationEnabled) Color(0xFF2E7D32) else Color.Gray
                    )
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "UMTP 앱이 사용자에게 직접 알림을 띄우기 위한 권한입니다. 현재 단계에서는 필수가 아닙니다.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Button(
                    onClick = {
                        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                                putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                            }
                        } else {
                            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                data = Uri.fromParts("package", context.packageName, null)
                            }
                        }
                        context.startActivity(intent)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.secondary
                    )
                ) {
                    Text(text = "앱 알림 설정 열기")
                }
            }
        }
    }
}

fun isNotificationListenerEnabled(context: Context): Boolean {
    val packageName = context.packageName
    val enabledListeners = Settings.Secure.getString(
        context.contentResolver,
        "enabled_notification_listeners"
    ) ?: ""

    Log.d("UMTP_PERMISSION", "enabled_notification_listeners=$enabledListeners")
    Log.d("UMTP_PERMISSION", "packageName=$packageName")

    val componentName = ComponentName(context, UmtpNotificationListenerService::class.java)
    val flat = componentName.flattenToString()
    val shortFlat = componentName.flattenToShortString()

    Log.d("UMTP_PERMISSION", "componentName flat=$flat")
    Log.d("UMTP_PERMISSION", "componentName shortFlat=$shortFlat")

    // Check for package name or component name in the enabled listeners string
    return enabledListeners.contains(packageName) || 
           enabledListeners.contains(flat) || 
           enabledListeners.contains(shortFlat)
}

fun isAppNotificationEnabled(context: Context): Boolean {
    return NotificationManagerCompat.from(context).areNotificationsEnabled()
}
