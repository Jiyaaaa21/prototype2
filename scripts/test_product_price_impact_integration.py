
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import DATA_DIR
from src.scenarios.product_price_scenario import ProductPriceScenarioEngine
from src.scenarios.impact_calculator import CrossComponentImpactCalculator


def load_datasets():
    """Load the five datasets required by the product price scenario."""

    files = {
        "customers": "olist_customers_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "products": "olist_products_dataset.csv",
        "category_translation": "product_category_name_translation.csv",
    }

    return {
        name: pd.read_csv(DATA_DIR / filename)
        for name, filename in files.items()
    }


def assert_close(actual, expected, message):
    assert np.isclose(
        actual,
        expected,
        rtol=1e-9,
        atol=1e-6
    ), f"{message}: expected {expected}, got {actual}"


def validate_transaction_alignment(baseline, scenario):
    """Confirm that the scenario changes prices, not transaction structure."""

    assert len(baseline) == len(scenario), (
        "Transaction row count changed."
    )

    assert baseline["order_item_id"].reset_index(drop=True).equals(
        scenario["order_item_id"].reset_index(drop=True)
    ), "Order item alignment changed."

    assert baseline["product_id"].reset_index(drop=True).equals(
        scenario["product_id"].reset_index(drop=True)
    ), "Product alignment changed."

    assert baseline["seller_id"].reset_index(drop=True).equals(
        scenario["seller_id"].reset_index(drop=True)
    ), "Seller alignment changed."

    assert_close(
        baseline["freight_value"].sum(),
        scenario["freight_value"].sum(),
        "Freight value changed"
    )

    assert_close(
        baseline["price"].sum() * 1.05,
        scenario["price"].sum(),
        "Scenario price adjustment is incorrect"
    )


def validate_dimension_reconciliation(
    scenario_impact,
    independent_impact
):
    """Compare the two impact calculations across all six dimensions."""

    dimensions = [
        "product",
        "category",
        "seller",
        "customer",
        "order",
        "monthly",
    ]

    for dimension in dimensions:
        assert dimension in scenario_impact, (
            f"Scenario output missing dimension: {dimension}"
        )

        assert dimension in independent_impact, (
            f"Independent calculator missing dimension: {dimension}"
        )

        scenario_frame = scenario_impact[dimension]
        independent_frame = independent_impact[dimension]

        scenario_change = scenario_frame[
            "merchandise_value_change"
        ].sum()

        independent_change = independent_frame[
            "merchandise_value_change"
        ].sum()

        assert_close(
            independent_change,
            scenario_change,
            f"{dimension} impact reconciliation failed"
        )

        print(f"{dimension}: reconciled.")


def main():
    print("\nLOADING OLIST DATASETS")
    data = load_datasets()

    # Preserve original data for immutability validation.
    original_data = {
        name: frame.copy(deep=True)
        for name, frame in data.items()
    }

    print("Datasets loaded.")

    print("\nEXECUTING PRODUCT PRICE SCENARIO")

    engine = ProductPriceScenarioEngine(
        products=data["products"],
        order_items=data["order_items"],
        orders=data["orders"],
        customers=data["customers"],
        category_translation=data["category_translation"],
        adjustment_rate=0.05,
    )

    scenario_results = engine.run()

    baseline_transactions = scenario_results[
        "baseline_transactions"
    ]

    scenario_transactions = scenario_results[
        "scenario_transactions"
    ]

    print("Product price scenario executed.")

    print("\nVALIDATING TRANSACTION ALIGNMENT")

    validate_transaction_alignment(
        baseline_transactions,
        scenario_transactions
    )

    assert len(baseline_transactions) == 112650
    print("Historical transaction count preserved.")

    print("\nRUNNING INDEPENDENT CROSS-COMPONENT IMPACT CALCULATOR")

    calculator = CrossComponentImpactCalculator()

    independent_results = calculator.calculate(
        baseline_transactions=baseline_transactions,
        scenario_transactions=scenario_transactions,
    )

    print("Independent impact calculation completed.")

    print("\nVALIDATING SIX BUSINESS DIMENSIONS")

    validate_dimension_reconciliation(

    scenario_results["impact"],
    independent_results["impact"],
    )


    print("\nVALIDATING OVERALL MERCHANDISE VALUE")

    baseline_value = baseline_transactions["price"].sum()
    scenario_value = scenario_transactions["price"].sum()
    expected_change = baseline_value * 0.05

    assert_close(
        baseline_value,
        13591643.70,
        "Baseline merchandise value"
    )

    assert_close(
        scenario_value,
        14271225.885,
        "Scenario merchandise value"
    )

    assert_close(
        scenario_value - baseline_value,
        expected_change,
        "Overall merchandise value change"
    )

    print(f"Baseline: R${baseline_value:,.2f}")
    print(f"Scenario: R${scenario_value:,.2f}")
    print(f"Change:   R${scenario_value - baseline_value:,.2f}")

    print("\nVALIDATING QUANTITY AND FREIGHT")

    assert len(baseline_transactions) == len(scenario_transactions)

    assert_close(
        baseline_transactions["freight_value"].sum(),
        scenario_transactions["freight_value"].sum(),
        "Freight value"
    )

    print("Item line count unchanged.")
    print("Freight value unchanged.")

    print("\nVALIDATING SOURCE DATA IMMUTABILITY")

    for name, original_frame in original_data.items():
        pd.testing.assert_frame_equal(
            data[name],
            original_frame,
            check_dtype=True,
            check_exact=True,
        )

    print("All original source DataFrames remain unchanged.")

    print("\nSCENARIO BOUNDARY VALIDATION")
    print("Payment impact: NOT MODELLED.")
    print("Delivery impact: NOT MODELLED.")
    print("Demand response: NOT MODELLED.")
    print("Historical data: NOT MODIFIED.")

    print("\n" + "=" * 55)
    print("ALL PRODUCT PRICE IMPACT INTEGRATION TESTS PASSED.")
    print("=" * 55)


if __name__ == "__main__":
    main()
