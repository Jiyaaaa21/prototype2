"""
Checkpoint 2 test: effect propagation on real Olist data.
Run from repo root:  python -m scripts.test_effect_propagation
"""
import pandas as pd

from config.assumptions import get_baseline_parameters
from src.scenarios.multi_parameter_scenario import MultiParameterScenarioEngine
from src.scenarios.effect_propagation import EffectPropagator

D = "data/raw/olist"


def load():
    r = lambda f: pd.read_csv(f"{D}/{f}")
    return (r("olist_products_dataset.csv"), r("olist_order_items_dataset.csv"),
            r("olist_orders_dataset.csv"), r("olist_customers_dataset.csv"),
            r("product_category_name_translation.csv"),
            r("olist_order_payments_dataset.csv"))


def run(products, items, orders, customers, trans, payments, scenario):
    base = get_baseline_parameters()
    scen = {**base, **scenario}
    eng = MultiParameterScenarioEngine(products, items, orders, customers, trans, base, scen)
    return EffectPropagator(eng.run(), payments).propagate()


def show(title, out):
    print(f"\n=== {title} ===")
    for st in out["stages"]:
        print(f"\n{st['stage']}")
        for s in st["steps"]:
            if s["baseline"] is None:
                print(f"  - {s['stage']}: {s['formula']}")
            else:
                print(f"  - {s['stage']}: {s['baseline']:,.2f} -> {s['scenario']:,.2f} "
                      f"(change {s['change']:+,.2f})")
    for name, passed in out["checks"]:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")


def main():
    *eng_data, payments = load()
    all_ok = True

    neutral = run(*eng_data, payments, {})
    show("NEUTRAL (scenario = baseline)", neutral)
    zero = all(abs(s["change"]) < 0.01 for st in neutral["stages"] for s in st["steps"])
    print(f"[{'PASS' if zero else 'FAIL'}] Neutral run: every change is zero")
    all_ok &= zero and all(p for _, p in neutral["checks"])

    combo = run(*eng_data, payments, {"product_price_adjustment": 0.10,
                                      "commission_rate": 0.21,
                                      "freight_adjustment": 0.05})
    show("COMBINED: price +10%, commission 21%, freight +5%", combo)
    all_ok &= all(p for _, p in combo["checks"])

    print("\nCHECKPOINT 2 VERIFIED" if all_ok else "\nCHECKPOINT 2 FAILED")


if __name__ == "__main__":
    main()
