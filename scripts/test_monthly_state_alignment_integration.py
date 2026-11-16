
import pandas as pd

from config.settings import DATA_DIR

from src.components.customer_management import CustomerManagement
from src.components.product_management import ProductManagement
from src.components.seller_management import SellerManagement
from src.components.order_sales_management import OrderSalesManagement
from src.components.payment_revenue_management import PaymentRevenueManagement
from src.components.delivery_customer_experience import (
    DeliveryCustomerExperience
)
from src.simulation.monthly_state_aligner import MonthlyStateAligner


def load_datasets():
    files = {
        "customers": "olist_customers_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "items": "olist_order_items_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "translation": "product_category_name_translation.csv"
    }

    return {
        name: pd.read_csv(DATA_DIR / filename)
        for name, filename in files.items()
    }


def check_close(actual, expected, label):
    assert abs(float(actual) - float(expected)) < 0.01, (
        f"{label} mismatch: actual={actual}, expected={expected}"
    )


def existing_columns(frame, candidates):
    return [column for column in candidates if column in frame.columns]


def build_monthly_states(data):
    # 1. Customer
    customer_manager = CustomerManagement(
        data["customers"],
        data["orders"],
        data["items"]
    )
    customer_manager.build_monthly_state()
    customer_monthly = customer_manager.monthly_state

    # 2. Product and Category
    product_manager = ProductManagement(
        data["products"],
        data["items"],
        data["translation"]
    )
    product_manager.orders = data["orders"].copy(deep=True)
    product_manager.build_monthly_state()

    product_monthly = product_manager.product_monthly_state
    category_monthly = product_manager.category_monthly_state

    # 3. Seller
    seller_manager = SellerManagement(
        data["sellers"],
        data["items"],
        data["orders"]
    )
    seller_manager.build_monthly_state()
    seller_monthly = seller_manager.monthly_state

    # 4. Order and Sales
    order_manager = OrderSalesManagement(
        data["orders"],
        data["items"],
        data["customers"],
        data["products"],
        data["sellers"]
    )
    order_manager.build_order_state()
    order_monthly = order_manager.monthly_state

    # 5. Payment and Revenue
    payment_manager = PaymentRevenueManagement(
        data["orders"],
        data["payments"]
    )
    payment_manager.build_payment_state()
    payment_monthly = payment_manager.monthly_state

    # 6. Delivery and Customer Experience
    delivery_manager = DeliveryCustomerExperience(
        data["orders"],
        data["items"],
        data["reviews"],
        data["customers"],
        data["sellers"]
    )
    delivery_manager.build_all_states()
    delivery_monthly = delivery_manager.monthly_state

    monthly_states = {
        "customer": customer_monthly,
        "product": product_monthly,
        "category": category_monthly,
        "seller": seller_monthly,
        "order_sales": order_monthly,
        "payment_revenue": payment_monthly,
        "delivery_experience": delivery_monthly
    }

    return monthly_states


def build_specifications(monthly_states):
    order_state = monthly_states["order_sales"]
    payment_state = monthly_states["payment_revenue"]
    delivery_state = monthly_states["delivery_experience"]

    order_status_columns = [
        column for column in order_state.columns
        if column.startswith("status_")
    ]

    payment_method_columns = [
        column for column in payment_state.columns
        if column.startswith("method_value_")
    ]

    delivery_count_candidates = [
        "total_orders",
        "delivered_orders",
        "late_orders",
        "on_time_orders",
        "pending_orders",
        "unavailable_orders",
        "orders_with_reviews",
        "total_review_records"
    ]

    delivery_zero_columns = existing_columns(
        delivery_state,
        delivery_count_candidates
    )

    return {
        "customer": {
            "entity_keys": [],
            "zero_fill_columns": [
                "total_orders",
                "active_customers",
                "orders_with_items",
                "item_count",
                "merchandise_spend",
                "freight_spend"
            ]
        },
        "product": {
            "entity_keys": ["product_id"],
            "zero_fill_columns": []
        },
        "category": {
            "entity_keys": ["category_english"],
            "zero_fill_columns": []
        },
        "seller": {
            "entity_keys": ["seller_id"],
            "zero_fill_columns": []
        },
        "order_sales": {
            "entity_keys": [],
            "zero_fill_columns": [
                "order_count",
                "orders_with_items",
                "merchandise_value",
                "freight_value",
                *order_status_columns
            ]
        },
        "payment_revenue": {
            "entity_keys": [],
            "zero_fill_columns": [
                "total_orders",
                "orders_with_payments",
                "payment_record_count",
                "total_payment_value",
                *payment_method_columns
            ]
        },
        "delivery_experience": {
            "entity_keys": [],
            "zero_fill_columns": delivery_zero_columns
        }
    }


def main():
    print("\nLOADING OLIST DATASETS")
    data = load_datasets()
    print("All datasets loaded.")

    print("\nBUILDING MONTHLY STATES")
    monthly_states = build_monthly_states(data)

    purchase_dates = pd.to_datetime(
        data["orders"]["order_purchase_timestamp"],
        errors="raise"
    )

    timeline = pd.period_range(
        start=purchase_dates.min().to_period("M"),
        end=purchase_dates.max().to_period("M"),
        freq="M"
    )

    assert len(timeline) == 26
    assert str(timeline[0]) == "2016-09"
    assert str(timeline[-1]) == "2018-10"

    print("Source timeline:", len(timeline), "months")
    print("Range:", timeline[0], "to", timeline[-1])

    specifications = build_specifications(monthly_states)

    aligner = MonthlyStateAligner(
        timeline=timeline,
        specifications=specifications
    )

    print("\nALIGNING ALL MONTHLY STATES")
    aligned = aligner.align(monthly_states)

    assert set(aligned) == set(monthly_states)

    # --------------------------------------------------
    # 1. TIMELINE AND GRAIN VALIDATION
    # --------------------------------------------------

    print("\nALIGNED STATE AUDIT")
    print("-" * 65)

    entity_keys = {
        "customer": ["purchase_month"],
        "product": ["purchase_month", "product_id"],
        "category": ["purchase_month", "category_english"],
        "seller": ["purchase_month", "seller_id"],
        "order_sales": ["purchase_month"],
        "payment_revenue": ["purchase_month"],
        "delivery_experience": ["purchase_month"]
    }

    for name, frame in aligned.items():
        keys = entity_keys[name]

        assert not frame.duplicated(keys).any(), (
            f"{name}: duplicate aligned keys found."
        )

        if not specifications[name]["entity_keys"]:
            assert frame["purchase_month"].astype(str).tolist() == (
                timeline.astype(str).tolist()
            ), f"{name}: summary timeline is incomplete."

        print(
            f"{name}: {len(frame)} records, "
            f"{frame['purchase_month'].nunique()} represented months"
        )

    # --------------------------------------------------
    # 2. ZERO-ACTIVITY MONTH VALIDATION
    # --------------------------------------------------

    print("\nZERO-ACTIVITY MONTH VALIDATION")
    print("-" * 65)

    zero_month = "2016-11"

    for name in [
        "customer",
        "order_sales",
        "payment_revenue",
        "delivery_experience"
    ]:
        row = aligned[name].loc[
            aligned[name]["purchase_month"] == zero_month
        ]

        assert len(row) == 1, (
            f"{name}: missing zero-activity month."
        )

        for column in specifications[name]["zero_fill_columns"]:
            assert row.iloc[0][column] == 0, (
                f"{name}: {column} was not zero-filled."
            )

    # Average metrics must not be invented for a zero-activity month.
    for name, average_columns in {
        "customer": ["average_order_value"],
        "order_sales": ["average_order_value"],
        "payment_revenue": ["average_payment_per_order"],
        "delivery_experience": [
            "average_delivery_duration_days",
            "average_delivery_delay_days",
            "average_review_score"
        ]
    }.items():
        row = aligned[name].loc[
            aligned[name]["purchase_month"] == zero_month
        ]

        for column in average_columns:
            if column in row.columns:
                assert pd.isna(row.iloc[0][column]), (
                    f"{name}: {column} should remain missing "
                    "for a zero-activity month."
                )

    print("Zero-activity month checks passed.")

    # Sparse entity-level states must not receive fabricated records.
    for name in ["product", "category", "seller"]:
        assert zero_month not in set(
            aligned[name]["purchase_month"]
        ), f"{name}: fabricated entity records found."

    print("Sparse entity-state checks passed.")

    # --------------------------------------------------
    # 3. HISTORICAL RECONCILIATION
    # --------------------------------------------------

    print("\nHISTORICAL RECONCILIATION")
    print("-" * 65)

    check_close(
        aligned["customer"]["total_orders"].sum(),
        monthly_states["customer"]["total_orders"].sum(),
        "Customer orders"
    )

    check_close(
        aligned["product"]["item_line_count"].sum(),
        monthly_states["product"]["item_line_count"].sum(),
        "Product item lines"
    )

    check_close(
        aligned["product"]["units_value"].sum(),
        monthly_states["product"]["units_value"].sum(),
        "Product merchandise value"
    )

    check_close(
        aligned["category"]["item_line_count"].sum(),
        monthly_states["category"]["item_line_count"].sum(),
        "Category item lines"
    )

    check_close(
        aligned["category"]["merchandise_value"].sum(),
        monthly_states["category"]["merchandise_value"].sum(),
        "Category merchandise value"
    )

    check_close(
        aligned["seller"]["item_line_count"].sum(),
        monthly_states["seller"]["item_line_count"].sum(),
        "Seller item lines"
    )

    check_close(
        aligned["seller"]["merchandise_value"].sum(),
        monthly_states["seller"]["merchandise_value"].sum(),
        "Seller merchandise value"
    )

    check_close(
        aligned["order_sales"]["order_count"].sum(),
        monthly_states["order_sales"]["order_count"].sum(),
        "Order count"
    )

    check_close(
        aligned["order_sales"]["merchandise_value"].sum(),
        monthly_states["order_sales"]["merchandise_value"].sum(),
        "Order merchandise value"
    )

    check_close(
        aligned["payment_revenue"]["total_payment_value"].sum(),
        monthly_states["payment_revenue"]["total_payment_value"].sum(),
        "Payment value"
    )

    check_close(
        aligned["delivery_experience"]["total_orders"].sum(),
        monthly_states["delivery_experience"]["total_orders"].sum(),
        "Delivery monthly order count"
    )

    print("All seven state reconciliations passed.")

    print("\nALL MONTHLY STATE ALIGNMENT INTEGRATION TESTS PASSED.")


if __name__ == "__main__":
    main()
