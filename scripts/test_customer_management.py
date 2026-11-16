
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from pandas.testing import assert_frame_equal

from config.settings import DATA_DIR
from src.components.customer_management import CustomerManagement


# 1. LOAD DATASETS
customers_df = pd.read_csv(
    DATA_DIR / "olist_customers_dataset.csv"
)

orders_df = pd.read_csv(
    DATA_DIR / "olist_orders_dataset.csv"
)

order_items_df = pd.read_csv(
    DATA_DIR / "olist_order_items_dataset.csv"
)


# 2. CREATE ORIGINAL SNAPSHOTS
original_snapshots = {
    "customers": customers_df.copy(deep=True),
    "orders": orders_df.copy(deep=True),
    "order_items": order_items_df.copy(deep=True)
}


# 3. INITIALIZE CUSTOMER MANAGEMENT
customer_management = CustomerManagement(
    customers_df=customers_df,
    orders_df=orders_df,
    order_items_df=order_items_df
)


# TEST 1: DATA VALIDATION
assert customer_management.validate_data() is True

print("TEST 1 PASSED: Customer data validation.")


# TEST 2: BUILD CUSTOMER STATE
customer_state = customer_management.build_customer_state()

assert customer_state is not None
assert not customer_state.empty

assert customer_state["customer_unique_id"].is_unique

print("TEST 2 PASSED: Customer historical state construction.")


# TEST 3: CUSTOMER IDENTITY AND ORDER COUNTS
assert customer_state["customer_unique_id"].notna().all()

assert customer_state["order_count"].sum() == orders_df["order_id"].nunique()

assert (customer_state["order_count"] >= 1).all()

print("TEST 3 PASSED: Customer identity and order aggregation.")


# TEST 4: REPEAT CUSTOMER CLASSIFICATION
expected_repeat = customer_state["order_count"] > 1

assert (
    customer_state["repeat_customer"] == expected_repeat
).all()

assert customer_state["repeat_customer"].sum() > 0

print("TEST 4 PASSED: Repeat customer classification.")


# TEST 5: FINANCIAL METRICS
assert (customer_state["merchandise_spend"] >= 0).all()
assert (customer_state["freight_spend"] >= 0).all()

print("TEST 5 PASSED: Merchandise and freight calculations.")


# TEST 6: SUMMARY METRICS
summary = customer_management.get_summary()

required_metrics = {
    "total_customers",
    "single_order_customers",
    "repeat_customers",
    "repeat_customer_share",
    "mean_orders_per_customer",
    "median_merchandise_spend_per_customer"
}

assert required_metrics.issubset(summary.keys())

assert (
    summary["single_order_customers"]
    + summary["repeat_customers"]
    == summary["total_customers"]
)

print("TEST 6 PASSED: Customer business metrics.")


# TEST 7: HISTORICAL DATA IMMUTABILITY
assert_frame_equal(original_snapshots["customers"], customers_df)
assert_frame_equal(original_snapshots["orders"], orders_df)
assert_frame_equal(original_snapshots["order_items"], order_items_df)

print("TEST 7 PASSED: Original historical datasets unchanged.")


# TEST 8: COMPONENT INPUT IMMUTABILITY
assert_frame_equal(
    original_snapshots["customers"],
    customer_management.customers
)

assert_frame_equal(
    original_snapshots["orders"],
    customer_management.orders
)

assert_frame_equal(
    original_snapshots["order_items"],
    customer_management.order_items
)

print("TEST 8 PASSED: Component input datasets unchanged.")


# 9. DISPLAY RESULTS
print("\nCUSTOMER MANAGEMENT SUMMARY")
print("=" * 50)

for metric, value in summary.items():
    print(f"{metric}: {value}")

print("\nCustomer State Records:", len(customer_state))
print("Customer State Columns:", customer_state.columns.tolist())

print("\n" + "=" * 50)
print("ALL CUSTOMER MANAGEMENT TESTS PASSED.")
print("=" * 50)
