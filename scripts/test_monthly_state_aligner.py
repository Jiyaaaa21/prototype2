
import pandas as pd

from src.simulation.monthly_state_aligner import MonthlyStateAligner


def build_aligner():
    timeline = pd.period_range(
        "2016-09",
        "2016-12",
        freq="M"
    )

    specifications = {
        "customer": {
            "entity_keys": [],
            "zero_fill_columns": [
                "total_orders",
                "active_customers",
                "merchandise_spend"
            ]
        },
        "product": {
            "entity_keys": ["product_id"],
            "zero_fill_columns": []
        },
        "delivery": {
            "entity_keys": [],
            "zero_fill_columns": [
                "total_orders",
                "late_orders"
            ]
        }
    }

    return MonthlyStateAligner(timeline, specifications)


def test_summary_alignment():
    aligner = build_aligner()

    states = {
        "customer": pd.DataFrame({
            "purchase_month": ["2016-09", "2016-11"],
            "total_orders": [10, 20],
            "active_customers": [8, 15],
            "merchandise_spend": [1000.0, 2000.0],
            "average_order_value": [100.0, 100.0]
        }),
        "product": pd.DataFrame({
            "purchase_month": ["2016-09", "2016-11"],
            "product_id": ["P1", "P1"],
            "item_line_count": [5, 7]
        }),
        "delivery": pd.DataFrame({
            "purchase_month": ["2016-09", "2016-11"],
            "total_orders": [10, 20],
            "late_orders": [2, 4],
            "average_delivery_duration_days": [12.0, 14.0]
        })
    }

    result = aligner.align(states)

    customer = result["customer"]

    assert customer["purchase_month"].tolist() == [
        "2016-09", "2016-10", "2016-11", "2016-12"
    ]

    october = customer.loc[
        customer["purchase_month"] == "2016-10"
    ].iloc[0]

    assert october["total_orders"] == 0
    assert october["active_customers"] == 0
    assert october["merchandise_spend"] == 0
    assert pd.isna(october["average_order_value"])

    delivery = result["delivery"]

    october_delivery = delivery.loc[
        delivery["purchase_month"] == "2016-10"
    ].iloc[0]

    assert october_delivery["total_orders"] == 0
    assert october_delivery["late_orders"] == 0
    assert pd.isna(
        october_delivery["average_delivery_duration_days"]
    )

    print("Summary alignment: PASSED")


def test_sparse_entity_state():
    aligner = build_aligner()

    states = {
        "customer": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "total_orders": [10],
            "active_customers": [8],
            "merchandise_spend": [1000.0]
        }),
        "product": pd.DataFrame({
            "purchase_month": ["2016-09", "2016-11"],
            "product_id": ["P1", "P2"],
            "item_line_count": [5, 7]
        }),
        "delivery": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "total_orders": [10],
            "late_orders": [2]
        })
    }

    result = aligner.align(states)

    product = result["product"]

    assert len(product) == 2
    assert product["product_id"].tolist() == ["P1", "P2"]
    assert "2016-10" not in product["purchase_month"].tolist()

    print("Sparse entity state preservation: PASSED")


def test_input_isolation():
    aligner = build_aligner()

    states = {
        "customer": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "total_orders": [10],
            "active_customers": [8],
            "merchandise_spend": [1000.0]
        }),
        "product": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "product_id": ["P1"],
            "item_line_count": [5]
        }),
        "delivery": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "total_orders": [10],
            "late_orders": [2]
        })
    }

    original = states["customer"].copy(deep=True)
    result = aligner.align(states)

    result["customer"].loc[0, "total_orders"] = 999

    pd.testing.assert_frame_equal(states["customer"], original)

    print("Input and output isolation: PASSED")


def test_duplicate_month_rejected():
    aligner = build_aligner()

    states = {
        "customer": pd.DataFrame({
            "purchase_month": ["2016-09", "2016-09"],
            "total_orders": [10, 11],
            "active_customers": [8, 9],
            "merchandise_spend": [1000.0, 1100.0]
        }),
        "product": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "product_id": ["P1"],
            "item_line_count": [5]
        }),
        "delivery": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "total_orders": [10],
            "late_orders": [2]
        })
    }

    try:
        aligner.align(states)
    except ValueError as exc:
        assert "duplicate records" in str(exc)
    else:
        raise AssertionError("Duplicate monthly records were not rejected.")

    print("Duplicate key validation: PASSED")


def test_outside_timeline_rejected():
    aligner = build_aligner()

    states = {
        "customer": pd.DataFrame({
            "purchase_month": ["2017-01"],
            "total_orders": [10],
            "active_customers": [8],
            "merchandise_spend": [1000.0]
        }),
        "product": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "product_id": ["P1"],
            "item_line_count": [5]
        }),
        "delivery": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "total_orders": [10],
            "late_orders": [2]
        })
    }

    try:
        aligner.align(states)
    except ValueError as exc:
        assert "outside simulation timeline" in str(exc)
    else:
        raise AssertionError("Out-of-range month was not rejected.")

    print("Timeline boundary validation: PASSED")


if __name__ == "__main__":
    test_summary_alignment()
    test_sparse_entity_state()
    test_input_isolation()
    test_duplicate_month_rejected()
    test_outside_timeline_rejected()

    print("\nALL MONTHLY STATE ALIGNER TESTS PASSED.")
