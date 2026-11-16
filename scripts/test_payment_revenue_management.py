
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR
from src.components.payment_revenue_management import (
    PaymentRevenueManagement
)


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

component = PaymentRevenueManagement(
    orders_df=orders,
    payments_df=payments
)


# --------------------------------------------------
# TEST 1: DATA VALIDATION
# --------------------------------------------------

assert component.validate_data() is True

print("TEST 1 PASSED: Payment and revenue data validation.")


# --------------------------------------------------
# TEST 2: HISTORICAL STATE CONSTRUCTION
# --------------------------------------------------

states = component.build_payment_state()

order_state = states["order_state"]
monthly_state = states["monthly_state"]
payment_method_state = states["payment_method_state"]

assert isinstance(order_state, pd.DataFrame)
assert isinstance(monthly_state, pd.DataFrame)
assert isinstance(payment_method_state, pd.DataFrame)

assert len(order_state) == len(orders)

assert order_state["order_id"].is_unique
assert monthly_state["purchase_month"].is_unique
assert payment_method_state["payment_type"].is_unique

print("TEST 2 PASSED: Historical payment state construction.")


# --------------------------------------------------
# TEST 3: ORDER-LEVEL PAYMENT AGGREGATION
# --------------------------------------------------

expected_payment_value = payments["payment_value"].sum()

assert np.isclose(
    order_state["total_payment_value"].sum(),
    expected_payment_value
)

assert (
    order_state["payment_record_count"].sum()
    == len(payments)
)

assert (
    order_state["has_payment"].sum()
    == payments["order_id"].nunique()
)

assert (
    order_state["order_id"].nunique()
    == orders["order_id"].nunique()
)

print("TEST 3 PASSED: Order-level payment aggregation.")


# --------------------------------------------------
# TEST 4: MONTHLY PAYMENT AGGREGATION
# --------------------------------------------------

assert (
    monthly_state["total_orders"].sum()
    == orders["order_id"].nunique()
)

assert (
    monthly_state["orders_with_payments"].sum()
    == payments["order_id"].nunique()
)

assert (
    monthly_state["payment_record_count"].sum()
    == len(payments)
)

assert np.isclose(
    monthly_state["total_payment_value"].sum(),
    expected_payment_value
)

print("TEST 4 PASSED: Monthly payment aggregation.")


# --------------------------------------------------
# TEST 5: MONTHLY PAYMENT METHOD INTEGRITY
# --------------------------------------------------

method_columns = [
    column for column in monthly_state.columns
    if column.startswith("method_value_")
]

assert len(method_columns) > 0

monthly_method_total = monthly_state[
    method_columns
].sum(axis=1)

assert np.allclose(
    monthly_method_total.to_numpy(),
    monthly_state["total_payment_value"].to_numpy()
)

print("TEST 5 PASSED: Monthly payment method distribution.")


# --------------------------------------------------
# TEST 6: PAYMENT METHOD CONTRIBUTION
# --------------------------------------------------

assert (
    payment_method_state["payment_record_count"].sum()
    == len(payments)
)

assert np.isclose(
    payment_method_state["total_payment_value"].sum(),
    expected_payment_value
)

assert (
    payment_method_state["distinct_orders"].max()
    <= orders["order_id"].nunique()
)

assert (
    payment_method_state["payment_type"].nunique()
    == payments["payment_type"].fillna("unknown").replace(
        "", "unknown"
    ).nunique()
)

print("TEST 6 PASSED: Payment method contribution.")


# --------------------------------------------------
# TEST 7: BUSINESS SUMMARY
# --------------------------------------------------

summary = component.get_summary()

expected_orders_with_payments = payments["order_id"].nunique()

expected_average_payment = (
    expected_payment_value / expected_orders_with_payments
)

assert summary["total_orders"] == orders["order_id"].nunique()

assert (
    summary["orders_with_payments"]
    == expected_orders_with_payments
)

assert (
    summary["orders_without_payments"]
    == summary["total_orders"] - expected_orders_with_payments
)

assert (
    summary["total_payment_records"] == len(payments)
)

assert np.isclose(
    summary["total_payment_value"],
    expected_payment_value
)

assert np.isclose(
    summary["average_payment_per_order"],
    expected_average_payment
)

print("TEST 7 PASSED: Payment and revenue business metrics.")


# --------------------------------------------------
# TEST 8: PAYMENT RECORD AND ORDER COUNTS
# --------------------------------------------------

assert (
    order_state["payment_record_count"].sum()
    == len(payments)
)

assert (
    order_state["has_payment"].sum()
    + (~order_state["has_payment"]).sum()
    == len(orders)
)

assert (
    summary["monthly_periods"]
    == orders["order_purchase_timestamp"].pipe(
        pd.to_datetime
    ).dt.to_period("M").nunique()
)

print("TEST 8 PASSED: Payment and order count integrity.")


# --------------------------------------------------
# TEST 9: ORIGINAL DATASETS UNCHANGED
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
# TEST 10: COMPONENT INPUT ISOLATION
# --------------------------------------------------

pd.testing.assert_frame_equal(
    component.orders,
    original_orders
)

pd.testing.assert_frame_equal(
    component.payments,
    original_payments
)

# Mutating returned states must not modify stored states.
returned_states = component.build_payment_state()

returned_states["order_state"].loc[
    0, "total_payment_value"
] = -999

assert (
    component.order_state.loc[0, "total_payment_value"] >= 0
)

print("TEST 10 PASSED: Component input and output isolation.")


# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

print("\nPAYMENT & REVENUE MANAGEMENT SUMMARY")
print("=" * 55)

for key, value in component.get_summary().items():
    print(f"{key}: {value}")

print("\nPayment Method Contribution:")
print(
    payment_method_state[
        [
            "payment_type",
            "payment_record_count",
            "distinct_orders",
            "total_payment_value",
            "average_payment_value"
        ]
    ].to_string(index=False)
)

print("\nMonthly Records:", len(monthly_state))

print("\n" + "=" * 55)
print("ALL PAYMENT & REVENUE MANAGEMENT TESTS PASSED.")
print("=" * 55)
