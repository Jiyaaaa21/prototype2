from pathlib import Path
import warnings
import numpy as np
import pandas as pd

try:
    import statsmodels.formula.api as smf
except ImportError as exc:
    raise SystemExit(
        "Install dependencies in your active venv:\n"
        "python -m pip install statsmodels openpyxl"
    ) from exc

from config.settings import REPORT_DIR

COHORTS = [
    ("Initial_573_style", 6, 10, 2),
    ("Moderate", 4, 10, 2),
    ("Strict", 8, 20, 3),
]
PRICE_CHANGE_THRESHOLD_PCT = 1.0


def main():
    input_path = (
        Path(REPORT_DIR) / "elasticity_feasibility"
        / "product_seller_month_panel.csv"
    )
    if not input_path.exists():
        raise FileNotFoundError(
            f"{input_path} not found. Run the feasibility audit first."
        )

    df = pd.read_csv(input_path)
    required = {
        "product_id", "seller_id", "month", "item_lines", "avg_price"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing panel columns: {sorted(missing)}")

    df["item_lines"] = pd.to_numeric(df["item_lines"], errors="coerce")
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    df["month"] = df["month"].astype(str)
    df = df.dropna(
        subset=["product_id", "seller_id", "month", "item_lines", "avg_price"]
    )
    df = df[(df["item_lines"] > 0) & (df["avg_price"] > 0)].copy()
    df["pair_id"] = (
        df["product_id"].astype(str) + "__" + df["seller_id"].astype(str)
    )
    df = df.sort_values(["pair_id", "month"]).reset_index(drop=True)
    df["price_change_pct"] = (
        df.groupby("pair_id")["avg_price"].pct_change(fill_method=None) * 100
    )

    pair_stats = (
        df.groupby("pair_id", as_index=False)
        .agg(
            product_id=("product_id", "first"),
            seller_id=("seller_id", "first"),
            active_months=("month", "nunique"),
            total_item_lines=("item_lines", "sum"),
            observed_months=("month", "size"),
            mean_price=("avg_price", "mean"),
            min_price=("avg_price", "min"),
            max_price=("avg_price", "max"),
            price_change_count=(
                "price_change_pct",
                lambda s: int((s.abs() > PRICE_CHANGE_THRESHOLD_PCT).sum()),
            ),
        )
    )

    model_results = []
    cohort_rows = []

    for name, min_months, min_lines, min_changes in COHORTS:
        eligible = pair_stats[
            (pair_stats["active_months"] >= min_months)
            & (pair_stats["total_item_lines"] >= min_lines)
            & (pair_stats["price_change_count"] >= min_changes)
        ]
        sample = df[df["pair_id"].isin(eligible["pair_id"])].copy()

        cohort_rows.append({
            "cohort": name,
            "minimum_active_months": min_months,
            "minimum_item_lines": min_lines,
            "minimum_price_changes_over_1pct": min_changes,
            "product_seller_pairs": len(eligible),
            "panel_observations": len(sample),
            "calendar_months": sample["month"].nunique(),
        })

        print(
            f"{name}: {len(eligible):,} pairs, "
            f"{len(sample):,} observed rows"
        )

        if len(eligible) < 2 or len(sample) <= len(eligible):
            print(f"[SKIP] {name}: insufficient within-pair observations.")
            continue

        sample["log_price"] = np.log(sample["avg_price"])
        sample["log_item_lines"] = np.log(sample["item_lines"])

        for winsorize in (False, True):
            model_data = sample.copy()
            if winsorize:
                low, high = model_data["log_price"].quantile([0.01, 0.99])
                model_data["log_price"] = model_data["log_price"].clip(low, high)

            formula = "log_item_lines ~ log_price + C(pair_id) + C(month)"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fitted = smf.ols(formula, data=model_data).fit(
                    cov_type="cluster",
                    cov_kwds={"groups": model_data["pair_id"]},
                )

            ci = fitted.conf_int().loc["log_price"]
            model_results.append({
                "model": name,
                "winsorized_log_price": winsorize,
                "observations": int(fitted.nobs),
                "product_seller_pairs": int(model_data["pair_id"].nunique()),
                "months": int(model_data["month"].nunique()),
                "elasticity_coefficient": float(fitted.params["log_price"]),
                "clustered_standard_error": float(fitted.bse["log_price"]),
                "ci_95_lower": float(ci.iloc[0]),
                "ci_95_upper": float(ci.iloc[1]),
                "p_value": float(fitted.pvalues["log_price"]),
                "r_squared": float(fitted.rsquared),
                "adjusted_r_squared": float(fitted.rsquared_adj),
                "fixed_effects": "Product-seller pair + calendar month",
                "standard_errors": "Clustered by product-seller pair",
            })

    diagnostics = pd.DataFrame([
        ["Panel observations", len(df)],
        ["Product-seller pairs", pair_stats["pair_id"].nunique()],
        ["Median active months per pair", pair_stats["active_months"].median()],
        ["Median item lines per pair", pair_stats["total_item_lines"].median()],
        ["Rows with one item line (%)", (df["item_lines"] == 1).mean() * 100],
        ["Zero-sales months", "Absent from input panel"],
    ], columns=["diagnostic", "value"])

    methodology = pd.DataFrame([
        ["Dependent variable", "Log monthly item-line count, not unit quantity."],
        ["Price variable", "Log monthly average item price."],
        ["Fixed effects", "Product-seller pair and calendar month."],
        ["Standard errors", "Clustered by product-seller pair."],
        ["Selection", "Observed product-seller-months with positive sales only."],
        ["Zero-sales months", "Absent; estimates are conditional on observed sales months."],
        ["Causal interpretation", "Not established; price endogeneity and selection bias remain."],
        ["Scenario engine", "Do not operationalize before identification and robustness review."],
    ], columns=["topic", "limitation_or_method"])

    output_dir = Path(REPORT_DIR) / "elasticity_estimation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "Price_Elasticity_Exploratory_Results.xlsx"

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(model_results).to_excel(
            writer, sheet_name="Model Results", index=False
        )
        pd.DataFrame(cohort_rows).to_excel(
            writer, sheet_name="Cohort Comparison", index=False
        )
        diagnostics.to_excel(writer, sheet_name="Data Diagnostics", index=False)
        pair_stats.to_excel(writer, sheet_name="Pair Statistics", index=False)
        methodology.to_excel(
            writer, sheet_name="Methodology & Limits", index=False
        )
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                width = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in col
                )
                ws.column_dimensions[col[0].column_letter].width = min(
                    max(width + 2, 12), 60
                )

    print("\nMODEL RESULTS")
    if model_results:
        print(pd.DataFrame(model_results)[[
            "model", "winsorized_log_price", "observations",
            "product_seller_pairs", "elasticity_coefficient",
            "clustered_standard_error", "ci_95_lower", "ci_95_upper",
            "p_value"
        ]].to_string(index=False))
    else:
        print("No estimable cohorts.")
    print(f"\nResults workbook: {output_path}")
    print(
        "\nWARNING: This is an observational elasticity of item-line counts "
        "conditional on observed sales months, not causal unit-demand elasticity."
    )


if __name__ == "__main__":
    main()
