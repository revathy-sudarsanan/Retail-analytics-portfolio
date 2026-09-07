"""
run_analysis.py
----------------
Loads the cleaned tables from /data/processed, computes the same metrics
defined in /sql/queries/*.sql (cohort retention, order volume trends, RFM
segmentation, churn risk), prints a summary, and saves chart PNGs to
/images.

Run with: python analysis/run_analysis.py
"""

import pandas as pd
import matplotlib.pyplot as plt

plt.style.use("seaborn-v0_8-whitegrid")
ACCENT = "#2E6F6E"
ACCENT2 = "#D98E48"
ACCENT3 = "#B23A48"

customers = pd.read_csv("data/processed/customers.csv", parse_dates=["first_order_date", "last_order_date"])
orders = pd.read_csv("data/processed/orders.csv", parse_dates=["order_date"])
top_products = pd.read_csv("data/processed/top_products.csv")

print(f"Customers: {len(customers):,} | Orders: {len(orders):,} | "
      f"Date range: {orders['order_date'].min().date()} to {orders['order_date'].max().date()}")


# ---------------------------------------------------------------------
# 1. Monthly cohort retention
# ---------------------------------------------------------------------
orders["order_month"] = orders["order_date"].dt.to_period("M")
first_order_month = orders.groupby("customer_id")["order_month"].min().rename("cohort_month")
orders_c = orders.join(first_order_month, on="customer_id")
orders_c["months_since_first"] = (
    orders_c["order_month"].astype(int) - orders_c["cohort_month"].astype(int)
)

cohort_sizes = first_order_month.value_counts()
retention = (
    orders_c.groupby(["cohort_month", "months_since_first"])["customer_id"]
    .nunique()
    .reset_index(name="active_customers")
)
retention["cohort_size"] = retention["cohort_month"].map(cohort_sizes)
retention["retention_pct"] = (100 * retention["active_customers"] / retention["cohort_size"]).round(1)
retention_pivot = retention.pivot(
    index="cohort_month", columns="months_since_first", values="retention_pct"
).sort_index()

n_periods = min(12, retention_pivot.shape[1])
fig, ax = plt.subplots(figsize=(10, 7))
im = ax.imshow(retention_pivot.iloc[:, :n_periods], cmap="YlGn", aspect="auto", vmin=0, vmax=100)
ax.set_xticks(range(n_periods))
ax.set_xticklabels([f"M{m}" for m in range(n_periods)])
ax.set_yticks(range(len(retention_pivot)))
ax.set_yticklabels([str(p) for p in retention_pivot.index], fontsize=7)
ax.set_title("Monthly Cohort Retention (%) - Online Retail II")
ax.set_xlabel("Months since first order")
ax.set_ylabel("First-order cohort")
fig.colorbar(im, ax=ax, label="Retention %")
plt.tight_layout()
plt.savefig("images/retention_cohort_heatmap.png", dpi=150)
plt.close()


# ---------------------------------------------------------------------
# 2. Order volume / revenue trend by top countries
# ---------------------------------------------------------------------
top_countries = orders["country"].value_counts().head(6).index
by_country = (
    orders[orders["country"].isin(top_countries)]
    .groupby(["order_month", "country"])["order_value"]
    .sum()
    .unstack(fill_value=0)
)
by_country.index = by_country.index.astype(str)

fig, ax = plt.subplots(figsize=(10, 5))
by_country.plot(ax=ax, marker="o", linewidth=2)
ax.set_title("Monthly Revenue by Top 6 Countries")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (GBP)")
ax.legend(title="Country", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("images/revenue_by_country.png", dpi=150)
plt.close()


# ---------------------------------------------------------------------
# 3. RFM segmentation
# ---------------------------------------------------------------------
max_date = orders["order_date"].max()
rfm = orders.groupby("customer_id").agg(
    recency_days=("order_date", lambda s: (max_date - s.max()).days),
    frequency=("invoice_no", "nunique"),
    monetary=("order_value", "sum"),
).reset_index()

rfm["r_score"] = pd.qcut(rfm["recency_days"].rank(method="first", ascending=False), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)


def segment(row):
    if row.r_score >= 3 and row.f_score >= 3 and row.m_score >= 3:
        return "Champions"
    if row.r_score >= 3 and row.f_score >= 2:
        return "Loyal / Engaged"
    if row.r_score <= 2 and row.f_score >= 3 and row.m_score >= 3:
        return "At Risk - High Value"
    if row.r_score <= 2 and row.f_score <= 2:
        return "Churned / Lost"
    return "Needs Attention"


rfm["segment"] = rfm.apply(segment, axis=1)
segment_summary = rfm.groupby("segment").agg(
    customers=("customer_id", "count"), total_monetary=("monetary", "sum")
).sort_values("total_monetary", ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
segment_summary["customers"].plot(kind="barh", ax=axes[0], color=ACCENT)
axes[0].set_title("Customers per RFM Segment")
axes[0].set_xlabel("Number of customers")
axes[0].invert_yaxis()

segment_summary["total_monetary"].plot(kind="barh", ax=axes[1], color=ACCENT2)
axes[1].set_title("Revenue by RFM Segment")
axes[1].set_xlabel("Total revenue (GBP)")
axes[1].invert_yaxis()
plt.tight_layout()
plt.savefig("images/rfm_segments.png", dpi=150)
plt.close()


# ---------------------------------------------------------------------
# 4. Churn / at-risk customers
# ---------------------------------------------------------------------
order_counts = orders.groupby("customer_id").size()
repeat_customers = order_counts[order_counts >= 3].index
gaps = (
    orders[orders["customer_id"].isin(repeat_customers)]
    .sort_values(["customer_id", "order_date"])
    .groupby("customer_id")["order_date"]
    .apply(lambda s: s.diff().dt.days.dropna())
)
avg_gap = gaps.groupby("customer_id").mean().rename("avg_reorder_gap_days")
last_order = orders.groupby("customer_id")["order_date"].max().rename("last_order_date")
risk_df = pd.concat([avg_gap, last_order], axis=1).dropna()
risk_df["days_since_last_order"] = (max_date - risk_df["last_order_date"]).dt.days
risk_df["churn_status"] = risk_df.apply(
    lambda r: "At risk" if r.days_since_last_order > 2 * r.avg_reorder_gap_days else "Healthy",
    axis=1,
)
risk_df = risk_df.join(customers.set_index("customer_id")["total_spend"])
churn_summary = risk_df.groupby("churn_status")["total_spend"].agg(["count", "sum"])

fig, ax = plt.subplots(figsize=(6, 5))
churn_summary["count"].plot(kind="bar", ax=ax, color=[ACCENT3, ACCENT])
ax.set_title("Repeat Customers: Healthy vs. At Risk")
ax.set_ylabel("Number of customers")
ax.tick_params(axis="x", rotation=0)
for i, v in enumerate(churn_summary["count"]):
    ax.text(i, v + 5, str(v), ha="center")
plt.tight_layout()
plt.savefig("images/churn_risk.png", dpi=150)
plt.close()


# ---------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------
print("=" * 60)
print("KEY METRICS SUMMARY")
print("=" * 60)
print(f"Total customers:            {len(customers):,}")
print(f"Total orders:               {len(orders):,}")
print(f"Total revenue:              £{orders['order_value'].sum():,.0f}")
print(f"Avg order value:            £{orders['order_value'].mean():.2f}")
print(f"Countries represented:      {orders['country'].nunique()}")
print()
print(f"Month-1 retention range across cohorts: "
      f"{retention_pivot[1].min():.0f}% - {retention_pivot[1].max():.0f}%")
print()
print("RFM segment sizes:")
print(segment_summary)
print()
print("At-risk vs healthy repeat customers:")
print(churn_summary)
print()
print("Top product by revenue:", top_products.iloc[0]["description"],
      f"(£{top_products.iloc[0]['total_revenue']:,.0f})")
print()
print("Charts saved to /images:")
print(" - retention_cohort_heatmap.png")
print(" - revenue_by_country.png")
print(" - rfm_segments.png")
print(" - churn_risk.png")
