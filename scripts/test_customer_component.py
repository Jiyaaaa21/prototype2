
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR
from src.components.base_component import BaseComponent
from src.components.customer_component import CustomerComponent


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

    component = CustomerComponent(
        customers_df=customers,
        orders_df=orders,
        order_items_df=order_items,
    )

    assert isinstance(component, BaseComponent)
    print("TEST 1 PASSED: BaseComponent inheritance.")

    output = component.run()
    print("TEST 2 PASSED: Component execution.")

    assert BaseComponent.REQUIRED_OUTPUT_KEYS.issubset(
        output.keys()
    )
    print("TEST 3 PASSED: Standard output schema.")

    assert output["component"] == "customer_management"
    assert output["status"] == "SUCCESS"
    print("TEST 4 PASSED: Component identity and status.")

    assert output["metadata"]["customer_count"] == 96096
    assert output["metadata"]["order_count"] == 99441
    print("TEST 5 PASSED: Component metadata.")

    historical = output["historical_state"]["customers"]

    assert len(historical) == 96096
    assert output["historical_state"]["record_counts"]["customers"] == 96096
    print("TEST 6 PASSED: Historical customer state.")

    metrics = output["business_metrics"]

    assert metrics["total_customers"] == 96096
    assert metrics["repeat_customers"] == 2997
    assert metrics["single_order_customers"] == 93099
    print("TEST 7 PASSED: Customer business metrics.")

    assert all(
        rule["passed"]
        for rule in output["business_rule_results"]
    )
    print("TEST 8 PASSED: Business rule validation.")

    output["business_metrics"]["total_customers"] = -1

    fresh_output = component.get_output()

    assert fresh_output["business_metrics"]["total_customers"] == 96096
    print("TEST 9 PASSED: Output isolation.")

    assert len(customers) == 99441
    assert len(orders) == 99441
    print("TEST 10 PASSED: Original dataset integrity.")

    print("\nALL CUSTOMER COMPONENT TESTS PASSED.")


if __name__ == "__main__":
    main()
