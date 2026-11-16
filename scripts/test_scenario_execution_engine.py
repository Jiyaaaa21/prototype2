
import pandas as pd
import numpy as np

from src.scenarios.scenario_definition import ScenarioDefinition
from src.scenarios.scenario_execution_engine import (
    ScenarioExecutionEngine
)


def create_definition(
    adjustment_type="percentage_increase",
    adjustment_value=5.0,
    scope=None
):
    return ScenarioDefinition(
        scenario_id="SCN-TEST",
        name="Execution Engine Test",
        target_component="product_management",
        target_variable="price",
        adjustment_type=adjustment_type,
        adjustment_value=adjustment_value,
        scope=scope or {"type": "all_records"},
        assumptions=("Test quantities remain unchanged.",)
    )


def main():

    print("\nTESTING SCENARIO EXECUTION ENGINE")
    print("-" * 60)

    engine = ScenarioExecutionEngine()

    source_states = {
        "product_management": pd.DataFrame({
            "product_id": ["P1", "P2", "P3"],
            "price": [100.0, 200.0, 300.0],
            "item_line_count": [10, 5, 0]
        }),
        "seller_management": pd.DataFrame({
            "seller_id": ["S1", "S2"],
            "merchandise_value": [1000.0, 2000.0]
        })
    }

    original_states = {
        name: frame.copy(deep=True)
        for name, frame in source_states.items()
    }

    # 1. Percentage increase
    result = engine.execute(
        create_definition(),
        source_states
    )

    expected = np.array([105.0, 210.0, 315.0])

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        expected
    )

    assert result["execution_report"]["status"] == "SUCCESS"
    assert result["execution_report"]["affected_records"] == 3

    print("Percentage increase: PASSED")

    # 2. Percentage decrease
    result = engine.execute(
        create_definition(
            "percentage_decrease", 10.0
        ),
        source_states
    )

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        [90.0, 180.0, 270.0]
    )

    print("Percentage decrease: PASSED")

    # 3. Absolute increase
    result = engine.execute(
        create_definition(
            "absolute_increase", 25.0
        ),
        source_states
    )

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        [125.0, 225.0, 325.0]
    )

    print("Absolute increase: PASSED")

    # 4. Absolute decrease
    result = engine.execute(
        create_definition(
            "absolute_decrease", 20.0
        ),
        source_states
    )

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        [80.0, 180.0, 280.0]
    )

    print("Absolute decrease: PASSED")

    # 5. Set value
    result = engine.execute(
        create_definition(
            "set_value", 150.0
        ),
        source_states
    )

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        [150.0, 150.0, 150.0]
    )

    print("Set value: PASSED")

    # 6. Historical sales scope
    result = engine.execute(
        create_definition(
            "percentage_increase",
            5.0,
            {"type": "all_products_with_historical_sales"}
        ),
        source_states
    )

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        [105.0, 210.0, 300.0]
    )

    assert result["execution_report"]["affected_records"] == 2

    print("Historical sales scope: PASSED")

    # 7. Filter scope
    result = engine.execute(
        create_definition(
            "percentage_increase",
            10.0,
            {
                "type": "filter",
                "filters": {"product_id": ["P1", "P3"]}
            }
        ),
        source_states
    )

    np.testing.assert_allclose(
        result["scenario_states"]["product_management"]["price"],
        [110.0, 200.0, 330.0]
    )

    print("Filter scope: PASSED")

    # 8. Source isolation
    for name in source_states:
        pd.testing.assert_frame_equal(
            source_states[name],
            original_states[name]
        )

    print("Source DataFrame isolation: PASSED")

    # 9. Non-target component isolation
    pd.testing.assert_frame_equal(
        result["scenario_states"]["seller_management"],
        original_states["seller_management"]
    )

    print("Non-target component isolation: PASSED")

    # 10. Invalid target variable
    invalid_definition = ScenarioDefinition(
        scenario_id="SCN-INVALID",
        name="Invalid Variable",
        target_component="product_management",
        target_variable="unknown_column",
        adjustment_type="percentage_increase",
        adjustment_value=5.0,
        scope={"type": "all_records"},
        assumptions=("Test assumption",)
    )

    try:
        engine.execute(invalid_definition, source_states)
        raise AssertionError("Invalid target variable was accepted.")
    except KeyError:
        print("Invalid target variable rejection: PASSED")

    # 11. Negative resulting value
    try:
        engine.execute(
            create_definition(
                "absolute_decrease", 500.0
            ),
            source_states
        )
        raise AssertionError("Negative result was accepted.")
    except ValueError:
        print("Negative result rejection: PASSED")

    print("\nALL SCENARIO EXECUTION ENGINE TESTS PASSED.")


if __name__ == "__main__":
    main()