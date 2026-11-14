"""JSON API for the UI.

Run:  uvicorn app:app --reload     then open http://localhost:8000 for the debug page.
"""
import os
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
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


# Limits that keep a public demo from burning the language-model budget. All can be changed in .env.
PER_MINUTE = int(os.environ.get("CHAT_PER_MINUTE", 10))  # messages per visitor (IP address) per minute
DAILY_LIMIT = int(os.environ.get("CHAT_DAILY_LIMIT", 1500))  # messages from everyone per day
MAX_MESSAGE = int(os.environ.get("CHAT_MAX_MESSAGE", 500))  # characters in the message being sent
MAX_HISTORY_TEXT = 2000  # characters kept of each earlier message
_recent = defaultdict(deque)  # visitor -> times of their messages in the last minute
_today = {"day": None, "count": 0}


def _refuse(body, message, error):
    """Same shape as a normal reply, so the app shows it as a coach message."""
    return {"reply": message, "cards": [], "charts": {}, "options": [], "life_stage": body.life_stage, "error": error}


@app.post("/chat")
def chat(body: ChatIn, request: Request):
    messages = [m for m in body.messages if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    if not messages or messages[-1]["role"] != "user":
        return _refuse(body, "I didn't get a question. Could you send it again?", "bad_request")
    if len(messages[-1]["content"]) > MAX_MESSAGE:
        return _refuse(body, f"That message is too long for this demo. Please keep it under {MAX_MESSAGE} characters.", "too_long")

    # Behind a proxy (Cloud Run) the visitor's address is the first one in X-Forwarded-For.
    visitor = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    now, sent = time.monotonic(), _recent[visitor]
    while sent and now - sent[0] > 60:
        sent.popleft()
    if len(sent) >= PER_MINUTE:
        return _refuse(body, "You're sending messages very quickly. Please wait a moment and try again.", "rate_limited")
    if _today["day"] != date.today():
        _today.update(day=date.today(), count=0)
        _recent.clear()
    if _today["count"] >= DAILY_LIMIT:
        return _refuse(body, "This demo has used up its budget for today. Please come back tomorrow.", "daily_limit")
    sent.append(now)
    _today["count"] += 1

    messages = [{"role": m["role"], "content": m["content"][:MAX_HISTORY_TEXT]} for m in messages]
    return coach.chat(body.customer_id, messages, body.life_stage)


@app.get("/")
def debug_page():
    return FileResponse(Path(__file__).parent / "debug.html")
