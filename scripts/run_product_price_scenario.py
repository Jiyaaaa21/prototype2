
from config.settings import (
    DATA_DIR,
    REPORT_DIR
)

from src.scenarios.scenario_orchestrator import (
    ScenarioOrchestrator
)


def main():

    print("=" * 60)
    print("COMMERCIAL & SALES DIGITAL TWIN")
    print("PRODUCT PRICE SCENARIO")
    print("=" * 60)

    datasets = {
        "products": "olist_products_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "category_translation": (
            "product_category_name_translation.csv"
        )
    }

    loaded_data = {}

    for name, filename in datasets.items():

        path = DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {path}"
            )

        loaded_data[name] = __import__("pandas").read_csv(path)

        print(
            f"[LOADED] {name}: "
            f"{len(loaded_data[name]):,} rows"
        )

    orchestrator = ScenarioOrchestrator(
        products=loaded_data["products"],
        order_items=loaded_data["order_items"],
        orders=loaded_data["orders"],
        customers=loaded_data["customers"],
        category_translation=loaded_data[
            "category_translation"
        ],
        output_dir=REPORT_DIR
    )

    results = orchestrator.run(adjustment_rate=0.05)

    summary = results["execution_summary"]

    print("\nSCENARIO EXECUTION COMPLETE")
    print("-" * 60)

    print(f"Status: {summary['status']}")
    print(f"Scenario ID: {summary['scenario_id']}")
    print(
        f"Price Adjustment: "
        f"{summary['adjustment_percentage']}%"
    )

    print(
        f"Baseline Merchandise Value: "
        f"R$ {summary['baseline_merchandise_value']:,.2f}"
    )

    print(
        f"Scenario Merchandise Value: "
        f"R$ {summary['scenario_merchandise_value']:,.2f}"
    )

    print(
        f"Merchandise Value Change: "
        f"R$ {summary['merchandise_value_change']:,.2f}"
    )

    print(
        f"Independent Validation: "
        f"{summary['independent_validation']}"
    )

    print("\nGENERATED REPORTS")
    print("-" * 60)

    for name, path in results["report_paths"].items():
        print(f"{name.upper()}: {path}")

    print("\nALL OPERATIONS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
