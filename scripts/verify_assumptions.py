"""Checkpoint 1 verification: assumption register vs engine, scripts and Olist data."""

import math

import pandas as pd

import config.settings as settings
from config.assumptions import (
    ASSUMPTIONS,
    IBGE_PAC_RETAIL_MARGIN_RATE,
    cost_to_sales_from_margin_rate,
    get_baseline_parameters,
    unverified_parameters,
)
from scripts.run_price_sensitivity_analysis import BASELINE_PARAMETERS
from src.scenarios.multi_parameter_scenario import MultiParameterScenarioEngine


def check(name, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {name} {detail}")
    if not condition:
        raise AssertionError(name)


def main():
    baseline = get_baseline_parameters()

    check("Register covers exactly the engine's 5 parameters",
          set(ASSUMPTIONS) == MultiParameterScenarioEngine.REQUIRED_PARAMETERS)

    MultiParameterScenarioEngine._validate_parameters(baseline, "baseline")
    check("Register baseline passes engine validation", True)

    expected_cost = 1 / (1 + IBGE_PAC_RETAIL_MARGIN_RATE[2018])
    check("Seller cost = 1/(1+0.376)",
          math.isclose(baseline["seller_cost_rate"], expected_cost, rel_tol=1e-12),
          f"({baseline['seller_cost_rate']:.6f})")

    for key, value in baseline.items():
        check(f"Sensitivity script baseline matches register: {key}",
              math.isclose(BASELINE_PARAMETERS[key], value, rel_tol=1e-9, abs_tol=1e-12))

    check("No conflicting COMMISSION_RATE left in config/settings.py",
          not hasattr(settings, "COMMISSION_RATE"))

    # Data evidence behind discount baseline = 0
    d = settings.DATA_DIR
    items = pd.read_csv(d / "olist_order_items_dataset.csv")
    pay = pd.read_csv(d / "olist_order_payments_dataset.csv")
    by_order = items.groupby("order_id").agg(price=("price", "sum"), freight=("freight_value", "sum"))
    by_order["paid"] = pay.groupby("order_id")["payment_value"].sum()
    by_order = by_order.dropna()
    share = ((by_order["paid"] - by_order["price"] - by_order["freight"]).abs() <= 0.01).mean()
    check("Discount baseline 0 supported: payments reconcile to price+freight",
          share >= 0.99, f"({share:.2%} of {len(by_order):,} orders)")

    # Engine applies commission to net merchandise value only (freight excluded).
    tiny = MultiParameterScenarioEngine._calculate_financials(
        pd.DataFrame({"historical_price": [100.0], "historical_freight": [20.0]}),
        {**baseline, "product_price_adjustment": 0.0},
    )
    check("Engine commission base excludes freight",
          math.isclose(float(tiny["commission"].iloc[0]), 100.0 * baseline["commission_rate"]),
          f"(commission={float(tiny['commission'].iloc[0]):.2f} on price 100, freight 20)")

    print("\nASSUMPTION REGISTER")
    print("-" * 78)
    for key, a in ASSUMPTIONS.items():
        rng = f"{a.evidence_range[0]:.4f}-{a.evidence_range[1]:.4f}" if a.evidence_range else "n/a"
        print(f"{key:26s} {a.baseline:8.4f}  {a.status:20s} range: {rng}")
    print("-" * 78)
    unverified = unverified_parameters()
    print("Unverified parameters:", ", ".join(unverified) if unverified else "none")
    print("Open caveats on commission:", len(ASSUMPTIONS["commission_rate"].caveats))
    print("\nCHECKPOINT 1 VERIFIED")


if __name__ == "__main__":
    main()
