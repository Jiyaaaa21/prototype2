from pathlib import Path

import pandas as pd

from config.settings import DATA_DIR, REPORT_DIR
from src.scenarios.scenario_orchestrator import ScenarioOrchestrator


# Evidence-backed modelling assumptions; these are external proxies,
# not transaction-level facts contained in the Olist dataset.
BASELINE_PARAMETERS = {
    "product_price_adjustment": 0.0,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.7267441860465117,
    "commission_rate": 0.20,
    "freight_adjustment": 0.0,
}

# Neutral-baseline test: scenario must be identical to baseline.
SCENARIO_PARAMETERS = BASELINE_PARAMETERS.copy()


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


def verify_neutral_impact(summary):
    baseline = summary["baseline_summary"]
    scenario = summary["scenario_summary"]

    assert set(baseline) == set(scenario), (
        "Baseline and scenario summary metrics differ."
    )

    for metric in baseline:
        baseline_value = baseline[metric]
        scenario_value = scenario[metric]
        if isinstance(baseline_value, (int, float)) and isinstance(
            scenario_value, (int, float)
        ):
            assert abs(float(scenario_value) - float(baseline_value)) <= 0.01, (
                f"Neutral scenario changed {metric}: "
                f"baseline={baseline_value}, scenario={scenario_value}"
            )

    for metric, impact_data in summary["overall_impact"].items():
        assert abs(float(impact_data["impact"])) <= 0.01, (
            f"Expected zero impact for {metric}, got {impact_data['impact']}"
        )

    print("[PASS] Baseline and scenario financial summaries are identical.")
    print("[PASS] All overall financial impacts are zero.")


def main():
    print("\nNEUTRAL-BASELINE SCENARIO ORCHESTRATOR TEST")
    print("=" * 58)

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

    expected_dimensions = {
        "product", "category", "seller", "customer", "order", "monthly"
    }
    actual_dimensions = set(results["scenario_results"]["impact"]["dimensions"])
    assert actual_dimensions == expected_dimensions
    assert set(summary["validated_dimensions"]) == expected_dimensions

    verify_neutral_impact(summary)

    # Commission should be non-zero under the evidence-backed 20% assumption,
    # and its base must include NMV plus adjusted freight.
    scenario_transactions = results["scenario_results"]["scenario"]["transactions"]
    expected_commission = (
        scenario_transactions["net_merchandise_value"]
        + scenario_transactions["freight_value"]
    ) * SCENARIO_PARAMETERS["commission_rate"]

    actual_commission_total = float(scenario_transactions["commission"].sum())
    expected_commission_total = float(expected_commission.sum())

    assert actual_commission_total > 0, "Commission should be positive at a 20% rate."
    assert abs(actual_commission_total - expected_commission_total) <= 0.01, (
        "Commission does not reconcile to NMV + adjusted freight."
    )

    print("[PASS] All six business dimensions.")
    print("[PASS] Commission base = NMV + adjusted freight.")
    print(f"[PASS] Commission total: {actual_commission_total:,.2f}")
    print(
        "Independent checks: "
        f"{summary['independent_checks_passed']}/"
        f"{summary['independent_checks_total']}"
    )

    verify_reports(results["report_paths"])
    verify_source_immutability(original, datasets)

    print("\nNEUTRAL-BASELINE TEST PASSED")


if __name__ == "__main__":
    main()
