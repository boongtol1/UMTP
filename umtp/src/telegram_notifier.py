import os

import requests
from dotenv import load_dotenv


TELEGRAM_API_TIMEOUT_SECONDS = 10


def send_telegram_alert(message, *, chat_id=None, allow_global_fallback=True):
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

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": resolved_chat_id,
        "text": message,
    }

    try:
        response = requests.post(
            api_url,
            data=payload,
            timeout=TELEGRAM_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        response_json = response.json()
        if not response_json.get("ok", False):
            print(f"텔레그램 전송 실패: {response_json}")
            return False

        print("텔레그램 전송 완료")
        return True
    except requests.RequestException as exc:
        print(f"텔레그램 전송 실패: {exc}")
        return False
    except ValueError as exc:
        print(f"텔레그램 응답 파싱 실패: {exc}")
        return False
