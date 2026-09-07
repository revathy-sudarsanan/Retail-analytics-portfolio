"""
clean_data.py
--------------
Cleans the raw Online Retail II (UCI) dataset and reshapes it from
line-item grain into an analysis-ready star schema:

    customers.csv        - one row per customer
    orders.csv            - one row per invoice (order)
    order_line_items.csv  - one row per invoice line (cleaned, but sampled
                             down to keep the repo lightweight - see NOTE)
    top_products.csv       - aggregated product performance

Why clean it at all: the raw file has cancelled orders (Invoice starting
with 'C'), negative/zero quantities, missing Customer IDs, and zero/negative
prices - about 20-25% of rows need to be dropped or corrected before any
retention/revenue analysis is trustworthy. This mirrors exactly the kind of
"keep data clean and reliable" work described in the job posting.

Input:  data/online_retail_II_raw.csv (download from Kaggle, not committed
         to the repo due to its size - see data/README.md)
Output: data/processed/*.csv (committed - small enough for GitHub)

Run with: python data/clean_data.py
"""

import pandas as pd
import numpy as np

RAW_PATH = "data/online_retail_II_raw.csv"
OUT_DIR = "data/processed"

print("Loading raw data (this file is ~1M rows, may take a moment)...")
df = pd.read_csv(RAW_PATH, encoding="ISO-8859-1", dtype={"Customer ID": "Int64"})
raw_rows = len(df)
print(f"Raw rows: {raw_rows:,}")

df.columns = [c.strip().replace(" ", "_") for c in df.columns]
# Expected columns after normalizing: Invoice, StockCode, Description,
# Quantity, InvoiceDate, Price, Customer_ID, Country

df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["Invoice"] = df["Invoice"].astype(str).str.strip()
df["Description"] = df["Description"].astype(str).str.strip()

# --- Cleaning steps ------------------------------------------------------
n0 = len(df)

# 1. Drop cancellations (Invoice starting with 'C')
df = df[~df["Invoice"].str.startswith("C")]
n1 = len(df)

# 2. Drop rows with missing Customer ID - can't attribute to a user
df = df.dropna(subset=["Customer_ID"])
n2 = len(df)

# 3. Drop non-positive quantity or price (returns, adjustments, data errors)
df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
n3 = len(df)

# 4. Drop known non-product stock codes (postage, fees, manual adjustments)
NON_PRODUCT_CODES = {"POST", "D", "M", "DOT", "CRUK", "BANK CHARGES", "AMAZONFEE", "C2"}
df = df[~df["StockCode"].astype(str).str.upper().isin(NON_PRODUCT_CODES)]
n4 = len(df)

df["Customer_ID"] = df["Customer_ID"].astype(int)
df["line_total"] = (df["Quantity"] * df["Price"]).round(2)

print(f"Removed cancellations:        {n0 - n1:,} rows")
print(f"Removed missing Customer ID:  {n1 - n2:,} rows")
print(f"Removed invalid qty/price:    {n2 - n3:,} rows")
print(f"Removed non-product codes:    {n3 - n4:,} rows")
print(f"Clean rows remaining:         {n4:,} ({100 * n4 / raw_rows:.1f}% of raw)")

# --- Build orders.csv (one row per invoice) -------------------------------
orders = (
    df.groupby(["Invoice", "Customer_ID", "Country"], as_index=False)
    .agg(
        order_date=("InvoiceDate", "min"),
        n_line_items=("StockCode", "nunique"),
        total_quantity=("Quantity", "sum"),
        order_value=("line_total", "sum"),
    )
    .rename(columns={"Invoice": "invoice_no", "Customer_ID": "customer_id", "Country": "country"})
)
orders["order_value"] = orders["order_value"].round(2)
orders["order_date"] = orders["order_date"].dt.date.astype(str)

# --- Build customers.csv ---------------------------------------------------
customers = (
    orders.groupby(["customer_id", "country"], as_index=False)
    .agg(
        first_order_date=("order_date", "min"),
        last_order_date=("order_date", "max"),
        total_orders=("invoice_no", "nunique"),
        total_spend=("order_value", "sum"),
    )
)
customers["total_spend"] = customers["total_spend"].round(2)
# A customer can technically show more than one country if they moved / typo'd;
# keep the country tied to their first order for a clean 1-country-per-customer dim.
first_country = (
    orders.sort_values("order_date")
    .groupby("customer_id")["country"]
    .first()
    .rename("country")
)
customers = customers.drop(columns=["country"]).merge(first_country, on="customer_id")

# --- Build top_products.csv -------------------------------------------------
top_products = (
    df.groupby(["StockCode", "Description"], as_index=False)
    .agg(
        total_quantity_sold=("Quantity", "sum"),
        total_revenue=("line_total", "sum"),
        n_orders=("Invoice", "nunique"),
    )
    .rename(columns={"StockCode": "stock_code", "Description": "description"})
    .sort_values("total_revenue", ascending=False)
    .head(200)
)
top_products["total_revenue"] = top_products["total_revenue"].round(2)

# --- Save a small sample of raw line items for schema reference ------------
sample_lines = df.sample(n=20000, random_state=42).sort_values("InvoiceDate")
sample_lines = sample_lines.rename(columns={
    "Invoice": "invoice_no", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "Price": "unit_price",
    "Customer_ID": "customer_id", "Country": "country",
})[["invoice_no", "stock_code", "description", "quantity", "invoice_date",
    "unit_price", "customer_id", "country", "line_total"]]

import os
os.makedirs(OUT_DIR, exist_ok=True)
customers.to_csv(f"{OUT_DIR}/customers.csv", index=False)
orders.to_csv(f"{OUT_DIR}/orders.csv", index=False)
top_products.to_csv(f"{OUT_DIR}/top_products.csv", index=False)
sample_lines.to_csv(f"{OUT_DIR}/order_line_items_sample.csv", index=False)

print()
print(f"customers.csv:                {len(customers):,} rows")
print(f"orders.csv:                   {len(orders):,} rows")
print(f"top_products.csv:             {len(top_products):,} rows")
print(f"order_line_items_sample.csv:  {len(sample_lines):,} rows (20k sample of {n4:,} clean lines)")
print(f"\nSaved to {OUT_DIR}/")
