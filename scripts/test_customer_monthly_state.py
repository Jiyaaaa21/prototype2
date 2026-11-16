
import pandas as pd

from config.settings import DATA_DIR
from src.components.customer_management import CustomerManagement


def main():
    customers = pd.read_csv(
        DATA_DIR / "olist_customers_dataset.csv"
    )
    orders = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv"
    )
    order_items = pd.read_csv(
        DATA_DIR / "olist_order_items_dataset.csv"
    )

    manager = CustomerManagement(
        customers,
        orders,
        order_items
    )

    original_orders = orders.copy(deep=True)
    original_items = order_items.copy(deep=True)
    original_customers = customers.copy(deep=True)

    monthly = manager.build_monthly_state()

    required_columns = {
        "purchase_month",
        "total_orders",
        "active_customers",
        "orders_with_items",
        "item_count",
        "merchandise_spend",
        "freight_spend",
        "average_order_value"
    }

    assert required_columns.issubset(monthly.columns)
    assert monthly["purchase_month"].is_unique
    assert monthly["total_orders"].sum() == len(orders)
    assert monthly["item_count"].sum() == len(order_items)
    assert (monthly["active_customers"] > 0).all()
    assert (monthly["merchandise_spend"] >= 0).all()
    assert (monthly["freight_spend"] >= 0).all()

    pd.testing.assert_frame_equal(orders, original_orders)
    pd.testing.assert_frame_equal(order_items, original_items)
    pd.testing.assert_frame_equal(customers, original_customers)

    print("\nCUSTOMER MONTHLY STATE")
    print("-" * 60)
    print(monthly.to_string(index=False))

    print("\nMonthly periods:", len(monthly))
    print("Total orders:", monthly["total_orders"].sum())
    print("Total item lines:", monthly["item_count"].sum())
    print("Total merchandise spend:", monthly["merchandise_spend"].sum())
    print("\nALL CUSTOMER MONTHLY STATE TESTS PASSED.")


if __name__ == "__main__":
    main()
