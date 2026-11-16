
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR
from src.components.base_component import BaseComponent
from src.components.order_sales_component import OrderSalesComponent


def main():
    orders = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv"
    )
    order_items = pd.read_csv(
        DATA_DIR / "olist_order_items_dataset.csv"
    )
    customers = pd.read_csv(
        DATA_DIR / "olist_customers_dataset.csv"
    )
    products = pd.read_csv(
        DATA_DIR / "olist_products_dataset.csv"
    )
    sellers = pd.read_csv(
        DATA_DIR / "olist_sellers_dataset.csv"
    )

    component = OrderSalesComponent(
        orders_df=orders,
        order_items_df=order_items,
        customers_df=customers,
        products_df=products,
        sellers_df=sellers,
    )

    assert isinstance(component, BaseComponent)
    print("TEST 1 PASSED: BaseComponent inheritance.")

    output = component.run()
    print("TEST 2 PASSED: Component execution.")

    assert BaseComponent.REQUIRED_OUTPUT_KEYS.issubset(
        output.keys()
    )
    print("TEST 3 PASSED: Standard output schema.")

    assert output["component"] == "order_sales_management"
    assert output["status"] == "SUCCESS"
    print("TEST 4 PASSED: Component identity and status.")

    metadata = output["metadata"]

    assert metadata["order_count"] == 99441
    assert metadata["monthly_period_count"] == 25
    assert metadata["order_item_count"] == 112650
    print("TEST 5 PASSED: Component metadata.")

    historical = output["historical_state"]

    assert len(historical["orders"]) == 99441
    assert len(historical["monthly"]) == 25

    assert set(historical["contributions"].keys()) == {
        "products",
        "categories",
        "sellers",
        "customers",
    }
    print("TEST 6 PASSED: Historical state structure.")

    metrics = output["business_metrics"]

    assert metrics["total_orders"] == 99441
    assert metrics["orders_with_items"] == 98666
    assert metrics["total_order_items"] == 112650
    print("TEST 7 PASSED: Order and sales metrics.")

    assert all(
        rule["passed"]
        for rule in output["business_rule_results"]
    )
    print("TEST 8 PASSED: Business rule validation.")

    output["business_metrics"]["total_orders"] = -1

    fresh_output = component.get_output()

    assert fresh_output["business_metrics"]["total_orders"] == 99441
    print("TEST 9 PASSED: Output isolation.")

    assert len(orders) == 99441
    assert len(order_items) == 112650
    print("TEST 10 PASSED: Original dataset integrity.")

    print("\nALL ORDER & SALES COMPONENT TESTS PASSED.")


if __name__ == "__main__":
    main()
