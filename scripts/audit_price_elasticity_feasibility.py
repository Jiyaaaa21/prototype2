from pathlib import Path
import pandas as pd

from config.settings import DATA_DIR, REPORT_DIR


def main():
    items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    orders = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv",
        usecols=["order_id", "order_purchase_timestamp"]
    )

    items["price"] = pd.to_numeric(items["price"], errors="coerce")
    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"], errors="coerce"
    )

    df = items.merge(
        orders, on="order_id", how="inner", validate="many_to_one"
    )

    df = df.dropna(
        subset=["product_id", "seller_id", "price",
                "order_purchase_timestamp"]
    )

    df["month"] = df["order_purchase_timestamp"].dt.to_period("M")

    # Product + seller + month panel
    panel = (
        df.groupby(["product_id", "seller_id", "month"])
        .agg(
            item_lines=("order_item_id", "count"),
            avg_price=("price", "mean"),
            median_price=("price", "median"),
            unique_orders=("order_id", "nunique")
        )
        .reset_index()
        .sort_values(["product_id", "seller_id", "month"])
    )

    # Measure variation within each product-seller pair
    pairs = (
        panel.groupby(["product_id", "seller_id"])
        .agg(
            active_months=("month", "nunique"),
            total_item_lines=("item_lines", "sum"),
            mean_price=("avg_price", "mean"),
            min_price=("avg_price", "min"),
            max_price=("avg_price", "max")
        )
        .reset_index()
    )

    pairs["price_range_pct"] = (
        (pairs["max_price"] - pairs["min_price"])
        / pairs["mean_price"] * 100
    )

    eligible = pairs[pairs["active_months"] >= 3]
    varying = eligible[eligible["price_range_pct"] > 1]

    # Month-to-month changes; descriptive only, not causal elasticity
    panel["price_change_pct"] = (
        panel.groupby(["product_id", "seller_id"])["avg_price"]
        .pct_change(fill_method=None) * 100
    )

    panel["demand_change_pct"] = (
        panel.groupby(["product_id", "seller_id"])["item_lines"]
        .pct_change(fill_method=None) * 100
    )

    changes = panel.dropna(
        subset=["price_change_pct", "demand_change_pct"]
    )

    correlation = changes[
        ["price_change_pct", "demand_change_pct"]
    ].corr().iloc[0, 1]

    print("\\n===== PRICE ELASTICITY FEASIBILITY AUDIT =====")
    print("Order-item rows:", len(df))
    print("Unique products:", df["product_id"].nunique())
    print("Unique sellers:", df["seller_id"].nunique())
    print("Months covered:", df["month"].nunique())
    print("Product-seller pairs:", len(pairs))
    print("Product-seller pairs with 3+ active months:", len(eligible))
    print("Pairs with >1% price variation:", len(varying))

    share = len(varying) / len(eligible) * 100 if len(eligible) else 0
    print(f"Eligible pairs with price variation: {share:.2f}%")
    print("Month-to-month observations:", len(changes))
    print(f"Descriptive price-demand correlation: {correlation:.4f}")

    output = Path(REPORT_DIR) / "elasticity_feasibility"
    output.mkdir(parents=True, exist_ok=True)

    panel.to_csv(output / "product_seller_month_panel.csv", index=False)
    pairs.to_csv(output / "product_seller_price_variation.csv", index=False)

    print("\\nAudit files saved to:", output)


if __name__ == "__main__":
    main()