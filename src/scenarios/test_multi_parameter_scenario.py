
import pandas as pd
from pandas.testing import assert_frame_equal

from src.scenarios.multi_parameter_scenario import (
    MultiParameterScenarioEngine,
)


# Explicit synthetic test configuration.
# These are test inputs, not historical Olist values.
PARAMETERS = {
    "product_price_adjustment": 0.0,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.0,
    "commission_rate": 0.0,
    "freight_adjustment": 0.0,
}


def build_engine(baseline=None, scenario=None):

    products = pd.DataFrame({
        "product_id": ["P1", "P2"],
        "product_category_name": ["electronics", "books"],
    })

    items = pd.DataFrame({
        "order_id": ["O1", "O1", "O2"],
        "order_item_id": [1, 2, 1],
        "product_id": ["P1", "P1", "P2"],
        "seller_id": ["S1", "S1", "S2"],
        "price": [100.0, 100.0, 200.0],
        "freight_value": [10.0, 10.0, 20.0],
    })

    orders = pd.DataFrame({
        "order_id": ["O1", "O2"],
        "customer_id": ["C1", "C2"],
        "order_purchase_timestamp": [
            "2018-01-10",
            "2018-02-10",
        ],
    })

    customers = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "customer_unique_id": ["U1", "U2"],
    })

    translations = pd.DataFrame({
        "product_category_name": ["electronics", "books"],
        "product_category_name_english": [
            "electronics",
            "books",
        ],
    })

    return MultiParameterScenarioEngine(
        products=products,
        order_items=items,
        orders=orders,
        customers=customers,
        category_translation=translations,
        baseline_parameters=(
            PARAMETERS.copy() if baseline is None else baseline
        ),
        scenario_parameters=(
            PARAMETERS.copy() if scenario is None else scenario
        ),
    )


def main():

    print("TEST 1: Baseline equals scenario")

    engine = build_engine()
    result = engine.run()

    assert result["status"] == "success"

    baseline = result["baseline"]["summary"]
    scenario = result["scenario"]["summary"]

    for metric in baseline:
        assert abs(
            baseline[metric] - scenario[metric]
        ) < 0.01

    print("PASSED")

    print("TEST 2: Combined parameter adjustments")

    scenario_parameters = {
        "product_price_adjustment": 0.10,
        "discount_rate": 0.05,
        "seller_cost_rate": 0.40,
        "commission_rate": 0.10,
        "freight_adjustment": 0.20,
    }

    engine = build_engine(
        baseline=PARAMETERS.copy(),
        scenario=scenario_parameters,
    )

    result = engine.run()
    summary = result["scenario"]["summary"]

    expected_values = {
        "gross_merchandise_value": 440.0,
        "discount_amount": 22.0,
        "net_merchandise_value": 418.0,
        "seller_cost": 160.0,
        "commission": 46.6,
        "seller_payout": 371.4,
        "seller_contribution": 211.4,
        "freight_value": 48.0,
    }

    for metric, expected in expected_values.items():
        assert abs(summary[metric] - expected) < 0.01, (
            f"{metric}: expected {expected}, "
            f"got {summary[metric]}"
        )

    print("PASSED")

    print("TEST 3: Six-dimensional reconciliation")

    dimensions = result["impact"]["dimensions"]
    overall = result["impact"]["overall"]

    assert len(dimensions) == 6

    for dimension, frame in dimensions.items():

        assert abs(
            frame["net_merchandise_value_impact"].sum()
            - overall["net_merchandise_value"]["impact"]
        ) < 0.01, f"Net merchandise reconciliation failed: {dimension}"

        assert abs(
            frame["freight_value_impact"].sum()
            - overall["freight_value"]["impact"]
        ) < 0.01, f"Freight reconciliation failed: {dimension}"

    assert result["validation"]["passed"] is True

    print("PASSED")

    print("TEST 4: Historical source immutability")

    original_items = engine.order_items.copy(deep=True)

    result["scenario"]["transactions"].loc[0, "price"] = 999999

    assert_frame_equal(
        engine.order_items,
        original_items,
    )

    assert engine.transactions.equals(
        engine._historical_transactions
    )

    print("PASSED")

    print("TEST 5: Missing hypothetical input rejected")

    invalid = PARAMETERS.copy()
    del invalid["seller_cost_rate"]

    try:
        build_engine(scenario=invalid)
        raise AssertionError(
            "Missing input was not rejected."
        )
    except ValueError:
        pass

    print("PASSED")

    print("\nALL FIVE TESTS PASSED")


if __name__ == "__main__":
    main()
