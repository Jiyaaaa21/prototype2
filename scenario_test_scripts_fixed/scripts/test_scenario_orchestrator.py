from pathlib import Path

import pandas as pd

from config.settings import DATA_DIR, REPORT_DIR
from src.scenarios.scenario_orchestrator import ScenarioOrchestrator


BASELINE_PARAMETERS = {
    "product_price_adjustment": 0.0,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.7267441860465117,
    "commission_rate": 0.20,
    "freight_adjustment": 0.0,
}

SCENARIO_PARAMETERS = {
    "product_price_adjustment": 0.05,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.7267441860465117,
    "commission_rate": 0.20,
    "freight_adjustment": 0.0,
}


def load_datasets():
    filenames = {
        "products": "olist_products_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "category_translation": "product_category_name_translation.csv",
    }
    datasets = {}
    for name, filename in filenames.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Required dataset not found: {path}")
        datasets[name] = pd.read_csv(path)
        print(f"Loaded {name}: {len(datasets[name]):,} rows")
    return datasets


def verify_source_immutability(original, current):
    for name in original:
        pd.testing.assert_frame_equal(
            original[name], current[name], check_dtype=True, check_exact=True
        )
    print("[PASS] Historical source data remains unchanged.")


def verify_reports(report_paths):
    for report_name in ("excel", "pdf"):
        path = Path(report_paths[report_name])
        assert path.exists() and path.stat().st_size > 0, (
            f"{report_name} report missing or empty: {path}"
        )
        print(f"[PASS] {report_name.upper()} report: {path}")


def main():
    print("\nSCENARIO ORCHESTRATOR INTEGRATION TEST")
    print("=" * 55)
    datasets = load_datasets()
    original = {name: frame.copy(deep=True) for name, frame in datasets.items()}

    orchestrator = ScenarioOrchestrator(
        **datasets,
        baseline_parameters=BASELINE_PARAMETERS,
        scenario_parameters=SCENARIO_PARAMETERS,
        output_dir=REPORT_DIR,
    )
    results = orchestrator.run()

    assert results["status"] == "SUCCESS"
    summary = results["execution_summary"]
    assert summary["independent_validation"] == "PASSED"
    assert summary["independent_checks_passed"] == summary["independent_checks_total"]

    expected_dimensions = {"product", "category", "seller", "customer", "order", "monthly"}
    actual_dimensions = set(results["scenario_results"]["impact"]["dimensions"])
    assert actual_dimensions == expected_dimensions
    assert set(summary["validated_dimensions"]) == expected_dimensions

    baseline_gmv = summary["baseline_summary"]["gross_merchandise_value"]
    scenario_gmv = summary["scenario_summary"]["gross_merchandise_value"]
    impact_gmv = summary["overall_impact"]["gross_merchandise_value"]["impact"]
    assert abs((scenario_gmv - baseline_gmv) - impact_gmv) <= 0.01

    # Explicitly verify commission is applied to NMV + adjusted freight.
    scenario = results["scenario_results"]["scenario"]["transactions"]
    expected_commission = (
        scenario["net_merchandise_value"] + scenario["freight_value"]
    ) * SCENARIO_PARAMETERS["commission_rate"]
    assert abs(scenario["commission"].sum() - expected_commission.sum()) <= 0.01

    print("[PASS] Scenario execution and independent validation.")
    print("[PASS] All six business dimensions.")
    print("[PASS] Commission base = NMV + adjusted freight.")
    print(f"Independent checks: {summary['independent_checks_passed']}/{summary['independent_checks_total']}")

    verify_reports(results["report_paths"])
    verify_source_immutability(original, datasets)
    print("\nALL SCENARIO ORCHESTRATOR TESTS PASSED")


if __name__ == "__main__":
    main()
