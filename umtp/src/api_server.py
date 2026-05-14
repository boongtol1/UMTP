from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.analysis_service import analyze_url_for_user
from src.user_watch_rules import (
    delete_user_watch_rule,
    get_recommended_watch_keywords,
    list_user_watch_rules,
    request_immediate_poll,
    set_watch_rule_enabled,
    upsert_user_watch_rule,
)
from src.user_settings_service import (
    get_all_macbook_air_units_sorted,
    get_user_fair_price_settings,
    register_user,
    upsert_user_fair_price_setting,
)


app = FastAPI(title="UMTP API", version="1.0")


class AnalyzeUrlRequest(BaseModel):
    user_id: str
    url: str


class UserRegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    device_id: Optional[str] = Field(default=None, max_length=200)


class UserFairPriceUpsertRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    product_type: str = Field(..., min_length=1, max_length=100)
    chip: Literal["M1", "M2", "M3", "M4", "M5"]
    screen_inch: int
    ram_gb: int
    ssd_gb: int
    fair_price_krw: int = Field(..., gt=0)
    alert_drop_rate_percent: float = Field(..., ge=0, le=100)
    enabled: bool


class UserWatchRuleUpsertRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    product_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    chip: Optional[str] = Field(default=None, min_length=1, max_length=20)
    screen_inch: Optional[int] = None
    ram_gb: Optional[int] = None
    ssd_gb: Optional[int] = None
    search_keyword: Optional[str] = Field(default=None, max_length=255)
    enabled: bool = True
    poll_interval_seconds: int = Field(default=60, ge=1)
    target_price_krw: Optional[int] = None
    fair_price_krw: Optional[int] = None


class UserWatchRuleSetEnabledRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    search_keyword: str = Field(..., min_length=1, max_length=255)
    enabled: bool


class UserWatchRuleDeleteRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    search_keyword: str = Field(..., min_length=1, max_length=255)


class UserWatchRuleRequestPollNowRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    search_keyword: str = Field(..., min_length=1, max_length=255)


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
    normalized_user_id = user_id.strip() if isinstance(user_id, str) else ""
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "items": []}

    try:
        items = get_user_fair_price_settings(normalized_user_id)
        return {"ok": True, "user_id": normalized_user_id, "items": items}
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

    if not user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        return register_user(
            user_id=user_id,
            device_id=device_id if device_id else None,
        )
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"사용자 등록 실패: {exc}",
            "user_id": user_id,
        }


@app.post("/user-fair-prices/upsert")
def user_fair_prices_upsert(request: UserFairPriceUpsertRequest):
    try:
        return upsert_user_fair_price_setting(
            user_id=request.user_id,
            product_type=request.product_type,
            chip=request.chip,
            screen_inch=request.screen_inch,
            ram_gb=request.ram_gb,
            ssd_gb=request.ssd_gb,
            fair_price_krw=request.fair_price_krw,
            alert_drop_rate_percent=request.alert_drop_rate_percent,
            enabled=request.enabled,
        )
    except Exception as exc:
        return {"ok": False, "reason": f"사용자 공정가 설정 저장 실패: {exc}"}


@app.get("/user-watch-rules")
def user_watch_rules(user_id: str):
    normalized_user_id = user_id.strip() if isinstance(user_id, str) else ""
    if not normalized_user_id:
        return {"ok": False, "reason": "invalid_user_id", "items": []}

    try:
        items = list_user_watch_rules(normalized_user_id)
        return {
            "ok": True,
            "user_id": normalized_user_id,
            "items": items,
        }
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"감시 조건 조회 실패: {exc}",
            "user_id": normalized_user_id,
            "items": [],
        }


@app.post("/user-watch-rules/upsert")
def user_watch_rules_upsert(request: UserWatchRuleUpsertRequest):
    try:
        return upsert_user_watch_rule(
            user_id=request.user_id,
            product_type=request.product_type,
            chip=request.chip,
            screen_inch=request.screen_inch,
            ram_gb=request.ram_gb,
            ssd_gb=request.ssd_gb,
            search_keyword=request.search_keyword,
            enabled=request.enabled,
            poll_interval_seconds=request.poll_interval_seconds,
            target_price_krw=request.target_price_krw,
            fair_price_krw=request.fair_price_krw,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except Exception as exc:
        return {"ok": False, "reason": f"감시 조건 저장 실패: {exc}"}


@app.post("/user-watch-rules/set-enabled")
def user_watch_rules_set_enabled(request: UserWatchRuleSetEnabledRequest):
    try:
        return set_watch_rule_enabled(
            user_id=request.user_id,
            search_keyword=request.search_keyword,
            enabled=request.enabled,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except Exception as exc:
        return {"ok": False, "reason": f"감시 조건 상태 변경 실패: {exc}"}


@app.post("/user-watch-rules/delete")
def user_watch_rules_delete(request: UserWatchRuleDeleteRequest):
    try:
        return delete_user_watch_rule(
            user_id=request.user_id,
            search_keyword=request.search_keyword,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except Exception as exc:
        return {"ok": False, "reason": f"감시 조건 삭제 실패: {exc}"}


@app.post("/user-watch-rules/request-poll-now")
def user_watch_rules_request_poll_now(request: UserWatchRuleRequestPollNowRequest):
    try:
        return request_immediate_poll(
            user_id=request.user_id,
            search_keyword=request.search_keyword,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except Exception as exc:
        return {"ok": False, "reason": f"즉시 검색 요청 실패: {exc}"}


@app.get("/user-watch-rules/recommended-keywords")
def user_watch_rules_recommended_keywords(
    product_type: str,
    chip: str,
    ram_gb: Optional[int] = None,
    ssd_gb: Optional[int] = None,
):
    try:
        items = get_recommended_watch_keywords(
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
        return {"ok": False, "reason": str(exc), "items": []}
    except Exception as exc:
        return {"ok": False, "reason": f"추천 검색어 조회 실패: {exc}", "items": []}


@app.post("/analyze-url")
def analyze_url(request: AnalyzeUrlRequest):
    try:
        return analyze_url_for_user(
            user_id=request.user_id,
            url=request.url,
        )
    except Exception as exc:
        return {
            "ok": False,
            "status": "failed",
            "url": request.url,
            "reason": f"API 처리 실패: {exc}",
        }
