
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


def main():
    data = load_datasets()

    print("\nBUILDING SIX MONTHLY STATES")
    print("-" * 65)

    # 1. Customer Management
    customer_manager = CustomerManagement(
        data["customers"], data["orders"], data["items"]
    )
    customer_manager.build_monthly_state()
    customer_monthly = customer_manager.monthly_state

    # 2. Product Management
    product_manager = ProductManagement(
        data["products"], data["items"], data["translation"]
    )
    # Orders provide the purchase timestamp needed for monthly grouping.
    product_manager.orders = data["orders"].copy(deep=True)
    product_manager.build_monthly_state()

    product_monthly = product_manager.product_monthly_state
    category_monthly = product_manager.category_monthly_state

    # 3. Seller Management
    seller_manager = SellerManagement(
        data["sellers"], data["items"], data["orders"]
    )
    seller_manager.build_monthly_state()
    seller_monthly = seller_manager.monthly_state

    # 4. Order & Sales Management
    order_manager = OrderSalesManagement(
        data["orders"],
        data["items"],
        data["customers"],
        data["products"],
        data["sellers"]
    )
    order_manager.build_order_state()
    order_monthly = order_manager.monthly_state

    # 5. Payment & Revenue Management
    payment_manager = PaymentRevenueManagement(
        data["orders"], data["payments"]
    )
    payment_manager.build_payment_state()
    payment_monthly = payment_manager.monthly_state

    # 6. Delivery & Customer Experience
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
        "Customer": customer_monthly,
        "Product": product_monthly,
        "Category": category_monthly,
        "Seller": seller_monthly,
        "Order & Sales": order_monthly,
        "Payment & Revenue": payment_monthly,
        "Delivery & Experience": delivery_monthly
    }

    # Build the continuous calendar from the source order timestamps.
    purchase_dates = pd.to_datetime(
        data["orders"]["order_purchase_timestamp"], errors="raise"
    )

    timeline = pd.period_range(
        start=purchase_dates.min().to_period("M"),
        end=purchase_dates.max().to_period("M"),
        freq="M"
    )

    print("\nMONTHLY PERIOD AUDIT")
    print("-" * 65)
    print("Simulation timeline periods:", len(timeline))
    print("Timeline:", timeline[0], "to", timeline[-1])

    for name, frame in monthly_states.items():
        assert "purchase_month" in frame.columns, (
            f"{name}: purchase_month column missing."
        )

        active_months = set(frame["purchase_month"].astype(str))
        missing_months = [
            str(period) for period in timeline
            if str(period) not in active_months
        ]

        unique_keys = {   
             
            "Customer": ["purchase_month"],
            "Product": ["purchase_month", "product_id"],
            "Category": ["purchase_month", "category_english"],
            "Seller": ["purchase_month", "seller_id"],
            "Order & Sales": ["purchase_month"],
            "Payment & Revenue": ["purchase_month"],
            "Delivery & Experience": ["purchase_month"]
        }


        assert not frame.duplicated(unique_keys[name]).any(), (
            f"{name}: duplicate records found for {unique_keys[name]}."
        )

        print(f"\n{name}")
        print("  Records:", len(frame))
        print("  Active months:", len(active_months))
        print("  Missing months:", missing_months)

    # Reconciliation checks.
    print("\nHISTORICAL RECONCILIATION")
    print("-" * 65)

    check_close(
        customer_monthly["total_orders"].sum(),
        len(data["orders"]),
        "Customer monthly order count"
    )

    check_close(
        product_monthly["item_line_count"].sum(),
        len(data["items"]),
        "Product monthly item lines"
    )

    check_close(
        category_monthly["item_line_count"].sum(),
        len(data["items"]),
        "Category monthly item lines"
    )

    expected_merchandise = data["items"]["price"].sum()
    expected_freight = data["items"]["freight_value"].sum()

    check_close(
        product_monthly["units_value"].sum(),
        expected_merchandise,
        "Product monthly merchandise value"
    )

    check_close(
        category_monthly["merchandise_value"].sum(),
        expected_merchandise,
        "Category monthly merchandise value"
    )

    check_close(
        seller_monthly["item_line_count"].sum(),
        len(data["items"]),
        "Seller monthly item lines"
    )

    check_close(
        seller_monthly["merchandise_value"].sum(),
        expected_merchandise,
        "Seller monthly merchandise value"
    )

    check_close(
        order_monthly["order_count"].sum(),
        len(data["orders"]),
        "Order monthly order count"
    )

    check_close(
        order_monthly["merchandise_value"].sum(),
        expected_merchandise,
        "Order monthly merchandise value"
    )

    check_close(
        payment_monthly["total_payment_value"].sum(),
        data["payments"]["payment_value"].sum(),
        "Payment monthly value"
    )

    check_close(
        delivery_monthly["total_orders"].sum(),
        len(data["orders"]),
        "Delivery monthly order count"
    )

    print("Customer monthly order count: PASSED")
    print("Product and category totals: PASSED")
    print("Seller monthly totals: PASSED")
    print("Order & Sales monthly totals: PASSED")
    print("Payment monthly total: PASSED")
    print("Delivery monthly order count: PASSED")

    print("\nALL SIX MONTHLY STATES AUDITED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
