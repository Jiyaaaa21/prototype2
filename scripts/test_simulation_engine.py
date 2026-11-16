import pandas as pd

from src.relationships import DependencyManager
from src.simulation import (
    SimulationEngine,
    StateManager,
    TimeManager
)


COMPONENTS = {
    "customer_management",
    "product_management",
    "seller_management",
    "order_sales_management",
    "payment_revenue_management",
    "delivery_customer_experience"
}


class MockComponent:

    def __init__(self, component_name, should_fail=False):

        self.component_name = component_name
        self.should_fail = should_fail
        self.execution_count = 0

    def run(self):

        self.execution_count += 1

        if self.should_fail:
            raise RuntimeError(
                f"{self.component_name} simulated failure."
            )

        return {
            "component": self.component_name,
            "metadata": {"currency": "BRL"},
            "historical_state": {
                "records": [{"value": 100}]
            },
            "business_metrics": {"total_value": 100},
            "scenario_results": [],
            "business_rule_results": [],
            "status": "SUCCESS"
        }


def create_engine(failing_component=None, add_dependency=False):

    components = {
        name: MockComponent(
            name,
            should_fail=(name == failing_component)
        )
        for name in COMPONENTS
    }

    dependency_manager = DependencyManager()

    if add_dependency:
        dependency_manager.add_dependency(
            "customer_management",
            "order_sales_management"
        )

    orders_df = pd.DataFrame({
        "order_purchase_timestamp": [
            "2017-01-10",
            "2017-02-15"
        ]
    })

    time_manager = TimeManager(orders_df)
    state_manager = StateManager()

    engine = SimulationEngine(
        components=components,
        dependency_manager=dependency_manager,
        time_manager=time_manager,
        state_manager=state_manager
    )

    return engine, components, state_manager


def test_successful_historical_execution():

    engine, components, state_manager = create_engine()

    report = engine.run_historical_execution()

    assert report["status"] == "SUCCESS"
    assert report["summary"]["successful"] == 6
    assert report["summary"]["failed"] == 0
    assert report["summary"]["skipped"] == 0

    assert report["historical_state_registered"] is True
    assert report["initial_simulation_period"] == "2017-01"

    assert len(state_manager.get_historical_state()) == 6

    assert all(
        component.execution_count == 1
        for component in components.values()
    )

    print("Successful historical execution test passed.")


def test_independent_components_continue_after_failure():

    engine, components, state_manager = create_engine(
        failing_component="customer_management"
    )

    report = engine.run_historical_execution()

    assert report["status"] == "FAILED"

    assert report["execution_results"][
        "customer_management"
    ]["status"] == "FAILED"

    assert report["summary"]["failed"] == 1
    assert report["summary"]["successful"] == 5

    assert all(
        component.execution_count == 1
        for component in components.values()
    )

    assert report["historical_state_registered"] is False

    assert state_manager.get_available_periods() == ()

    print("Independent execution after failure test passed.")


def test_dependent_component_is_skipped():

    engine, components, state_manager = create_engine(
        failing_component="customer_management",
        add_dependency=True
    )

    report = engine.run_historical_execution()

    assert report["execution_results"][
        "customer_management"
    ]["status"] == "FAILED"

    assert report["execution_results"][
        "order_sales_management"
    ]["status"] == "SKIPPED"

    assert report["summary"]["failed"] == 1
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["successful"] == 4

    assert components["order_sales_management"].execution_count == 0

    assert report["historical_state_registered"] is False

    print("Dependency failure handling test passed.")


def test_execution_report_is_defensive():

    engine, _, _ = create_engine()

    engine.run_historical_execution()

    report = engine.get_execution_report()

    report["status"] = "MODIFIED"

    actual_report = engine.get_execution_report()

    assert actual_report["status"] == "SUCCESS"

    print("Execution report isolation test passed.")


def test_duplicate_execution_is_rejected():

    engine, _, _ = create_engine()

    engine.run_historical_execution()

    try:
        engine.run_historical_execution()
    except RuntimeError:
        pass
    else:
        raise AssertionError(
            "Duplicate historical execution was accepted."
        )

    print("Duplicate execution prevention test passed.")


if __name__ == "__main__":

    test_successful_historical_execution()
    test_independent_components_continue_after_failure()
    test_dependent_component_is_skipped()
    test_execution_report_is_defensive()
    test_duplicate_execution_is_rejected()

    print("\nALL SIMULATION ENGINE TESTS PASSED.")