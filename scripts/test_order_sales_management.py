
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config.settings import DATA_DIR
from src.components.order_sales_management import OrderSalesManagement


# ============================================================
# LOAD DATASETS
# ============================================================

orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")


# Preserve original datasets
originals = [
    orders.copy(deep=True),
    order_items.copy(deep=True),
    customers.copy(deep=True),
    products.copy(deep=True),
    sellers.copy(deep=True)
]


# ============================================================
# INITIALIZE COMPONENT
# ============================================================

component = OrderSalesManagement(
    orders_df=orders,
    order_items_df=order_items,
    customers_df=customers,
    products_df=products,
    sellers_df=sellers
)


# ============================================================
# TEST 1: DATA VALIDATION
# ============================================================

assert component.validate_data() is True

print("TEST 1 PASSED: Order and sales data validation.")


# ============================================================
# TEST 2: HISTORICAL STATE CONSTRUCTION
# ============================================================

result = component.build_order_state()

order_state = result["order_state"]
monthly_state = result["monthly_state"]
contributions = result["contribution_state"]

assert not order_state.empty
assert not monthly_state.empty
assert order_state["order_id"].is_unique

print("TEST 2 PASSED: Historical state construction.")


# ============================================================
# TEST 3: ORDER-LEVEL AGGREGATION
# ============================================================

assert len(order_state) == len(orders)

assert order_state["item_count"].sum() == len(order_items)

assert abs(
    order_state["merchandise_value"].sum()
    - order_items["price"].sum()
) < 0.01

assert abs(
    order_state["freight_value"].sum()
    - order_items["freight_value"].sum()
) < 0.01

print("TEST 3 PASSED: Order-level aggregation.")


# ============================================================
# TEST 4: MONTHLY AGGREGATION
# ============================================================

assert monthly_state["purchase_month"].is_unique

assert monthly_state["order_count"].sum() == len(orders)

assert abs(
    monthly_state["merchandise_value"].sum()
    - order_items["price"].sum()
) < 0.01

assert abs(
    monthly_state["freight_value"].sum()
    - order_items["freight_value"].sum()
) < 0.01

print("TEST 4 PASSED: Monthly historical aggregation.")


# TEST 5: Monthly order status integrity

status_columns = [
    column for column in monthly_state.columns
    if column.startswith("status_")
]

monthly_status_total = monthly_state[status_columns].sum(axis=1)

assert (
    monthly_status_total.to_numpy()
    == monthly_state["order_count"].to_numpy()
).all()

print("TEST 5 PASSED: Monthly order status distribution.")


# ============================================================
# TEST 6: CONTRIBUTION-LEVEL AGGREGATION
# ============================================================

product_contribution = contributions["products"]
seller_contribution = contributions["sellers"]
customer_contribution = contributions["customers"]

assert product_contribution["product_id"].is_unique
assert seller_contribution["seller_id"].is_unique
assert customer_contribution["customer_unique_id"].is_unique

for contribution in contributions.values():

    assert contribution["item_lines"].sum() == len(order_items)

    assert abs(
        contribution["merchandise_value"].sum()
        - order_items["price"].sum()
    ) < 0.01

print(
    "TEST 6 PASSED: Product, seller and customer contributions."
)


# ============================================================
# TEST 7: BUSINESS SUMMARY
# ============================================================

summary = component.get_summary()

assert summary["total_orders"] == len(orders)

assert summary["total_order_items"] == len(order_items)

assert abs(
    summary["total_merchandise_value"]
    - order_items["price"].sum()
) < 0.01

assert abs(
    summary["total_freight_value"]
    - order_items["freight_value"].sum()
) < 0.01

assert summary["monthly_periods"] == len(monthly_state)

print("TEST 7 PASSED: Order and sales business metrics.")


# ============================================================
# TEST 8: DELIVERED AND CANCELLED ORDER COUNTS
# ============================================================

expected_delivered = (
    orders["order_status"] == "delivered"
).sum()

expected_cancelled = (
    orders["order_status"] == "canceled"
).sum()

assert summary["delivered_orders"] == expected_delivered
assert summary["cancelled_orders"] == expected_cancelled

print("TEST 8 PASSED: Delivered and cancelled order counts.")


# ============================================================
# TEST 9: ORIGINAL DATASETS UNCHANGED
# ============================================================

for current, original in zip(
    [orders, order_items, customers, products, sellers],
    originals
):
    pd.testing.assert_frame_equal(current, original)

print("TEST 9 PASSED: Original datasets unchanged.")


# ============================================================
# TEST 10: COMPONENT INPUT ISOLATION
# ============================================================

for current, original in zip(
    [
        component.orders,
        component.order_items,
        component.customers,
        component.products,
        component.sellers
    ],
    originals
):
    pd.testing.assert_frame_equal(current, original)

print("TEST 10 PASSED: Component input datasets unchanged.")


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\nORDER & SALES MANAGEMENT SUMMARY")
print("=" * 55)

for metric, value in summary.items():
    print(f"{metric}: {value}")

print("\nMonthly Records:", len(monthly_state))

print("\nTop 5 Months by Merchandise Value:")

print(
    monthly_state
    .sort_values("merchandise_value", ascending=False)
    [["purchase_month", "order_count", "merchandise_value"]]
    .head(5)
    .to_string(index=False)
)

print("\n" + "=" * 55)
print("ALL ORDER & SALES MANAGEMENT TESTS PASSED.")
print("=" * 55)
