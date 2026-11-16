
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR
from src.components.delivery_customer_experience import (
    DeliveryCustomerExperience,
)


def load_data():
    return {
        "orders_df": pd.read_csv(
            DATA_DIR / "olist_orders_dataset.csv"
        ),
        "order_items_df": pd.read_csv(
            DATA_DIR / "olist_order_items_dataset.csv"
        ),
        "reviews_df": pd.read_csv(
            DATA_DIR / "olist_order_reviews_dataset.csv"
        ),
        "customers_df": pd.read_csv(
            DATA_DIR / "olist_customers_dataset.csv"
        ),
        "sellers_df": pd.read_csv(
            DATA_DIR / "olist_sellers_dataset.csv"
        ),
    }


def main():
    data = load_data()

    component = DeliveryCustomerExperience(**data)
    states = component.build_all_states()
    summary = component.get_summary()

    print("\nDELIVERY & CUSTOMER EXPERIENCE SUMMARY")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nSTATE DIMENSIONS")
    for name, dataframe in states.items():
        print(
            f"{name}: {dataframe.shape[0]} rows, "
            f"{dataframe.shape[1]} columns"
        )

    assert states["orders"]["order_id"].is_unique
    assert states["sellers"]["seller_id"].is_unique
    assert states["monthly"]["purchase_month"].is_unique

    assert len(states["orders"]) == data["orders_df"]["order_id"].nunique()

    assert (
        states["orders"]["delivery_performance"].notna().all()
    )

    assert (
        states["orders"]["review_record_count"].sum()
        == len(data["reviews_df"])
    )

    print("\nALL DELIVERY & CUSTOMER EXPERIENCE TESTS PASSED.")


if __name__ == "__main__":
    main()
