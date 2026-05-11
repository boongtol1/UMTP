from fastapi import FastAPI
from pydantic import BaseModel

from src.analysis_service import analyze_url_for_user


app = FastAPI(title="UMTP API", version="0.9")


class AnalyzeUrlRequest(BaseModel):
    user_id: str
    url: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze-url")
def analyze_url(request: AnalyzeUrlRequest):
    return analyze_url_for_user(
        user_id=request.user_id,
        url=request.url,
    )
