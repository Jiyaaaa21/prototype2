
from config.settings import DATA_DIR

from src.components.order_sales_management import OrderSalesManagement
from src.components.payment_revenue_management import PaymentRevenueManagement
from src.components.delivery_customer_experience import DeliveryCustomerExperience

import pandas as pd


def load_data():
    files = {
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
    }

    return {
        name: pd.read_csv(DATA_DIR / filename)
        for name, filename in files.items()
    }


def inspect(name, dataframe):
    print(f"\n{name}")
    print("=" * 70)
    print("Shape:", dataframe.shape)
    print("Columns:", dataframe.columns.tolist())
    print("\nFirst 3 records:")
    print(dataframe.head(3).to_string(index=False))
    print("\nData types:")
    print(dataframe.dtypes.to_string())


def main():
    print("LOADING DATASETS...")
    data = load_data()

    print("\nBUILDING ORDER & SALES STATES...")
    order_manager = OrderSalesManagement(
        data["orders"],
        data["order_items"],
        data["customers"],
        data["products"],
        data["sellers"],
    )
    order_manager.build_order_state()

    print("BUILDING PAYMENT & REVENUE STATES...")
    payment_manager = PaymentRevenueManagement(
        data["orders"],
        data["payments"],
    )
    payment_manager.build_payment_state()

    print("BUILDING DELIVERY & CUSTOMER EXPERIENCE STATES...")
    delivery_manager = DeliveryCustomerExperience(
        data["orders"],
        data["order_items"],
        data["reviews"],
        data["customers"],
        data["sellers"],
    )
    delivery_manager.build_all_states()

    inspect("ORDER MONTHLY STATE", order_manager.monthly_state)
    inspect("PAYMENT MONTHLY STATE", payment_manager.monthly_state)
    inspect("DELIVERY MONTHLY STATE", delivery_manager.monthly_state)

    print("\nMONTHLY STATE SUMMARY")
    print("=" * 70)

    states = {
        "Order & Sales": order_manager.monthly_state,
        "Payment & Revenue": payment_manager.monthly_state,
        "Delivery & Customer Experience": delivery_manager.monthly_state,
    }

    for name, dataframe in states.items():
        print(f"{name}: {len(dataframe)} monthly records")


if __name__ == "__main__":
    main()
