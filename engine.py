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

    housing = [-table[m].get("Housing", 0) for m in months]
    before, after = statistics.median(housing[:RECENT]), statistics.median(housing[-RECENT:])
    if before == 0 and after > 0:
        signals.append({"stage": "moving_out", "why": "You recently started paying for housing."})
    elif before > 0 and after > before * 1.25:
        signals.append({"stage": "moving_out", "why": f"Your housing cost rose from about €{before:.0f} to €{after:.0f} a month."})

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
        "saved_monthly": round(saved),
        "months_to_target_now": months_to_target(surplus),
        "months_to_target_after": months_to_target(surplus + saved),
    }


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST00001"
    print(json.dumps({
        "profile": profile(cid),
        "safe_to_spend": safe_to_spend(cid),
        "can_i_afford_600": can_i_afford(cid, 600),
        "cut_restaurants_20": what_if_cut(cid, "Restaurants", 20),
    }, indent=2, ensure_ascii=False))
