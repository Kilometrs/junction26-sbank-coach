"""Chart tools the coach can call to draw inside its reply.

The model picks the chart type, labels and values; the app draws it. Every number in a chart must be one the
engine returned while answering this message (or that is in the customer's profile), so a chart can never show a
number the model made up. A chart call that breaks this gets an error back and the model can fix it.

The reply places a chart with a [[chart:c1]] line; place_charts() tidies those markers.
"""
import math
import re

UNITS = ["eur", "months", "percent", "count"]
_TEXT = {"type": "string"}
_NUM = {"type": "number"}
_UNIT = {"type": "string", "enum": UNITS}
_ARR = lambda items: {"type": "array", "items": items}  # noqa: E731
_OBJ = lambda required, **props: {"type": "object", "properties": props, "required": required}  # noqa: E731
_LABELLED = _OBJ(["label", "value"], label=_TEXT, value=_NUM)
# Kept short on purpose: these definitions are sent with every call. How to use them is in PROMPT.
_COMMON = {"title": _TEXT, "note": _TEXT}

CHART_TOOLS = [
    ("bar_chart", "Horizontal bar chart. Each series has one value per category.", {
        **_COMMON, "unit": _UNIT, "categories": _ARR(_TEXT),
        "series": _ARR(_OBJ(["name", "values"], name=_TEXT, values=_ARR(_NUM))),
        "highlight": {"type": "string", "description": "A category to stand out"},
        "stacked": {"type": "boolean"},
    }, ["title", "unit", "categories", "series"]),
    ("line_chart", "Line chart. x_unit months: series have points, x = months from now. x_unit labels: series have one value per x label.", {
        **_COMMON, "unit": _UNIT, "x_unit": {"type": "string", "enum": ["months", "labels"]}, "x_labels": _ARR(_TEXT),
        "series": _ARR(_OBJ(["name"], name=_TEXT, points=_ARR(_OBJ(["x", "y"], x=_NUM, y=_NUM)), values=_ARR(_NUM),
                            dashed={"type": "boolean"})),
        "reference": {**_LABELLED, "description": "Horizontal target line"},
    }, ["title", "unit", "x_unit", "series"]),
    ("progress", "Progress bars towards a target.", {
        **_COMMON, "unit": _UNIT, "bars": _ARR(_LABELLED), "target": _LABELLED, "badge": _TEXT,
    }, ["title", "unit", "bars"]),
    ("key_figures", "A few key numbers: an optional headline and rows. sign shows +€ or −€.", {
        **_COMMON, "badge": _TEXT,
        "headline": _OBJ(["label", "value", "unit"], label=_TEXT, value=_NUM, unit=_UNIT),
        "rows": _ARR(_OBJ(["label", "value", "unit"], label=_TEXT, value=_NUM, unit=_UNIT,
                          sign={"type": "string", "enum": ["plus", "minus"]})),
    }, ["title", "rows"]),
]
CHART_NAMES = {name for name, *_ in CHART_TOOLS}
CHART_SPECS = [
    {"type": "function", "function": {"name": name, "description": desc,
                                      "parameters": {"type": "object", "properties": props, "required": required}}}
    for name, desc, props, required in CHART_TOOLS
]

PROMPT = """Charts:
- You can draw a chart inside your reply with bar_chart, line_chart, progress or key_figures, once you have the numbers. Charts are numbered c1, c2… in the order you draw them in this answer. To save time, draw the charts and write your whole answer in the same step, with [[chart:c1]] on a line of its own right after the sentence it belongs to.
- Every value in a chart must be a number a tool returned while answering this message, copied exactly. Never calculate, round or combine numbers for a chart: if you need a number, call a tool. A chart call with other numbers is rejected; then fix it or leave the chart out.
- Good charts for each tool:
  - safe_to_spend: key_figures, headline = left, rows = flexible_budget, safety_net_contribution and spent_so_far.
  - can_i_afford: progress in months, bars = months_before and months_after, target = target_months.
  - what_if_cut: line_chart with x_unit months, a line from (0, 0) to (months_to_target_after, missing_eur), the current pace dashed from (0, 0) to (months_to_target_now, missing_eur) when it is not null, reference = missing_eur.
  - goal_plan: when the safety net comes first, a stacked bar_chart in months with one category and two series, months_to_fill_safety_net_first and months_at_current_surplus; otherwise key_figures with needed_monthly and monthly_surplus.
  - upcoming_bills: key_figures, one row per bill with sign minus, the salary with sign plus.
  - trend: bar_chart with one bar per month, highlight = highest_month.
  - compare_to_peers: bar_chart with two categories, the customer and a typical peer; put who the peers are in note.
  - spending: key_figures with total and usual_per_month.
- Write titles and labels in the user's language. Draw a chart when your answer rests on a tool result, at most two per answer, and let your sentence point at the chart instead of repeating all of its numbers."""


def _num_key(v):
    return round(abs(float(v)), 6)


_NUMBER_IN_TEXT = re.compile(r"\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?")


def _numbers_in_text(text):
    out = []
    for m in _NUMBER_IN_TEXT.findall(text):
        s = re.sub(r"[   ]", "", m)
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):  # 1,200 and 1,200.5: thousands
            s = s.replace(",", "")
        out.append(float(s.replace(",", ".")))  # 1,5: Finnish decimal comma
    return out


def allowed_numbers(*sources):
    """Every number in the given engine results: values, numbers inside strings, and dict keys like "2026-04"."""
    found = {0.0}

    def walk(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            if math.isfinite(x):
                found.add(_num_key(x))
        elif isinstance(x, str):
            found.update(_num_key(n) for n in _numbers_in_text(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)

    for s in sources:
        walk(s)
    return found


class ChartError(ValueError):
    pass


def _need(cond, message):
    if not cond:
        raise ChartError(message)


def validate_chart(kind, spec, data_numbers, text_numbers):
    """Check a chart call. data_numbers: numbers from the engine; text_numbers: those plus the tool arguments.

    Returns the cleaned spec with its "type", or raises ChartError saying what to fix."""
    _need(kind in CHART_NAMES, f"Unknown chart type {kind}.")
    _need(isinstance(spec.get("title"), str) and spec["title"].strip(), "A chart needs a title.")
    values, texts = [], [spec["title"], spec.get("note", ""), spec.get("badge", "")]

    def value(v, where):
        _need(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v), f"{where}: {v!r} is not a number.")
        values.append((v, where))
        return v

    def unit(u, where="unit"):
        _need(u in UNITS, f"{where} must be one of {', '.join(UNITS)}.")
        return u

    out = {"type": kind, "title": spec["title"].strip()}
    for key in ("note", "badge"):
        if isinstance(spec.get(key), str) and spec[key].strip():
            out[key] = spec[key].strip()

    if kind == "bar_chart":
        out["unit"] = unit(spec.get("unit"))
        cats = spec.get("categories") or []
        series = spec.get("series") or []
        _need(cats and all(isinstance(c, str) for c in cats), "categories must be a list of labels.")
        _need(series, "series must have at least one series.")
        out["categories"] = cats
        out["series"] = []
        for s in series:
            vals = s.get("values") or []
            _need(len(vals) == len(cats), f"series '{s.get('name')}' needs one value per category ({len(cats)}).")
            out["series"].append({"name": str(s.get("name", "")), "values": [value(v, f"series '{s.get('name')}'") for v in vals]})
            texts.append(str(s.get("name", "")))
        texts += cats
        if spec.get("highlight") in cats:
            out["highlight"] = spec["highlight"]
        out["stacked"] = bool(spec.get("stacked"))

    elif kind == "line_chart":
        out["unit"] = unit(spec.get("unit"))
        out["x_unit"] = spec.get("x_unit")
        _need(out["x_unit"] in ("months", "labels"), "x_unit must be months or labels.")
        series = spec.get("series") or []
        _need(series, "series must have at least one line.")
        out["series"] = []
        if out["x_unit"] == "labels":
            labels = spec.get("x_labels") or []
            _need(labels, "x_unit labels needs x_labels.")
            out["x_labels"] = labels
            texts += labels
        for s in series:
            name = str(s.get("name", ""))
            texts.append(name)
            line = {"name": name, "dashed": bool(s.get("dashed"))}
            if out["x_unit"] == "months":
                pts = s.get("points") or []
                _need(len(pts) >= 2, f"line '{name}' needs at least two points.")
                line["points"] = [{"x": value(p.get("x"), f"line '{name}' x"), "y": value(p.get("y"), f"line '{name}' y")} for p in pts]
            else:
                vals = s.get("values") or []
                _need(len(vals) == len(out["x_labels"]), f"line '{name}' needs one value per x label.")
                line["values"] = [value(v, f"line '{name}'") for v in vals]
            out["series"].append(line)
        ref = spec.get("reference")
        if ref:
            out["reference"] = {"label": str(ref.get("label", "")), "value": value(ref.get("value"), "reference")}
            texts.append(out["reference"]["label"])

    elif kind == "progress":
        out["unit"] = unit(spec.get("unit"))
        bars = spec.get("bars") or []
        _need(bars, "bars must have at least one bar.")
        out["bars"] = [{"label": str(b.get("label", "")), "value": value(b.get("value"), f"bar '{b.get('label')}'")} for b in bars]
        texts += [b["label"] for b in out["bars"]]
        tgt = spec.get("target")
        if tgt:
            out["target"] = {"label": str(tgt.get("label", "")), "value": value(tgt.get("value"), "target")}
            texts.append(out["target"]["label"])

    elif kind == "key_figures":
        rows = spec.get("rows") or []
        _need(rows, "rows must have at least one row.")
        out["rows"] = []
        for r in rows:
            row = {"label": str(r.get("label", "")), "value": value(r.get("value"), f"row '{r.get('label')}'"), "unit": unit(r.get("unit"), f"row '{r.get('label')}' unit")}
            if r.get("sign") in ("plus", "minus"):
                row["sign"] = r["sign"]
            out["rows"].append(row)
            texts.append(row["label"])
        head = spec.get("headline")
        if head:
            out["headline"] = {"label": str(head.get("label", "")), "value": value(head.get("value"), "headline"), "unit": unit(head.get("unit"), "headline unit")}
            texts.append(out["headline"]["label"])

    if kind in ("bar_chart", "line_chart") and len(out["series"]) > 1:
        shapes = [repr(ser.get("values") or ser.get("points")) for ser in out["series"]]
        _need(len(set(shapes)) == len(shapes), "Two series have exactly the same values. Draw each different result once, "
              "and leave out a series whose value is null in the tool result.")

    bad = [f"{where}: {v:g}" for v, where in values if _num_key(v) not in data_numbers]
    bad += [f"text: {n:g}" for t in texts if t for n in _numbers_in_text(t) if _num_key(n) not in text_numbers]
    _need(not bad, "These numbers are not in any tool result of this answer: " + "; ".join(bad)
          + ". Use only numbers the tools returned, copied exactly, or call a tool for the number you need.")
    return out


MARKER = re.compile(r"\[\[chart:([A-Za-z0-9_]+)\]\]")
OLD_MARKER = re.compile(r"\[\[show:[a-z_]+\]\]")


def place_charts(reply, charts):
    """Keep one [[chart:id]] line per chart that exists; add charts the reply forgot to place at the end."""
    placed = []

    def keep(m):
        cid = m.group(1)
        if cid in charts and cid not in placed:
            placed.append(cid)
            return f"\n[[chart:{cid}]]\n"
        return ""

    text = OLD_MARKER.sub("", MARKER.sub(keep, reply or ""))
    text += "".join(f"\n[[chart:{cid}]]\n" for cid in charts if cid not in placed)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
