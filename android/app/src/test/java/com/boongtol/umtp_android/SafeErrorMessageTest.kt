package com.boongtol.umtp_android

import com.boongtol.umtp_android.ui.ErrorContext
import com.boongtol.umtp_android.ui.resolveSafeErrorMessage
import com.boongtol.umtp_android.ui.sanitizeErrorMessage
import com.boongtol.umtp_android.ui.toSafeUserMessage
import com.google.gson.JsonSyntaxException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test
import java.net.ConnectException

class SafeErrorMessageTest {
    @Test
    fun sanitizeErrorMessage_hidesIpAndPort() {
        val raw = "192.168.0.10:8000 connection failed"
        assertNull(sanitizeErrorMessage(raw))
    }

    @Test
    fun sanitizeErrorMessage_hidesBearerToken() {
        val raw = "Bearer xxx.yyy.zzz"
        assertNull(sanitizeErrorMessage(raw))
    }

    @Test
    fun sanitizeErrorMessage_hidesLocalPath() {
        val raw = "/Users/boongtol_air/Desktop/UMTP/.env missing"
        assertNull(sanitizeErrorMessage(raw))
    }

    @Test
    fun resolveSafeErrorMessage_returnsGenericNetworkMessageWithoutRawContent() {
        val message = resolveSafeErrorMessage(
            context = ErrorContext.NETWORK,
            rawMessage = "https://api.example.com:443 timeout",
            rawReason = "192.168.0.10:8000 connection failed",
        )

        assertEquals(
            "서버에 연결하지 못했어요. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.",
            message,
        )
        assertFalse(message.contains("192.168.0.10"))
        assertFalse(message.contains("https://"))
    }

    @Test
    fun throwableMapper_returnsNetworkMessage_forConnectException() {
        val message = ConnectException("connect failed").toSafeUserMessage(ErrorContext.SAVE)
        assertEquals(
            "서버에 연결하지 못했어요. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.",
            message,
        )
    }

    @Test
    fun throwableMapper_returnsDataFormatMessage_forJsonSyntaxException() {
        val message = JsonSyntaxException(
            "Expected BOOLEAN but was NUMBER at path $.items[0].activation_lock_off",
        ).toSafeUserMessage(ErrorContext.NETWORK)

        assertEquals(
            "데이터 형식이 맞지 않아요. 앱 로그에서 실패 필드를 확인해 주세요.",
            message,
        )
    }
}
