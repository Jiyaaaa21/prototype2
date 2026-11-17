"""
Observed business metrics for the Business Overview page.
Pure pandas, no Streamlit. Every figure is computed from the Olist tables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

THIN_MONTH_ORDERS = 500      # months below this are flagged as thin
MIN_DELIVERED_MONTH = 100    # on-time rate shown only for months with this many


def _month(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.to_period("M").astype(str)


def compute_overview(data: dict) -> dict:
    items, orders = data["items"], data["orders"]
    customers, products = data["customers"], data["products"]
    payments, reviews = data["payments"], data["reviews"]
    trans = data["translation"]

    items = items.copy()
    items["line_value"] = items["price"] + items["freight_value"]
    orders = orders.copy()
    orders["month"] = _month(orders["order_purchase_timestamp"])

    # ---------------- KPIs ----------------
    revenue = float(items["line_value"].sum())
    orders_with_items = int(items["order_id"].nunique())
    kpis = {
        "revenue": revenue,
        "merchandise": float(items["price"].sum()),
        "freight": float(items["freight_value"].sum()),
        "orders": int(len(orders)),
        "orders_with_items": orders_with_items,
        "aov": revenue / orders_with_items,
        "customers": int(customers["customer_unique_id"].nunique()),
        "sellers": int(items["seller_id"].nunique()),
        "products": int(items["product_id"].nunique()),
        "first_month": orders["month"].min(), "last_month": orders["month"].max(),
    }

    # ---------------- monthly ----------------
    om = items.merge(orders[["order_id", "month"]], on="order_id")
    monthly = om.groupby("month").agg(
        revenue=("line_value", "sum"), orders=("order_id", "nunique")).reset_index()
    monthly["thin"] = monthly["orders"] < THIN_MONTH_ORDERS

    # ---------------- categories ----------------
    tcol = ("category_english" if "category_english" in trans.columns
            else "product_category_name_english")
    cat = items.merge(products[["product_id", "product_category_name"]],
                      on="product_id", how="left")
    cat = cat.merge(trans[["product_category_name", tcol]],
                    on="product_category_name", how="left")
    cat["category"] = cat[tcol].fillna(cat["product_category_name"]).fillna("uncategorised")
    category = (cat.groupby("category")["price"].sum().sort_values(ascending=False)
                .head(10).reset_index().rename(columns={"price": "merchandise"}))

    # ---------------- sellers ----------------
    s = items.groupby("seller_id").agg(
        merchandise=("price", "sum"), lines=("order_id", "size"),
        orders=("order_id", "nunique")).sort_values("merchandise", ascending=False)
    top_n = max(1, int(np.ceil(len(s) * 0.10)))
    kpis["top10pct_sellers_share"] = float(
        s["merchandise"].head(top_n).sum() / s["merchandise"].sum())
    top_sellers = s.head(10).reset_index()
    top_sellers["label"] = top_sellers["seller_id"].str[:8]

    # ---------------- delivery ----------------
    d = orders[orders["order_status"] == "delivered"].copy()
    for c in ("order_purchase_timestamp", "order_delivered_customer_date",
              "order_estimated_delivery_date"):
        d[c] = pd.to_datetime(d[c], errors="coerce")
    d = d.dropna(subset=["order_delivered_customer_date", "order_estimated_delivery_date"])
    d["days"] = (d["order_delivered_customer_date"]
                 - d["order_purchase_timestamp"]).dt.total_seconds() / 86400
    d["late"] = d["order_delivered_customer_date"] > d["order_estimated_delivery_date"]
    kpis["delivered_orders"] = int(len(d))
    kpis["on_time_rate"] = float(1 - d["late"].mean())
    kpis["avg_delivery_days"] = float(d["days"].mean())

    dm = d.groupby("month").agg(delivered=("order_id", "size"),
                                on_time=("late", lambda x: 1 - x.mean())).reset_index()
    delivery_monthly = dm[dm["delivered"] >= MIN_DELIVERED_MONTH]

    # reviews: one score per order (mean of its reviews)
    r = reviews.groupby("order_id")["review_score"].mean().rename("score")
    d = d.join(r, on="order_id")
    kpis["avg_review"] = float(d["score"].mean())
    bins = [-np.inf, 7, 14, 30, np.inf]
    labels = ["Up to 7 days", "8 to 14 days", "15 to 30 days", "Over 30 days"]
    d["bucket"] = pd.cut(d["days"], bins=bins, labels=labels)
    review_by_delivery = (d.groupby("bucket", observed=True)
                          .agg(score=("score", "mean"), orders=("order_id", "size"))
                          .reset_index())
    kpis["review_on_time"] = float(d.loc[~d["late"], "score"].mean())
    kpis["review_late"] = float(d.loc[d["late"], "score"].mean())

    # ---------------- payments ----------------
    pay = (payments.groupby("payment_type")["payment_value"].sum()
           .sort_values(ascending=False).reset_index())
    pay = pay[pay["payment_type"] != "not_defined"]

    return {"kpis": kpis, "monthly": monthly, "category": category,
            "top_sellers": top_sellers, "delivery_monthly": delivery_monthly,
            "review_by_delivery": review_by_delivery, "payment_types": pay}
