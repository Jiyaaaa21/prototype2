"""
Demand-response test (customer outlay = price + freight).
Run from repo root:  python -m scripts.test_demand_response
"""
import math

from config.assumptions import get_baseline_parameters
from scripts.test_effect_propagation import load
from src.scenarios.demand_response import (
    break_even_elasticity, outlay_factor, volume_multiplier,
)
from src.scenarios.effect_propagation import EffectPropagator
from src.scenarios.multi_parameter_scenario import MultiParameterScenarioEngine

results = []


def check(name, cond):
    results.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def step(out, name):
    return {s["stage"]: s for st in out["stages"] for s in st["steps"]}[name]


def run(tables, params):
    products, items, orders, customers, trans, _ = tables
    base = get_baseline_parameters()
    return MultiParameterScenarioEngine(
        products, items, orders, customers, trans, base, {**base, **params}).run()


def main():
    tables = load()
    payments = tables[5]

    res = run(tables, {"product_price_adjustment": 0.10})
    bs, ss = res["baseline"]["summary"], res["scenario"]["summary"]
    N, F = bs["net_merchandise_value"], bs["freight_value"]

    f = outlay_factor(bs, ss)
    check("outlay factor = (1.1 N + F) / (N + F)", abs(f - (1.1 * N + F) / (N + F)) < 1e-12)
    check("elasticity 0 gives multiplier 1", volume_multiplier(f, 0.0) == 1.0)

    base_out = EffectPropagator(res, payments).propagate()
    zero_out = EffectPropagator(res, payments, volume_multiplier(f, 0.0)).propagate()
    check("elasticity 0 reproduces the constant-volume results", all(
        abs(a["scenario"] - b["scenario"]) < 1e-6
        for sa, sb in zip(base_out["stages"], zero_out["stages"])
        for a, b in zip(sa["steps"], sb["steps"]) if a["scenario"] is not None))

    m = volume_multiplier(f, -1.0)
    check("elasticity -1: multiplier = 1 / outlay factor", abs(m - 1 / f) < 1e-12)
    out = EffectPropagator(res, payments, m).propagate()
    check("scenario merchandise = multiplier x constant-volume value",
          abs(step(out, "Net merchandise value")["scenario"] - m * ss["net_merchandise_value"]) < 0.01)
    check("customer outlay unchanged at elasticity -1 (unit elasticity)",
          abs(step(out, "Order value (all orders with items)")["change"]) < 0.01)
    check("orders scale with the multiplier",
          abs(step(out, "Orders")["scenario"] - step(out, "Orders")["baseline"] * m) < 1e-6)
    check("all reconciliation checks pass with volume response",
          all(p for _, p in out["checks"]))

    ratio = ss["commission"] / bs["commission"]
    e_star = break_even_elasticity(ratio, f)
    be = EffectPropagator(res, payments, volume_multiplier(f, e_star)).propagate()
    check(f"commission break-even elasticity {e_star:.4f}: change ~ 0",
          abs(step(be, "Platform commission")["change"]) < 0.01)

    fres = run(tables, {"freight_adjustment": 0.20})
    f2 = outlay_factor(fres["baseline"]["summary"], fres["scenario"]["summary"])
    check("freight-only change moves customer outlay: f = (N + 1.2 F) / (N + F)",
          abs(f2 - (N + 1.2 * F) / (N + F)) < 1e-12 and f2 > 1)

    for label, fn in [("positive elasticity rejected", lambda: volume_multiplier(1.1, 0.5)),
                      ("non-positive outlay factor rejected", lambda: volume_multiplier(-1.0, -1.0))]:
        try:
            fn(); check(label, False)
        except ValueError:
            check(label, True)
    check("no break-even when outlay is unchanged", break_even_elasticity(1.2, 1.0) is None)

    print("\nDEMAND RESPONSE VERIFIED" if all(results) else "\nDEMAND RESPONSE FAILED")


if __name__ == "__main__":
    main()
