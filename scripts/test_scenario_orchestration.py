
import pandas as pd

from src.scenarios.scenario_orchestrator import ScenarioOrchestrator

DATA_DIR = "data/raw/olist"

# Explicit test inputs only — not historical business assumptions.
BASELINE_PARAMETERS = {
    "product_price_adjustment": 0.0,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.0,
    "commission_rate": 0.0,
    "freight_adjustment": 0.0,
}

SCENARIO_PARAMETERS = {
    "product_price_adjustment": 0.10,
    "discount_rate": 0.05,
    "seller_cost_rate": 0.40,
    "commission_rate": 0.10,
    "freight_adjustment": 0.20,
}


def main():

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

    print("Initializing orchestrator...")

    orchestrator = ScenarioOrchestrator(
        products=products,
        order_items=order_items,
        orders=orders,
        customers=customers,
        category_translation=category_translation,
        baseline_parameters=BASELINE_PARAMETERS,
        scenario_parameters=SCENARIO_PARAMETERS,
    )

    print("Executing complete scenario pipeline...")

    result = orchestrator.run()

    print("\n========== EXECUTION SUMMARY ==========")
    print(result["execution_summary"])

    print("\n========== INDEPENDENT VALIDATION ==========")
    print(result["independent_validation"]["passed_checks"])
    print("/", result["independent_validation"]["total_checks"])

    print("\n========== REPORT FILES ==========")
    print("Excel:", result["report_paths"]["excel"])
    print("PDF:", result["report_paths"]["pdf"])

    assert result["status"] == "SUCCESS"
    assert result["independent_validation"]["passed"]
    assert result["scenario_results"]["validation"]["passed"]

    print("\nFULL SCENARIO PIPELINE PASSED")


if __name__ == "__main__":
    main()
