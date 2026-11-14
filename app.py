"""JSON API for the UI.

Run:  uvicorn app:app --reload     then open http://localhost:8000 for the debug page.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import coach
import engine

app = FastAPI(title="S-Bank coach")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEMO = {
    "CUST00152": "Student, 21, almost no safety net",
    "CUST00001": "Stable job, 63, close to target",
    "CUST00007": "Stable job, 49, big safety net",
    "CUST05014": "Irregular income, 23",
    "CUST00983": "Just started paying for housing, 48",
    "CUST00394": "Buying a home, 45",
}


class ChatIn(BaseModel):
    customer_id: str
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
    life_stage: str | None = None


@app.get("/customers")
def customers():
    return [{"id": cid, "label": label} for cid, label in DEMO.items()]


@app.get("/life-stages")
def life_stages():
    return engine.LIFE_STAGES


@app.get("/profile/{customer_id}")
def profile(customer_id: str, life_stage: str | None = None):
    p = engine.profile(customer_id, life_stage)
    return p | {"safe_to_spend": engine.safe_to_spend(customer_id, life_stage), "persona_text": engine.persona_text(p)}


@app.post("/chat")
def chat(body: ChatIn):
    return coach.chat(body.customer_id, body.messages, body.life_stage)


@app.get("/")
def debug_page():
    return FileResponse(Path(__file__).parent / "debug.html")
