"""Split the S-Bank dataset into small per-customer files so the app never touches the 346 MB CSV.

Usage:  python prep.py [path/to/Junction-2026-S-pankki]
Output: data/tx/<customer_id>.csv.gz, data/customers.csv, data/mortgages.csv, data/summary.json

        python prep.py --demo
Output: demo-data/, the same files for the six demo customers only (1.4 MB), for the hosted demo's container.
"""
import csv
import gzip
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "data"


def write_demo():
    """Pack what the hosted demo needs: the demo customers' transactions, plus the small shared files."""
    import engine

    demo = ROOT / "demo-data"
    (demo / "tx").mkdir(parents=True, exist_ok=True)
    for name in ("customers.csv", "mortgages.csv", "summary.json"):  # ages, mortgage links, peer averages
        shutil.copy(OUT / name, demo / name)
    for cid in engine.DEMO_CUSTOMERS:
        shutil.copy(OUT / "tx" / f"{cid}.csv.gz", demo / "tx" / f"{cid}.csv.gz")
    print(f"wrote {len(engine.DEMO_CUSTOMERS)} demo customers to {demo}")


def main():
    if sys.argv[1:] == ["--demo"]:
        return write_demo()
    src = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SBANK_DATA_DIR", ROOT.parent / "Junction-2026-S-pankki"))
    tx_path = src / "tx_junction_transactions.csv"
    with open(tx_path, "rb") as f:
        if f.read(7) == b"version":
            sys.exit(f"{tx_path} is a Git LFS pointer, not the data. See the dataset README.")

    (OUT / "tx").mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "tx_customers_junction.csv", OUT / "customers.csv")
    shutil.copy(src / "mtg_tx_customer_link_and_final_mtg_infio.csv", OUT / "mortgages.csv")

    # The file is sorted by customer, so we only ever hold one output file open.
    current, out, writer, n = None, None, None, 0
    with open(tx_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row[0] != current:
                if out:
                    out.close()
                current = row[0]
                out = gzip.open(OUT / "tx" / f"{current}.csv.gz", "wt", newline="")
                writer = csv.writer(out)
                writer.writerow(header)
                n += 1
            writer.writerow(row)
    if out:
        out.close()
    print(f"wrote {n} customer files to {OUT / 'tx'}")
    write_summary()


def write_summary():
    """Monthly averages for every customer, so the coach can compare someone with their peers."""
    import engine

    summary = {}
    for cid in engine._customers():
        p = engine.profile(cid)
        summary[cid] = {"age": p["age"], "income": p["income_monthly"], "spend": p["by_category_monthly"]}
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f)
    print(f"wrote summary of {len(summary)} customers")


if __name__ == "__main__":
    main()
