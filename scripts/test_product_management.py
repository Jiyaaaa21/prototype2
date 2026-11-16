import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd

from config.settings import DATA_DIR
from src.components.product_management import ProductManagement


# Load source datasets
products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
category_translation = pd.read_csv(
    DATA_DIR / "product_category_name_translation.csv"
)

# Preserve original snapshots
products_original = products.copy(deep=True)
items_original = order_items.copy(deep=True)
translation_original = category_translation.copy(deep=True)

# Initialize component
component = ProductManagement(
    products_df=products,
    order_items_df=order_items,
    category_translation_df=category_translation
)


# TEST 1: Data validation
assert component.validate_data() is True
print("TEST 1 PASSED: Product data validation.")


# TEST 2: Product and category state construction
result = component.build_product_state()

product_state = result["product_state"]
category_state = result["category_state"]

assert not product_state.empty
assert not category_state.empty
assert product_state["product_id"].is_unique
assert category_state["category_english"].is_unique

print("TEST 2 PASSED: Product and category state construction.")


# TEST 3: Product identity and sales aggregation
assert product_state["product_id"].notna().all()

assert (
    product_state["item_line_count"].sum()
    == len(order_items)
)

assert (
    product_state["distinct_orders"].sum()
    <= len(order_items)
)

assert (product_state["item_line_count"] >= 0).all()

print("TEST 3 PASSED: Product identity and sales aggregation.")


# TEST 4: Category aggregation integrity
assert (
    category_state["item_line_count"].sum()
    == len(order_items)
)

assert (
    category_state["distinct_products"].sum()
    == product_state["product_id"].nunique()
)

assert category_state["distinct_orders"].between(
    0, order_items["order_id"].nunique()
).all()

print("TEST 4 PASSED: Category aggregation integrity.")


# TEST 5: Financial calculations
assert (product_state["units_value"] >= 0).all()
assert (product_state["freight_value"] >= 0).all()

assert abs(
    product_state["units_value"].sum()
    - order_items["price"].sum()
) < 0.01

assert abs(
    product_state["freight_value"].sum()
    - order_items["freight_value"].sum()
) < 0.01

print("TEST 5 PASSED: Merchandise and freight calculations.")


# TEST 6: Merchandise contribution
assert product_state["merchandise_share"].between(0, 1).all()
assert category_state["merchandise_share"].between(0, 1).all()

assert abs(
    product_state["merchandise_share"].sum() - 1
) < 1e-9

assert abs(
    category_state["merchandise_share"].sum() - 1
) < 1e-9

print("TEST 6 PASSED: Merchandise contribution calculations.")


# TEST 7: Business summary
summary = component.get_summary()

required_metrics = {
    "total_catalogue_products",
    "distinct_product_categories",
    "total_item_lines",
    "total_distinct_orders",
    "total_merchandise_value",
    "total_freight_value",
    "products_with_sales"
}

assert required_metrics.issubset(summary.keys())

assert summary["total_catalogue_products"] == len(products)
assert summary["total_item_lines"] == len(order_items)
assert summary["products_with_sales"] <= summary["total_catalogue_products"]

print("TEST 7 PASSED: Product business metrics.")


# TEST 8: Original datasets remain unchanged
pd.testing.assert_frame_equal(products, products_original)
pd.testing.assert_frame_equal(order_items, items_original)
pd.testing.assert_frame_equal(category_translation, translation_original)

print("TEST 8 PASSED: Original historical datasets unchanged.")


# TEST 9: Component input datasets remain unchanged
pd.testing.assert_frame_equal(component.products, products_original)
pd.testing.assert_frame_equal(component.order_items, items_original)
pd.testing.assert_frame_equal(
    component.category_translation,
    translation_original
)

print("TEST 9 PASSED: Component input datasets unchanged.")


# Display results
print("\nPRODUCT MANAGEMENT SUMMARY")
print("=" * 50)

for metric, value in summary.items():
    print(f"{metric}: {value}")

print("\nProduct State Records:", len(product_state))
print("Category State Records:", len(category_state))

print("\nTop 5 Categories by Merchandise Value:")
print(
    category_state
    .sort_values("merchandise_value", ascending=False)
    [["category_english", "distinct_products",
      "distinct_orders", "merchandise_value"]]
    .head(5)
    .to_string(index=False)
)

print("\n" + "=" * 50)
print("ALL PRODUCT MANAGEMENT TESTS PASSED.")
print("=" * 50)


