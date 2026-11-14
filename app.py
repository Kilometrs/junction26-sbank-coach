"""JSON API for the UI.

Run:  uvicorn app:app --reload     then open http://localhost:8000 for the debug page.
"""
import os
import threading
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import coach
import engine

# The phone app built for the browser (the Dockerfile puts it in web/). When it is there this is the hosted demo:
# the server shows the app at /, so one address serves the app and its API, and the pages meant for development
# (the debug page, FastAPI's automatic API pages) are switched off.
WEB = Path(__file__).parent / "web"
HOSTED = WEB.is_dir()
app = FastAPI(title="S-Bank coach", **({"docs_url": None, "redoc_url": None, "openapi_url": None} if HOSTED else {}))
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEMO = engine.DEMO_CUSTOMERS


def _demo_customer(customer_id):
    """The API only serves the demo customers: nobody can ask for another id, or for a path dressed up as one."""
    if customer_id not in DEMO:
        raise HTTPException(404, "Unknown customer. GET /customers lists the demo customers.")


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
    _demo_customer(customer_id)
    p = engine.profile(customer_id, life_stage)
    return p | {"safe_to_spend": engine.safe_to_spend(customer_id, life_stage), "persona_text": engine.persona_text(p),
                "insight": engine.insight(customer_id)["text"]}


# Limits that keep a public demo from burning the language-model budget. All can be changed in .env.
PER_MINUTE = int(os.environ.get("CHAT_PER_MINUTE", 10))  # messages per visitor (IP address) per minute
DAILY_LIMIT = int(os.environ.get("CHAT_DAILY_LIMIT", 1500))  # messages from everyone per day
MAX_MESSAGE = int(os.environ.get("CHAT_MAX_MESSAGE", 500))  # characters in the message being sent
MAX_HISTORY_TEXT = 2000  # characters kept of each earlier message
# Proxies in front of the server that add the visitor's address to X-Forwarded-For: 0 when visitors connect
# directly (the header is then ignored, because anyone can write it), 1 on Cloud Run.
PROXY_HOPS = int(os.environ.get("CHAT_PROXY_HOPS", 0))
_lock = threading.Lock()  # handlers run in a thread pool
_recent = defaultdict(deque)  # visitor -> times of their messages in the last minute
_today = {"day": None, "count": 0}


def _refuse(body, message, error):
    """Same shape as a normal reply, so the app shows it as a coach message."""
    return {"reply": message, "cards": [], "charts": {}, "options": [], "life_stage": body.life_stage, "error": error}


def _visitor(request):
    """Who to count a message against. Each proxy appends the address it saw to X-Forwarded-For, so only the
    last PROXY_HOPS entries can be trusted; anything before them was written by the caller."""
    forwarded = [a.strip() for a in request.headers.get("x-forwarded-for", "").split(",") if a.strip()]
    if PROXY_HOPS and len(forwarded) >= PROXY_HOPS:
        return forwarded[-PROXY_HOPS]
    return request.client.host if request.client else "?"


@app.post("/chat")
def chat(body: ChatIn, request: Request):
    _demo_customer(body.customer_id)
    messages = [m for m in body.messages if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    if not messages or messages[-1]["role"] != "user":
        return _refuse(body, "I didn't get a question. Could you send it again?", "bad_request")
    if len(messages[-1]["content"]) > MAX_MESSAGE:
        return _refuse(body, f"That message is too long for this demo. Please keep it under {MAX_MESSAGE} characters.", "too_long")

    with _lock:
        if _today["day"] != date.today():  # before reading _recent, so today's first message is counted too
            _today.update(day=date.today(), count=0)
            _recent.clear()
        now, sent = time.monotonic(), _recent[_visitor(request)]
        while sent and now - sent[0] > 60:
            sent.popleft()
        if len(sent) >= PER_MINUTE:
            return _refuse(body, "You're sending messages very quickly. Please wait a moment and try again.", "rate_limited")
        if _today["count"] >= DAILY_LIMIT:
            return _refuse(body, "This demo has used up its budget for today. Please come back tomorrow.", "daily_limit")
        sent.append(now)
        _today["count"] += 1

    messages = [{"role": m["role"], "content": m["content"][:MAX_HISTORY_TEXT]} for m in messages]
    out = coach.chat(body.customer_id, messages, body.life_stage)
    # For the app's simulated "start saving in S-mobiili" button: an amount the engine worked out, or None.
    out["saving_offer"] = None if out.get("error") else engine.saving_offer(out["cards"])
    return out


if HOSTED:
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
else:

    @app.get("/")
    def debug_page():
        return FileResponse(Path(__file__).parent / "debug.html")
