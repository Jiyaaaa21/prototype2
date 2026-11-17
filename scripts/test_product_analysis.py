"""
Product-wise analysis test on real data.
Run from repo root:  python -m scripts.test_product_analysis
"""
from scripts.test_effect_propagation import load
from config.assumptions import get_baseline_parameters
from src.scenarios.product_analysis import (
    impact_by_month, impact_by_seller, portfolio_comparison, product_profile,
    run_product_scenario,
)
from src.scenarios.product_focus import focus_on_product, product_candidates

PRODUCT = "53b36df67ebb7c41585e8d54d6772e08"
results = []


def check(name, cond):
    results.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def main():
    products, items, orders, customers, trans, payments = load()
    data = dict(products=products, items=items, orders=orders, customers=customers,
                translation=trans, payments=payments)
    scoped, info = focus_on_product(data, PRODUCT)
    base = get_baseline_parameters()
    params = {**base, "product_price_adjustment": 0.10}

    prof = product_profile(scoped)
    print(f"profile: {prof['orders']} orders, {prof['sellers']} sellers, "
          f"order value {prof['order_value']:,.2f}, freight share {prof['freight_share']:.1%}")
    check("profile orders = scope orders", prof["orders"] == info["orders_in_scope"])
    check("profile sellers = scope sellers", prof["sellers"] == info["sellers"])
    check("history orders sum to profile orders", prof["history"]["orders"].sum() == prof["orders"])

    result, f, m, chain = run_product_scenario(scoped, params, -1.0)
    bs, ss = result["baseline"]["summary"], result["scenario"]["summary"]
    sellers = impact_by_seller(result, m)
    months = impact_by_month(result, m)
    check("seller baseline payouts sum to total", abs(sellers["base_payout"].sum() - bs["seller_payout"]) < 0.01)
    check("seller scenario payouts sum to multiplier x total",
          abs(sellers["scen_payout"].sum() - m * ss["seller_payout"]) < 0.01)
    check("monthly baseline sums to baseline outlay",
          abs(months["baseline"].sum() - (bs["net_merchandise_value"] + bs["freight_value"])) < 0.01)
    check("monthly scenario sums to multiplier x scenario outlay",
          abs(months["scenario"].sum() - m * (ss["net_merchandise_value"] + ss["freight_value"])) < 0.01)
    check("profile order value = baseline outlay",
          abs(prof["order_value"] - (bs["net_merchandise_value"] + bs["freight_value"])) < 0.01)

    cands = product_candidates(items, orders, products, trans).head(5)
    pf = portfolio_comparison(data, cands, params, 0.0)
    print(pf[["category", "orders", "base_order_value", "order_value_pct"]].to_string())
    check("portfolio has one row per product", len(pf) == len(cands))
    check("sorted by absolute change", pf["order_value_change"].abs().is_monotonic_decreasing)
    check("price +10% at constant volume: change % < 10% (freight does not rise)",
          ((pf["order_value_pct"] > 0) & (pf["order_value_pct"] < 10)).all())
    if PRODUCT in set(pf["product_id"]):
        row = pf[pf["product_id"] == PRODUCT].iloc[0]
        check("portfolio row matches the single-product run",
              abs(row["base_order_value"] - prof["order_value"]) < 0.01)

    print("\nPRODUCT ANALYSIS VERIFIED" if all(results) else "\nPRODUCT ANALYSIS FAILED")


if __name__ == "__main__":
    main()
