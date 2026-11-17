"""
Checkpoint 6b - read-only probe: which products can support a clean
single-product demo?

A product's payments can be attributed exactly only for orders that contain
that product alone ("pure" orders). Writes nothing.

Run from repo root:  python -m scripts.probe_product_candidates
"""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/olist")
TOL = 0.01


def main() -> None:
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv",
                        usecols=["order_id", "product_id", "seller_id",
                                 "price", "freight_value"])
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv",
                         usecols=["order_id", "order_purchase_timestamp"])
    products = pd.read_csv(RAW / "olist_products_dataset.csv",
                           usecols=["product_id", "product_category_name"])
    trans = pd.read_csv(RAW / "product_category_name_translation.csv")
    pays = pd.read_csv(RAW / "olist_order_payments_dataset.csv",
                       usecols=["order_id", "payment_value"])

    order_info = items.groupby("order_id").agg(
        n_products=("product_id", "nunique"),
        items_total=("price", "sum"), freight=("freight_value", "sum"))
    order_info["items_total"] += order_info["freight"]
    order_info = order_info.join(pays.groupby("order_id")["payment_value"].sum())
    order_info["pure"] = order_info["n_products"] == 1
    order_info["reconciled"] = (
        (order_info["payment_value"] - order_info["items_total"]).abs() <= TOL)

    df = items.merge(order_info[["pure", "reconciled"]],
                     left_on="order_id", right_index=True)
    df = df.merge(orders, on="order_id")
    df["month"] = pd.to_datetime(df["order_purchase_timestamp"]).dt.to_period("M")

    g = df.groupby("product_id")
    out = pd.DataFrame({
        "lines": g.size(),
        "orders": g["order_id"].nunique(),
        "sellers": g["seller_id"].nunique(),
        "months": g["month"].nunique(),
        "price_min": g["price"].min(),
        "price_median": g["price"].median(),
        "price_max": g["price"].max(),
    })
    pure = df[df["pure"]].groupby("product_id")["order_id"].nunique()
    rec = df[df["pure"] & df["reconciled"]].groupby("product_id")["order_id"].nunique()
    out["pure_orders"] = pure.reindex(out.index).fillna(0).astype(int)
    out["pure_share"] = (out["pure_orders"] / out["orders"]).round(3)
    out["pure_reconciled_share"] = (
        rec.reindex(out.index).fillna(0) / out["pure_orders"].where(out["pure_orders"] > 0)
    ).round(3)
    out = out.join(products.set_index("product_id")["product_category_name"])
    out = out.join(trans.set_index("product_category_name")
                   ["product_category_name_english"], on="product_category_name")

    top = out.sort_values("pure_orders", ascending=False).head(12)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    print("=" * 70)
    print("TOP 12 PRODUCTS BY SINGLE-PRODUCT ORDERS")
    print("=" * 70)
    print(top.drop(columns=["product_category_name"]).to_string())
    print(f"\nProducts overall: {len(out):,}; with >=100 pure orders: "
          f"{int((out['pure_orders'] >= 100).sum())}")
    print("\nPROBE COMPLETE (read-only, nothing written)")


if __name__ == "__main__":
    main()
