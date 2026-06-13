"""
generate_test_incremental.py
------------------------------------------------------------
Utility script — generates two controlled test CSV files
for testing incremental load and duplicate handling.

Place in: utils/
Run from: project root

    python utils/generate_test_incremental.py

OUTPUT
------------------------------------------------------------
data/test/fact_sales_incremental_today.csv
    ~150 rows of brand new orders dated TODAY.
    Simulates tonight's nightly batch arriving from the source.
    Use this to test incremental load — these rows should be
    picked up by the loaded_at watermark and inserted into mart.

data/test/fact_sales_incremental_duplicate.csv
    Exact copy of the above file.
    Use this to test duplicate handling — re-running the same
    batch should produce ZERO new rows in mart because the
    md5 surrogate key (order_sk) already exists.
    If your row count increases, your incremental logic is broken.

TEST SEQUENCE
------------------------------------------------------------
Step 1 — Make sure you have a full load baseline in mart first:
    python loader/load_full.py
    dbt seed && dbt snapshot && dbt run && dbt test

Step 2 — Check current mart row count:
    SELECT COUNT(*) FROM mart.fact_sales;
    -- note this number, call it BASELINE

Step 3 — Load today's incremental batch:
    python loader/load_incremental.py --file data/test/fact_sales_incremental_today.csv
    dbt run
    SELECT COUNT(*) FROM mart.fact_sales;
    -- should be BASELINE + ~150 rows

Step 4 — Test duplicate handling (re-run same file):
    python loader/load_incremental.py --file data/test/fact_sales_incremental_duplicate.csv
    dbt run
    SELECT COUNT(*) FROM mart.fact_sales;
    -- should be IDENTICAL to Step 3 — proves idempotency

WHAT GOOD LOOKS LIKE
------------------------------------------------------------
    Step 2: 841
    Step 3: 991   (+150 — new rows inserted)
    Step 4: 991   (unchanged — duplicates correctly ignored)

WHAT BAD LOOKS LIKE
------------------------------------------------------------
    Step 4: 1141  (+150 again — duplicates were inserted)
    This means your incremental unique_key or delete+insert
    strategy in dbt is not working correctly.

NOTES
------------------------------------------------------------
- OrderNumbers start from SO300000 — no overlap with any existing data
- All ProductKey, CustomerKey, TerritoryKey values are valid against dim tables
- Dates use D/MM/YYYY format — matches source CSV convention
- Run this script any time you want a fresh test batch dated today
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import calendar
import os

np.random.seed(42)

# ── Output paths ──────────────────────────────────────────────────────────────
OUTPUT_DIR      = os.path.join("data", "test")
TODAY_FILE      = os.path.join(OUTPUT_DIR, "fact_sales_incremental_today.csv")
DUPLICATE_FILE  = os.path.join(OUTPUT_DIR, "fact_sales_incremental_duplicate.csv")

# ── Valid FK values (subset — controlled and small) ───────────────────────────
PRODUCT_KEYS   = [1, 2, 3, 4, 5, 10, 15, 20, 25, 30]
CUSTOMER_KEYS  = list(range(1, 51))    # customers 1–50
TERRITORY_KEYS = list(range(1, 16))    # all 15 territories including AU/NZ

# OrderNumber sequence — starts at SO300000, no overlap with any existing data
SO_START = 300000

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_date(d):
    """Format date as DD/MM/YYYY — matches source CSV convention."""
    return d.strftime("%d/%m/%Y")


def generate_todays_orders(n_orders, so_start):
    """
    Generate n_orders of sales rows all dated TODAY.
    Each order has 1–3 line items.
    StockDate is 14–90 days before today (realistic lead time).
    Returns (DataFrame, next SO counter).
    """
    today = date.today()
    rows  = []
    so    = so_start

    for _ in range(n_orders):
        order_num  = f"SO{so}"
        so        += 1
        n_lines    = np.random.choice([1, 2, 3], p=[0.50, 0.35, 0.15])
        lead_days  = np.random.randint(14, 90)
        stock_date = today - timedelta(days=lead_days)
        territory  = int(np.random.choice(TERRITORY_KEYS))
        customer   = int(np.random.choice(CUSTOMER_KEYS))

        for line in range(1, n_lines + 1):
            rows.append({
                "OrderDate"    : fmt_date(today),        # always TODAY
                "StockDate"    : fmt_date(stock_date),
                "OrderNumber"  : order_num,
                "ProductKey"   : int(np.random.choice(PRODUCT_KEYS)),
                "CustomerKey"  : customer,
                "TerritoryKey" : territory,
                "OrderLineItem": line,
                "OrderQuantity": int(np.random.choice([1, 2, 3], p=[0.60, 0.30, 0.10])),
            })

    return pd.DataFrame(rows), so


# ── Generate ──────────────────────────────────────────────────────────────────
today_str = date.today().strftime("%d/%m/%Y")
print(f"Generating test data for today: {today_str}")

N_ORDERS = 100   # ~100 orders = ~150 rows depending on line distribution
df_today, _ = generate_todays_orders(N_ORDERS, SO_START)

# Duplicate file is identical — used to prove idempotency
df_duplicate = df_today.copy()

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
df_today.to_csv(TODAY_FILE,     index=False, encoding="utf-8")
df_duplicate.to_csv(DUPLICATE_FILE, index=False, encoding="utf-8")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FILES GENERATED")
print("=" * 60)

for label, df, path in [
    ("Incremental — today's batch",  df_today,     TODAY_FILE),
    ("Duplicate  — idempotency test", df_duplicate, DUPLICATE_FILE),
]:
    print(f"\n  {label}")
    print(f"    File      : {path}")
    print(f"    Rows      : {len(df):,}")
    print(f"    Orders    : {df['OrderNumber'].nunique():,}")
    print(f"    Order date: {df['OrderDate'].iloc[0]}")

print("\n" + "=" * 60)
print("TEST SEQUENCE")
print("=" * 60)
print(f"""
  -- Check baseline before you start
  SELECT COUNT(*) FROM mart.fact_sales;

  -- Step 1: load today's batch
  python loader/load_incremental.py --file {TODAY_FILE}
  dbt run
  SELECT COUNT(*) FROM mart.fact_sales;
  -- expect: baseline + {len(df_today)} rows

  -- Step 2: re-run same file (duplicate test)
  python loader/load_incremental.py --file {DUPLICATE_FILE}
  dbt run
  SELECT COUNT(*) FROM mart.fact_sales;
  -- expect: SAME count as above (idempotency confirmed)
""")