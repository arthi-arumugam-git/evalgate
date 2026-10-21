"""HTTP surface for HelpDesk (deployed to Cloud Run) + EvalGate live scorecard."""
import json, os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.bot import answer, mock_mode

app = FastAPI(title="HelpDesk (guarded by EvalGate)")
REPORT = Path(os.getenv("EVALGATE_REPORT", "out/report.json"))


class Q(BaseModel):
    question: str


@app.get("/healthz")
def healthz():
    return {"ok": True, "mock": mock_mode(), "version": os.getenv("APP_VERSION", "dev")}


@app.post("/chat")
def chat(q: Q):
    return answer(q.question)


@app.get("/", response_class=HTMLResponse)
def scorecard():
    from evalgate.report import render_html
    data = json.loads(REPORT.read_text()) if REPORT.exists() else None
    return render_html(data)
