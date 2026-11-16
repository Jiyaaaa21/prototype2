import pandas as pd

from config.settings import DATA_DIR

from src.components.seller_component import SellerComponent
from src.components.customer_component import CustomerComponent
from src.components.product_component import ProductComponent
from src.components.order_sales_component import OrderSalesComponent
from src.components.payment_component import PaymentComponent
from src.components.delivery_component import DeliveryComponent

from src.relationships import DependencyManager
from src.simulation import (
    SimulationEngine,
    StateManager,
    TimeManager
)


def load_dataset(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    return pd.read_csv(path)


def main():

    print("\nLOADING OLIST DATASETS...")

    customers = load_dataset("olist_customers_dataset.csv")
    orders = load_dataset("olist_orders_dataset.csv")
    order_items = load_dataset("olist_order_items_dataset.csv")
    products = load_dataset("olist_products_dataset.csv")
    sellers = load_dataset("olist_sellers_dataset.csv")
    payments = load_dataset("olist_order_payments_dataset.csv")
    reviews = load_dataset("olist_order_reviews_dataset.csv")
    category_translation = load_dataset(
        "product_category_name_translation.csv"
    )

    print("All eight datasets loaded successfully.")

    print("\nINITIALIZING SIX COMPONENTS...")

    components = {
        "seller_management": SellerComponent(
            sellers,
            order_items,
            orders
        ),

        "customer_management": CustomerComponent(
            customers,
            orders,
            order_items
        ),

        "product_management": ProductComponent(
            products,
            order_items,
            category_translation
        ),

        "order_sales_management": OrderSalesComponent(
            orders,
            order_items,
            customers,
            products,
            sellers
        ),

        "payment_revenue_management": PaymentComponent(
            orders,
            payments
        ),

        "delivery_customer_experience": DeliveryComponent(
            orders,
            order_items,
            reviews,
            customers,
            sellers
        )
    }

    print("Six components initialized.")

    dependency_manager = DependencyManager()
    time_manager = TimeManager(orders)
    state_manager = StateManager()

    engine = SimulationEngine(
        components=components,
        dependency_manager=dependency_manager,
        time_manager=time_manager,
        state_manager=state_manager
    )

    print("\nRUNNING REAL HISTORICAL EXECUTION...")

    report = engine.run_historical_execution()

    print("\nEXECUTION REPORT")
    print("----------------")

    print("Status:", report["status"])
    print("Execution order:", report["execution_order"])
    print("Summary:", report["summary"])

    for component, result in report["execution_results"].items():
        print(f"{component}: {result['status']}")

    print(
        "Historical state registered:",
        report["historical_state_registered"]
    )

    print(
        "Initial simulation period:",
        report["initial_simulation_period"]
    )

    if report["orchestration_error"]:
        print(
            "Orchestration error:",
            report["orchestration_error"]
        )

    assert report["status"] == "SUCCESS"
    assert report["summary"]["successful"] == 6
    assert report["summary"]["failed"] == 0
    assert report["summary"]["skipped"] == 0
    assert report["historical_state_registered"] is True

    historical_states = state_manager.get_historical_state()

    assert len(historical_states) == 6

    simulation_state = state_manager.get_simulation_state()

    assert simulation_state["period"] == time_manager.get_current_period()

    print("\nREAL COMPONENT INTEGRATION TEST PASSED.")


if __name__ == "__main__":
    main()