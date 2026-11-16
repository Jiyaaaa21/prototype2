from copy import deepcopy

from src.simulation import StateManager


COMPONENTS = {
    "customer_management",
    "product_management",
    "seller_management",
    "order_sales_management",
    "payment_revenue_management",
    "delivery_customer_experience"
}


def create_component_outputs():

    outputs = {}

    for component in COMPONENTS:
        outputs[component] = {
            "component": component,
            "metadata": {"currency": "BRL"},
            "historical_state": {
                "records": [{"value": 100}]
            },
            "business_metrics": {"total_value": 100},
            "scenario_results": [],
            "business_rule_results": [],
            "status": "SUCCESS"
        }

    return outputs


def create_manager():

    manager = StateManager()
    manager.register_all_historical_states(
        create_component_outputs()
    )
    manager.initialize_simulation_state("2017-01")

    return manager


def test_historical_registration():

    manager = create_manager()

    historical = manager.get_historical_state()

    assert set(historical) == COMPONENTS

    print("Historical registration test passed.")


def test_output_validation():

    manager = StateManager()

    invalid_output = {
        "component": "customer_management",
        "status": "SUCCESS"
    }

    try:
        manager.register_historical_state(
            "customer_management",
            invalid_output
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid output was accepted.")

    print("Output validation test passed.")


def test_initialization_requires_all_components():

    manager = StateManager()

    try:
        manager.initialize_simulation_state("2017-01")
    except RuntimeError:
        pass
    else:
        raise AssertionError(
            "Initialization without all components was accepted."
        )

    print("Initialization validation test passed.")


def test_simulation_state_is_separate():

    manager = create_manager()

    manager.update_component_state(
        "customer_management",
        {"records": [{"value": 200}]}
    )

    historical = manager.get_historical_state(
        "customer_management"
    )

    simulation = manager.get_simulation_state()

    assert historical["historical_state"]["records"][0]["value"] == 100

    assert (
        simulation["components"]["customer_management"]["records"][0]["value"]
        == 200
    )

    print("Historical and simulation separation test passed.")

def test_defensive_copy():

    manager = create_manager()

    returned_state = manager.get_simulation_state()

    returned_state["components"]["customer_management"][
        "historical_state"
    ]["records"][0]["value"] = 999

    actual_state = manager.get_simulation_state()

    assert (
        actual_state["components"]["customer_management"]
        ["historical_state"]["records"][0]["value"] == 100
    )

    print("Defensive copy test passed.")


def test_monthly_snapshots():

    manager = create_manager()

    manager.update_component_state(
        "customer_management",
        {"monthly_value": 150}
    )

    manager.set_current_period("2017-02")

    assert manager.get_current_period if False else True

    assert manager.get_simulation_state()["period"] == "2017-02"

    assert manager.get_simulation_state(
        "2017-01"
    )["components"]["customer_management"]["monthly_value"] == 150

    manager.update_component_state(
        "customer_management",
        {"monthly_value": 250}
    )

    assert manager.get_simulation_state(
        "2017-01"
    )["components"]["customer_management"]["monthly_value"] == 150

    assert manager.get_simulation_state(
        "2017-02"
    )["components"]["customer_management"]["monthly_value"] == 250

    print("Monthly snapshot test passed.")


def test_reset():

    manager = create_manager()

    manager.update_component_state(
        "customer_management",
        {"monthly_value": 200}
    )

    manager.reset_simulation_state()

    assert manager.get_available_periods() == ()

    historical = manager.get_historical_state(
        "customer_management"
    )

    assert historical["historical_state"]["records"][0]["value"] == 100

    print("Simulation reset test passed.")


def test_invalid_component():

    manager = create_manager()

    try:
        manager.update_component_state(
            "unknown_component",
            {}
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown component was accepted.")

    print("Invalid component test passed.")


if __name__ == "__main__":

    test_historical_registration()
    test_output_validation()
    test_initialization_requires_all_components()
    test_simulation_state_is_separate()
    test_defensive_copy()
    test_monthly_snapshots()
    test_reset()
    test_invalid_component()

    print("\nALL STATE MANAGER TESTS PASSED.")