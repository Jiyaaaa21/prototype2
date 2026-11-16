
import sys
import json
from pathlib import Path
import numpy as np

import pandas as pd

# --------------------------------------------------
# PROJECT IMPORT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR

from src.components.seller_component import SellerComponent
from src.components.customer_component import CustomerComponent
from src.components.product_component import ProductComponent
from src.components.order_sales_component import OrderSalesComponent
from src.components.payment_component import PaymentComponent
from src.components.delivery_component import DeliveryComponent


# --------------------------------------------------
# LOAD DATASETS
# --------------------------------------------------

def load_datasets():
    """Load all required Olist source datasets."""

    return {
        "customers": pd.read_csv(
            DATA_DIR / "olist_customers_dataset.csv"
        ),
        "orders": pd.read_csv(
            DATA_DIR / "olist_orders_dataset.csv"
        ),
        "order_items": pd.read_csv(
            DATA_DIR / "olist_order_items_dataset.csv"
        ),
        "sellers": pd.read_csv(
            DATA_DIR / "olist_sellers_dataset.csv"
        ),
        "products": pd.read_csv(
            DATA_DIR / "olist_products_dataset.csv"
        ),
        "category_translation": pd.read_csv(
            DATA_DIR / "product_category_name_translation.csv"
        ),
        "payments": pd.read_csv(
            DATA_DIR / "olist_order_payments_dataset.csv"
        ),
        "reviews": pd.read_csv(
            DATA_DIR / "olist_order_reviews_dataset.csv"
        ),
    }


# --------------------------------------------------
# BUSINESS RULE VALIDATION
# --------------------------------------------------

def validate_business_rules(component_name, rules):
    """
    Validate business-rule result structures.

    Different components may use different rule schemas.
    Recognized pass/fail fields are checked without
    assuming every component uses the same field names.
    """

    if not isinstance(rules, list):
        raise AssertionError(
            f"{component_name}: business_rule_results must be a list."
        )

    if not rules:
        print(
            f"WARNING: {component_name} has no explicit "
            "business-rule results."
        )
        return

    recognized_boolean_fields = {
        "passed",
        "success",
        "is_valid",
        "valid",
    }

    recognized_status_fields = {
        "status",
        "result",
        "validation_status",
        "execution_status",
    }

    failure_values = {
        "FAIL",
        "FAILED",
        "FAILURE",
        "ERROR",
        "INVALID",
    }

    checked_rules = 0
    unrecognized_rules = 0

    for index, rule in enumerate(rules, start=1):

        assert isinstance(rule, dict), (
            f"{component_name}: rule {index} must be a dictionary."
        )

        assert rule, (
            f"{component_name}: rule {index} cannot be empty."
        )

        json.dumps(rule, default=str)

        recognized = False

        # Check boolean pass/fail fields.
        for key, value in rule.items():

            normalized_key = str(key).lower()

            if normalized_key in recognized_boolean_fields:
                recognized = True

                assert isinstance(value, (bool, np.bool_)), (
                    f"{component_name}: rule {index}, "
                    f"field '{key}' must contain a boolean."
                )

                assert bool (value), (
                    f"{component_name}: business rule failed: {rule}"
                )

            # Check textual status fields.
            if normalized_key in recognized_status_fields:
                recognized = True

                if isinstance(value, str):
                    assert value.strip().upper() not in failure_values, (
                        f"{component_name}: business rule failed: {rule}"
                    )

        if recognized:
            checked_rules += 1
        else:
            unrecognized_rules += 1
            print(
                f"WARNING: {component_name} rule {index} "
                "uses an unrecognized result schema."
            )
            print(f"Rule details: {rule}")

    print(
        f"{component_name}: {len(rules)} rules found, "
        f"{checked_rules} checked, "
        f"{unrecognized_rules} requiring schema review."
    )


# --------------------------------------------------
# OUTPUT CONTRACT VALIDATION
# --------------------------------------------------

def check_output_contract(name, output):

    required_keys = {
        "component",
        "metadata",
        "historical_state",
        "business_metrics",
        "scenario_results",
        "business_rule_results",
        "status",
    }

    assert isinstance(output, dict), (
        f"{name}: output must be a dictionary."
    )

    missing_keys = required_keys - set(output.keys())

    assert not missing_keys, (
        f"{name}: missing output keys: {missing_keys}"
    )

    assert output["component"], (
        f"{name}: component identity cannot be empty."
    )

    assert isinstance(output["metadata"], dict), (
        f"{name}: metadata must be a dictionary."
    )

    assert isinstance(output["historical_state"], dict), (
        f"{name}: historical_state must be a dictionary."
    )

    assert isinstance(output["business_metrics"], dict), (
        f"{name}: business_metrics must be a dictionary."
    )

    assert isinstance(output["scenario_results"], list), (
        f"{name}: scenario_results must be a list."
    )

    assert output["status"] == "SUCCESS", (
        f"{name}: component execution failed. "
        f"Status: {output['status']}"
    )

    # Validate business-rule results using component-specific schemas.
    validate_business_rules(
        name,
        output["business_rule_results"]
    )

    # Check complete output JSON serialization.
    try:
        json.dumps(output, default=str)
    except (TypeError, ValueError) as error:
        raise AssertionError(
            f"{name}: output is not JSON serializable: {error}"
        )

    print(f"PASSED: {name} output contract.")


# --------------------------------------------------
# COMPONENT INITIALIZATION
# --------------------------------------------------

def initialize_components(data):

    return {
        "seller": SellerComponent(
            sellers_df=data["sellers"],
            order_items_df=data["order_items"],
            orders_df=data["orders"],
        ),

        "customer": CustomerComponent(
            customers_df=data["customers"],
            orders_df=data["orders"],
            order_items_df=data["order_items"],
        ),

        "product": ProductComponent(
            products_df=data["products"],
            order_items_df=data["order_items"],
            category_translation_df=data["category_translation"],
        ),

        "order_sales": OrderSalesComponent(
            orders_df=data["orders"],
            order_items_df=data["order_items"],
            customers_df=data["customers"],
            products_df=data["products"],
            sellers_df=data["sellers"],
        ),

        "payment": PaymentComponent(
            orders_df=data["orders"],
            payments_df=data["payments"],
        ),

        "delivery": DeliveryComponent(
            orders_df=data["orders"],
            order_items_df=data["order_items"],
            reviews_df=data["reviews"],
            customers_df=data["customers"],
            sellers_df=data["sellers"],
        ),
    }


# --------------------------------------------------
# HISTORICAL RECORD COUNT VALIDATION
# --------------------------------------------------

def validate_record_counts(outputs):

    expected_counts = {
        "seller": {
            "seller_count": 3095,
            "order_item_count": 112650,
        },

        "customer": {
            "customer_count": 96096,
        },

        "product": {
            "product_count": 32951,
            "category_count": 74,
        },

        "order_sales": {
            "order_count": 99441,
            "monthly_period_count": 25,
        },

        "payment": {
            "order_count": 99441,
            "payment_record_count": 103886,
        },

        "delivery": {
            "order_count": 99441,
            "seller_count": 3095,
            "monthly_period_count": 25,
        },
    }

    for component_name, expected_values in expected_counts.items():

        metadata = outputs[component_name]["metadata"]

        for key, expected_value in expected_values.items():

            assert key in metadata, (
                f"{component_name}: missing metadata field '{key}'."
            )

            actual_value = metadata[key]

            assert actual_value == expected_value, (
                f"{component_name}: {key} mismatch. "
                f"Expected {expected_value}, got {actual_value}."
            )

        print(
            f"PASSED: {component_name} historical record counts."
        )


# --------------------------------------------------
# SOURCE DATA IMMUTABILITY
# --------------------------------------------------

def validate_data_immutability(data, original_data):

    for name, original_df in original_data.items():

        pd.testing.assert_frame_equal(
            data[name],
            original_df,
            check_dtype=True,
            check_exact=True,
        )

        print(f"PASSED: {name} source dataset unchanged.")


# --------------------------------------------------
# MAIN INTEGRATION TEST
# --------------------------------------------------

def main():

    print("\n" + "=" * 60)
    print("COMMERCIAL & SALES DIGITAL TWIN")
    print("SIX-COMPONENT INTEGRATION TEST")
    print("=" * 60)

    # 1. Load datasets.
    print("\n[1] LOADING OLIST DATASETS")

    data = load_datasets()

    print("All datasets loaded successfully.")

    # 2. Preserve original data.
    original_data = {
        name: dataframe.copy(deep=True)
        for name, dataframe in data.items()
    }

    # 3. Initialize components.
    print("\n[2] INITIALIZING COMPONENTS")

    components = initialize_components(data)

    print(f"Initialized {len(components)} components.")

    # 4. Execute components.
    print("\n[3] EXECUTING COMPONENTS")

    outputs = {}

    for name, component in components.items():

        print(f"\nRunning {name} component...")

        output = component.run()

        outputs[name] = output

        check_output_contract(name, output)

    # 5. Validate historical record counts.
    print("\n[4] VALIDATING HISTORICAL RECORD COUNTS")

    validate_record_counts(outputs)

    # 6. Validate source immutability.
    print("\n[5] VALIDATING SOURCE DATA IMMUTABILITY")

    validate_data_immutability(data, original_data)

    # 7. Execution summary.
    print("\n[6] COMPONENT EXECUTION SUMMARY")

    for name, output in outputs.items():

        rules = output["business_rule_results"]

        print(
            f"{name:12} | "
            f"Status: {output['status']:7} | "
            f"Rules: {len(rules)}"
        )

    print("\n" + "=" * 60)
    print("ALL SIX COMPONENTS EXECUTED SUCCESSFULLY.")
    print("OUTPUT CONTRACT CHECKS PASSED.")
    print("HISTORICAL RECORD COUNT CHECKS PASSED.")
    print("SOURCE DATA IMMUTABILITY CHECKS PASSED.")
    print("=" * 60)

    print(
        "\nNOTE: Any unrecognized or missing business-rule "
        "schemas remain flagged for review."
    )


if __name__ == "__main__":
    main()
