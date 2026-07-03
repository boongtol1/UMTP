package com.boongtol.umtp_android.ui

import com.google.gson.JsonParseException
import com.google.gson.JsonSyntaxException
import com.google.gson.stream.MalformedJsonException
import retrofit2.HttpException
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

enum class ErrorContext {
    NETWORK,
    SAVE,
    SEARCH_REQUEST,
    UNKNOWN,
}

private const val NETWORK_ERROR_MESSAGE =
    "서버에 연결하지 못했어요. 네트워크 상태를 확인한 뒤 다시 시도해 주세요."
private const val DATA_FORMAT_ERROR_MESSAGE =
    "데이터 형식이 맞지 않아요. 앱 로그에서 실패 필드를 확인해 주세요."
private const val SAVE_ERROR_MESSAGE =
    "설정을 저장하지 못했어요. 잠시 후 다시 시도해 주세요."
private const val SEARCH_REQUEST_ERROR_MESSAGE =
    "검색 요청을 보내지 못했어요. 잠시 후 다시 시도해 주세요."
private const val UNKNOWN_ERROR_MESSAGE =
    "일시적인 오류가 발생했어요. 다시 시도해 주세요."

private val IP_V4_OR_WITH_PORT_REGEX = Regex(
    pattern = """\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?::\d{1,5})?\b""",
)
private val URL_REGEX = Regex("""https?://\S+""", RegexOption.IGNORE_CASE)
private val UNIX_PATH_REGEX = Regex("""(?:/Users/|/home/|/var/|/etc/|/opt/)\S+""")
private val WINDOWS_PATH_REGEX = Regex("""[A-Za-z]:\\[^\s]+""")
private val TOKEN_LIKE_REGEX =
    Regex("""(?i)\b(?:authorization|bearer|api[_ -]?key|token|secret|password)\b\s*[:=]?\s*\S+""")
private val DB_CREDENTIAL_HINT_REGEX = Regex(
    """(?i)\b(?:db_host|db_user|db_password|database|jdbc:mysql|mysql:\/\/)\b""",
)
private val STACKTRACE_LINE_REGEX = Regex("""\bat\s+[A-Za-z0-9_.$]+\(.+\)""")

private fun ErrorContext.defaultMessage(): String {
    return when (this) {
        ErrorContext.NETWORK -> NETWORK_ERROR_MESSAGE
        ErrorContext.SAVE -> SAVE_ERROR_MESSAGE
        ErrorContext.SEARCH_REQUEST -> SEARCH_REQUEST_ERROR_MESSAGE
        ErrorContext.UNKNOWN -> UNKNOWN_ERROR_MESSAGE
    }
}

private fun containsSensitiveContent(raw: String): Boolean {
    return IP_V4_OR_WITH_PORT_REGEX.containsMatchIn(raw) ||
        URL_REGEX.containsMatchIn(raw) ||
        UNIX_PATH_REGEX.containsMatchIn(raw) ||
        WINDOWS_PATH_REGEX.containsMatchIn(raw) ||
        TOKEN_LIKE_REGEX.containsMatchIn(raw) ||
        DB_CREDENTIAL_HINT_REGEX.containsMatchIn(raw) ||
        STACKTRACE_LINE_REGEX.containsMatchIn(raw)
}

fun sanitizeErrorMessage(raw: String?): String? {
    if (raw.isNullOrBlank()) {
        return null
    }
    val singleLine = raw.lineSequence().firstOrNull()?.trim().orEmpty()
    if (singleLine.isBlank()) {
        return null
    }
    if (containsSensitiveContent(singleLine)) {
        return null
    }
    return singleLine.take(160)
}

fun resolveSafeErrorMessage(
    context: ErrorContext,
    rawMessage: String? = null,
    rawReason: String? = null,
): String {
    val safeReason = sanitizeErrorMessage(rawReason)
    val safeMessage = sanitizeErrorMessage(rawMessage)

    return safeReason ?: safeMessage ?: context.defaultMessage()
}

private fun Throwable.isJsonExceptionByName(): Boolean {
    val className = javaClass.name
    return className.contains("SerializationException") ||
        className.contains("JsonDataException") ||
        className.contains("MalformedJsonException")
}

private fun Throwable.isJsonRelatedIllegalState(): Boolean {
    if (this !is IllegalStateException) {
        return false
    }
    val messageLooksLikeGsonPath = message?.let {
        it.contains("Expected ") && it.contains(" but was ") && it.contains("path $")
    } == true
    return messageLooksLikeGsonPath ||
        stackTrace.any { frame ->
            frame.className.startsWith("com.google.gson") ||
                frame.className.startsWith("retrofit2.converter.gson")
        }
}

private fun Throwable.isJsonParsingError(): Boolean {
    if (this is JsonParseException ||
        this is JsonSyntaxException ||
        this is MalformedJsonException ||
        isJsonExceptionByName() ||
        isJsonRelatedIllegalState()
    ) {
        return true
    }

    val nestedCause = cause
    return nestedCause != null && nestedCause !== this && nestedCause.isJsonParsingError()
}

private fun Throwable.isNetworkConnectionError(): Boolean {
    return this is UnknownHostException ||
        this is ConnectException ||
        this is SocketTimeoutException ||
        (this is IOException && !isJsonParsingError())
}

fun Throwable.toSafeUserMessage(context: ErrorContext): String {
    return when {
        isJsonParsingError() -> DATA_FORMAT_ERROR_MESSAGE
        isNetworkConnectionError() -> ErrorContext.NETWORK.defaultMessage()
        this is HttpException -> "서버 오류가 발생했어요. (HTTP ${code()})"
        else -> context.defaultMessage()
    }
}
