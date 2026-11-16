
from src.scenarios.scenario_definition import ScenarioDefinition


def main():

    print("\nTESTING SCENARIO DEFINITION")
    print("-" * 60)

    # 1. Valid scenario
    scenario = ScenarioDefinition(
        scenario_id="SCN-001",
        name="Product Price Adjustment",
        target_component="product_management",
        target_variable="price",
        adjustment_type="percentage_increase",
        adjustment_value=5.0,
        scope={
            "type": "all_products_with_historical_sales"
        },
        assumptions=(
            "Historical quantities remain constant.",
            "Demand response is not modelled.",
            "Historical source data remains unchanged."
        )
    )

    assert scenario.validate()
    print("Valid scenario creation: PASSED")

    # 2. Serialization
    data = scenario.to_dict()

    assert data["scenario_id"] == "SCN-001"
    assert data["adjustment_value"] == 5.0

    print("Scenario serialization: PASSED")

    # 3. Invalid component
    try:
        ScenarioDefinition(
            "SCN-002", "Invalid", "unknown_component",
            "price", "percentage_increase", 5.0,
            {}, ("Test assumption",)
        )
        raise AssertionError("Invalid component accepted.")
    except ValueError:
        print("Invalid component rejection: PASSED")

    # 4. Invalid adjustment type
    try:
        ScenarioDefinition(
            "SCN-003", "Invalid", "product_management",
            "price", "random_change", 5.0,
            {}, ("Test assumption",)
        )
        raise AssertionError("Invalid adjustment accepted.")
    except ValueError:
        print("Invalid adjustment rejection: PASSED")

    # 5. Invalid percentage
    try:
        ScenarioDefinition(
            "SCN-004", "Invalid", "product_management",
            "price", "percentage_increase", 150.0,
            {}, ("Test assumption",)
        )
        raise AssertionError("Invalid percentage accepted.")
    except ValueError:
        print("Invalid percentage rejection: PASSED")

    # 6. Missing assumptions
    try:
        ScenarioDefinition(
            "SCN-005", "Invalid", "product_management",
            "price", "percentage_increase", 5.0,
            {}, ()
        )
        raise AssertionError("Missing assumptions accepted.")
    except ValueError:
        print("Missing assumptions rejection: PASSED")

    # 7. Immutability
    try:
        scenario.adjustment_value = 10.0
        raise AssertionError("Scenario was modified.")
    except AttributeError:
        print("Scenario immutability: PASSED")

    print("\nALL SCENARIO DEFINITION TESTS PASSED.")


if __name__ == "__main__":
    main()
