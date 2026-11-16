
import pandas as pd

from config.settings import DATA_DIR
from src.components.product_management import ProductManagement


def main():
    products = pd.read_csv(
        DATA_DIR / "olist_products_dataset.csv"
    )
    order_items = pd.read_csv(
        DATA_DIR / "olist_order_items_dataset.csv"
    )
    orders = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv"
    )
    translation = pd.read_csv(
        DATA_DIR / "product_category_name_translation.csv"
    )

    original_products = products.copy(deep=True)
    original_items = order_items.copy(deep=True)
    original_orders = orders.copy(deep=True)
    original_translation = translation.copy(deep=True)

    manager = ProductManagement(
        products,
        order_items,
        translation
    )

    # Attach orders for monthly attribution.
    manager.orders = orders.copy(deep=True)

    result = manager.build_monthly_state()

    product_state = result["product_monthly_state"]
    category_state = result["category_monthly_state"]

    assert not product_state.empty
    assert not category_state.empty

    assert {
        "purchase_month",
        "product_id",
        "item_line_count",
        "distinct_orders",
        "units_value",
        "freight_value",
        "merchandise_share"
    }.issubset(product_state.columns)

    assert {
        "purchase_month",
        "category_english",
        "item_line_count",
        "distinct_orders",
        "distinct_products",
        "merchandise_value",
        "freight_value",
        "merchandise_share"
    }.issubset(category_state.columns)

    assert not product_state.duplicated(
        ["purchase_month", "product_id"]
    ).any()

    assert not category_state.duplicated(
        ["purchase_month", "category_english"]
    ).any()

    assert product_state["item_line_count"].sum() == len(order_items)

    assert abs(
        product_state["units_value"].sum()
        - order_items["price"].sum()
    ) < 0.01

    assert abs(
        category_state["merchandise_value"].sum()
        - order_items["price"].sum()
    ) < 0.01

    assert (
        product_state.groupby("purchase_month")[
            "merchandise_share"
        ].sum().sub(1).abs() < 1e-9
    ).all()

    assert (
        category_state.groupby("purchase_month")[
            "merchandise_share"
        ].sum().sub(1).abs() < 1e-9
    ).all()

    pd.testing.assert_frame_equal(products, original_products)
    pd.testing.assert_frame_equal(order_items, original_items)
    pd.testing.assert_frame_equal(orders, original_orders)
    pd.testing.assert_frame_equal(translation, original_translation)

    print("\nPRODUCT MONTHLY STATE")
    print("-" * 60)
    print("Product records:", len(product_state))
    print("Category records:", len(category_state))
    print("Monthly periods:", product_state["purchase_month"].nunique())

    print("\nTop 5 monthly product records:")
    print(product_state.head().to_string(index=False))

    print("\nTop 5 monthly category records:")
    print(category_state.head().to_string(index=False))

    print("\nTotal item lines:", product_state["item_line_count"].sum())
    print("Total merchandise value:", product_state["units_value"].sum())

    print("\nALL PRODUCT MONTHLY STATE TESTS PASSED.")


if __name__ == "__main__":
    main()
