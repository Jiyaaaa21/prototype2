"""
Exploratory price-response robustness checks for the Olist Digital Twin.

Run from the project root:
    python scripts/robustness_price_elasticity.py

Expected input:
    data/outputs/reports/elasticity_feasibility/product_seller_month_panel.csv

Expected panel fields (aliases are accepted):
    product_id, seller_id, month, avg_price, item_lines

Important:
- This is observational analysis, not causal identification.
- The panel contains observed-sales months only; it does not create zero-sales rows.
- item_lines are order-item records, not physical unit quantities.
- PPML is a functional-form robustness check, not a fix for sample selection.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


PROJECT_ROOT = Path.cwd()
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "outputs"
    / "reports"
    / "elasticity_feasibility"
    / "product_seller_month_panel.csv"
)
OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "outputs"
    / "reports"
    / "elasticity_robustness"
)
OUTPUT_FILE = OUTPUT_DIR / "Price_Elasticity_Robustness_Results.xlsx"

# Cohort thresholds: active months, total item lines, qualifying price changes.
COHORTS = {
    "Core_6m_10lines_2changes": (6, 10, 2),
    "Moderate_4m_10lines_2changes": (4, 10, 2),
    "Strict_8m_20lines_3changes": (8, 20, 3),
}

MIN_PRICE_CHANGE_PCT = 0.01
WINSOR_LOWER = 0.01
WINSOR_UPPER = 0.99


def find_column(df: pd.DataFrame, candidates: list[str], purpose: str) -> str:
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    raise ValueError(
        f"Could not identify the {purpose} column. "
        f"Available columns: {list(df.columns)}"
    )


def load_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Input panel not found:\n{path}\n"
            "Run the elasticity feasibility pipeline first, or update INPUT_FILE."
        )

    df = pd.read_csv(path)

    product_col = find_column(df, ["product_id"], "product ID")
    seller_col = find_column(df, ["seller_id"], "seller ID")
    month_col = find_column(df, ["month", "order_month", "year_month"], "month")
    price_col = find_column(df, ["avg_price", "average_price", "mean_price"], "average price")
    count_col = find_column(
        df, ["item_lines", "item_line_count", "order_item_lines", "sales_count"],
        "item-line count"
    )

    df = df.rename(
        columns={
            product_col: "product_id",
            seller_col: "seller_id",
            month_col: "month",
            price_col: "avg_price",
            count_col: "item_lines",
        }
    )

    df["product_id"] = df["product_id"].astype(str)
    df["seller_id"] = df["seller_id"].astype(str)
    df["pair_id"] = df["product_id"] + "__" + df["seller_id"]
    df["month"] = df["month"].astype(str)
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    df["item_lines"] = pd.to_numeric(df["item_lines"], errors="coerce")

    df = df.dropna(subset=["pair_id", "month", "avg_price", "item_lines"]).copy()
    df = df[(df["avg_price"] > 0) & (df["item_lines"] > 0)].copy()
    df = df.sort_values(["pair_id", "month"]).reset_index(drop=True)

    # A price change is measured between consecutive observed rows for a pair.
    # A missing month is not interpreted as a zero-sales month.
    df["previous_price"] = df.groupby("pair_id")["avg_price"].shift(1)
    df["price_change_pct"] = (
        (df["avg_price"] / df["previous_price"]) - 1
    ).abs()
    df["qualifying_price_change"] = (
        df["price_change_pct"] > MIN_PRICE_CHANGE_PCT
    ).fillna(False)

    return df


def make_pair_statistics(panel: pd.DataFrame) -> pd.DataFrame:
    stats = (
        panel.groupby("pair_id")
        .agg(
            product_id=("product_id", "first"),
            seller_id=("seller_id", "first"),
            active_months=("month", "nunique"),
            total_item_lines=("item_lines", "sum"),
            observed_months=("month", "size"),
            mean_price=("avg_price", "mean"),
            min_price=("avg_price", "min"),
            max_price=("avg_price", "max"),
            price_change_count=("qualifying_price_change", "sum"),
        )
        .reset_index()
    )
    stats["price_range_pct"] = (
        (stats["max_price"] - stats["min_price"]) / stats["mean_price"]
    )
    return stats


def cohort_panel(
    panel: pd.DataFrame, pair_stats: pd.DataFrame, thresholds: tuple[int, int, int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    min_months, min_lines, min_changes = thresholds
    eligible = pair_stats[
        (pair_stats["active_months"] >= min_months)
        & (pair_stats["total_item_lines"] >= min_lines)
        & (pair_stats["price_change_count"] >= min_changes)
    ].copy()
    subset = panel[panel["pair_id"].isin(eligible["pair_id"])].copy()
    return subset, eligible


def fit_model(
    data: pd.DataFrame,
    family: str,
    winsorize_price: bool = False,
    trim_outcome: bool = False,
) -> dict:
    d = data.copy()

    if winsorize_price:
        lo, hi = d["log_price"].quantile([WINSOR_LOWER, WINSOR_UPPER])
        d["model_log_price"] = d["log_price"].clip(lo, hi)
    else:
        d["model_log_price"] = d["log_price"]

    if trim_outcome:
        low, high = d["item_lines"].quantile([0.01, 0.99])
        d = d[(d["item_lines"] >= low) & (d["item_lines"] <= high)].copy()

    formula = "item_lines ~ model_log_price + C(pair_id) + C(month)"
    if family == "OLS_log":
        d = d[d["item_lines"] > 0].copy()
        d["item_lines"] = np.log(d["item_lines"])
        formula = "item_lines ~ model_log_price + C(pair_id) + C(month)"
        model = smf.ols(formula, data=d)
    elif family == "PPML":
        model = smf.glm(
            formula=formula,
            data=d,
            family=sm.families.Poisson(),
        )
    else:
        raise ValueError(f"Unsupported model family: {family}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = model.fit(
            cov_type="cluster",
            cov_kwds={"groups": d["pair_id"]},
            maxiter=200,
        )

    term = "model_log_price"
    coef = float(result.params[term])
    se = float(result.bse[term])
    ci = result.conf_int().loc[term]
    return {
        "model": family,
        "winsorized_price": winsorize_price,
        "trimmed_outcome_1_99": trim_outcome,
        "observations": int(result.nobs),
        "product_seller_pairs": int(d["pair_id"].nunique()),
        "calendar_months": int(d["month"].nunique()),
        "price_coefficient": coef,
        "clustered_standard_error": se,
        "ci_95_lower": float(ci.iloc[0]),
        "ci_95_upper": float(ci.iloc[1]),
        "p_value": float(result.pvalues[term]),
        "converged": bool(getattr(result, "converged", True)),
    }


def main() -> None:
    panel = load_panel(INPUT_FILE)
    pair_stats = make_pair_statistics(panel)

    cohort_rows = []
    model_rows = []
    price_diagnostics = []

    # Overall panel diagnostics.
    diagnostics = [
        ("Panel observations", len(panel)),
        ("Unique product-seller pairs", panel["pair_id"].nunique()),
        ("Calendar months", panel["month"].nunique()),
        ("Observed zero-sales rows", 0),
        ("Median item lines per panel row", float(panel["item_lines"].median())),
        ("Share of rows with one item line", float((panel["item_lines"] == 1).mean())),
        ("Median absolute observed price change", float(panel["price_change_pct"].median())),
    ]

    for cohort_name, thresholds in COHORTS.items():
        subset, eligible = cohort_panel(panel, pair_stats, thresholds)
        min_months, min_lines, min_changes = thresholds

        cohort_rows.append(
            {
                "cohort": cohort_name,
                "minimum_active_months": min_months,
                "minimum_total_item_lines": min_lines,
                "minimum_price_changes_over_1pct": min_changes,
                "product_seller_pairs": eligible["pair_id"].nunique(),
                "panel_observations": len(subset),
                "calendar_months": subset["month"].nunique(),
            }
        )

        if subset.empty:
            continue

        subset["log_price"] = np.log(subset["avg_price"])

        for family in ["OLS_log", "PPML"]:
            for winsor in [False, True]:
                for trim in ([False, True] if family == "OLS_log" else [False]):
                    row = fit_model(
                        subset,
                        family=family,
                        winsorize_price=winsor,
                        trim_outcome=trim,
                    )
                    row["cohort"] = cohort_name
                    model_rows.append(row)

        changes = eligible["price_change_count"]
        price_diagnostics.append(
            {
                "cohort": cohort_name,
                "pairs": len(eligible),
                "median_price_change_count": float(changes.median()),
                "pairs_with_2plus_changes": int((changes >= 2).sum()),
                "pairs_with_3plus_changes": int((changes >= 3).sum()),
                "median_price_range_pct": float(eligible["price_range_pct"].median()),
                "median_item_lines_per_pair": float(eligible["total_item_lines"].median()),
            }
        )

    # Explicitly reconcile the old 573-style screening number with the
    # actual cohort criteria and current panel-derived count.
    core = cohort_rows[0]
    reconciliation = pd.DataFrame(
        [
            {
                "earlier_screening_count": 573,
                "current_count_using_explicit_core_criteria": core["product_seller_pairs"],
                "difference": 573 - core["product_seller_pairs"],
                "criteria": "6+ active months, 10+ item lines, 2+ observed price changes >1%",
                "note": (
                    "The earlier screening used a different calculation or filtering "
                    "sequence. Use the count recomputed from this panel and these "
                    "explicit criteria; do not force the count to 573."
                ),
            }
        ]
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        pd.DataFrame(model_rows).to_excel(writer, sheet_name="Model Results", index=False)
        pd.DataFrame(cohort_rows).to_excel(writer, sheet_name="Cohort Comparison", index=False)
        pd.DataFrame(diagnostics, columns=["diagnostic", "value"]).to_excel(
            writer, sheet_name="Data Diagnostics", index=False
        )
        pair_stats.to_excel(writer, sheet_name="Pair Statistics", index=False)
        pd.DataFrame(price_diagnostics).to_excel(
            writer, sheet_name="Price Variation Diagnostics", index=False
        )
        reconciliation.to_excel(writer, sheet_name="Count Reconciliation", index=False)

        limitations = pd.DataFrame(
            [
                ("Interpretation", "Coefficients are conditional associations, not causal price elasticities."),
                ("Outcome", "item_lines counts order-item records, not physical units sold."),
                ("Zero-sales months", "Absent from the source panel; no zero-sales rows are created."),
                ("PPML", "Alternative count-model functional form; it does not solve missing zero-sales months or endogeneity."),
                ("Price endogeneity", "Prices may respond to demand, promotions, product mix, or other omitted factors."),
                ("Fixed effects", "Product-seller and calendar-month fixed effects control only time-invariant pair differences and common month shocks."),
                ("Inference", "Standard errors are clustered by product-seller pair."),
                ("Use in simulation", "Do not use these coefficients as validated causal demand-response parameters."),
            ],
            columns=["topic", "limitation_or_interpretation"],
        )
        limitations.to_excel(writer, sheet_name="Methodology & Limits", index=False)

    print("\nROBUSTNESS TESTS COMPLETED")
    print(f"Input rows: {len(panel):,}")
    print(f"Unique product-seller pairs: {panel['pair_id'].nunique():,}")
    print("\nCOHORT COUNTS")
    print(pd.DataFrame(cohort_rows).to_string(index=False))
    print("\nMODEL RESULTS")
    results = pd.DataFrame(model_rows)
    if not results.empty:
        print(
            results[
                [
                    "cohort",
                    "model",
                    "winsorized_price",
                    "trimmed_outcome_1_99",
                    "observations",
                    "product_seller_pairs",
                    "price_coefficient",
                    "clustered_standard_error",
                    "ci_95_lower",
                    "ci_95_upper",
                    "p_value",
                ]
            ].to_string(index=False)
        )
    print(f"\nExcel report saved to:\n{OUTPUT_FILE}")
    print(
        "\nInterpretation warning: PPML and OLS results remain conditional on "
        "observed-sales months. Do not label them causal elasticity estimates."
    )


if __name__ == "__main__":
    main()
