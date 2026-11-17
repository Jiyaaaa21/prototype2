"""
Product-wise analysis helpers (no Streamlit).

Everything here is derived from the scenario engine's own transaction tables
or from observed Olist order lines for one product.
"""
from __future__ import annotations

import pandas as pd

from config.assumptions import get_baseline_parameters
from src.scenarios.demand_response import (
    break_even_elasticity, outlay_factor, volume_multiplier,
)
from src.scenarios.effect_propagation import EffectPropagator
from src.scenarios.multi_parameter_scenario import MultiParameterScenarioEngine
from src.scenarios.product_focus import focus_on_product, _order_product_counts


def product_profile(scoped: dict) -> dict:
    """Observed facts about the scoped product (single-product orders only)."""
    items, orders = scoped["items"], scoped["orders"]
    o = orders[["order_id", "order_purchase_timestamp"]].copy()
    o["month"] = pd.to_datetime(o["order_purchase_timestamp"]).dt.to_period("M").astype(str)
    df = items.merge(o[["order_id", "month"]], on="order_id")
    nmv, freight = float(items["price"].sum()), float(items["freight_value"].sum())
    history = (df.groupby("month")
               .agg(orders=("order_id", "nunique"), avg_price=("price", "mean"))
               .reset_index())
    return {
        "orders": int(items["order_id"].nunique()),
        "item_lines": int(len(items)),
        "sellers": int(items["seller_id"].nunique()),
        "months": int(df["month"].nunique()),
        "first_month": df["month"].min(), "last_month": df["month"].max(),
        "price_min": float(items["price"].min()), "price_max": float(items["price"].max()),
        "avg_price": float(items["price"].mean()),
        "order_value": nmv + freight,
        "freight_share": freight / (nmv + freight),
        "history": history,
    }


def impact_by_seller(result: dict, m: float) -> pd.DataFrame:
    b = result["baseline"]["transactions"]
    s = result["scenario"]["transactions"]
    out = pd.DataFrame({
        "seller_id": b["seller_id"].values,
        "base_payout": b["seller_payout"].values, "scen_payout": s["seller_payout"].values * m,
        "base_commission": b["commission"].values, "scen_commission": s["commission"].values * m,
        "base_value": (b["net_merchandise_value"] + b["freight_value"]).values,
        "scen_value": (s["net_merchandise_value"] + s["freight_value"]).values * m,
    })
    g = out.groupby("seller_id", as_index=False).sum()
    g["label"] = g["seller_id"].str[:8]
    return g.sort_values("base_value", ascending=False)


def impact_by_month(result: dict, m: float) -> pd.DataFrame:
    b = result["baseline"]["transactions"]
    s = result["scenario"]["transactions"]
    out = pd.DataFrame({
        "month": b["purchase_month"].astype(str).values,
        "baseline": (b["net_merchandise_value"] + b["freight_value"]).values,
        "scenario": (s["net_merchandise_value"] + s["freight_value"]).values * m,
    })
    return out.groupby("month", as_index=False).sum().sort_values("month")


def run_product_scenario(scoped: dict, scenario_params: dict, elasticity: float):
    """Engine + propagation for one scoped dataset. Returns (result, factor, m, chain)."""
    base = get_baseline_parameters()
    engine = MultiParameterScenarioEngine(
        scoped["products"], scoped["items"], scoped["orders"], scoped["customers"],
        scoped["translation"], base, scenario_params)
    result = engine.run()
    if result["status"] != "success":
        raise ValueError("Scenario engine validation failed.")
    f = outlay_factor(result["baseline"]["summary"], result["scenario"]["summary"])
    m = volume_multiplier(f, elasticity)
    chain = EffectPropagator(result, scoped["payments"], m).propagate()
    return result, f, m, chain


def portfolio_comparison(data: dict, candidates: pd.DataFrame, scenario_params: dict,
                         elasticity: float) -> pd.DataFrame:
    """The same scenario applied to each candidate product separately."""
    n_prod = _order_product_counts(data["items"])
    rows = []
    for pid, info in candidates.iterrows():
        scoped, scope = focus_on_product(data, pid, n_prod)
        result, f, m, chain = run_product_scenario(scoped, scenario_params, elasticity)
        steps = {s["stage"]: s for st in chain["stages"] for s in st["steps"]}
        ov = steps["Order value (all orders with items)"]
        cm = steps["Platform commission"]
        bs, ss = result["baseline"]["summary"], result["scenario"]["summary"]
        ratio = ss["commission"] / bs["commission"] if bs["commission"] > 0 else 0.0
        rows.append({
            "product_id": pid, "category": info["category"],
            "orders": scope["orders_in_scope"], "sellers": scope["sellers"],
            "outlay_factor": f, "volume_multiplier": m,
            "base_order_value": ov["baseline"], "scen_order_value": ov["scenario"],
            "order_value_change": ov["change"],
            "order_value_pct": ov["change"] / ov["baseline"] * 100,
            "commission_change": cm["change"],
            "commission_break_even": break_even_elasticity(ratio, f),
        })
    return (pd.DataFrame(rows)
            .sort_values("order_value_change", key=lambda s: s.abs(), ascending=False)
            .reset_index(drop=True))
