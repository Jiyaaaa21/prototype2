
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config.settings import DATA_DIR
from src.components.base_component import BaseComponent
from src.components.payment_component import PaymentComponent


# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

orders = pd.read_csv(
    DATA_DIR / "olist_orders_dataset.csv"
)

payments = pd.read_csv(
    DATA_DIR / "olist_order_payments_dataset.csv"
)

original_orders = orders.copy(deep=True)
original_payments = payments.copy(deep=True)

component = PaymentComponent(
    orders_df=orders,
    payments_df=payments
)


# --------------------------------------------------
# TEST 1: BASE COMPONENT INHERITANCE
# --------------------------------------------------

assert isinstance(component, BaseComponent)

assert (
    component.component_name
    == "payment_revenue_management"
)

print("TEST 1 PASSED: BaseComponent inheritance.")


# --------------------------------------------------
# TEST 2: COMPONENT EXECUTION
# --------------------------------------------------

output = component.run()

assert isinstance(output, dict)
assert output["status"] == "SUCCESS"

print("TEST 2 PASSED: Payment component execution.")


# --------------------------------------------------
# TEST 3: STANDARD OUTPUT SCHEMA
# --------------------------------------------------

required_keys = {
    "component",
    "metadata",
    "historical_state",
    "business_metrics",
    "scenario_results",
    "business_rule_results",
    "status"
}

assert required_keys.issubset(output.keys())

assert output["component"] == "payment_revenue_management"

print("TEST 3 PASSED: Standard output schema.")


# --------------------------------------------------
# TEST 4: METADATA VALIDATION
# --------------------------------------------------

metadata = output["metadata"]

assert metadata["currency"] == "BRL"

assert (
    metadata["data_type"]
    == "historical_payment_analysis"
)

assert metadata["order_count"] == len(orders)

assert metadata["payment_record_count"] == len(payments)

assert metadata["payment_method_count"] == 5

assert metadata["generated_at"]

print("TEST 4 PASSED: Component metadata.")


# --------------------------------------------------
# TEST 5: HISTORICAL STATE VALIDATION
# --------------------------------------------------

historical_state = output["historical_state"]

assert set(historical_state.keys()) == {
    "orders",
    "monthly",
    "payment_methods",
    "record_counts"
}

assert (
    historical_state["record_counts"]["orders"]
    == len(orders)
)

assert (
    historical_state["record_counts"]["monthly"]
    == 25
)

assert (
    historical_state["record_counts"]["payment_methods"]
    == 5
)

assert len(historical_state["orders"]) == len(orders)

assert len(historical_state["monthly"]) == 25

assert len(historical_state["payment_methods"]) == 5

print("TEST 5 PASSED: Historical state structure.")


# --------------------------------------------------
# TEST 6: BUSINESS METRICS
# --------------------------------------------------

metrics = output["business_metrics"]

assert metrics["total_orders"] == len(orders)

assert metrics["total_payment_records"] == len(payments)

assert metrics["orders_with_payments"] == (
    payments["order_id"].nunique()
)

assert metrics["orders_without_payments"] == (
    len(orders) - payments["order_id"].nunique()
)

assert metrics["distinct_payment_methods"] == 5

assert metrics["monthly_periods"] == 25

print("TEST 6 PASSED: Business metrics.")


# --------------------------------------------------
# TEST 7: SCENARIO AND BUSINESS RULE STRUCTURE
# --------------------------------------------------

assert output["scenario_results"] == []

rules = output["business_rule_results"]

assert len(rules) == 8
assert all(rule["passed"] for rule in rules)
assert output["status"] == "SUCCESS"

print("TEST 7 PASSED: Scenario and business rule structure.")


# --------------------------------------------------
# TEST 8: OUTPUT ACCESS AND ISOLATION
# --------------------------------------------------

stored_output = component.get_output()

assert stored_output == output

stored_output["business_metrics"]["total_orders"] = -1

assert (
    component.get_output()["business_metrics"]["total_orders"]
    == len(orders)
)

print("TEST 8 PASSED: Output isolation.")


# --------------------------------------------------
# TEST 9: INPUT DATA IMMUTABILITY
# --------------------------------------------------

pd.testing.assert_frame_equal(
    orders,
    original_orders
)

pd.testing.assert_frame_equal(
    payments,
    original_payments
)

print("TEST 9 PASSED: Original datasets unchanged.")


# --------------------------------------------------
# TEST 10: COMPONENT RE-EXECUTION
# --------------------------------------------------

second_output = component.run()

assert second_output["status"] == "SUCCESS"

assert (
    second_output["business_metrics"]["total_payment_value"]
    == output["business_metrics"]["total_payment_value"]
)

assert (
    second_output["historical_state"]["record_counts"]
    == output["historical_state"]["record_counts"]
)

print("TEST 10 PASSED: Component re-execution.")


# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

print("\nPAYMENT COMPONENT OUTPUT SUMMARY")
print("=" * 55)

print("Component:", output["component"])
print("Status:", output["status"])

print("\nMetadata:")
for key, value in output["metadata"].items():
    print(f"{key}: {value}")

print("\nBusiness Metrics:")
for key, value in output["business_metrics"].items():
    print(f"{key}: {value}")

print("\nHistorical State Record Counts:")
for key, value in historical_state["record_counts"].items():
    print(f"{key}: {value}")

print("\n" + "=" * 55)
print("ALL PAYMENT COMPONENT TESTS PASSED.")
print("=" * 55)
