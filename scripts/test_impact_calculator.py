
import pandas as pd
import numpy as np

from src.scenarios.impact_calculator import (
    CrossComponentImpactCalculator
)


def main():

    print("\nTESTING CROSS-COMPONENT IMPACT CALCULATOR")
    print("-" * 65)

    baseline = pd.DataFrame({
        "product_id": ["P1", "P1", "P2", "P2"],
        "category_english": [
            "Electronics", "Electronics",
            "Furniture", "Furniture"
        ],
        "seller_id": ["S1", "S2", "S1", "S2"],
        "customer_unique_id": ["C1", "C2", "C1", "C2"],
        "order_id": ["O1", "O2", "O3", "O4"],
        "purchase_month": [
            "2018-01", "2018-01",
            "2018-02", "2018-02"
        ],
        "price": [100.0, 200.0, 300.0, 400.0],
        "freight_value": [10.0, 20.0, 30.0, 40.0]
    })

    scenario = baseline.copy(deep=True)
    scenario["price"] = scenario["price"] * 1.05

    original_baseline = baseline.copy(deep=True)
    original_scenario = scenario.copy(deep=True)

    calculator = CrossComponentImpactCalculator()

    result = calculator.calculate(
        baseline,
        scenario
    )

    # 1. Dimension availability
    expected_dimensions = {
        "product",
        "category",
        "seller",
        "customer",
        "order",
        "monthly"
    }

    assert set(result["impact"]) == expected_dimensions

    print("Six business dimensions generated: PASSED")

    # 2. Baseline merchandise value
    expected_baseline = 1000.0

    assert np.isclose(
        result["summary"]["baseline_merchandise_value"],
        expected_baseline
    )

    print("Baseline aggregation: PASSED")

    # 3. Scenario merchandise value
    expected_scenario = 1050.0

    assert np.isclose(
        result["summary"]["scenario_merchandise_value"],
        expected_scenario
    )

    print("Scenario aggregation: PASSED")

    # 4. Total impact
    expected_change = 50.0

    assert np.isclose(
        result["summary"]["merchandise_value_change"],
        expected_change
    )

    assert np.isclose(
        result["summary"]["merchandise_value_change_pct"],
        5.0
    )

    print("Merchandise value impact: PASSED")

    # 5. Cross-component reconciliation
    for dimension, frame in result["impact"].items():

        total_change = frame[
            "merchandise_value_change"
        ].sum()

        assert np.isclose(
            total_change,
            expected_change
        ), f"{dimension} reconciliation failed."

    print("Cross-component reconciliation: PASSED")

    # 6. Quantity preservation
    for dimension in expected_dimensions:

        base = result["baseline"][dimension]
        changed = result["scenario"][dimension]

        assert base["item_line_count"].sum() == (
            changed["item_line_count"].sum()
        )

        assert base["distinct_orders"].sum() == (
            changed["distinct_orders"].sum()
        )

    print("Quantity and order-count preservation: PASSED")

    # 7. Freight preservation for this price-only scenario
    for dimension, frame in result["impact"].items():

        assert np.allclose(
            frame["freight_value_change"],
            0.0
        )

    print("Freight preservation: PASSED")

    # 8. Source DataFrame isolation
    pd.testing.assert_frame_equal(
        baseline,
        original_baseline
    )

    pd.testing.assert_frame_equal(
        scenario,
        original_scenario
    )

    print("Source DataFrame isolation: PASSED")

    # 9. Summary validation
    assert result["summary"]["reconciliation_status"] == "PASSED"

    assert len(
        result["summary"]["dimensions_validated"]
    ) == 6

    print("Impact summary validation: PASSED")

    # 10. Invalid input rejection
    invalid = baseline.drop(columns=["seller_id"])

    try:
        calculator.calculate(invalid, scenario)
        raise AssertionError("Missing column was accepted.")
    except ValueError:
        print("Invalid input rejection: PASSED")

    print("\nALL IMPACT CALCULATOR TESTS PASSED.")


if __name__ == "__main__":
    main()
