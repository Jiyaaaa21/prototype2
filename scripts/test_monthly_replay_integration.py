
from copy import deepcopy

from scripts.test_monthly_state_alignment_integration import (
    load_datasets,
    build_monthly_states,
    build_specifications
)

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

from src.simulation.monthly_state_aligner import (
    MonthlyStateAligner
)

from src.simulation.monthly_state_payload_builder import (
    MonthlyStatePayloadBuilder
)


def main():

    print("\nLOADING OLIST DATASETS...")
    data = load_datasets()
    print("All datasets loaded.")

    orders = data["orders"]
    customers = data["customers"]
    order_items = data["items"]
    products = data["products"]
    sellers = data["sellers"]
    payments = data["payments"]
    reviews = data["reviews"]
    category_translation = data["translation"]

    print("\nBUILDING MONTHLY STATES...")
    monthly_states = build_monthly_states(data)

    purchase_dates = orders["order_purchase_timestamp"]
    purchase_dates = __import__("pandas").to_datetime(
        purchase_dates,
        errors="raise"
    )

    timeline = __import__("pandas").period_range(
        start=purchase_dates.min().to_period("M"),
        end=purchase_dates.max().to_period("M"),
        freq="M"
    )

    assert len(timeline) == 26

    specifications = build_specifications(monthly_states)

    aligner = MonthlyStateAligner(
        timeline=timeline,
        specifications=specifications
    )

    aligned_states = aligner.align(monthly_states)

    payload_builder = MonthlyStatePayloadBuilder(
        aligned_states
    )

    assert len(payload_builder.get_timeline()) == 26

    print("Monthly states aligned.")
    print("Payload builder initialized.")

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

    dependency_manager = DependencyManager()
    time_manager = TimeManager(orders)
    state_manager = StateManager()

    engine = SimulationEngine(
        components=components,
        dependency_manager=dependency_manager,
        time_manager=time_manager,
        state_manager=state_manager
    )

    print("Six components initialized.")

    print("\nRUNNING HISTORICAL EXECUTION...")

    historical_report = engine.run_historical_execution()

    assert historical_report["status"] == "SUCCESS"
    assert historical_report["summary"]["successful"] == 6

    historical_baseline = deepcopy(
        state_manager.get_historical_state()
    )

    print("Historical execution passed.")

    print("\nRUNNING MONTHLY REPLAY...")

    replay_report = engine.run_monthly_replay(
        payload_builder
    )

    print("\nMONTHLY REPLAY REPORT")
    print("-" * 60)

    print("Status:", replay_report["status"])
    print("Total months:", replay_report["total_months"])
    print("Processed months:", replay_report["processed_months"])
    print("Start:", replay_report["start_period"])
    print("End:", replay_report["end_period"])

    assert replay_report["status"] == "SUCCESS"
    assert replay_report["total_months"] == 26
    assert replay_report["processed_months"] == 26
    assert replay_report["start_period"] == "2016-09"
    assert replay_report["end_period"] == "2018-10"

    print("\nVALIDATING MONTHLY SNAPSHOTS...")

    expected_components = SimulationEngine.COMPONENTS
    stored_periods = state_manager.get_available_periods()

    assert stored_periods == tuple(
        payload_builder.get_timeline()
    )

    for month in stored_periods:

        snapshot = state_manager.get_simulation_state(month)

        assert snapshot["period"] == month

        component_states = snapshot["components"]

        assert set(component_states) == expected_components

        for component_name, component_state in component_states.items():
            assert component_state["purchase_month"] == month

        print(f"{month}: six component states validated.")

    print("\nZERO-ACTIVITY MONTH VALIDATION...")

    november = state_manager.get_simulation_state("2016-11")
    november_states = november["components"]

    assert november_states["customer_management"]["summary"][
        "total_orders"
    ] == 0

    assert november_states["product_management"]["products"] == []
    assert november_states["product_management"]["categories"] == []
    assert november_states["seller_management"]["sellers"] == []

    assert november_states["order_sales_management"]["summary"][
        "order_count"
    ] == 0

    print("November 2016 zero-activity checks passed.")

    print("\nOCTOBER 2018 SPARSE STATE VALIDATION...")

    october = state_manager.get_simulation_state("2018-10")
    october_states = october["components"]

    assert october_states["product_management"]["products"] == []
    assert october_states["product_management"]["categories"] == []
    assert october_states["seller_management"]["sellers"] == []

    print("October 2018 sparse-state checks passed.")

    print("\nHISTORICAL STATE ISOLATION...")

    assert state_manager.get_historical_state() == historical_baseline

    print("Historical component outputs remain unchanged.")

    assert time_manager.get_current_period() == "2018-10"
    assert time_manager.is_complete()

    print("\nALL MONTHLY REPLAY INTEGRATION TESTS PASSED.")


if __name__ == "__main__":
    main()
