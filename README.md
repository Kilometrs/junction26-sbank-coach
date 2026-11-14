# junction26-sbank-coach

Junction 2026 · S-Bank "Personal Economic Trainer" challenge.

A finance coach that understands **where you are in life** (student, moving out, new baby, lost job) and coaches you accordingly: first a safety net of 3–6 months of spending, then saving for goals.

## How it works
- **Engine (plain Python):** sorts spending into S-Bank's three categories (mandatory regular, mandatory irregular, everyday spending that slips away), finds recurring bills, computes the safety net and safe-to-spend, and runs what-ifs. All numbers come from here.
- **Coach (LLM):** understands the question, calls the engine and explains the answer in plain language. It never does the maths itself.
- **Life stage:** inferred from transactions, always confirmed by the user, opt-in.
- **UI:** phone-width page with cards and a chat, styled after S-mobiili.

## Data
Uses S-Bank's synthetic dataset, which is not included in this repo. Clone `hackjunction/Junction-2026-S-pankki` next to this repo and set `SBANK_DATA_DIR` in `.env` (see `.env.example`).

## Run
```bash
python prep.py              # once: splits the dataset into data/tx/<customer>.csv.gz
python engine.py CUST00152  # prints the profile and example answers for one customer
```

## Demo customers
| Customer | Who | "Can I afford a €600 laptop?" |
|---|---|---|
| `CUST00152` | 21, income ~€1,500, half a month of safety net | wait |
| `CUST00001` | 63, stable, 2.8 months of safety net | yes, but it dips into the safety net |
| `CUST00007` | 49, stable, 10 months of safety net | yes |
| `CUST05014` | 23, irregular income, 0.4 months of safety net | wait |
| `CUST00243` | 52, housing cost doubled (moved), 0.6 months | wait |
