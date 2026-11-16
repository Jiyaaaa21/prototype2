
import pandas as pd

from config.settings import DATA_DIR
from src.scenarios.product_price_scenario import (
    ProductPriceScenarioEngine
)


def load_datasets():
    files = {
        "customers": "olist_customers_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "items": "olist_order_items_dataset.csv",
        "products": "olist_products_dataset.csv",
        "translation": "product_category_name_translation.csv"
    }

    return {
        name: pd.read_csv(DATA_DIR / filename)
        for name, filename in files.items()
    }


def check_close(actual, expected, label):
    assert abs(float(actual) - float(expected)) < 0.01, (
        f"{label} mismatch: actual={actual}, expected={expected}"
    )


def main():

    print("\nLOADING OLIST DATASETS")
    data = load_datasets()
    print("Datasets loaded.")

    # Preserve original data for immutability checks.
    original_items = data["items"].copy(deep=True)
    original_products = data["products"].copy(deep=True)
    original_orders = data["orders"].copy(deep=True)
    original_customers = data["customers"].copy(deep=True)

    print("\nINITIALIZING PRODUCT PRICE SCENARIO")

    engine = ProductPriceScenarioEngine(
        products=data["products"],
        order_items=data["items"],
        orders=data["orders"],
        customers=data["customers"],
        category_translation=data["translation"],
        adjustment_rate=0.05
    )

    print("Scenario initialized.")

    print("\nEXECUTING SCENARIO")
    results = engine.run()

    summary = results["summary"]
    baseline = results["baseline"]
    scenario = results["scenario"]
    impact = results["impact"]

    print("Scenario executed successfully.")

    # --------------------------------------------------
    # 1. SCENARIO CONFIGURATION
    # --------------------------------------------------

    print("\nSCENARIO CONFIGURATION")
    print("-" * 60)

    assert summary["scenario_id"] == "SCN-001"
    assert summary["adjustment_percentage"] == 5.0
    assert summary["historical_data_modified"] is False
    assert summary["demand_response_modelled"] is False

    print("Scenario ID:", summary["scenario_id"])
    print("Price adjustment:", summary["adjustment_percentage"], "%")
    print("Quantity assumption:", summary["quantity_assumption"])

    # --------------------------------------------------
    # 2. PRODUCT SCOPE VALIDATION
    # --------------------------------------------------

    print("\nPRODUCT SCOPE VALIDATION")
    print("-" * 60)

    sold_products = set(original_items["product_id"].unique())
    catalogue_products = set(original_products["product_id"].unique())

    assert summary["products_with_historical_sales"] == len(
        sold_products
    )

    assert summary["products_without_historical_sales"] == (
        len(catalogue_products - sold_products)
    )

    print("Catalogue products:", len(catalogue_products))
    print("Products with historical sales:", len(sold_products))
    print(
        "Products without historical sales:",
        len(catalogue_products - sold_products)
    )

    # --------------------------------------------------
    # 3. PRICE ADJUSTMENT VALIDATION
    # --------------------------------------------------

    print("\nPRICE ADJUSTMENT VALIDATION")
    print("-" * 60)

    expected_total = (
        pd.to_numeric(original_items["price"]).sum() * 1.05
    )

    actual_total = scenario["order"]["merchandise_value"].sum()

    check_close(
        actual_total,
        expected_total,
        "Adjusted merchandise value"
    )

    check_close(
        summary["merchandise_value_change"],
        expected_total - pd.to_numeric(
            original_items["price"]
        ).sum(),
        "Merchandise value change"
    )

    print("Baseline merchandise value:",
          round(pd.to_numeric(original_items["price"]).sum(), 2))

    print("Scenario merchandise value:", round(actual_total, 2))

    print(
        "Merchandise value increase:",
        round(summary["merchandise_value_change"], 2)
    )

    # --------------------------------------------------
    # 4. QUANTITY AND FREIGHT VALIDATION
    # --------------------------------------------------

    print("\nQUANTITY AND FREIGHT VALIDATION")
    print("-" * 60)

    assert len(original_items) == len(
        data["items"]
    )

    check_close(
        scenario["order"]["freight_value"].sum(),
        pd.to_numeric(original_items["freight_value"]).sum(),
        "Freight value"
    )

    check_close(
        scenario["order"]["item_line_count"].sum(),
        len(original_items),
        "Item line count"
    )

    print("Item line count unchanged.")
    print("Freight value unchanged.")

    # --------------------------------------------------
    # 5. CROSS-COMPONENT RECONCILIATION
    # --------------------------------------------------

    print("\nCROSS-COMPONENT RECONCILIATION")
    print("-" * 60)

    total_change = summary["merchandise_value_change"]

    for component in [
        "product",
        "category",
        "seller",
        "customer",
        "order",
        "monthly"
    ]:

        change = impact[component][
            "merchandise_value_change"
        ].sum()

        check_close(
            change,
            total_change,
            f"{component} impact reconciliation"
        )

        print(f"{component}: reconciled.")

    # --------------------------------------------------
    # 6. BASELINE VS SCENARIO INVARIANTS
    # --------------------------------------------------

    print("\nBASELINE VS SCENARIO INVARIANTS")
    print("-" * 60)

    for component in [
        "product",
        "category",
        "seller",
        "customer",
        "order",
        "monthly"
    ]:

        base = baseline[component]
        changed = scenario[component]

        assert base["item_line_count"].sum() == (
            changed["item_line_count"].sum()
        ), f"{component}: item line count changed."

        assert base["distinct_orders"].sum() == (
            changed["distinct_orders"].sum()
        ), f"{component}: distinct order count changed."

        check_close(
            base["freight_value"].sum(),
            changed["freight_value"].sum(),
            f"{component} freight"
        )

    print("All quantity and freight invariants passed.")

    # --------------------------------------------------
    # 7. SOURCE DATA IMMUTABILITY
    # --------------------------------------------------

    print("\nSOURCE DATA IMMUTABILITY")
    print("-" * 60)

    pd.testing.assert_frame_equal(
        data["items"], original_items
    )

    pd.testing.assert_frame_equal(
        data["products"], original_products
    )

    pd.testing.assert_frame_equal(
        data["orders"], original_orders
    )

    pd.testing.assert_frame_equal(
        data["customers"], original_customers
    )

    print("All original source DataFrames remain unchanged.")

    # --------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------

    print("\nSCENARIO SUMMARY")
    print("=" * 60)

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nALL PRODUCT PRICE SCENARIO TESTS PASSED.")


if __name__ == "__main__":
    main()
