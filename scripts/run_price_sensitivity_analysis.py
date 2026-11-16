from pathlib import Path

import pandas as pd

from config.settings import DATA_DIR, REPORT_DIR
from src.scenarios.scenario_orchestrator import ScenarioOrchestrator


# Fixed assumptions for all five deterministic price scenarios.
# These are model assumptions/proxies, not transaction-level Olist facts.
BASELINE_PARAMETERS = {
    "product_price_adjustment": 0.0,
    "discount_rate": 0.0,
    "seller_cost_rate": 0.7267441860465117,
    "commission_rate": 0.20,
    "freight_adjustment": 0.0,
}

PRICE_SCENARIOS = [
    ("S1_MINUS_10", -0.10),
    ("S2_MINUS_5", -0.05),
    ("S3_NEUTRAL", 0.00),
    ("S4_PLUS_5", 0.05),
    ("S5_PLUS_10", 0.10),
]

METRICS = [
    "gross_merchandise_value",
    "discount_amount",
    "net_merchandise_value",
    "freight_value",
    "commission",
    "seller_cost",
    "seller_payout",
    "seller_contribution",
    "item_line_count",
]

DIMENSIONS = ["product", "category", "seller", "customer", "order", "monthly"]


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


def validate_source_immutability(original, current):
    for name in original:
        pd.testing.assert_frame_equal(
            original[name], current[name], check_dtype=True, check_exact=True
        )
    print("[PASS] Original source datasets remain unchanged.")


def run_scenario(datasets, scenario_name, price_adjustment, output_dir):
    scenario_parameters = BASELINE_PARAMETERS.copy()
    scenario_parameters["product_price_adjustment"] = price_adjustment

    orchestrator = ScenarioOrchestrator(
        **datasets,
        baseline_parameters=BASELINE_PARAMETERS.copy(),
        scenario_parameters=scenario_parameters,
        output_dir=output_dir,
    )
    result = orchestrator.run()

    assert result["status"] == "SUCCESS", f"{scenario_name} did not succeed."
    summary = result["execution_summary"]
    assert summary["independent_validation"] == "PASSED"
    assert (
        summary["independent_checks_passed"]
        == summary["independent_checks_total"]
    )
    assert set(summary["validated_dimensions"]) == set(DIMENSIONS)

    # Validate commission on transaction-level results.
    tx = result["scenario_results"]["scenario"]["transactions"]
    expected_commission = (
        tx["net_merchandise_value"] + tx["freight_value"]
    ) * scenario_parameters["commission_rate"]
    actual_total = float(tx["commission"].sum())
    expected_total = float(expected_commission.sum())
    assert abs(actual_total - expected_total) <= 0.01, (
        f"{scenario_name}: commission reconciliation failed."
    )

    print(
        f"[PASS] {scenario_name}: price {price_adjustment:+.0%}, "
        f"independent checks "
        f"{summary['independent_checks_passed']}/"
        f"{summary['independent_checks_total']}"
    )

    return result


def build_output_tables(results_by_scenario):
    summary_rows = []
    impact_rows = []
    dimension_rows = []

    for scenario_name, price_adjustment, result in results_by_scenario:
        execution = result["execution_summary"]
        baseline = execution["baseline_summary"]
        scenario = execution["scenario_summary"]
        overall_impact = execution["overall_impact"]

        for metric in METRICS:
            impact = overall_impact[metric]
            summary_rows.append({
                "scenario": scenario_name,
                "price_adjustment_pct": price_adjustment * 100,
                "metric": metric,
                "baseline_value": baseline[metric],
                "scenario_value": scenario[metric],
                "absolute_impact": impact["impact"],
                "impact_pct": impact["impact_pct"],
            })
            impact_rows.append({
                "scenario": scenario_name,
                "price_adjustment_pct": price_adjustment * 100,
                "metric": metric,
                "baseline_value": baseline[metric],
                "scenario_value": scenario[metric],
                "absolute_impact": impact["impact"],
                "impact_pct": impact["impact_pct"],
            })

        # Check each dimension's summed impact against the overall impact.
        dimension_results = result["scenario_results"]["impact"]["dimensions"]
        for dimension in DIMENSIONS:
            frame = dimension_results[dimension]
            for metric in METRICS:
                impact_column = f"{metric}_impact"
                dimension_impact = float(frame[impact_column].sum())
                overall_value = float(overall_impact[metric]["impact"])
                difference = dimension_impact - overall_value

                dimension_rows.append({
                    "scenario": scenario_name,
                    "price_adjustment_pct": price_adjustment * 100,
                    "dimension": dimension,
                    "metric": metric,
                    "dimension_impact_sum": dimension_impact,
                    "overall_impact": overall_value,
                    "reconciliation_difference": difference,
                    "passed": abs(difference) <= 0.01,
                })

    summary_df = pd.DataFrame(summary_rows)
    impact_df = pd.DataFrame(impact_rows)
    dimension_df = pd.DataFrame(dimension_rows)

    if not dimension_df["passed"].all():
        failures = dimension_df.loc[~dimension_df["passed"]]
        raise AssertionError(
            "Dimensional impact reconciliation failed:\n"
            + failures.to_string(index=False)
        )

    return summary_df, impact_df, dimension_df


def main():
    print("\nFIVE-POINT PRODUCT PRICE SENSITIVITY ANALYSIS")
    print("=" * 62)
    print("All non-price assumptions remain fixed.")
    print("Demand and item-line volume are held constant (no elasticity model).")

    datasets = load_datasets()
    original = {
        name: frame.copy(deep=True)
        for name, frame in datasets.items()
    }

    run_root = Path(REPORT_DIR) / "price_sensitivity_runs"
    run_root.mkdir(parents=True, exist_ok=True)

    results_by_scenario = []

    for scenario_name, price_adjustment in PRICE_SCENARIOS:
        print(f"\nRunning {scenario_name}...")
        scenario_output_dir = run_root / scenario_name
        scenario_output_dir.mkdir(parents=True, exist_ok=True)

        result = run_scenario(
            datasets=datasets,
            scenario_name=scenario_name,
            price_adjustment=price_adjustment,
            output_dir=scenario_output_dir,
        )
        results_by_scenario.append(
            (scenario_name, price_adjustment, result)
        )

    summary_df, impact_df, dimension_df = build_output_tables(
        results_by_scenario
    )

    # The neutral control must produce zero impact for every metric.
    neutral = impact_df[impact_df["scenario"] == "S3_NEUTRAL"]
    assert (neutral["absolute_impact"].abs() <= 0.01).all(), (
        "Neutral scenario did not produce zero impact."
    )
    print("\n[PASS] Neutral control scenario produces zero financial impact.")
    print("[PASS] All six dimensional impact reconciliations passed.")

    output_path = Path(REPORT_DIR) / "Price_Sensitivity_Analysis.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    methodology_df = pd.DataFrame([
        ["Purpose", "Deterministic sensitivity of financial outputs to product price adjustments."],
        ["Price scenarios", "-10%, -5%, 0%, +5%, +10%."],
        ["Discount rate", "0% across all scenarios."],
        ["Seller cost rate", "72.6744186% proxy, held fixed across scenarios."],
        ["Commission rate", "20% external historical benchmark, held fixed across scenarios."],
        ["Freight adjustment", "0% across all scenarios."],
        ["Demand response", "Not modelled. Historical item-line volume is held constant."],
        ["Seller cost basis", "Applied to historical item price; does not increase with adjusted selling price."],
        ["Commission base", "Net merchandise value plus adjusted freight."],
        ["Interpretation", "Results are conditional model outputs, not forecasts or observed outcomes."],
        ["Currency", "Olist monetary amounts are in Brazilian real (BRL)."],
    ], columns=["item", "description"])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Scenario Summary", index=False)
        impact_df.to_excel(writer, sheet_name="KPI Impact", index=False)
        dimension_df.to_excel(
            writer, sheet_name="Dimension Reconciliation", index=False
        )
        methodology_df.to_excel(writer, sheet_name="Methodology", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                max_length = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                worksheet.column_dimensions[
                    column_cells[0].column_letter
                ].width = min(max(max_length + 2, 12), 55)

    validate_source_immutability(original, datasets)

    print("\nSENSITIVITY ANALYSIS COMPLETED")
    print(f"Combined workbook: {output_path}")
    print(f"Per-scenario validated reports: {run_root}")
    print(
        "Dimension reconciliation checks: "
        f"{len(dimension_df):,}/{len(dimension_df):,} passed"
    )


if __name__ == "__main__":
    main()
