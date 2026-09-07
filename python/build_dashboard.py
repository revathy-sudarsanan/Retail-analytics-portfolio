"""
build_dashboard.py
-------------------
Builds a single self-contained interactive HTML dashboard (Plotly)
summarizing revenue, retention, RFM segments, and churn risk from the
cleaned Online Retail II data.

This stands in for an AWS QuickSight dashboard (which needs a live AWS
account to host) - same KPI definitions and chart choices, but portable
as a static file anyone can open in a browser.

Run with: python analysis/build_dashboard.py
Outputs: dashboard.html
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

customers = pd.read_csv("data/processed/customers.csv", parse_dates=["first_order_date", "last_order_date"])
orders = pd.read_csv("data/processed/orders.csv", parse_dates=["order_date"])

orders["order_month"] = orders["order_date"].dt.to_period("M").dt.to_timestamp()
monthly_revenue = orders.groupby("order_month")["order_value"].sum()
monthly_orders = orders.groupby("order_month").size()
top_countries = orders.groupby("country")["order_value"].sum().sort_values(ascending=False).head(8)

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
segment_counts = rfm["segment"].value_counts()

fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        "Monthly Revenue & Order Count",
        "Revenue by Country (Top 8)",
        "RFM Customer Segments",
        "Revenue Distribution per Order",
    ),
    specs=[[{"secondary_y": True}, {}], [{"type": "pie"}, {}]],
    vertical_spacing=0.14,
    horizontal_spacing=0.1,
)

fig.add_trace(
    go.Scatter(x=monthly_revenue.index, y=monthly_revenue.values, name="Revenue (£)",
               mode="lines+markers", line=dict(color="#2E6F6E", width=3)),
    row=1, col=1, secondary_y=False,
)
fig.add_trace(
    go.Bar(x=monthly_orders.index, y=monthly_orders.values, name="Orders",
           marker_color="#D98E48", opacity=0.55),
    row=1, col=1, secondary_y=True,
)

fig.add_trace(
    go.Bar(x=top_countries.index, y=top_countries.values, name="Revenue by country",
           marker_color="#2E6F6E"),
    row=1, col=2,
)

fig.add_trace(
    go.Pie(labels=segment_counts.index, values=segment_counts.values, hole=0.45,
           name="RFM segments"),
    row=2, col=1,
)

fig.add_trace(
    go.Histogram(x=orders["order_value"].clip(upper=orders["order_value"].quantile(0.95)),
                 nbinsx=40, marker_color="#B23A48", name="Order value (£)"),
    row=2, col=2,
)

total_revenue = orders["order_value"].sum()
total_customers = customers.shape[0]
champions = segment_counts.get("Champions", 0)

fig.update_layout(
    title=dict(
        text=(f"Online Retail II Analytics Dashboard &nbsp;|&nbsp; "
              f"Total revenue: £{total_revenue:,.0f} &nbsp;|&nbsp; "
              f"Customers: {total_customers:,} &nbsp;|&nbsp; "
              f"Champions: {champions:,}"),
        x=0.5, xanchor="center", font=dict(size=16),
    ),
    height=800,
    width=1150,
    showlegend=True,
    template="plotly_white",
    margin=dict(t=110),
)
fig.update_yaxes(title_text="Revenue (£)", row=1, col=1, secondary_y=False)
fig.update_yaxes(title_text="Order count", row=1, col=1, secondary_y=True)
fig.update_yaxes(title_text="Revenue (£)", row=1, col=2)
fig.update_xaxes(title_text="Order value (£, clipped at 95th pct)", row=2, col=2)
fig.update_yaxes(title_text="Number of orders", row=2, col=2)

fig.write_html("dashboard.html", include_plotlyjs="cdn")
print("Dashboard written to dashboard.html")
