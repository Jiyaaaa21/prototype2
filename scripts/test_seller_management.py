
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config.settings import (
    SELLERS_FILE,
    ORDERS_FILE,
    ORDER_ITEMS_FILE
)

from src.components.seller_management import SellerManagement


# Load source data
sellers_df = pd.read_csv(SELLERS_FILE)
orders_df = pd.read_csv(ORDERS_FILE)
order_items_df = pd.read_csv(ORDER_ITEMS_FILE)

# Initialize component
seller_component = SellerManagement(
    sellers_df=sellers_df,
    order_items_df=order_items_df,
    orders_df=orders_df
)

# Validate data
print("Data validation:", seller_component.validate_data())

# Build seller state
seller_state = seller_component.build_seller_state()

# Display summary
print("\nSeller Management Summary:")
for metric, value in seller_component.get_summary().items():
    print(f"{metric}: {value}")

print("\nSeller state shape:", seller_state.shape)
print("\nSample records:")
print(seller_state.head())