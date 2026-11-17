"""
Checkpoint 6c test: single-product focus on real data.
Run from repo root:  python -m scripts.test_product_focus
"""
from config.assumptions import get_baseline_parameters
from scripts.test_effect_propagation import load
from src.scenarios.effect_propagation import EffectPropagator
from src.scenarios.multi_parameter_scenario import MultiParameterScenarioEngine
from src.scenarios.product_focus import focus_on_product, product_candidates

PRODUCT = "53b36df67ebb7c41585e8d54d6772e08"   # watches_gifts, 3 sellers
results = []


def check(name, cond):
    results.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def run(scoped, params):
    base = get_baseline_parameters()
    eng = MultiParameterScenarioEngine(
        scoped["products"], scoped["items"], scoped["orders"],
        scoped["customers"], scoped["translation"], base, {**base, **params})
    res = eng.run()
    return res, EffectPropagator(res, scoped["payments"]).propagate()


def step(chain, name):
    return {s["stage"]: s for st in chain["stages"] for s in st["steps"]}[name]


def main():
    products, items, orders, customers, trans, payments = load()
    data = dict(products=products, items=items, orders=orders,
                customers=customers, translation=trans, payments=payments)

    cands = product_candidates(items, orders, products, trans)
    check(f"candidates found (>=100 single-product orders): {len(cands)}", len(cands) > 0)
    check("selected product is a candidate", PRODUCT in cands.index)

    n_items_before, n_orders_before = len(items), len(orders)
    scoped, info = focus_on_product(data, PRODUCT)
    print(f"\nScope: {info['orders_in_scope']} of {info['orders_total']} orders "
          f"({info['scope_share']:.1%}), {info['lines_in_scope']} of "
          f"{info['lines_total']} item lines, {info['sellers']} sellers")
    check("every in-scope line is the chosen product",
          (scoped["items"]["product_id"] == PRODUCT).all())
    check("in-scope orders contain only this product",
          scoped["items"].groupby("order_id")["product_id"].nunique().eq(1).all())
    check("original datasets untouched",
          len(items) == n_items_before and len(orders) == n_orders_before)

    res, chain = run(scoped, {})
    print("\nNEUTRAL baseline for this product:")
    for nm in ["Net merchandise value", "Freight", "Platform commission",
               "Order value (all orders with items)", "Orders",
               "Customer payments, orders with a payment record"]:
        print(f"  {nm}: {step(chain, nm)['baseline']:,.2f}")
    check("neutral run: all checks pass", all(p for _, p in chain["checks"]))
    nv = step(chain, "Order value (all orders with items)")["baseline"]
    pay = step(chain, "Customer payments, orders with a payment record")["baseline"]
    check("product order value reconciles to recorded payments (within R$1)",
          abs(nv - pay) <= 1.0)
    check("orders in scope = engine orders", step(chain, "Orders")["baseline"]
          == info["orders_in_scope"])

    res2, chain2 = run(scoped, {"product_price_adjustment": 0.10})
    nmv_b = step(chain2, "Net merchandise value")["baseline"]
    nmv_s = step(chain2, "Net merchandise value")["scenario"]
    check("price +10%: merchandise value rises exactly 10%",
          abs(nmv_s / nmv_b - 1.10) < 1e-9)
    check("price +10%: all reconciliation checks pass",
          all(p for _, p in chain2["checks"]))

    print("\nCHECKPOINT 6c VERIFIED" if all(results) else "\nCHECKPOINT 6c FAILED")


if __name__ == "__main__":
    main()
