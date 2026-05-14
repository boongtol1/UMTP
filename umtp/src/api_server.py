from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.analysis_service import analyze_url_for_user
from src.user_settings_service import get_all_macbook_air_units_sorted, register_user


app = FastAPI(title="UMTP API", version="1.0")


class AnalyzeUrlRequest(BaseModel):
    user_id: str
    url: str


class UserRegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    nickname: Optional[str] = Field(default=None, max_length=100)


@app.get("/health")
def health():
    return {"ok": True}


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


@app.post("/users/register")
def users_register(request: UserRegisterRequest):
    user_id = request.user_id.strip() if isinstance(request.user_id, str) else ""
    nickname = request.nickname.strip() if isinstance(request.nickname, str) else None

    if not user_id:
        return {"ok": False, "reason": "invalid_user_id"}

    try:
        return register_user(user_id=user_id, nickname=nickname)
    except Exception as exc:
        return {"ok": False, "reason": f"사용자 등록 실패: {exc}", "user_id": user_id}


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
