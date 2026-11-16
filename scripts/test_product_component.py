
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config.settings import DATA_DIR
from src.components.product_component import ProductComponent


# Load datasets
products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
category_translation = pd.read_csv(
    DATA_DIR / "product_category_name_translation.csv"
)

# Preserve original datasets
products_original = products.copy(deep=True)
items_original = order_items.copy(deep=True)
translation_original = category_translation.copy(deep=True)


# Initialize component
component = ProductComponent(
    products_df=products,
    order_items_df=order_items,
    category_translation_df=category_translation
)


# TEST 1: Component execution
output = component.run()

assert output["status"] == "SUCCESS"
assert output["component"] == "product_management"

print("TEST 1 PASSED: Product component execution.")


# TEST 2: Standard output schema
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

print("TEST 2 PASSED: Standard BaseComponent output schema.")


# TEST 3: Historical state integrity
historical_state = output["historical_state"]

assert historical_state["product_record_count"] == len(products)
assert historical_state["category_record_count"] > 0

assert len(historical_state["products"]) == len(products)
assert len(historical_state["categories"]) > 0

print("TEST 3 PASSED: Historical product and category state.")


# TEST 4: Business metrics
metrics = output["business_metrics"]

assert metrics["total_catalogue_products"] == len(products)
assert metrics["total_item_lines"] == len(order_items)

assert abs(
    metrics["total_merchandise_value"]
    - order_items["price"].sum()
) < 0.01

assert abs(
    metrics["total_freight_value"]
    - order_items["freight_value"].sum()
) < 0.01

print("TEST 4 PASSED: Product business metrics.")


# TEST 5: Metadata integrity
metadata = output["metadata"]

assert metadata["currency"] == "BRL"
assert metadata["data_type"] == "historical_product_analysis"
assert metadata["product_count"] == len(products)
assert metadata["order_item_count"] == len(order_items)
assert "generated_at" in metadata

print("TEST 5 PASSED: Component metadata.")


# TEST 6: Scenario and business rule placeholders
assert output["scenario_results"] == []
rules = output["business_rule_results"]

assert len(rules) == 8
assert all(rule["passed"] for rule in rules)
assert output["status"] == "SUCCESS"

print("TEST 6 PASSED: Scenario and rule output structure.")


# TEST 7: Output isolation
output["business_metrics"]["total_catalogue_products"] = -1

fresh_output = component.get_output()

assert (
    fresh_output["business_metrics"]["total_catalogue_products"]
    == len(products)
)

print("TEST 7 PASSED: Output isolation.")


# TEST 8: Original datasets unchanged
pd.testing.assert_frame_equal(products, products_original)
pd.testing.assert_frame_equal(order_items, items_original)
pd.testing.assert_frame_equal(
    category_translation,
    translation_original
)

print("TEST 8 PASSED: Original datasets unchanged.")


# TEST 9: Component input datasets unchanged
pd.testing.assert_frame_equal(component.products_df, products_original)
pd.testing.assert_frame_equal(component.order_items_df, items_original)

pd.testing.assert_frame_equal(
    component.category_translation_df,
    translation_original
)

print("TEST 9 PASSED: Component input datasets unchanged.")


print("\nPRODUCT COMPONENT SUMMARY")
print("=" * 50)

for key, value in fresh_output["business_metrics"].items():
    print(f"{key}: {value}")

print("\nProduct Records:",
      fresh_output["historical_state"]["product_record_count"])

print("Category Records:",
      fresh_output["historical_state"]["category_record_count"])

print("\n" + "=" * 50)
print("ALL PRODUCT COMPONENT TESTS PASSED.")
print("=" * 50)
