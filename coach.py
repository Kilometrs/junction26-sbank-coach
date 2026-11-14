"""The talking part. The LLM picks an engine function, we run it, the LLM explains the result.

Works with any OpenAI-compatible provider (Gemini by default). Set in .env:
  GEMINI_API_KEY or LLM_API_KEY, optionally LLM_BASE_URL and LLM_MODEL
  (LLM_MODEL can list several models separated by commas: the next one is used when one is over quota or slow).

Chat in the terminal:  python coach.py CUST00152
"""
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, OpenAI

import charts
import engine

load_dotenv(Path(__file__).parent / ".env")
MODELS = os.environ.get("LLM_MODEL", "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", 1500))  # per model call: room for an answer with two charts, no more
client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    # Gemini sometimes times out, rate-limits (429) or is overloaded (5xx). The client retries such a call once,
    # after a short pause (longer when Gemini says how long to wait); if that fails too, the next model takes over.
    timeout=30,
    max_retries=1,
)


def _complete(convo, answer_now=False):
    """Ask the first model that answers. A model that still fails after its retry moves to the back of the queue.

    answer_now: no more tool calls, the model has to write its reply."""
    for model in list(MODELS):
        try:
            return client.chat.completions.create(model=model.strip(), messages=convo, tools=TOOL_SPECS, max_tokens=MAX_TOKENS,
                                                  tool_choice="none" if answer_now else "auto").choices[0].message
        except APIError as e:
            print(f"[coach] {model}: {type(e).__name__}", file=sys.stderr)
            MODELS.append(MODELS.pop(MODELS.index(model)))
    return None

SYSTEM = """You are a personal finance coach inside S-Bank's mobile app. You help one customer understand their own money and build better habits.

How you work:
- Every number you say must come from a tool result or from the profile below. Never calculate or estimate yourself. If you need a number, call a tool.
- Coach by life stage. The same question deserves a different answer for a student, a new parent or someone who lost their job. The life stage changes the safety-net target and what you prioritise.
- If the life stage is only a guess, confirm it once: when the question depends on it (affording something, goals, the safety net), add one short question at the end and mention what made you think so. Do not ask again if you already asked in this conversation, and do not ask on simple lookups like "how much did I spend on X".
- If the user confirms or tells you a different situation, call set_life_stage. Ask about anything else in the profile that you cannot be sure of.
- If the user lost their job, their income figures are out of date: talk about the balance as a runway (how many months of must-pay costs it covers) and do not promise any monthly surplus.
- Monthly figures in the profile are averages of the last 6 months; one month alone can be much higher or lower. When you give a number, say what it covers ("on average", "in September"). If two figures differ, they cover different periods: explain that, and never say an earlier figure was wrong unless a tool result shows it was.
- Your earlier replies in this conversation were built on tool results that are no longer shown to you. Treat their figures as checked: do not apologise for them or "correct" them. Just call the tools again for what you need now.
- Priorities, in order: 1) a safety net of a few months of must-pay costs, 2) then saving for goals and bigger purchases.
- Teach the three kinds of spending when it helps: mandatory and regular (rent), mandatory but irregular (a broken washing machine), and everyday spending that slips away (coffees).
- When comparing with peers, be kind: it is information, not a judgement.
- Say how full the safety net is as a percentage of its target ("your safety net is at 26% of its target") or in euros. Never use fractions of a month like "0.3 months" or "0.5 months"; for a runway say whole months, or "less than a month". Never give negative months.
- Explain, don't lecture. Be warm, concrete and brief: two to four short sentences, plain words, no jargon. Suggest one small next step when it fits.
- The app shows your reply as plain text. You may put **bold** around the one key figure or verdict. When you list several items (categories, bills, options), put each on its own line starting with "- ", with the name first and the amount after it, and put the total on its own line; never run a list together in one sentence. Use no other Markdown (no headings, no tables). List amounts from largest to smallest (tools return them in that order; months stay in time order). The profile tool's by_bucket_monthly gives the categories of each kind of spending (fixed, irregular, flexible) with that group's total: use those totals as they are and never put a total next to a group it does not belong to. mandatory_monthly is fixed plus irregular together.
- You give education, not investment advice. Never recommend specific financial products.
- When you talk to the user, call it their "situation" ("your situation", "in your situation"), never their "life stage" or "stage".
- Answer in the language the user writes in. That language goes for everything you produce: your reply, chart titles and labels, and answer buttons. S-Bank is Finnish, but do not use Finnish unless the user wrote in Finnish.

{charts}

Questions with answer buttons:
- When you ask the user something with a few clear answers (yes or no, confirming a life-stage guess, picking one of a few options), call ask_with_options with 2 to 4 short answers. Write them in the same language as your reply (the language of the user's last message), the way the user would say them: for an English question, for example "Yes, I'm a student" and "No, something else".
- The app shows them as buttons under your reply, and the user can still type something else. End your reply with the question itself, and ask at most one such question per reply. Call it in the same step as your charts. It is a tool call: never write its name or [[...]] for it in your reply.

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
    ("goal_plan", "Plan for saving towards a goal: monthly amount needed, whether it fits, and whether the safety net should come first.", {
        "amount": {"type": "number", "description": "Goal in euros"},
        "months": {"type": "integer", "description": "Months until the money is needed"},
    }),
    ("compare_to_peers", "Compare the customer's monthly spending in one category with customers of similar age and income.", {
        "category": {"type": "string", "enum": list(engine.BUCKET_OF)},
    }),
    ("upcoming_bills", "Regular bills and salary to expect next month.", {}),
    ("trend", "Month-by-month spending and whether it is going up or down.", {
        "what": {"type": "string", "description": "A category, a bucket (fixed, irregular, flexible) or 'all'"},
        "months": {"type": "integer", "description": "How many months to look at, usually 6"},
    }),
    ("set_life_stage", "Record the life stage after the user confirmed it or told you their situation.", {
        "stage": {"type": "string", "enum": list(engine.LIFE_STAGES)},
    }),
]
STAGE_FREE = {"spending", "compare_to_peers", "upcoming_bills", "trend"}  # same answer for every life stage
TOOL_SPECS = [
    {"type": "function", "function": {"name": name, "description": desc,
                                      "parameters": {"type": "object", "properties": props, "required": list(props)}}}
    for name, desc, props in TOOLS
] + charts.CHART_SPECS

ASK = "ask_with_options"
TOOL_SPECS.append({"type": "function", "function": {
    "name": ASK,
    "description": "Show the user buttons with answers to the question you end your reply with, for example yes and no.",
    "parameters": {"type": "object", "properties": {"options": {
        "type": "array", "items": {"type": "string"},
        "description": "2 to 4 short answers in the same language as your reply, written as the user would say them",
    }}, "required": ["options"]},
}})


def answer_options(args):
    """The answers to show as buttons: 2-4 different, short ones. Raises ValueError saying what to fix."""
    options, seen = [], set()
    for o in args.get("options") or []:
        text = " ".join(str(o).split())
        if text and text.lower() not in seen:
            seen.add(text.lower())
            options.append(text)
    if not 2 <= len(options) <= 4:
        raise ValueError("Give 2 to 4 different answers.")
    if too_long := [o for o in options if len(o) > 40]:
        raise ValueError(f"Keep each answer under 40 characters: {too_long}")
    return options


_STRAY_TAG = re.compile(r"\[\[(?!chart:)[^\]\n]*\]\]")


def finish(reply, drawn):
    """The reply as the app shows it: no leftover [[tags]], and its chart markers tidied."""
    return charts.place_charts(_STRAY_TAG.sub("", reply or ""), drawn)


HISTORY = 10  # messages sent to the model; older ones are left out to keep each call small


def recent(messages):
    """The last HISTORY messages, starting with one of the user's."""
    kept = messages[-HISTORY:]
    while kept and kept[0]["role"] != "user":
        kept = kept[1:]
    return kept or messages[-1:]


def chat(customer_id, messages, life_stage=None):
    """messages: [{"role": "user"|"assistant", "content": str}, ...]. Returns reply, cards, charts and life stage.

    cards are the engine calls behind the reply ({tool, args, result}). charts are the charts the coach drew,
    by id; the reply has a [[chart:id]] line where each one goes. options are answers to the question the reply
    ends with, for the app to show as buttons (empty when there is none)."""
    cards, drawn, options = [], {}, []

    def ask(args):
        nonlocal options
        options = answer_options(args)  # a second call replaces the first: one question per reply
        return {"shown": options, "next": "End your reply with the question these answer."}

    def run(name, args):
        nonlocal life_stage
        if name == "set_life_stage":
            life_stage = args["stage"]
            return engine.profile(customer_id, life_stage)["safety_net"] | {"life_stage": life_stage}
        if name in STAGE_FREE:
            return getattr(engine, name)(customer_id, **args)
        return getattr(engine, name)(customer_id, **args, life_stage=life_stage)

    p = engine.profile(customer_id, life_stage)
    persona = engine.persona_text(p)
    system = SYSTEM.format(
        charts=charts.PROMPT,
        stages=", ".join(f"{k} ({v['label']}, {v['target_months']} months)" for k, v in engine.LIFE_STAGES.items()),
        as_of=p["as_of"],
        persona=persona,
    )
    convo = [{"role": "system", "content": system}, *recent(messages)]

    def draw(name, args):
        """Check a chart call against the numbers the engine gave in this reply, and keep it."""
        results = [p, persona] + [c["result"] for c in cards if not (isinstance(c["result"], dict) and "error" in c["result"])]
        data = charts.allowed_numbers(*results)
        spec = charts.validate_chart(name, args, data, data | charts.allowed_numbers(*(c["args"] for c in cards)))
        cid = f"c{len(drawn) + 1}"
        drawn[cid] = spec
        return {"chart_id": cid, "place_it_with": f"[[chart:{cid}]]"}

    said = []  # text the model wrote alongside its tool calls: the answer if the last message has none
    rounds = 8  # tool rounds; chart and question calls count too
    for i in range(rounds):
        msg = _complete(convo, answer_now=i == rounds - 1)
        if msg is None:
            return {"reply": "The coach can't reach its language model right now. Please try again in a moment.",
                    "cards": cards, "charts": {}, "options": [], "life_stage": life_stage, "error": "llm_unavailable"}
        if not msg.tool_calls or i == rounds - 1:
            reply = msg.content or ""
            if not charts.MARKER.sub("", reply).strip():  # the answer came with the tool calls, only markers at the end
                reply = "\n\n".join(t for t in [*said, reply] if t.strip())
            return {"reply": finish(reply, drawn), "cards": cards, "charts": drawn, "options": options,
                    "life_stage": life_stage}
        if msg.content and msg.content.strip():
            said.append(msg.content)
        convo.append(msg.model_dump(exclude_none=True))
        needs_data = False  # an engine call or a rejected chart this step: the model must see the results
        for call in msg.tool_calls:
            name, args = call.function.name, {}
            try:
                args = json.loads(call.function.arguments or "{}")
                if name in charts.CHART_NAMES:
                    result = draw(name, args)
                elif name == ASK:
                    result = ask(args)
                else:
                    result = run(name, args)
            except Exception as e:  # bad arguments from the model: let it retry
                result = {"error": str(e)}
            if name not in charts.CHART_NAMES and name != ASK:
                cards.append({"tool": name, "args": args, "result": result})
                needs_data = True
            elif "error" in result:
                print(f"[coach] {name} rejected: {result['error']}", file=sys.stderr)
                needs_data = True  # let the model fix it
            convo.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        # The answer came together with its charts and question, and they were all accepted: done, no extra call.
        text = msg.content or ""
        if not needs_data and charts.MARKER.sub("", text).strip():
            return {"reply": finish(text, drawn), "cards": cards, "charts": drawn, "options": options,
                    "life_stage": life_stage}
    return {"reply": "Sorry, I got stuck on that one. Could you ask it another way?", "cards": cards, "charts": {}, "options": [],
            "life_stage": life_stage}


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
