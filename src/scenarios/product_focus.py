"""
Single-product focus (Checkpoint 6c).

Scopes the datasets to ONE product so the twin can be demonstrated on a
simple, traceable case. Payments are recorded per order, so a product's
payments can be attributed exactly only for orders that contain that
product alone ("single-product orders"). Only those orders are in scope.
"""
from __future__ import annotations

import pandas as pd

MIN_PURE_ORDERS = 100


def _order_product_counts(items: pd.DataFrame) -> pd.Series:
    return items.groupby("order_id")["product_id"].nunique()


def product_candidates(items: pd.DataFrame, orders: pd.DataFrame,
                       products: pd.DataFrame,
                       translation: pd.DataFrame | None = None,
                       min_pure_orders: int = MIN_PURE_ORDERS) -> pd.DataFrame:
    """Products with enough single-product orders, best first."""
    n_prod = _order_product_counts(items)
    df = items[["order_id", "product_id", "seller_id", "price"]].merge(
        orders[["order_id", "order_purchase_timestamp"]], on="order_id")
    df["pure"] = df["order_id"].map(n_prod) == 1
    df["month"] = pd.to_datetime(df["order_purchase_timestamp"]).dt.to_period("M")
    g = df.groupby("product_id")
    out = pd.DataFrame({
        "orders": g["order_id"].nunique(),
        "lines": g.size(),
        "sellers": g["seller_id"].nunique(),
        "months": g["month"].nunique(),
        "price_min": g["price"].min(),
        "price_max": g["price"].max(),
    })
    pure = df[df["pure"]].groupby("product_id")["order_id"].nunique()
    out["pure_orders"] = pure.reindex(out.index).fillna(0).astype(int)
    out["pure_share"] = out["pure_orders"] / out["orders"]
    cat = products.set_index("product_id")["product_category_name"]
    out["category"] = out.index.map(cat)
    if translation is not None:
        tcol = ("category_english" if "category_english" in translation.columns
                else "product_category_name_english")
        t = translation.set_index("product_category_name")[tcol]
        out["category"] = out["category"].map(t).fillna(out["category"])
    out = out[out["pure_orders"] >= min_pure_orders]
    return out.sort_values("pure_orders", ascending=False)


def focus_on_product(data: dict, product_id: str,
                     n_prod: pd.Series | None = None) -> tuple[dict, dict]:
    """
    Return (scoped_data, scope_info). Scoped data keeps the same keys as
    `data`: only single-product orders of `product_id` remain in items,
    orders and payments.
    """
    items = data["items"]
    if n_prod is None:
        n_prod = _order_product_counts(items)
    has_p = items.loc[items["product_id"] == product_id, "order_id"].unique()
    if len(has_p) == 0:
        raise ValueError(f"Unknown product_id: {product_id}")
    pure_ids = [o for o in has_p if n_prod[o] == 1]
    if not pure_ids:
        raise ValueError("No single-product orders for this product.")

    pure_set = set(pure_ids)
    scoped = dict(data)
    scoped["items"] = items[items["order_id"].isin(pure_set)].reset_index(drop=True)
    scoped["orders"] = data["orders"][data["orders"]["order_id"].isin(pure_set)
                                      ].reset_index(drop=True)
    scoped["payments"] = data["payments"][data["payments"]["order_id"].isin(pure_set)
                                          ].reset_index(drop=True)
    all_lines = int((items["product_id"] == product_id).sum())
    info = {
        "product_id": product_id,
        "orders_total": int(len(has_p)),
        "orders_in_scope": int(len(pure_ids)),
        "scope_share": len(pure_ids) / len(has_p),
        "lines_total": all_lines,
        "lines_in_scope": int(len(scoped["items"])),
        "sellers": int(scoped["items"]["seller_id"].nunique()),
    }
    return scoped, info
