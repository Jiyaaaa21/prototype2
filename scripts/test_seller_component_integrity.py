
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from pandas.testing import assert_frame_equal

from config.settings import (
    SELLERS_FILE,
    ORDERS_FILE,
    ORDER_ITEMS_FILE
)

from src.components.seller_component import SellerComponent


# --------------------------------------------------
# 1. LOAD HISTORICAL DATA
# --------------------------------------------------

sellers_df = pd.read_csv(SELLERS_FILE)
orders_df = pd.read_csv(ORDERS_FILE)
order_items_df = pd.read_csv(ORDER_ITEMS_FILE)


# --------------------------------------------------
# 2. CREATE SNAPSHOTS BEFORE EXECUTION
# --------------------------------------------------

original_snapshots = {
    "sellers": sellers_df.copy(deep=True),
    "orders": orders_df.copy(deep=True),
    "order_items": order_items_df.copy(deep=True)
}


# --------------------------------------------------
# 3. INITIALIZE AND RUN COMPONENT
# --------------------------------------------------

component = SellerComponent(
    sellers_df=sellers_df,
    order_items_df=order_items_df,
    orders_df=orders_df
)

output = component.run()


# --------------------------------------------------
# 4. TEST HISTORICAL DATA IMMUTABILITY
# --------------------------------------------------

assert_frame_equal(
    original_snapshots["sellers"],
    sellers_df
)

assert_frame_equal(
    original_snapshots["orders"],
    orders_df
)

assert_frame_equal(
    original_snapshots["order_items"],
    order_items_df
)

print("TEST 1 PASSED: Original historical datasets unchanged.")


# --------------------------------------------------
# 5. TEST COMPONENT INPUT DATA IMMUTABILITY
# --------------------------------------------------

assert_frame_equal(
    original_snapshots["sellers"],
    component.sellers_df
)

assert_frame_equal(
    original_snapshots["orders"],
    component.orders_df
)

assert_frame_equal(
    original_snapshots["order_items"],
    component.order_items_df
)

print("TEST 2 PASSED: Component input datasets unchanged.")


# --------------------------------------------------
# 6. TEST OUTPUT INTEGRITY
# --------------------------------------------------

assert output["component"] == "seller_management"

assert output["metadata"]["seller_count"] == 3095

assert output["historical_state"]["record_count"] == 3095

assert len(output["scenario_results"]) == 6

assert len(output["business_rule_results"]) == 5

assert all(
    rule["status"] == "PASSED"
    for rule in output["business_rule_results"]
)

assert output["business_metrics"]["total_sellers"] == 3095

print("TEST 3 PASSED: Structured output integrity verified.")


# --------------------------------------------------
# 7. TEST SCENARIO ISOLATION
# --------------------------------------------------

seller_state_before = (
    component.seller_management.seller_state.copy(deep=True)
)

component.scenario_engine.run_scenarios()

seller_state_after = (
    component.seller_management.seller_state.copy(deep=True)
)

assert_frame_equal(
    seller_state_before,
    seller_state_after
)

print("TEST 4 PASSED: Scenario execution did not alter seller state.")


# --------------------------------------------------
# FINAL RESULT
# --------------------------------------------------

print("\n" + "=" * 60)
print("ALL SELLER COMPONENT INTEGRITY TESTS PASSED.")
print("=" * 60)
