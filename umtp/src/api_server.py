from typing import Literal, Optional

import logging
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.alert_price_direction import (
    DEFAULT_ALERT_PRICE_DIRECTION,
    MAX_ALERT_DROP_RATE_PERCENT,
    MIN_ALERT_DROP_RATE_PERCENT,
)
from src.analysis_service import analyze_url_for_user
from src.notification_worker import (
    clear_all_read_alert_events_for_user,
    clear_selected_read_alert_events_for_user,
    list_alert_events_for_user,
    list_grouped_read_alert_events_for_user,
    mark_alert_event_read_for_user,
    mark_all_alert_events_read_for_user,
)
from src.push_token_service import upsert_user_push_token
from src.user_settings_service import (
    get_all_macbook_air_units_sorted,
    get_recommended_setting_keywords,
    get_user_fair_price_settings,
    refresh_user_fair_price_saved_at_for_active_rules,
    refresh_user_fair_price_saved_at_for_single_rule,
    register_user,
    upsert_user_fair_price_setting,
)


app = FastAPI(title="UMTP API", version="1.0")
logger = logging.getLogger("umtp.api")


def _normalize_user_id(value: Optional[str]) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _ensure_user_registered(raw_user_id: Optional[str], *, source: str) -> str:
    normalized_user_id = _normalize_user_id(raw_user_id)
    if not normalized_user_id:
        raise ValueError("invalid_user_id")

    registration_result = register_user(user_id=normalized_user_id)
    if not registration_result.get("ok"):
        reason = registration_result.get("reason") or registration_result.get("message") or "user_register_failed"
        raise RuntimeError(reason)

    saved_user_id = _normalize_user_id(registration_result.get("user_id"))
    resolved_user_id = saved_user_id if saved_user_id else normalized_user_id
    if resolved_user_id != normalized_user_id:
        logger.info(
            "[%s] user_id remapped requested=%s saved=%s",
            source,
            normalized_user_id,
            resolved_user_id,
        )
    return resolved_user_id


def _normalize_is_read_query(value: Optional[str]) -> str:
    normalized = _normalize_user_id(value).lower()
    if not normalized:
        return "0"
    if normalized in {"0", "false", "unread"}:
        return "0"
    if normalized in {"1", "true", "read"}:
        return "1"
    if normalized == "all":
        return "all"
    raise ValueError("invalid_is_read")


class AnalyzeUrlRequest(BaseModel):
    user_id: str
    url: str


class UserRegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=200)


class UserFairPriceUpsertRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    product_type: str = Field(..., min_length=1, max_length=100)
    chip: str = Field(..., min_length=1, max_length=20)
    screen_inch: int
    ram_gb: int
    ssd_gb: int
    fair_price_krw: int = Field(..., gt=0)
    alert_drop_rate_percent: float = Field(
        ...,
        ge=MIN_ALERT_DROP_RATE_PERCENT,
        le=MAX_ALERT_DROP_RATE_PERCENT,
    )
    alert_price_direction: Literal["BELOW_OR_EQUAL", "ABOVE_OR_EQUAL"] = Field(
        default=DEFAULT_ALERT_PRICE_DIRECTION
    )
    min_price_krw: Optional[int] = Field(default=None, ge=0)
    max_price_krw: Optional[int] = Field(default=None, ge=0)
    enabled: bool
    condition_change_candidate_notice_enabled: bool = False
    search_keyword: Optional[str] = Field(default=None, max_length=255)
    poll_interval_seconds: int = Field(default=60, ge=1)


class PushTokenRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=1024)
    platform: str = Field(default="android", min_length=1, max_length=30)


class ClearSelectedReadArchiveRequest(BaseModel):
    alert_event_ids: list[int] = Field(default_factory=list)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/.well-known/security.txt", response_class=PlainTextResponse)
def security_txt():
    # Basic security.txt to avoid crawler 404 noise.
    return (
        "Contact: mailto:security@localhost\n"
        "Preferred-Languages: ko, en\n"
        "Expires: 2027-12-31T23:59:59Z\n"
    )


@app.get("/macbook-air-units")
def macbook_air_units():
    try:
        units = get_all_macbook_air_units_sorted()
        return {"ok": True, "units": units}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"MacBook Air 단위 목록 조회 실패: {exc}",
            "units": [],
        }


@app.get("/user-fair-prices")
def user_fair_prices(user_id: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "items": []}

    try:
        resolved_user_id = _ensure_user_registered(normalized_user_id, source="api/user-fair-prices")
        items = get_user_fair_price_settings(resolved_user_id)
        return {"ok": True, "user_id": resolved_user_id, "items": items}
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id", "items": []}
    except RuntimeError as exc:
        return {
            "ok": False,
            "reason": f"사용자 등록 실패: {exc}",
            "user_id": normalized_user_id,
            "items": [],
        }
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"사용자 공정가 설정 조회 실패: {exc}",
            "user_id": normalized_user_id,
            "items": [],
        }


@app.post("/users/register")
def users_register(request: UserRegisterRequest):
    user_id = request.user_id.strip() if isinstance(request.user_id, str) else ""
    device_id = request.device_id.strip() if isinstance(request.device_id, str) else ""
    masked_device_id = f"{device_id[:4]}...{device_id[-4:]}" if len(device_id) > 8 else device_id

    logger.info(
        "[api/users/register] received user_id=%s device_id=%s",
        user_id,
        masked_device_id,
    )

    if not user_id:
        logger.warning("[api/users/register] invalid_user_id request body=%s", request.model_dump())
        return {"ok": False, "reason": "invalid_user_id"}
    if not device_id:
        logger.warning("[api/users/register] invalid_device_id request body=%s", request.model_dump())
        return {"ok": False, "reason": "invalid_device_id"}

    try:
        result = register_user(
            user_id=user_id,
            device_id=device_id,
        )
        logger.info("[api/users/register] result=%s", result)
        return result
    except Exception as exc:
        logger.exception(
            "[api/users/register] failed user_id=%s device_id=%s",
            user_id,
            masked_device_id,
        )
        return {
            "ok": False,
            "reason": f"사용자 등록 실패: {exc}",
            "message": f"사용자 등록 실패: {exc}",
            "user_id": user_id,
        }


@app.post("/users/{user_id}/push-token")
def users_push_token_upsert(user_id: str, request: PushTokenRequest):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "message": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(normalized_user_id, source="api/users/push-token")
        result = upsert_user_push_token(
            user_id=resolved_user_id,
            token=request.token,
            platform=request.platform,
        )
        if result.get("ok"):
            return {
                "ok": True,
                "message": "푸시 토큰 저장 완료",
            }
        return {
            "ok": False,
            "reason": result.get("reason") or "push_token_upsert_failed",
            "message": result.get("message") or "푸시 토큰 저장 실패",
        }
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id", "message": "invalid_user_id"}
    except RuntimeError as exc:
        return {
            "ok": False,
            "reason": f"사용자 등록 실패: {exc}",
            "message": f"사용자 등록 실패: {exc}",
            "user_id": normalized_user_id,
        }
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"푸시 토큰 저장 실패: {exc}",
            "message": f"푸시 토큰 저장 실패: {exc}",
            "user_id": normalized_user_id,
        }


@app.post("/user-fair-prices/upsert")
def user_fair_prices_upsert(request: UserFairPriceUpsertRequest):
    try:
        resolved_user_id = _ensure_user_registered(request.user_id, source="api/user-fair-prices/upsert")
        return upsert_user_fair_price_setting(
            user_id=resolved_user_id,
            product_type=request.product_type,
            chip=request.chip,
            screen_inch=request.screen_inch,
            ram_gb=request.ram_gb,
            ssd_gb=request.ssd_gb,
            fair_price_krw=request.fair_price_krw,
            alert_drop_rate_percent=request.alert_drop_rate_percent,
            enabled=request.enabled,
            alert_price_direction=request.alert_price_direction,
            min_price_krw=request.min_price_krw,
            max_price_krw=request.max_price_krw,
            search_keyword=request.search_keyword,
            poll_interval_seconds=request.poll_interval_seconds,
            condition_change_candidate_notice_enabled=request.condition_change_candidate_notice_enabled,
        )
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"사용자 공정가 설정 저장 실패: {exc}"}


@app.post("/users/{user_id}/rules/refresh")
def refresh_user_rules_saved_at(user_id: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(normalized_user_id, source="api/users/rules/refresh")
        result = refresh_user_fair_price_saved_at_for_active_rules(resolved_user_id)
        if result.get("ok"):
            result.setdefault("user_id", resolved_user_id)
        return result
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": normalized_user_id}
    except Exception as exc:
        return {"ok": False, "reason": f"저장 조건 새로고침 실패: {exc}", "user_id": normalized_user_id}


@app.post("/users/{user_id}/rules/{rule_id}/refresh")
def refresh_single_user_rule_saved_at(user_id: str, rule_id: int):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/rules/{rule_id}/refresh",
        )
        result = refresh_user_fair_price_saved_at_for_single_rule(resolved_user_id, rule_id)
        if result.get("ok"):
            result.setdefault("user_id", resolved_user_id)
            result.setdefault("rule_id", rule_id)
        return result
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": normalized_user_id}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"저장 조건 단일 새로고침 실패: {exc}",
            "user_id": normalized_user_id,
            "rule_id": rule_id,
        }


def _list_alerts_response(*, user_id: str, limit: int = 200, is_read: Optional[str] = "0", source: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "items": []}

    if not isinstance(limit, int) or limit <= 0:
        return {"ok": False, "reason": "invalid_limit", "items": []}

    try:
        normalized_is_read = _normalize_is_read_query(is_read)
        resolved_user_id = _ensure_user_registered(normalized_user_id, source=source)
        items = list_alert_events_for_user(
            resolved_user_id,
            limit=min(limit, 200),
            is_read=normalized_is_read,
        )
        return {
            "ok": True,
            "user_id": resolved_user_id,
            "is_read_filter": normalized_is_read,
            "items": items,
        }
    except RuntimeError as exc:
        return {
            "ok": False,
            "reason": f"사용자 등록 실패: {exc}",
            "user_id": normalized_user_id,
            "items": [],
        }
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "items": []}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"알림 조회 실패: {exc}",
            "user_id": normalized_user_id,
            "items": [],
        }


@app.get("/alerts")
def alerts(user_id: str, limit: int = 200, is_read: Optional[str] = "0"):
    return _list_alerts_response(
        user_id=user_id,
        limit=limit,
        is_read=is_read,
        source="api/alerts",
    )


@app.get("/alert-events")
def alert_events(user_id: str, limit: int = 200, is_read: Optional[str] = "0"):
    return _list_alerts_response(
        user_id=user_id,
        limit=limit,
        is_read=is_read,
        source="api/alert-events",
    )


@app.patch("/alert-events/{alert_event_id}/read")
def mark_alert_event_as_read(alert_event_id: int, user_id: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(normalized_user_id, source="api/alert-events/{id}/read")
        result = mark_alert_event_read_for_user(
            user_id=resolved_user_id,
            alert_event_id=alert_event_id,
        )
        if result.get("ok"):
            result.setdefault("user_id", resolved_user_id)
            result.setdefault("message", "읽음 처리 완료")
        return result
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": normalized_user_id}
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "user_id": normalized_user_id}
    except Exception as exc:
        return {"ok": False, "reason": f"읽음 처리 실패: {exc}", "user_id": normalized_user_id}


@app.patch("/alert-events/read-all")
def mark_all_alert_events_as_read(user_id: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(normalized_user_id, source="api/alert-events/read-all")
        result = mark_all_alert_events_read_for_user(user_id=resolved_user_id)
        if result.get("ok"):
            result.setdefault("user_id", resolved_user_id)
            result.setdefault("message", "모두 읽음 처리 완료")
        return result
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": normalized_user_id}
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "user_id": normalized_user_id}
    except Exception as exc:
        return {"ok": False, "reason": f"모두 읽음 처리 실패: {exc}", "user_id": normalized_user_id}


@app.patch("/alert-events/read/archive/clear-all")
def clear_all_read_alert_events(user_id: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/alert-events/read/archive/clear-all",
        )
        result = clear_all_read_alert_events_for_user(user_id=resolved_user_id)
        if result.get("ok"):
            result.setdefault("user_id", resolved_user_id)
            result.setdefault("message", "읽음 보관함 전체 비우기 완료")
        return result
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": normalized_user_id}
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "user_id": normalized_user_id}
    except Exception as exc:
        return {"ok": False, "reason": f"읽음 보관함 전체 비우기 실패: {exc}", "user_id": normalized_user_id}


@app.patch("/alert-events/read/archive/clear-selected")
def clear_selected_read_alert_events(user_id: str, request: ClearSelectedReadArchiveRequest):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/alert-events/read/archive/clear-selected",
        )
        result = clear_selected_read_alert_events_for_user(
            user_id=resolved_user_id,
            alert_event_ids=request.alert_event_ids,
        )
        if result.get("ok"):
            result.setdefault("user_id", resolved_user_id)
            result.setdefault("message", "읽음 보관함 선택 비우기 완료")
        return result
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": normalized_user_id}
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "user_id": normalized_user_id}
    except Exception as exc:
        return {"ok": False, "reason": f"읽음 보관함 선택 비우기 실패: {exc}", "user_id": normalized_user_id}


@app.get("/alert-events/read/grouped")
def grouped_read_alert_events(user_id: str, limit: int = 500):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "groups": {}}
    if not isinstance(limit, int) or limit <= 0:
        return {"ok": False, "reason": "invalid_limit", "groups": {}}

    try:
        resolved_user_id = _ensure_user_registered(normalized_user_id, source="api/alert-events/read/grouped")
        groups = list_grouped_read_alert_events_for_user(
            user_id=resolved_user_id,
            limit=min(limit, 1000),
        )
        return {
            "ok": True,
            "user_id": resolved_user_id,
            "groups": groups,
        }
    except RuntimeError as exc:
        return {
            "ok": False,
            "reason": f"사용자 등록 실패: {exc}",
            "user_id": normalized_user_id,
            "groups": {},
        }
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "groups": {}}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"읽음 알림 그룹 조회 실패: {exc}",
            "user_id": normalized_user_id,
            "groups": {},
        }


@app.get("/user-fair-prices/recommended-keywords")
def user_fair_prices_recommended_keywords(
    product_type: str,
    chip: str,
    ram_gb: Optional[int] = None,
    ssd_gb: Optional[int] = None,
):
    try:
        items = get_recommended_setting_keywords(
            product_type=product_type,
            chip=chip,
            ram_gb=ram_gb,
            ssd_gb=ssd_gb,
        )
        return {
            "ok": True,
            "items": items,
        }
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "message": str(exc), "items": []}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"추천 검색어 조회 실패: {exc}",
            "message": f"추천 검색어 조회 실패: {exc}",
            "items": [],
        }


@app.post("/analyze-url")
def analyze_url(request: AnalyzeUrlRequest):
    try:
        resolved_user_id = _ensure_user_registered(request.user_id, source="api/analyze-url")
        return analyze_url_for_user(
            user_id=resolved_user_id,
            url=request.url,
        )
    except ValueError:
        return {
            "ok": False,
            "status": "failed",
            "url": request.url,
            "reason": "invalid_user_id",
        }
    except RuntimeError as exc:
        return {
            "ok": False,
            "status": "failed",
            "url": request.url,
            "reason": f"사용자 등록 실패: {exc}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "failed",
            "url": request.url,
            "reason": f"API 처리 실패: {exc}",
        }
