
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR
from src.components.base_component import BaseComponent
from src.components.delivery_component import DeliveryComponent


def load_data():
    return {
        "orders_df": pd.read_csv(
            DATA_DIR / "olist_orders_dataset.csv"
        ),
        "order_items_df": pd.read_csv(
            DATA_DIR / "olist_order_items_dataset.csv"
        ),
        "reviews_df": pd.read_csv(
            DATA_DIR / "olist_order_reviews_dataset.csv"
        ),
        "customers_df": pd.read_csv(
            DATA_DIR / "olist_customers_dataset.csv"
        ),
        "sellers_df": pd.read_csv(
            DATA_DIR / "olist_sellers_dataset.csv"
        ),
    }


def main():
    data = load_data()

    component = DeliveryComponent(**data)

    assert isinstance(component, BaseComponent)
    print("TEST 1 PASSED: BaseComponent inheritance.")

    output = component.run()
    print("TEST 2 PASSED: Component execution.")

    required_keys = BaseComponent.REQUIRED_OUTPUT_KEYS
    assert required_keys.issubset(output.keys())
    print("TEST 3 PASSED: Standard output schema.")

    assert output["component"] == "delivery_customer_experience"
    assert output["status"] == "SUCCESS"
    print("TEST 4 PASSED: Component identity and status.")

    metadata = output["metadata"]

    assert metadata["order_count"] == 99441
    assert metadata["seller_count"] == 3095
    assert metadata["monthly_period_count"] == 25
    print("TEST 5 PASSED: Component metadata.")

    historical = output["historical_state"]

    assert len(historical["orders"]) == 99441
    assert len(historical["monthly"]) == 25
    assert len(historical["sellers"]) == 3095
    print("TEST 6 PASSED: Historical state structure.")

    metrics = output["business_metrics"]

    assert metrics["total_orders"] == 99441
    assert metrics["delivered_orders"] == 96470
    assert metrics["late_orders"] == 7826
    print("TEST 7 PASSED: Business metrics.")

    assert all(
        rule["passed"]
        for rule in output["business_rule_results"]
    )
    print("TEST 8 PASSED: Business rule validation.")

    output["business_metrics"]["total_orders"] = -1

    fresh_output = component.get_output()

    assert fresh_output["business_metrics"]["total_orders"] == 99441
    print("TEST 9 PASSED: Output isolation.")

    assert len(data["orders_df"]) == 99441
    assert len(data["reviews_df"]) == 99224
    print("TEST 10 PASSED: Original dataset integrity.")

    print("\nDELIVERY COMPONENT SUMMARY")
    for key, value in fresh_output["business_metrics"].items():
        print(f"{key}: {value}")

    print("\nALL DELIVERY COMPONENT TESTS PASSED.")


if __name__ == "__main__":
    main()
