"""
generate_test_failures.py
------------------------------------------------------------
Utility script — generates controlled broken datasets for
pipeline resilience testing.

Place in : utils/tests/
Run from : project root

    python utils/tests/generate_test_failures.py

PURPOSE
------------------------------------------------------------
After the happy-path pipeline is working, use these files to
deliberately break it and verify the pipeline responds correctly —
logs the error, fails loudly, and does not silently corrupt data.

This is the difference between a pipeline that works and a
pipeline that is production-grade.

OUTPUT — all files written to data/test/failures/
------------------------------------------------------------
1. fact_sales_null_fk.csv
   ProductKey is NULL on some rows.
   Tests: NOT NULL constraint on staging, dbt not_null test on mart.
   Expected: PostgreSQL rejects the row OR dbt test fails loudly.

2. fact_sales_invalid_fk.csv
   ProductKey values that do not exist in dim_product.
   Tests: dbt relationships test (referential integrity).
   Expected: dbt test fails — lists the offending keys.

3. fact_sales_wrong_dtype.csv
   ProductKey contains "abc" strings instead of integers.
   Tests: staging DDL type casting, loader error handling.
   Expected: PostgreSQL cast fails — loader logs error with batch_id.

4. fact_sales_schema_evolution.csv
   A new column "DiscountPct" added that does not exist in staging DDL.
   Tests: how dbt and loader handle unexpected columns.
   Expected: loader ignores unknown columns OR raises a clear warning.

5. fact_sales_partial_batch.csv
   First 50 rows are valid. Rows 51–100 have a NULL ProductKey.
   Tests: whether the loader commits valid rows before hitting the error,
   and whether a re-run after fixing produces duplicates.
   Expected: transaction rolls back entirely OR valid rows are committed
   and logged — behaviour depends on your loader transaction strategy.

6. fact_sales_late_arriving.csv
   Valid rows but OrderDate is 6 months in the past.
   Tests: incremental watermark logic — loaded_at vs OrderDate.
   Expected: rows ARE picked up (watermark is on loaded_at, not OrderDate).
   This is correct behaviour — late-arriving data should still land.

7. fact_sales_duplicate_natural_key.csv
   Same OrderNumber + OrderLineItem appears twice in one batch.
   Tests: surrogate key deduplication (md5 hash).
   Expected: only one row inserted into mart — the second is ignored.

HOW TO USE EACH FILE
------------------------------------------------------------
For each test:
  1. Run the loader against the failure file
  2. Observe what happens (error, warning, silent pass)
  3. Query the mart to verify data integrity was preserved
  4. Document the behaviour in docs/architecture.md

See WHAT GOOD LOOKS LIKE section per file below for expected SQL results.

NOTES
------------------------------------------------------------
- OrderNumbers start from SO400000 — no overlap with any existing data
- All valid rows use ProductKey 1–30, CustomerKey 1–50, TerritoryKey 1–15
- Dates use D/MM/YYYY format — matches source CSV convention
- Run: python utils/tests/generate_test_failures.py
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import os

np.random.seed(7)

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join("data", "test", "failures")

# ── Valid FK values ───────────────────────────────────────────────────────────
VALID_PRODUCT_KEYS   = [1, 2, 3, 4, 5, 10, 15, 20, 25, 30]
VALID_CUSTOMER_KEYS  = list(range(1, 51))
VALID_TERRITORY_KEYS = list(range(1, 16))

SO_START = 400000   # no overlap with production or incremental test data

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_date(d):
    return d.strftime("%d/%m/%Y")


def base_row(so_counter, line=1, order_date=None):
    """Return one valid sales row. Override fields after calling."""
    today      = order_date or date.today()
    lead_days  = np.random.randint(14, 90)
    stock_date = today - timedelta(days=lead_days)
    return {
        "OrderDate"    : fmt_date(today),
        "StockDate"    : fmt_date(stock_date),
        "OrderNumber"  : f"SO{so_counter}",
        "ProductKey"   : int(np.random.choice(VALID_PRODUCT_KEYS)),
        "CustomerKey"  : int(np.random.choice(VALID_CUSTOMER_KEYS)),
        "TerritoryKey" : int(np.random.choice(VALID_TERRITORY_KEYS)),
        "OrderLineItem": line,
        "OrderQuantity": int(np.random.choice([1, 2, 3])),
    }


def make_valid_rows(n, so_start, order_date=None):
    """Generate n fully valid rows across n orders."""
    rows = []
    for i in range(n):
        rows.append(base_row(so_start + i, order_date=order_date))
    return rows, so_start + n


# ── 1. NULL foreign key ───────────────────────────────────────────────────────
def gen_null_fk(so_start):
    """
    20 rows — ProductKey is NULL on rows 5, 10, 15, 20.
    Tests: NOT NULL constraint on staging.fact_sales.ProductKey
           dbt not_null test on mart.fact_sales.ProductKey
    Expected:
      - PostgreSQL rejects the INSERT — raises NOT NULL violation
      - Loader catches exception, logs: "NOT NULL violation — ProductKey"
      - mart.fact_sales row count does not change
    SQL check:
      SELECT COUNT(*) FROM mart.fact_sales
      WHERE order_sk IN (
          SELECT md5(OrderNumber || cast(OrderLineItem as varchar))
          FROM staging.fact_sales
          WHERE batch_id = '<your_batch_id>'
      );
      -- expect: 0 rows (entire batch rejected or nulls skipped)
    """
    rows, so = make_valid_rows(20, so_start)
    for i in [4, 9, 14, 19]:       # 0-indexed rows 5, 10, 15, 20
        rows[i]["ProductKey"] = None
    return pd.DataFrame(rows), so


# ── 2. Invalid foreign key ────────────────────────────────────────────────────
def gen_invalid_fk(so_start):
    """
    20 rows — ProductKey 9999, 8888 do not exist in dim_product.
    Tests: dbt relationships test
           dbt test: relationships(to=ref('dim_product'), field='ProductKey')
    Expected:
      - Rows land in staging (no constraint at staging level)
      - dbt test FAILS — reports offending ProductKey values
      - mart rows referencing invalid keys have no dim join match
    SQL check after dbt run:
      SELECT f.order_sk, f.ProductKey
      FROM mart.fact_sales f
      LEFT JOIN mart.dim_product d ON f.ProductKey = d.ProductKey
      WHERE d.ProductKey IS NULL;
      -- expect: rows with ProductKey 9999 / 8888 appear here
    """
    rows, so = make_valid_rows(20, so_start)
    rows[3]["ProductKey"]  = 9999   # does not exist in dim_product
    rows[11]["ProductKey"] = 8888   # does not exist in dim_product
    return pd.DataFrame(rows), so


# ── 3. Wrong data type ────────────────────────────────────────────────────────
def gen_wrong_dtype(so_start):
    """
    20 rows — ProductKey contains "abc" strings on 3 rows.
    Tests: staging DDL CAST(ProductKey AS INT)
           loader error handling and logging
    Expected:
      - PostgreSQL raises: invalid input syntax for type integer
      - Loader catches exception, logs error with batch_id
      - No rows from this batch reach staging
    SQL check:
      SELECT COUNT(*) FROM staging.fact_sales
      WHERE batch_id = '<your_batch_id>';
      -- expect: 0 rows (entire batch rejected)
    """
    rows, so = make_valid_rows(20, so_start)
    rows[2]["ProductKey"]  = "abc"
    rows[9]["ProductKey"]  = "xyz"
    rows[16]["ProductKey"] = "!!!"
    return pd.DataFrame(rows), so


# ── 4. Schema evolution ───────────────────────────────────────────────────────
def gen_schema_evolution(so_start):
    """
    20 rows — extra column "DiscountPct" that does not exist in staging DDL.
    Tests: loader column handling (does it fail or ignore unknown columns?)
           dbt model handling of unexpected source columns
    Expected (two valid outcomes):
      A) Loader strips unknown columns before INSERT — rows land cleanly
      B) Loader raises: column "DiscountPct" does not exist — fails loudly
    The key is that behaviour is EXPLICIT — not a silent corruption.
    SQL check:
      SELECT COUNT(*) FROM staging.fact_sales
      WHERE batch_id = '<your_batch_id>';
      -- expect: 20 rows (if loader strips) OR 0 rows (if loader rejects)
    """
    rows, so = make_valid_rows(20, so_start)
    df = pd.DataFrame(rows)
    df["DiscountPct"] = np.random.choice([0.0, 0.05, 0.10, 0.15], size=len(df))
    return df, so


# ── 5. Partial batch ─────────────────────────────────────────────────────────
def gen_partial_batch(so_start):
    """
    100 rows — rows 1–50 valid, rows 51–100 have NULL ProductKey.
    Tests: transaction strategy in load_incremental.py
           Does the loader commit valid rows before hitting the error?
           Does a re-run after fixing cause duplicates for rows 1–50?
    Two valid strategies:
      A) Atomic transaction — all-or-nothing, entire batch rolled back
         Re-run inserts all 100 (if fixed) — no duplicates because
         surrogate key deduplication handles rows 1–50
      B) Row-by-row — valid rows committed, invalid rows skipped and logged
         Re-run of fixed batch: rows 1–50 deduplicated, rows 51–100 inserted
    Document which strategy your loader uses in architecture.md.
    SQL check:
      SELECT COUNT(*) FROM staging.fact_sales
      WHERE batch_id = '<your_batch_id>';
      -- Strategy A: 0 rows (rolled back)
      -- Strategy B: 50 rows (valid rows committed)
    """
    valid_rows, so = make_valid_rows(50, so_start)
    broken_rows, so = make_valid_rows(50, so)
    for row in broken_rows:
        row["ProductKey"] = None
    return pd.DataFrame(valid_rows + broken_rows), so


# ── 6. Late-arriving data ────────────────────────────────────────────────────
def gen_late_arriving(so_start):
    """
    20 rows — OrderDate is 6 months in the past, but loaded TODAY.
    Tests: incremental watermark logic
           Watermark is on loaded_at (when row arrived), NOT OrderDate
    Expected:
      - Rows ARE picked up by incremental load (loaded_at = today)
      - OrderDate is 6 months old — this is fine and correct
      - Revenue/profit calculations for those orders use historical prices
    This is CORRECT BEHAVIOUR — late-arriving data must still land.
    SQL check:
      SELECT OrderDate, loaded_at
      FROM mart.fact_sales
      WHERE batch_id = '<your_batch_id>'
      ORDER BY OrderDate;
      -- expect: OrderDate ~6 months ago, loaded_at = today
    """
    late_date = date.today() - timedelta(days=180)
    rows, so  = make_valid_rows(20, so_start, order_date=late_date)
    return pd.DataFrame(rows), so


# ── 7. Duplicate natural key ─────────────────────────────────────────────────
def gen_duplicate_natural_key(so_start):
    """
    40 rows — same OrderNumber + OrderLineItem appears twice (20 unique orders duplicated).
    Tests: md5 surrogate key deduplication
           dbt incremental unique_key: order_sk
    Expected:
      - Both rows land in staging (staging has no unique constraint)
      - dbt incremental model deduplicates on order_sk (md5 hash)
      - Only 20 rows inserted into mart — the second copy of each is ignored
    SQL check:
      SELECT COUNT(*) FROM mart.fact_sales
      WHERE order_sk IN (
          SELECT md5(OrderNumber || cast(OrderLineItem as varchar))
          FROM staging.fact_sales
          WHERE batch_id = '<your_batch_id>'
      );
      -- expect: 20 (not 40)
    """
    rows, so = make_valid_rows(20, so_start)
    duplicates = [row.copy() for row in rows]   # exact copies
    return pd.DataFrame(rows + duplicates), so


# ── Generate all files ────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    so = SO_START
    tests = []

    generators = [
        ("fact_sales_null_fk.csv",              gen_null_fk,              "NULL foreign key"),
        ("fact_sales_invalid_fk.csv",           gen_invalid_fk,           "Invalid foreign key"),
        ("fact_sales_wrong_dtype.csv",          gen_wrong_dtype,          "Wrong data type"),
        ("fact_sales_schema_evolution.csv",     gen_schema_evolution,     "Schema evolution"),
        ("fact_sales_partial_batch.csv",        gen_partial_batch,        "Partial batch failure"),
        ("fact_sales_late_arriving.csv",        gen_late_arriving,        "Late-arriving data"),
        ("fact_sales_duplicate_natural_key.csv",gen_duplicate_natural_key,"Duplicate natural key"),
    ]

    for filename, gen_fn, label in generators:
        df, so = gen_fn(so)
        path   = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(path, index=False, encoding="utf-8")
        tests.append((label, filename, len(df)))

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("FAILURE TEST FILES GENERATED")
    print("=" * 62)
    print(f"  Output dir: {OUTPUT_DIR}\n")

    for label, filename, rows in tests:
        print(f"  [{rows:>3} rows]  {filename}")
        print(f"           {label}")
        print()

    print("=" * 62)
    print("NEXT STEPS")
    print("=" * 62)
    print("""
  Run each file through the loader and observe the behaviour:

    python loader/load_incremental.py --file data/test/failures/<file>
    dbt run
    dbt test

  For each test document in docs/architecture.md:
    - What error was raised (or not raised)
    - Where it was caught (PostgreSQL / loader / dbt test)
    - Whether mart data integrity was preserved
    - What you had to fix or handle

  See docstring inside each generator function for the
  exact SQL query to verify correct behaviour.
""")


if __name__ == "__main__":
    main()