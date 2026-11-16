
from copy import deepcopy
import pandas as pd

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
from src.simulation import SimulationEngine, StateManager, TimeManager
from src.simulation.monthly_state_aligner import MonthlyStateAligner
from src.simulation.monthly_state_payload_builder import (
    MonthlyStatePayloadBuilder
)


def main():

    print("\nLOADING DATASETS...")
    data = load_datasets()

    orders = data["orders"]
    customers = data["customers"]
    order_items = data["items"]
    products = data["products"]
    sellers = data["sellers"]
    payments = data["payments"]
    reviews = data["reviews"]
    translation = data["translation"]

    print("\nBUILDING MONTHLY PAYLOADS...")
    monthly_states = build_monthly_states(data)

    purchase_dates = pd.to_datetime(
        orders["order_purchase_timestamp"],
        errors="raise"
    )

    timeline = pd.period_range(
        start=purchase_dates.min().to_period("M"),
        end=purchase_dates.max().to_period("M"),
        freq="M"
    )

    specifications = build_specifications(monthly_states)

    aligner = MonthlyStateAligner(
        timeline=timeline,
        specifications=specifications
    )

    aligned_states = aligner.align(monthly_states)

    payload_builder = MonthlyStatePayloadBuilder(aligned_states)

    print("\nINITIALIZING COMPONENTS...")

    components = {
        "seller_management": SellerComponent(
            sellers, order_items, orders
        ),
        "customer_management": CustomerComponent(
            customers, orders, order_items
        ),
        "product_management": ProductComponent(
            products, order_items, translation
        ),
        "order_sales_management": OrderSalesComponent(
            orders, order_items, customers, products, sellers
        ),
        "payment_revenue_management": PaymentComponent(
            orders, payments
        ),
        "delivery_customer_experience": DeliveryComponent(
            orders, order_items, reviews, customers, sellers
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

    print("\nRUNNING HISTORICAL EXECUTION...")

    historical_report = engine.run_historical_execution()

    assert historical_report["status"] == "SUCCESS"

    historical_baseline = deepcopy(
        state_manager.get_historical_state()
    )

    initial_simulation_state = deepcopy(
        state_manager.get_simulation_state()
    )

    initial_period = time_manager.get_current_period()

    print("Historical execution passed.")

    # Inject a controlled failure during March 2017.
    original_update = state_manager.update_all_component_states

    def failing_update(component_states):

        current_period = time_manager.get_current_period()

        if current_period == "2017-03":
            raise RuntimeError(
                "INJECTED FAILURE: March 2017 update."
            )

        return original_update(component_states)

    state_manager.update_all_component_states = failing_update

    print("\nRUNNING MONTHLY REPLAY WITH INJECTED FAILURE...")

    try:
        engine.run_monthly_replay(payload_builder)

    except RuntimeError as error:
        print("Expected replay failure:", error)

    else:
        raise AssertionError(
            "Replay should have failed at March 2017."
        )

    # 1. Validate failure report.
    report = engine.get_monthly_replay_report()

    assert report["status"] == "FAILED"
    assert report["snapshots_validated"] is False
    assert "INJECTED FAILURE" in report["error"]

    print("Failure report validation: PASSED")

    # 2. Validate only the initial snapshot remains.
    stored_periods = state_manager.get_available_periods()

    assert stored_periods == (initial_period,)

    restored_state = state_manager.get_simulation_state()

    assert restored_state == initial_simulation_state

    print("Simulation snapshot rollback: PASSED")

    # 3. Validate TimeManager rollback.
    assert time_manager.get_current_period() == initial_period
    assert not time_manager.is_complete()

    print("TimeManager rollback: PASSED")

    # 4. Validate historical state isolation.
    assert state_manager.get_historical_state() == historical_baseline

    print("Historical state isolation: PASSED")

    print("\nALL FAILURE RECOVERY TESTS PASSED.")


if __name__ == "__main__":
    main()
