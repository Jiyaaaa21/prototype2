"""
Checkpoint 2a - read-only probe: payment coverage of orders that have items.

Decides how the propagation layer reconciles Order & Sales to Payment & Revenue.
Reads the raw Olist CSVs only. Writes nothing.

Run from repo root:
    python -m scripts.probe_payment_coverage
"""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/olist")
TOL = 0.01  # BRL tolerance for items+freight vs payments


def main() -> None:
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv",
                         usecols=["order_id", "order_status"])
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv",
                        usecols=["order_id", "price", "freight_value"])
    pays = pd.read_csv(RAW / "olist_order_payments_dataset.csv",
                       usecols=["order_id", "payment_type", "payment_value"])

    per_order = items.groupby("order_id").agg(
        nmv=("price", "sum"), freight=("freight_value", "sum")).reset_index()
    per_order["items_total"] = per_order["nmv"] + per_order["freight"]

    pay_order = pays.groupby("order_id").agg(
        paid=("payment_value", "sum"), n_pay_rows=("payment_value", "size")
    ).reset_index()

    df = (per_order.merge(orders, on="order_id", how="left")
                   .merge(pay_order, on="order_id", how="left"))
    df["has_payment"] = df["paid"].notna()
    df["gap"] = df["paid"].fillna(0) - df["items_total"]
    df["reconciled"] = df["has_payment"] & (df["gap"].abs() <= TOL)

    n = len(df)
    print("=" * 60)
    print("PAYMENT COVERAGE PROBE (orders that have item lines)")
    print("=" * 60)
    print(f"Orders with items:              {n:,}")
    print(f"  with >=1 payment row:         {int(df.has_payment.sum()):,}")
    print(f"  with NO payment row:          {int((~df.has_payment).sum()):,}")
    print(f"  payment == items+freight:     {int(df.reconciled.sum()):,} "
          f"({df.reconciled.mean():.2%})")
    print(f"  has payment but mismatched:   "
          f"{int((df.has_payment & ~df.reconciled).sum()):,}")
    print(f"Items+freight value, all:       {df.items_total.sum():,.2f}")
    print(f"Items+freight value, no payment:"
          f" {df.loc[~df.has_payment, 'items_total'].sum():,.2f}")
    print(f"Net gap (paid - items+freight): {df.gap.sum():,.2f}")

    print("\nBy order_status (orders with items):")
    g = df.groupby("order_status").agg(
        orders=("order_id", "size"),
        no_payment=("has_payment", lambda s: int((~s).sum())),
        mismatched=("reconciled", lambda s: int((~s).sum())),
    )
    print(g.sort_values("orders", ascending=False).to_string())

    mism = df[df.has_payment & ~df.reconciled]
    if len(mism):
        print(f"\nMismatched orders: mean |gap| = {mism.gap.abs().mean():.2f}, "
              f"max |gap| = {mism.gap.abs().max():.2f}")
    print("\nPROBE COMPLETE (read-only, nothing written)")


if __name__ == "__main__":
    main()
