
import pandas as pd

from src.scenarios.multi_parameter_scenario import (
    MultiParameterScenarioEngine,
)

DATA_DIR = "data/raw/olist"

# Neutral technical validation configuration.
# These are NOT historical business rates or production assumptions.
VALIDATION_PARAMETERS = {
    "product_price_adjustment": 0.0,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.0,
    "commission_rate": 0.0,
    "freight_adjustment": 0.0,
}


def load_datasets():

    print("Loading Olist datasets...")

    products = pd.read_csv(
        f"{DATA_DIR}/olist_products_dataset.csv"
    )

    order_items = pd.read_csv(
        f"{DATA_DIR}/olist_order_items_dataset.csv"
    )

    orders = pd.read_csv(
        f"{DATA_DIR}/olist_orders_dataset.csv"
    )

    customers = pd.read_csv(
        f"{DATA_DIR}/olist_customers_dataset.csv"
    )

    category_translation = pd.read_csv(
        f"{DATA_DIR}/product_category_name_translation.csv"
    )

    print("All required datasets loaded.")

    return (
        products,
        order_items,
        orders,
        customers,
        category_translation,
    )


def main():

    datasets = load_datasets()

    print("\nInitializing scenario engine...")

    engine = MultiParameterScenarioEngine(
        products=datasets[0],
        order_items=datasets[1],
        orders=datasets[2],
        customers=datasets[3],
        category_translation=datasets[4],
        baseline_parameters=VALIDATION_PARAMETERS.copy(),
        scenario_parameters=VALIDATION_PARAMETERS.copy(),
    )

    print("\nRunning real-data scenario...")

    result = engine.run()

    print("\n========== EXECUTION RESULTS ==========")

    print("Status:", result["status"])

    print(
        "Transaction records:",
        len(result["scenario"]["transactions"]),
    )

    print(
        "Unique products:",
        result["scenario"]["transactions"]["product_id"].nunique(),
    )

    print(
        "Unique sellers:",
        result["scenario"]["transactions"]["seller_id"].nunique(),
    )

    print(
        "Unique customers:",
        result["scenario"]["transactions"]["customer_unique_id"].nunique(),
    )

    print(
        "Unique orders:",
        result["scenario"]["transactions"]["order_id"].nunique(),
    )

    print("\n========== SIX DIMENSIONS ==========")

    for dimension, dataframe in (
        result["scenario"]["dimensions"].items()
    ):
        print(
            f"{dimension}: {len(dataframe)} aggregated records"
        )

    print("\n========== FINANCIAL SUMMARY ==========")

    for metric, value in (
        result["scenario"]["summary"].items()
    ):
        print(f"{metric}: {value:,.2f}")

    print("\n========== VALIDATION ==========")

    validation = result["validation"]

    print("Overall validation:", validation["passed"])

    print(
        "Baseline checks:",
        validation["baseline"]["passed_checks"],
        "/",
        validation["baseline"]["total_checks"],
    )

    print(
        "Scenario checks:",
        validation["scenario"]["passed_checks"],
        "/",
        validation["scenario"]["total_checks"],
    )

    print(
        "Historical transactions unchanged:",
        validation["historical_transactions_unchanged"],
    )

    if not validation["passed"]:
        print("\nFAILED CHECKS:")

        print(
            "Baseline:",
            validation["baseline"]["failed_checks"],
        )

        print(
            "Scenario:",
            validation["scenario"]["failed_checks"],
        )

        raise AssertionError(
            "Real Olist integration validation failed."
        )

    assert len(result["scenario"]["dimensions"]) == 6

    print("\nREAL OLIST INTEGRATION TEST PASSED")


if __name__ == "__main__":
    main()
