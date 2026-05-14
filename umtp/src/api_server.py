from fastapi import FastAPI
from pydantic import BaseModel

from src.analysis_service import analyze_url_for_user
from src.user_settings_service import get_all_macbook_air_units_sorted


app = FastAPI(title="UMTP API", version="1.0")


class AnalyzeUrlRequest(BaseModel):
    user_id: str
    url: str


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
