
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config.settings import (
    SELLERS_FILE,
    ORDERS_FILE,
    ORDER_ITEMS_FILE
)

from src.components.seller_component import SellerComponent


# Load historical datasets
sellers_df = pd.read_csv(SELLERS_FILE)
orders_df = pd.read_csv(ORDERS_FILE)
order_items_df = pd.read_csv(ORDER_ITEMS_FILE)

# Initialize unified component
seller_component = SellerComponent(
    sellers_df=sellers_df,
    order_items_df=order_items_df,
    orders_df=orders_df
)

# Execute component
seller_output = seller_component.run()

# Verify output structure
required_keys = [
    "component",
    "metadata",
    "historical_state",
    "business_metrics",
    "scenario_results",
    "business_rule_results",
    "cost_disclosure"
]

assert all(key in seller_output for key in required_keys)

# Verify historical state
assert seller_output["metadata"]["seller_count"] == 3095
assert seller_output["historical_state"]["record_count"] == 3095

# Verify scenarios
assert len(seller_output["scenario_results"]) == 6

# Verify business rules
rule_results = seller_output["business_rule_results"]

assert all(
    rule["status"] == "PASSED"
    for rule in rule_results
)

# Verify output access method
assert seller_component.get_output() == seller_output

# Display summary
print("\nSELLER COMPONENT INTEGRATION TEST")
print("=" * 55)

print("Component:", seller_output["component"])
print("Metadata:", seller_output["metadata"])

print("\nBusiness Metrics:")
print(seller_output["business_metrics"])

print("\nHistorical State Records:",
      seller_output["historical_state"]["record_count"])

print("\nScenario Count:",
      len(seller_output["scenario_results"]))

print("\nBusiness Rule Results:")
print(pd.DataFrame(rule_results).to_string(index=False))

print("\nOUTPUT KEYS:")
print(list(seller_output.keys()))

print("\nSELLER COMPONENT INTEGRATION TEST PASSED.")
