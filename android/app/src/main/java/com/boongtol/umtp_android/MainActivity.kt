package com.boongtol.umtp_android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.boongtol.umtp_android.ui.UmtpUrlAnalyzeScreen
import com.boongtol.umtp_android.ui.theme.UMTP_ANDROIDTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            UMTP_ANDROIDTheme {
                UmtpUrlAnalyzeScreen()
            }
        }
    }
}
