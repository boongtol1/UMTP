from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.analysis_service import analyze_url_for_user
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
