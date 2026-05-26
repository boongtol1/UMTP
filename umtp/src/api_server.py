from typing import Any, Literal, Optional

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
from src.resale_trade_journeys import (
    create_or_hydrate_resale_trade_journey_from_product,
    delete_completed_resale_trade_journeys,
    list_completed_resale_trade_journeys,
    list_purchased_resale_trade_journeys,
    patch_resale_trade_journey_purchase,
    patch_resale_trade_journey_resale,
    patch_resale_trade_journey_sold,
    start_resale_trade_journey_from_alert,
    start_resale_trade_journey_from_read_archive,
    start_resale_trade_journey_from_url,
    upsert_resale_trade_after_purchase,
    upsert_resale_trade_after_resale,
)
from src.user_settings_service import (
    bulk_set_user_watch_rules_enabled,
    bulk_update_user_fair_price_drop_rate,
    get_all_macbook_air_units_sorted,
    get_recommended_setting_keywords,
    get_user_fair_price_settings,
    refresh_user_fair_price_saved_at_for_active_rules,
    refresh_user_fair_price_saved_at_for_single_rule,
    register_user,
    reset_user_fair_prices_to_system_market_prices,
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
    priority: Optional[str] = Field(default="NORMAL", max_length=20)


class PushTokenRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=1024)
    platform: str = Field(default="android", min_length=1, max_length=30)


class ClearSelectedReadArchiveRequest(BaseModel):
    alert_event_ids: list[int] = Field(default_factory=list)


class UserWatchRulesBulkEnabledRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    enabled: bool
    product_type: Optional[str] = Field(default=None, min_length=1, max_length=100)


class UserFairPricesBulkDropRateRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    alert_drop_rate_percent: float = Field(
        ...,
        ge=MIN_ALERT_DROP_RATE_PERCENT,
        le=MAX_ALERT_DROP_RATE_PERCENT,
    )
    product_type: Optional[str] = Field(default=None, min_length=1, max_length=100)


class UserFairPricesResetToSystemRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    product_type: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ResaleTradeAfterPurchaseUpsertRequest(BaseModel):
    user_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    source: str = Field(default="joongna", min_length=1, max_length=50)
    product_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    updates: dict = Field(default_factory=dict)


class ResaleTradeAfterResaleUpsertRequest(BaseModel):
    user_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    source: str = Field(default="joongna", min_length=1, max_length=50)
    product_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    updates: dict = Field(default_factory=dict)


class ResaleTradeJourneyFromProductRequest(BaseModel):
    source: str = Field(default="joongna", min_length=1, max_length=50)
    product_id: str = Field(..., min_length=1, max_length=100)


class ResaleTradeJourneyDeleteSelectedRequest(BaseModel):
    journey_ids: list[int] = Field(default_factory=list)


class TradeJourneyStartFromUrlRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=1000)


class TradeJourneyStartFromAlertRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    alert_event_id: int = Field(..., gt=0)


class TradeJourneyStartFromReadArchiveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    read_archive_event_id: int = Field(..., gt=0)


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
@app.get("/silicon-mac-units")
def macbook_air_units():
    try:
        units = get_all_macbook_air_units_sorted()
        return {"ok": True, "units": units}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"실리콘 Mac 단위 목록 조회 실패: {exc}",
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
            priority=request.priority,
            condition_change_candidate_notice_enabled=request.condition_change_candidate_notice_enabled,
        )
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"사용자 공정가 설정 저장 실패: {exc}"}


@app.patch("/user-watch-rules/bulk-enabled")
def user_watch_rules_bulk_enabled(request: UserWatchRulesBulkEnabledRequest):
    try:
        resolved_user_id = _ensure_user_registered(request.user_id, source="api/user-watch-rules/bulk-enabled")
        return bulk_set_user_watch_rules_enabled(
            user_id=resolved_user_id,
            enabled=request.enabled,
            product_type=request.product_type,
        )
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"일괄 알림 ON/OFF 적용 실패: {exc}"}


@app.patch("/user-fair-prices/bulk-drop-rate")
def user_fair_prices_bulk_drop_rate(request: UserFairPricesBulkDropRateRequest):
    try:
        resolved_user_id = _ensure_user_registered(request.user_id, source="api/user-fair-prices/bulk-drop-rate")
        return bulk_update_user_fair_price_drop_rate(
            user_id=resolved_user_id,
            alert_drop_rate_percent=request.alert_drop_rate_percent,
            product_type=request.product_type,
        )
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"시장가와의 차이 % 일괄 적용 실패: {exc}"}


@app.post("/user-fair-prices/reset-to-system-market-prices")
def user_fair_prices_reset_to_system_market_prices(request: UserFairPricesResetToSystemRequest):
    try:
        resolved_user_id = _ensure_user_registered(
            request.user_id,
            source="api/user-fair-prices/reset-to-system-market-prices",
        )
        return reset_user_fair_prices_to_system_market_prices(
            user_id=resolved_user_id,
            product_type=request.product_type,
        )
    except ValueError:
        return {"ok": False, "reason": "invalid_user_id"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"시스템 기준 시장가 초기화 실패: {exc}"}


def _prepare_resale_trade_payload(request):
    if not isinstance(request.updates, dict):
        raise ValueError("invalid_updates_payload")

    payload = request.model_dump(exclude_none=True)
    updates = payload.pop("updates", {}) or {}
    if not isinstance(updates, dict):
        raise ValueError("invalid_updates_payload")

    payload.update(updates)
    return payload


def _normalize_patch_updates(request_body: Any) -> dict[str, Any]:
    if not isinstance(request_body, dict):
        return {}

    nested_updates = request_body.get("updates")
    if isinstance(nested_updates, dict):
        merged = {**request_body, **nested_updates}
        merged.pop("updates", None)
        return merged

    return dict(request_body)


@app.post("/resale-trades/after-purchase/upsert")
def resale_trades_after_purchase_upsert(request: ResaleTradeAfterPurchaseUpsertRequest):
    try:
        payload = _prepare_resale_trade_payload(request)

        raw_user_id = payload.get("user_id")
        normalized_user_id = _normalize_user_id(raw_user_id)
        if normalized_user_id:
            resolved_user_id = _ensure_user_registered(
                normalized_user_id,
                source="api/resale-trades/after-purchase/upsert",
            )
            payload["user_id"] = resolved_user_id

        return upsert_resale_trade_after_purchase(**payload)
    except ValueError as exc:
        reason = str(exc) or "invalid_payload"
        if reason == "invalid_identity":
            reason = "product_id 또는 url 중 하나는 필요합니다."
        elif reason == "invalid_product_id":
            reason = "product_id를 확인해 주세요."
        elif reason == "invalid_user_id":
            reason = "invalid_user_id"
        elif reason == "invalid_updates_payload":
            reason = "updates는 JSON object 형태여야 합니다."
        return {"ok": False, "reason": reason}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"구매 후 데이터 저장 실패: {exc}"}


@app.post("/resale-trades/after-resale/upsert")
def resale_trades_after_resale_upsert(request: ResaleTradeAfterResaleUpsertRequest):
    try:
        payload = _prepare_resale_trade_payload(request)

        raw_user_id = payload.get("user_id")
        normalized_user_id = _normalize_user_id(raw_user_id)
        if normalized_user_id:
            resolved_user_id = _ensure_user_registered(
                normalized_user_id,
                source="api/resale-trades/after-resale/upsert",
            )
            payload["user_id"] = resolved_user_id

        return upsert_resale_trade_after_resale(**payload)
    except ValueError as exc:
        reason = str(exc) or "invalid_payload"
        if reason == "invalid_identity":
            reason = "product_id 또는 url 중 하나는 필요합니다."
        elif reason == "invalid_product_id":
            reason = "product_id를 확인해 주세요."
        elif reason == "invalid_user_id":
            reason = "invalid_user_id"
        elif reason == "invalid_updates_payload":
            reason = "updates는 JSON object 형태여야 합니다."
        return {"ok": False, "reason": reason}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"되팔이 후 데이터 저장 실패: {exc}"}


@app.post("/users/{user_id}/resale-trade-journeys/from-product")
def create_resale_trade_journey_from_product(user_id: str, request: ResaleTradeJourneyFromProductRequest):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/from-product",
        )
        return create_or_hydrate_resale_trade_journey_from_product(
            user_id=resolved_user_id,
            source=request.source,
            product_id=request.product_id,
        )
    except ValueError as exc:
        reason = str(exc) or "invalid_payload"
        if reason == "invalid_product_id":
            reason = "product_id는 필수입니다."
        elif reason == "invalid_user_id":
            reason = "invalid_user_id"
        return {"ok": False, "reason": reason}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"거래 기록 생성 실패: {exc}"}


@app.post("/trade-journeys/start-from-url")
def start_trade_journey_from_url(request: TradeJourneyStartFromUrlRequest):
    normalized_user_id = _normalize_user_id(request.user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/trade-journeys/start-from-url",
        )
        return start_resale_trade_journey_from_url(
            user_id=resolved_user_id,
            url=request.url,
        )
    except ValueError as exc:
        reason = str(exc)
        if reason == "invalid_url":
            reason = "URL을 확인해 주세요."
        elif reason == "invalid_product_id":
            reason = "URL에서 product_id를 찾지 못했습니다."
        return {"ok": False, "reason": reason}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"URL 거래 기록 시작 실패: {exc}"}


@app.post("/trade-journeys/start-from-alert")
def start_trade_journey_from_alert(request: TradeJourneyStartFromAlertRequest):
    normalized_user_id = _normalize_user_id(request.user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/trade-journeys/start-from-alert",
        )
        return start_resale_trade_journey_from_alert(
            user_id=resolved_user_id,
            alert_event_id=request.alert_event_id,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"알림 기반 거래 기록 시작 실패: {exc}"}


@app.post("/trade-journeys/start-from-read-archive")
def start_trade_journey_from_read_archive(request: TradeJourneyStartFromReadArchiveRequest):
    normalized_user_id = _normalize_user_id(request.user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/trade-journeys/start-from-read-archive",
        )
        return start_resale_trade_journey_from_read_archive(
            user_id=resolved_user_id,
            read_archive_event_id=request.read_archive_event_id,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"읽음 보관함 기반 거래 기록 시작 실패: {exc}"}


@app.patch("/users/{user_id}/resale-trade-journeys/{journey_id}/purchase")
def patch_resale_trade_purchase(user_id: str, journey_id: int, request: dict[str, Any]):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/{id}/purchase",
        )
        updates = _normalize_patch_updates(request)
        return patch_resale_trade_journey_purchase(
            user_id=resolved_user_id,
            journey_id=journey_id,
            updates=updates,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc) or "invalid_payload"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"구매 후 입력 저장 실패: {exc}"}


@app.patch("/users/{user_id}/resale-trade-journeys/{journey_id}/resale")
def patch_resale_trade_resale(user_id: str, journey_id: int, request: dict[str, Any]):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/{id}/resale",
        )
        updates = _normalize_patch_updates(request)
        return patch_resale_trade_journey_resale(
            user_id=resolved_user_id,
            journey_id=journey_id,
            updates=updates,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc) or "invalid_payload"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"되팔이 입력 저장 실패: {exc}"}


@app.patch("/users/{user_id}/resale-trade-journeys/{journey_id}/sold")
def patch_resale_trade_sold(user_id: str, journey_id: int, request: dict[str, Any]):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/{id}/sold",
        )
        updates = _normalize_patch_updates(request)
        return patch_resale_trade_journey_sold(
            user_id=resolved_user_id,
            journey_id=journey_id,
            updates=updates,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc) or "invalid_payload"}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"판매 완료 입력 저장 실패: {exc}"}


@app.get("/users/{user_id}/resale-trade-journeys/completed")
def get_completed_resale_trade_journeys(user_id: str, limit: int = 200):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "items": []}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/completed",
        )
        return list_completed_resale_trade_journeys(
            user_id=resolved_user_id,
            limit=limit,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "items": []}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "items": []}
    except Exception as exc:
        return {"ok": False, "reason": f"완료 거래 조회 실패: {exc}", "items": []}


@app.get("/users/{user_id}/resale-trade-journeys/purchased")
def get_purchased_resale_trade_journeys(user_id: str, limit: int = 200):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "items": []}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/purchased",
        )
        return list_purchased_resale_trade_journeys(
            user_id=resolved_user_id,
            limit=limit,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc), "items": []}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "items": []}
    except Exception as exc:
        return {"ok": False, "reason": f"구매 거래 조회 실패: {exc}", "items": []}


@app.patch("/users/{user_id}/resale-trade-journeys/completed/delete-selected")
def delete_selected_completed_resale_trade_journeys(user_id: str, request: ResaleTradeJourneyDeleteSelectedRequest):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/completed/delete-selected",
        )
        return delete_completed_resale_trade_journeys(
            user_id=resolved_user_id,
            journey_ids=request.journey_ids,
            delete_all=False,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"완료 거래 선택 삭제 실패: {exc}"}


@app.patch("/users/{user_id}/resale-trade-journeys/completed/delete-all")
def delete_all_completed_resale_trade_journeys(user_id: str):
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        resolved_user_id = _ensure_user_registered(
            normalized_user_id,
            source="api/users/{user_id}/resale-trade-journeys/completed/delete-all",
        )
        return delete_completed_resale_trade_journeys(
            user_id=resolved_user_id,
            delete_all=True,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"완료 거래 전체 삭제 실패: {exc}"}


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


@app.api_route("/alert-events/{alert_event_id}/read", methods=["PATCH", "POST"])
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


@app.api_route("/alert-events/read-all", methods=["PATCH", "POST"])
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
