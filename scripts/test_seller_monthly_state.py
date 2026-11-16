import pandas as pd
from pandas.testing import assert_frame_equal

from config.settings import DATA_DIR
from src.components.seller_management import SellerManagement


def load_data():
    sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
    order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")

    return sellers, order_items, orders


def main():
    sellers, items, orders = load_data()

    original_sellers = sellers.copy(deep=True)
    original_items = items.copy(deep=True)
    original_orders = orders.copy(deep=True)

    manager = SellerManagement(sellers, items, orders)
    monthly_state = manager.build_monthly_state()

    required_columns = {
        "purchase_month",
        "seller_id",
        "item_line_count",
        "distinct_orders",
        "distinct_products",
        "merchandise_value",
        "freight_value",
        "delivered_item_lines",
        "delivered_orders",
        "delivered_merchandise_value",
        "associated_freight_value",
        "merchandise_share"
    }

    assert required_columns.issubset(monthly_state.columns)
    assert not monthly_state.duplicated(
        ["purchase_month", "seller_id"]
    ).any()

    # Reconciliation against the source order-item dataset.
    assert monthly_state["item_line_count"].sum() == len(items)

    expected_merchandise = pd.to_numeric(items["price"]).sum()
    expected_freight = pd.to_numeric(items["freight_value"]).sum()

    assert abs(
        monthly_state["merchandise_value"].sum()
        - expected_merchandise
    ) < 0.01

    assert abs(
        monthly_state["freight_value"].sum()
        - expected_freight
    ) < 0.01

    # Delivered metrics must reconcile to delivered order items.
    delivered_order_ids = set(
        orders.loc[
            orders["order_status"] == "delivered", "order_id"
        ]
    )
    delivered_items = items[items["order_id"].isin(delivered_order_ids)]

    assert (
        monthly_state["delivered_item_lines"].sum()
        == len(delivered_items)
    )

    assert abs(
        monthly_state["delivered_merchandise_value"].sum()
        - pd.to_numeric(delivered_items["price"]).sum()
    ) < 0.01

    assert abs(
        monthly_state["associated_freight_value"].sum()
        - pd.to_numeric(delivered_items["freight_value"]).sum()
    ) < 0.01

    # Seller merchandise shares must total 1 in each active month.
    monthly_shares = monthly_state.groupby(
        "purchase_month"
    )["merchandise_share"].sum()

    assert (monthly_shares.sub(1).abs() < 1e-9).all()

    # Source data must remain unchanged.
    assert_frame_equal(sellers, original_sellers)
    assert_frame_equal(items, original_items)
    assert_frame_equal(orders, original_orders)

    print("\nSELLER MONTHLY STATE")
    print("-" * 60)
    print("Seller-month records:", len(monthly_state))
    print("Distinct sellers:", monthly_state["seller_id"].nunique())
    print("Active months:", monthly_state["purchase_month"].nunique())
    print("Total item lines:", monthly_state["item_line_count"].sum())
    print("Total merchandise value:", monthly_state["merchandise_value"].sum())
    print("Total freight value:", monthly_state["freight_value"].sum())
    print(
        "Delivered item lines:",
        monthly_state["delivered_item_lines"].sum()
    )
    print("\nTop 5 monthly seller records:")
    print(monthly_state.head().to_string(index=False))
    print("\nALL SELLER MONTHLY STATE TESTS PASSED.")


if __name__ == "__main__":
    main()