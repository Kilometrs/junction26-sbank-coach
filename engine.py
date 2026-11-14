"""Deterministic money maths. No AI in here: every number the coach says comes from this file.

Try it:  python engine.py CUST00001
"""
import csv
import gzip
import json
import statistics
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"

# S-Bank's three categories, plus what is not spending at all.
BUCKETS = {
    "fixed": ["Housing", "Utilities", "Groceries", "Transportation"],  # mandatory and regular
    "irregular": ["Health", "Home & Tech"],  # mandatory but irregular
    "flexible": ["Restaurants", "Entertainment", "Lifestyle", "Travel"],  # everyday spending that slips away
}
BUCKET_OF = {cat: b for b, cats in BUCKETS.items() for cat in cats}
INCOME = ["Salary", "Other Income"]
SAVING = ["Invest Deposit", "Salary Sweep"]

# Safety-net target in months of mandatory spending, per life stage.
LIFE_STAGES = {
    "student": {"label": "Student / just starting out", "target_months": 2},
    "moving_out": {"label": "Moving out or recently moved", "target_months": 3},
    "stable": {"label": "Stable job", "target_months": 3},
    "buying_home": {"label": "Buying a home", "target_months": 4},
    "new_parent": {"label": "Baby coming / new parent", "target_months": 6},
    "irregular_income": {"label": "Irregular income", "target_months": 6},
    "job_loss": {"label": "Lost job / income dropped", "target_months": 6},
}
RECENT = 6  # months used for "what is normal for you right now"

# Card merchant codes in the dataset, so people can ask about "taxis" or "coffee".
MCC = {
    "5411": "supermarkets", "5499": "convenience stores", "5422": "butchers", "5451": "dairy shops",
    "5812": "restaurants", "5814": "fast food and cafes", "5813": "bars",
    "5541": "fuel", "5542": "fuel (self-service)", "7523": "parking", "4111": "public transport",
    "4121": "taxis", "7512": "car rental", "4511": "flights", "7011": "hotels", "4722": "travel agencies",
    "5912": "pharmacies", "8011": "doctors", "8021": "dentists", "8099": "other health services",
    "7922": "theatre and concerts", "7999": "recreation", "7832": "cinema", "7991": "attractions",
    "7996": "amusement parks", "5200": "home improvement", "5251": "hardware", "5712": "furniture",
    "5732": "electronics", "5734": "software", "5941": "sports goods", "5942": "books",
    "5945": "toys and games", "5651": "clothing", "5691": "clothing (other)", "5999": "other shops",
}


@lru_cache(maxsize=None)
def _customers():
    with open(DATA / "customers.csv", encoding="utf-8-sig") as f:
        return {r["customer_id"]: r for r in csv.DictReader(f)}


@lru_cache(maxsize=None)
def _mortgages():
    with open(DATA / "mortgages.csv", encoding="utf-8-sig") as f:
        return {r["customer_id"]: r for r in csv.DictReader(f)}


@lru_cache(maxsize=64)
def load(customer_id):
    """All transactions of one customer, oldest first."""
    with gzip.open(DATA / "tx" / f"{customer_id}.csv.gz", "rt") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = float(r["tx_amount_eur"])
        r["balance"] = float(r["balance_after_eur"])
        r["month"] = r["tx_date"][:7]
    return rows


def _monthly(rows):
    """month -> category -> total EUR (spending is negative)."""
    table = defaultdict(lambda: defaultdict(float))
    for r in rows:
        table[r["month"]][r["category"]] += r["amount"]
    return dict(sorted(table.items()))


def _avg(table, months, cats):
    return sum(-table[m].get(c, 0) for m in months for c in cats) / len(months)


def _signals(customer_id, table, months, income_by_month):
    """Hints about life stage. These are guesses: the coach must ask the user to confirm."""
    age = int(_customers()[customer_id]["customer_age"])
    signals = []
    income = statistics.median(income_by_month)
    salaries = [table[m].get("Salary", 0) for m in months]

    if age <= 25 and income < 2300:
        signals.append({"stage": "student", "why": f"You are {age} and your income is modest."})
    if sum(1 for s in salaries if s == 0) >= 3:
        signals.append({"stage": "irregular_income", "why": "Some months have no salary at all, so your income looks irregular."})
    if all(s == 0 for s in salaries[-2:]) and any(salaries[:-2]):
        signals.append({"stage": "job_loss", "why": "No salary has arrived in the last two months."})

    # Last six months against the year before. Months without a payment are skipped,
    # because some people pay housing every other month.
    housing = [-table[m].get("Housing", 0) for m in months]
    earlier = [h for h in housing[-18:-RECENT] if h > 0]
    recent = [h for h in housing[-RECENT:] if h > 0]
    if recent and not earlier:
        signals.append({"stage": "moving_out", "why": "You started paying for housing in the last six months."})
    elif len(recent) >= 3 and len(earlier) >= 3 and statistics.mean(recent) > statistics.mean(earlier) * 1.3:
        signals.append({"stage": "moving_out", "why": f"Your housing cost rose from about €{statistics.mean(earlier):.0f} to €{statistics.mean(recent):.0f} a month."})

    mortgage = _mortgages().get(customer_id)
    if mortgage:
        signals.append({"stage": "buying_home", "why": f"You have a mortgage application ({mortgage['final_decision']})."})
    return signals


def profile(customer_id, life_stage=None):
    """Everything the coach and the UI need to know about one customer."""
    rows = load(customer_id)
    table = _monthly(rows)
    months = list(table)
    recent = months[-RECENT:]

    income_by_month = [sum(table[m].get(c, 0) for c in INCOME) for m in months]
    buckets = {b: round(_avg(table, recent, cats)) for b, cats in BUCKETS.items()}
    by_category = {c: round(_avg(table, recent, [c])) for c in BUCKET_OF}
    mandatory = buckets["fixed"] + buckets["irregular"]
    balance = rows[-1]["balance"]
    signals = _signals(customer_id, table, months, income_by_month)

    stage = life_stage or (signals[0]["stage"] if signals else "stable")
    target_months = LIFE_STAGES[stage]["target_months"]
    target = mandatory * target_months

    return {
        "customer_id": customer_id,
        "age": int(_customers()[customer_id]["customer_age"]),
        "as_of": rows[-1]["tx_date"],
        "balance": round(balance),
        "income_monthly": round(statistics.median(income_by_month[-RECENT:])),
        "income_lowest_month": round(min(income_by_month[-12:])),
        "saving_monthly": round(_avg(table, recent, SAVING)),
        "buckets_monthly": buckets,
        "by_category_monthly": by_category,
        "mandatory_monthly": mandatory,
        "life_stage": stage,
        "life_stage_confirmed": life_stage is not None,
        "life_stage_signals": signals,
        "safety_net": {
            "months_now": round(balance / mandatory, 1) if mandatory else None,
            "target_months": target_months,
            "target_eur": round(target),
            "missing_eur": round(max(0, target - balance)),
        },
    }


def persona_text(p):
    """Short written profile for the coach. The LLM sees this instead of raw transactions."""
    b, net = p["buckets_monthly"], p["safety_net"]
    lines = [
        f"Age {p['age']}. Income about €{p['income_monthly']} a month (lowest month in the past year: €{p['income_lowest_month']}).",
        f"Monthly spending: €{b['fixed']} mandatory and regular, €{b['irregular']} mandatory but irregular, €{b['flexible']} everyday spending that slips away.",
        f"Account balance €{p['balance']}, which covers {net['months_now']} months of must-pay costs. Target for this life stage: {net['target_months']} months (€{net['target_eur']}).",
        f"Already puts aside about €{p['saving_monthly']} a month." if p["saving_monthly"] else "No regular saving visible.",
        f"Life stage: {LIFE_STAGES[p['life_stage']]['label']} ({'confirmed by the user' if p['life_stage_confirmed'] else 'a guess, NOT yet confirmed by the user'}).",
    ]
    lines += [f"Hint ({s['stage']}): {s['why']}" for s in p["life_stage_signals"]]
    return "\n".join(lines)


def spending(customer_id, what, months=1):
    """Spending on a category ("Restaurants") or a merchant type ("taxis") over the last N months."""
    rows = load(customer_id)
    all_months = sorted({r["month"] for r in rows})
    period = set(all_months[-months:])
    key = what.strip().lower()

    def matches(r):
        return r["category"].lower() == key or MCC.get(r["mcc_code"], "").startswith(key)

    hits = [r for r in rows if r["amount"] < 0 and matches(r)]
    if not hits:
        return {"error": f"Nothing found for '{what}'.", "categories": list(BUCKET_OF), "merchant_types": sorted(set(MCC.values()))}
    in_period = [r for r in hits if r["month"] in period]
    return {
        "what": what,
        "period": f"{min(period)} to {max(period)}",
        "total": round(-sum(r["amount"] for r in in_period)),
        "purchases": len(in_period),
        "usual_per_month": round(-sum(r["amount"] for r in hits) / len(all_months)),
        "bucket": BUCKET_OF.get(hits[0]["category"]),
    }


def safe_to_spend(customer_id, life_stage=None):
    """How much flexible money is left this month after bills and the safety-net contribution."""
    p = profile(customer_id, life_stage)
    net = p["safety_net"]
    # Fill the safety net over a year, but never ask for more than 20% of income.
    contribution = min(net["missing_eur"] / 12, p["income_monthly"] * 0.2)
    budget = p["income_monthly"] - p["mandatory_monthly"] - contribution

    rows = load(customer_id)
    this_month = rows[-1]["month"]
    spent = -sum(r["amount"] for r in rows if r["month"] == this_month and BUCKET_OF.get(r["category"]) == "flexible")
    return {
        "month": this_month,
        "flexible_budget": round(budget),
        "safety_net_contribution": round(contribution),
        "spent_so_far": round(spent),
        "left": round(budget - spent),
        "usual_flexible_spend": p["buckets_monthly"]["flexible"],
    }


def can_i_afford(customer_id, amount, life_stage=None):
    """What a one-off purchase does to the safety net."""
    p = profile(customer_id, life_stage)
    net = p["safety_net"]
    mandatory = p["mandatory_monthly"]
    after = p["balance"] - amount
    monthly_surplus = p["income_monthly"] - mandatory - p["buckets_monthly"]["flexible"]

    if after >= net["target_eur"]:
        verdict = "yes"  # safety net stays full
    elif after >= mandatory:
        verdict = "yes_but"  # dips into the safety net, at least one month remains
    else:
        verdict = "wait"  # would leave less than one month of must-pay costs
    return {
        "amount": amount,
        "verdict": verdict,
        "months_before": net["months_now"],
        "months_after": round(after / mandatory, 1) if mandatory else None,
        "target_months": net["target_months"],
        "monthly_surplus": round(monthly_surplus),
        "months_to_save_up": round(amount / monthly_surplus, 1) if monthly_surplus > 0 else None,
    }


def what_if_cut(customer_id, category, percent, life_stage=None):
    """Effect of spending less in one category on reaching the safety-net target."""
    p = profile(customer_id, life_stage)
    saved = p["by_category_monthly"][category] * percent / 100
    surplus = p["income_monthly"] - p["mandatory_monthly"] - p["buckets_monthly"]["flexible"]
    missing = p["safety_net"]["missing_eur"]

    def months_to_target(monthly):
        return round(missing / monthly, 1) if monthly > 0 else None

    return {
        "category": category,
        "percent": percent,
        "saved_monthly": round(saved),
        "missing_eur": missing,  # the safety-net gap both paces fill
        "months_to_target_now": months_to_target(surplus),
        "months_to_target_after": months_to_target(surplus + saved),
    }


def goal_plan(customer_id, amount, months, life_stage=None):
    """Saving for a goal: how much per month, and whether the safety net should come first."""
    p = profile(customer_id, life_stage)
    surplus = p["income_monthly"] - p["mandatory_monthly"] - p["buckets_monthly"]["flexible"]
    needed = amount / months
    missing = p["safety_net"]["missing_eur"]
    shortfall = max(0, needed - surplus)
    flexible = p["buckets_monthly"]["flexible"]

    if missing > 0:
        verdict = "safety_net_first"  # fill the safety net, then save for the goal
    elif shortfall == 0:
        verdict = "on_track"
    else:
        verdict = "tight"  # needs spending cuts or more time
    goal_months = round(amount / surplus, 1) if surplus > 0 else None
    net_months = round(missing / surplus, 1) if missing and surplus > 0 else (0 if not missing else None)
    return {
        "amount": amount,
        "months": months,
        "verdict": verdict,
        "needed_monthly": round(needed),
        "monthly_surplus": round(surplus),
        "shortfall_monthly": round(shortfall),
        "cut_flexible_percent_to_close_gap": round(shortfall / flexible * 100) if shortfall and flexible else 0,
        "months_at_current_surplus": goal_months,
        "safety_net_missing_eur": missing,
        "months_to_fill_safety_net_first": net_months,
        # Safety net first, then the goal, both from everything left over each month.
        "goal_ready_after_months": round(net_months + goal_months, 1) if net_months is not None and goal_months is not None else None,
    }


@lru_cache(maxsize=None)
def _summary():
    """Per-customer averages for everyone, written by prep.py. Used to find peers."""
    with open(DATA / "summary.json") as f:
        return json.load(f)


def compare_to_peers(customer_id, category):
    """Compare monthly spending in one category with customers of similar age and income."""
    everyone = _summary()
    me = everyone[customer_id]
    peers = [
        c for cid, c in everyone.items()
        if cid != customer_id and abs(c["age"] - me["age"]) <= 5 and abs(c["income"] - me["income"]) <= me["income"] * 0.25
    ]
    if len(peers) < 20:
        return {"error": "Too few similar customers for a fair comparison."}
    values = sorted(c["spend"][category] for c in peers)
    mine = me["spend"][category]
    return {
        "category": category,
        "you_monthly": mine,
        "peers_typical_monthly": round(statistics.median(values)),
        "you_spend_more_than_percent_of_peers": round(sum(v < mine for v in values) / len(values) * 100),
        "peers": f"{len(peers)} customers aged {me['age'] - 5}-{me['age'] + 5} with a similar income",
    }


def upcoming_bills(customer_id):
    """Regular payments to expect next month, learned from the last six months."""
    rows = load(customer_id)
    months = sorted({r["month"] for r in rows})[-RECENT:]
    recent = [r for r in rows if r["month"] in months]
    bills = []
    for category in ["Housing", "Utilities"]:
        hits = [r for r in recent if r["category"] == category]
        if not hits:
            continue
        per_month = len(hits) / len(months)
        bills.append({
            "what": category,
            "expected_total": round(-sum(r["amount"] for r in hits) / len(months)),
            "payments_per_month": round(per_month, 1),
            "usually_around_day": round(statistics.median(int(r["tx_date"][8:]) for r in hits)) if per_month < 1.5 else None,
        })
    salaries = [r for r in recent if r["category"] == "Salary"]
    salary = {
        "expected": round(statistics.median(r["amount"] for r in salaries)),
        "usually_around_day": round(statistics.median(int(r["tx_date"][8:]) for r in salaries)),
        "arrived_in_months": f"{len({r['month'] for r in salaries})} of the last {len(months)}",
    } if salaries else None
    return {"bills": bills, "bills_total": sum(b["expected_total"] for b in bills), "salary": salary}


def trend(customer_id, what, months=6):
    """Month-by-month spending for a category, a bucket (fixed, irregular, flexible) or "all"."""
    table = _monthly(load(customer_id))
    key = what.strip().lower()
    cats = [c for c in BUCKET_OF if key in ("all", c.lower(), BUCKET_OF[c])]
    if not cats:
        return {"error": f"Unknown '{what}'.", "options": ["all", *BUCKETS, *BUCKET_OF]}
    series = {m: round(-sum(table[m].get(c, 0) for c in cats)) for m in list(table)[-months:]}
    values = list(series.values())
    half = len(values) // 2
    earlier, later = statistics.mean(values[:half]), statistics.mean(values[half:])
    change = round((later - earlier) / earlier * 100) if earlier else None
    return {
        "what": what,
        "by_month": series,
        "change_percent": change,  # later half of the period vs the earlier half
        "direction": "flat" if change is None or abs(change) < 10 else ("up" if change > 0 else "down"),
        "highest_month": max(series, key=series.get),
    }


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST00001"
    print(json.dumps({
        "profile": profile(cid),
        "safe_to_spend": safe_to_spend(cid),
        "can_i_afford_600": can_i_afford(cid, 600),
        "cut_restaurants_20": what_if_cut(cid, "Restaurants", 20),
    }, indent=2, ensure_ascii=False))
