
import pandas as pd

from src.simulation.monthly_state_payload_builder import (
    MonthlyStatePayloadBuilder
)


def build_test_states():
    months = ["2016-09", "2016-10"]

    return {
        "customer": pd.DataFrame({
            "purchase_month": months,
            "total_orders": [10, 20],
            "average_order_value": [100.0, 120.0]
        }),

        "product": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "product_id": ["P1"],
            "item_line_count": [5]
        }),

        "category": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "category_english": ["electronics"],
            "item_line_count": [5]
        }),

        "seller": pd.DataFrame({
            "purchase_month": ["2016-09"],
            "seller_id": ["S1"],
            "item_line_count": [5]
        }),

        "order_sales": pd.DataFrame({
            "purchase_month": months,
            "order_count": [10, 20],
            "merchandise_value": [1000.0, 2400.0]
        }),

        "payment_revenue": pd.DataFrame({
            "purchase_month": months,
            "total_payment_value": [1100.0, 2600.0]
        }),

        "delivery_experience": pd.DataFrame({
            "purchase_month": months,
            "total_orders": [10, 20],
            "average_review_score": [4.5, 4.2]
        })
    }


def main():
    states = build_test_states()
    original_states = {
        name: frame.copy(deep=True)
        for name, frame in states.items()
    }

    builder = MonthlyStatePayloadBuilder(states)

    # Test 1: Six component payloads.
    september = builder.build("2016-09")

    assert len(september) == 6
    assert set(september) == builder.COMPONENT_KEYS

    print("Six-component payload structure: PASSED")

    # Test 2: Summary extraction.
    assert september["customer_management"]["summary"][
        "total_orders"
    ] == 10

    assert september["order_sales_management"]["summary"][
        "merchandise_value"
    ] == 1000.0

    print("Monthly summary extraction: PASSED")

    # Test 3: Product and category grouping.
    product_payload = september["product_management"]

    assert len(product_payload["products"]) == 1
    assert len(product_payload["categories"]) == 1

    print("Product and category grouping: PASSED")

    # Test 4: Sparse state preservation.
    october = builder.build("2016-10")

    assert october["product_management"]["products"] == []
    assert october["product_management"]["categories"] == []
    assert october["seller_management"]["sellers"] == []

    print("Sparse entity-state preservation: PASSED")

    # Test 5: No fabricated entity records.
    assert october["product_management"]["products"] == []
    assert october["seller_management"]["sellers"] == []

    print("No fabricated entity records: PASSED")

    # Test 6: Timeline validation.
    assert builder.get_timeline() == [
        "2016-09",
        "2016-10"
    ]

    print("Timeline validation: PASSED")

    # Test 7: Input isolation.
    for name in states:
        pd.testing.assert_frame_equal(
            states[name],
            original_states[name]
        )

    september["customer_management"]["summary"]["total_orders"] = 999

    assert builder.build("2016-09")[
        "customer_management"
    ]["summary"]["total_orders"] == 10

    print("Input and payload isolation: PASSED")

    # Test 8: Invalid month.
    try:
        builder.build("2016-11")
        raise AssertionError("Invalid month was accepted.")
    except ValueError:
        pass

    print("Invalid month rejection: PASSED")

    print("\nALL MONTHLY PAYLOAD BUILDER TESTS PASSED.")


if __name__ == "__main__":
    main()
