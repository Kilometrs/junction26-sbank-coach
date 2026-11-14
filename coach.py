"""The talking part. The LLM picks an engine function, we run it, the LLM explains the result.

Works with any OpenAI-compatible provider (Gemini by default). Set in .env:
  GEMINI_API_KEY or LLM_API_KEY, optionally LLM_BASE_URL and LLM_MODEL
  (LLM_MODEL can list several models separated by commas: the next one is used when one is over quota or slow).

Chat in the terminal:  python coach.py CUST00152
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, OpenAI

import engine

load_dotenv(Path(__file__).parent / ".env")
MODELS = os.environ.get("LLM_MODEL", "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")
client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    timeout=20,
    max_retries=0,
)


def _complete(convo):
    """Ask the first model that answers. A model over quota or timing out moves to the back of the queue."""
    for model in list(MODELS):
        try:
            return client.chat.completions.create(model=model.strip(), messages=convo, tools=TOOL_SPECS).choices[0].message
        except APIError as e:
            print(f"[coach] {model}: {type(e).__name__}", file=sys.stderr)
            MODELS.append(MODELS.pop(MODELS.index(model)))
    return None

SYSTEM = """You are a personal finance coach inside S-Bank's mobile app. You help one customer understand their own money and build better habits.

How you work:
- Every number you say must come from a tool result or from the profile below. Never calculate or estimate yourself. If you need a number, call a tool.
- Coach by life stage. The same question deserves a different answer for a student, a new parent or someone who lost their job. The life stage changes the safety-net target and what you prioritise.
- If the life stage is only a guess, ask the user to confirm it before you rely on it, in one short question, and mention what made you think so. If they confirm or tell you a different situation, call set_life_stage. Ask about anything else in the profile that you cannot be sure of.
- Priorities, in order: 1) a safety net of a few months of must-pay costs, 2) then saving for goals and bigger purchases.
- Teach the three kinds of spending when it helps: mandatory and regular (rent), mandatory but irregular (a broken washing machine), and everyday spending that slips away (coffees).
- Explain, don't lecture. Be warm, concrete and brief: two to four short sentences, plain words, no jargon. Suggest one small next step when it fits.
- You give education, not investment advice. Never recommend specific financial products.
- Answer in the language the user writes in.

Life stages you can set: {stages}

What we know about this customer (as of {as_of}):
{persona}"""

TOOLS = [
    ("profile", "Full money overview: income, the three spending categories, balance and safety net.", {}),
    ("spending", "How much the customer spent on a category or merchant type over the last N months.", {
        "what": {"type": "string", "description": "A category (Restaurants, Groceries, Travel…) or merchant type (taxis, bars, fuel, cinema…)"},
        "months": {"type": "integer", "description": "How many months back, 1 = the latest month"},
    }),
    ("safe_to_spend", "Flexible money left this month after bills and the safety-net contribution.", {}),
    ("can_i_afford", "Effect of a one-off purchase on the safety net, with a verdict: yes, yes_but or wait.", {
        "amount": {"type": "number", "description": "Price in euros"},
    }),
    ("what_if_cut", "What happens if the customer spends less in one category.", {
        "category": {"type": "string", "enum": list(engine.BUCKET_OF)},
        "percent": {"type": "number", "description": "How much less, in percent"},
    }),
    ("set_life_stage", "Record the life stage after the user confirmed it or told you their situation.", {
        "stage": {"type": "string", "enum": list(engine.LIFE_STAGES)},
    }),
]
TOOL_SPECS = [
    {"type": "function", "function": {"name": name, "description": desc,
                                      "parameters": {"type": "object", "properties": props, "required": list(props)}}}
    for name, desc, props in TOOLS
]


def chat(customer_id, messages, life_stage=None):
    """messages: [{"role": "user"|"assistant", "content": str}, ...]. Returns reply, cards and life stage."""
    cards = []

    def run(name, args):
        nonlocal life_stage
        if name == "set_life_stage":
            life_stage = args["stage"]
            return engine.profile(customer_id, life_stage)["safety_net"] | {"life_stage": life_stage}
        return getattr(engine, name)(customer_id, **args, life_stage=life_stage) if name != "spending" \
            else engine.spending(customer_id, **args)

    p = engine.profile(customer_id, life_stage)
    system = SYSTEM.format(
        stages=", ".join(f"{k} ({v['label']}, {v['target_months']} months)" for k, v in engine.LIFE_STAGES.items()),
        as_of=p["as_of"],
        persona=engine.persona_text(p),
    )
    convo = [{"role": "system", "content": system}, *messages]

    for _ in range(6):  # tool rounds
        msg = _complete(convo)
        if msg is None:
            return {"reply": "The coach can't reach its language model right now. Please try again in a moment.",
                    "cards": cards, "life_stage": life_stage, "error": "llm_unavailable"}
        if not msg.tool_calls:
            return {"reply": msg.content, "cards": cards, "life_stage": life_stage}
        convo.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            try:
                result = run(call.function.name, args)
            except Exception as e:  # bad arguments from the model: let it retry
                result = {"error": str(e)}
            cards.append({"tool": call.function.name, "args": args, "result": result})
            convo.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return {"reply": "Sorry, I got stuck on that one. Could you ask it another way?", "cards": cards, "life_stage": life_stage}


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST00152"
    history, stage = [], None
    print(engine.persona_text(engine.profile(cid)), "\n")
    while True:
        try:
            text = input("you> ")
        except (EOFError, KeyboardInterrupt):
            break
        history.append({"role": "user", "content": text})
        out = chat(cid, history, stage)
        stage = out["life_stage"]
        history.append({"role": "assistant", "content": out["reply"]})
        for c in out["cards"]:
            print(f"  [{c['tool']} {c['args']}] -> {c['result']}")
        print(f"coach> {out['reply']}\n")
