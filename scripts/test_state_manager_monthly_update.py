
from copy import deepcopy

from src.simulation.state_manager import StateManager


COMPONENTS = StateManager.COMPONENTS


def build_historical_outputs():
    return {
        name: {
            "component": name,
            "metadata": {},
            "historical_state": {"baseline": True},
            "business_metrics": {},
            "scenario_results": [],
            "business_rule_results": [],
            "status": "SUCCESS",
        }
        for name in COMPONENTS
    }


def build_monthly_states():
    return {
        name: {
            "purchase_month": "2016-09",
            "records": []
        }
        for name in COMPONENTS
    }


def main():

    manager = StateManager()

    manager.register_all_historical_states(
        build_historical_outputs()
    )

    manager.initialize_simulation_state("2016-09")

    monthly_states = build_monthly_states()

    # 1. Valid six-component update.
    assert manager.update_all_component_states(monthly_states)

    snapshot = manager.get_simulation_state()

    assert snapshot["period"] == "2016-09"
    assert set(snapshot["components"]) == COMPONENTS

    for name in COMPONENTS:
        assert snapshot["components"][name] == monthly_states[name]

    print("Atomic six-component update: PASSED")

    committed_state = deepcopy(
        manager.get_simulation_state()
    )

    # 2. Missing component rejection.
    invalid_keys = build_monthly_states()
    invalid_keys.pop("seller_management")

    try:
        manager.update_all_component_states(invalid_keys)
        raise AssertionError("Missing component was accepted.")
    except ValueError:
        pass

    assert manager.get_simulation_state() == committed_state

    print("Missing component rejection: PASSED")

    # 3. Invalid component-state type rejection.
    invalid_type = build_monthly_states()
    invalid_type["seller_management"] = ["invalid"]

    try:
        manager.update_all_component_states(invalid_type)
        raise AssertionError("Invalid component state was accepted.")
    except TypeError:
        pass

    assert manager.get_simulation_state() == committed_state

    print("Invalid component-state rejection: PASSED")

    # 4. Input isolation.
    monthly_states["customer_management"]["records"].append(
        "external modification"
    )

    assert (
        manager.get_simulation_state()["components"]
        == committed_state["components"]
    )

    print("Input isolation: PASSED")

    # 5. Output isolation.
    returned_state = manager.get_simulation_state()

    returned_state["components"]["customer_management"][
        "records"
    ].append("external modification")

    assert (
        manager.get_simulation_state()["components"]
        == committed_state["components"]
    )

    print("Output isolation: PASSED")

    # 6. Historical state isolation.
    historical = manager.get_historical_state()

    for name in COMPONENTS:
        assert historical[name]["historical_state"] == {
            "baseline": True
        }

    print("Historical state isolation: PASSED")

    print("\nALL MONTHLY STATE UPDATE TESTS PASSED.")


if __name__ == "__main__":
    main()
