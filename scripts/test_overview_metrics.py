"""
Checkpoint 7 test: Business Overview metrics on real Olist data.
Run from repo root:  python -m scripts.test_overview_metrics
"""
from scripts.test_monthly_state_alignment_integration import load_datasets
from src.dashboard.overview_metrics import compute_overview

results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def main():
    data = load_datasets()
    m = compute_overview(data)
    k = m["kpis"]
    print(f"revenue={k['revenue']:,.2f} orders={k['orders']:,} customers={k['customers']:,} "
          f"sellers={k['sellers']:,} aov={k['aov']:.2f}")
    print(f"delivered={k['delivered_orders']:,} on_time={k['on_time_rate']:.3%} "
          f"days={k['avg_delivery_days']:.2f} top10%={k['top10pct_sellers_share']:.3%}")
    print(f"review on-time={k['review_on_time']:.2f} late={k['review_late']:.2f}")

    check("orders = 99,441", k["orders"] == 99441)
    check("customers = 96,096", k["customers"] == 96096)
    check("sellers = 3,095", k["sellers"] == 3095)
    check("revenue = items + freight = 15,843,553.24", abs(k["revenue"] - 15843553.24) < 0.01)
    check("merchandise = 13,591,643.70", abs(k["merchandise"] - 13591643.70) < 0.01)
    check("orders with items = 98,666", k["orders_with_items"] == 98666)
    check("about 8% of delivered orders late (profile: 8.1%)",
          0.07 < 1 - k["on_time_rate"] < 0.09)
    check("mean delivery about 12 days (profile: 12.1)", 11.5 < k["avg_delivery_days"] < 12.7)
    check("top 10% of sellers earn about 67.5% (profile)",
          abs(k["top10pct_sellers_share"] - 0.675) < 0.01)
    check("reviews lower when late than on time", k["review_late"] < k["review_on_time"])
    check("monthly revenue sums to total revenue",
          abs(m["monthly"]["revenue"].sum() - k["revenue"]) < 0.01)
    check("category list has 10 rows", len(m["category"]) == 10)
    check("payment shares sum to recorded payments",
          abs(m["payment_types"]["payment_value"].sum()
              - data["payments"].loc[data["payments"]["payment_type"] != "not_defined",
                                     "payment_value"].sum()) < 0.01)
    print("\nCHECKPOINT 7 VERIFIED" if all(results) else "\nCHECKPOINT 7 FAILED")


if __name__ == "__main__":
    main()
