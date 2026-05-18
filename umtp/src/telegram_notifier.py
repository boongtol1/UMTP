import os

import requests
from dotenv import load_dotenv


TELEGRAM_API_TIMEOUT_SECONDS = 10
TELEGRAM_CAPTION_MAX_LENGTH = 1024


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _truncate_telegram_caption(text):
    normalized = _normalize_optional_text(text)
    if normalized is None:
        return None
    if len(normalized) <= TELEGRAM_CAPTION_MAX_LENGTH:
        return normalized
    return f"{normalized[: TELEGRAM_CAPTION_MAX_LENGTH - 3].rstrip()}..."


def _post_telegram(api_url, payload):
    response = requests.post(
        api_url,
        data=payload,
        timeout=TELEGRAM_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    response_json = response.json()
    if not response_json.get("ok", False):
        raise RuntimeError(str(response_json))
    return True


def send_telegram_alert(message, *, chat_id=None, allow_global_fallback=True, image_url=None):
    load_dotenv()
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    resolved_chat_id = (chat_id or "").strip()
    if not resolved_chat_id and allow_global_fallback:
        resolved_chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
        if resolved_chat_id:
            print("전역 TELEGRAM_CHAT_ID fallback 사용(deprecated)")

    if not bot_token or not resolved_chat_id:
        print("텔레그램 설정 없음")
        return False

    normalized_image_url = _normalize_optional_text(image_url)
    normalized_caption = _truncate_telegram_caption(message)
    send_photo_api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    send_message_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        if normalized_image_url is not None:
            try:
                _post_telegram(
                    send_photo_api_url,
                    {
                        "chat_id": resolved_chat_id,
                        "photo": normalized_image_url,
                        "caption": normalized_caption or "-",
                    },
                )
                print("텔레그램 이미지 전송 완료")
                return True
            except Exception as photo_exc:
                print(f"텔레그램 이미지 전송 실패, 텍스트 전송으로 fallback: {photo_exc}")

        _post_telegram(
            send_message_api_url,
            {
                "chat_id": resolved_chat_id,
                "text": message,
            },
        )

        print("텔레그램 전송 완료")
        return True
    except requests.RequestException as exc:
        print(f"텔레그램 전송 실패: {exc}")
        return False
    except RuntimeError as exc:
        print(f"텔레그램 전송 실패: {exc}")
        return False
    except ValueError as exc:
        print(f"텔레그램 응답 파싱 실패: {exc}")
        return False
