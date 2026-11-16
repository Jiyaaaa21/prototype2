
import pandas as pd


class CustomerManagement:
    """
    Handles historical customer analysis for the
    Commercial & Sales Digital Twin.
    """

    def __init__(self, customers_df, orders_df, order_items_df):

        # Preserve independent copies of historical data
        self.customers = customers_df.copy(deep=True)
        self.orders = orders_df.copy(deep=True)
        self.order_items = order_items_df.copy(deep=True)

        self.customer_state = None

    def validate_data(self):
        """
        Validate customer, order, and order-item relationships.
        """

        required_columns = {
            "customers": {
                "customer_id",
                "customer_unique_id",
                "customer_city",
                "customer_state"
            },
            "orders": {
                "order_id",
                "customer_id",
                "order_purchase_timestamp"
            },
            "order_items": {
                "order_id",
                "order_item_id",
                "price",
                "freight_value"
            }
        }

        datasets = {
            "customers": self.customers,
            "orders": self.orders,
            "order_items": self.order_items
        }

        # Validate required columns
        for name, required in required_columns.items():

            missing = required - set(datasets[name].columns)

            if missing:
                raise ValueError(
                    f"{name} dataset is missing columns: {sorted(missing)}"
                )

        # Validate customer identifiers
        if self.customers["customer_id"].isna().any():
            raise ValueError("Missing customer_id values found.")

        if self.customers["customer_unique_id"].isna().any():
            raise ValueError("Missing customer_unique_id values found.")

        if self.customers["customer_id"].duplicated().any():
            raise ValueError("Duplicate customer_id values found.")

        # Validate order identifiers
        if self.orders["order_id"].isna().any():
            raise ValueError("Missing order_id values found.")

        if self.orders["order_id"].duplicated().any():
            raise ValueError("Duplicate order_id values found.")

        if self.orders["customer_id"].isna().any():
            raise ValueError("Orders contain missing customer_id values.")

        # Validate customer references
        valid_customers = set(self.customers["customer_id"])

        invalid_customers = (
            set(self.orders["customer_id"]) - valid_customers
        )

        if invalid_customers:
            raise ValueError(
                f"Invalid customer references found: {len(invalid_customers)}"
            )

        # Validate order-item references
        valid_orders = set(self.orders["order_id"])

        invalid_orders = (
            set(self.order_items["order_id"].dropna()) - valid_orders
        )

        if invalid_orders:
            raise ValueError(
                f"Invalid order references in order_items: {len(invalid_orders)}"
            )

        if self.order_items["order_id"].isna().any():
            raise ValueError("Order items contain missing order_id values.")

        # Validate financial fields
        for column in ["price", "freight_value"]:

            if self.order_items[column].isna().any():
                raise ValueError(
                    f"Missing values found in order_items.{column}"
                )

            if not pd.to_numeric(
                self.order_items[column], errors="coerce"
            ).notna().all():
                raise ValueError(
                    f"Non-numeric values found in order_items.{column}"
                )

            if (self.order_items[column] < 0).any():
                raise ValueError(
                    f"Negative values found in order_items.{column}"
                )

        return True

    def build_customer_state(self):
        """
        Construct one historical record per underlying customer.
        """

        if not self.validate_data():
            raise RuntimeError("Customer data validation failed.")

        # Convert purchase timestamps
        orders = self.orders.copy(deep=True)

        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"],
            errors="coerce"
        )

        if orders["order_purchase_timestamp"].isna().any():
            raise ValueError(
                "Invalid or missing order purchase timestamps found."
            )

        # Aggregate order items to one row per order.
        # This prevents customer metrics from being inflated
        # by joining orders directly to multiple item rows.

        items_by_order = (
            self.order_items
            .groupby("order_id", as_index=False)
            .agg(
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum"),
                item_count=("order_item_id", "count")
            )
        )

        # Connect orders to customer identities
        orders_analysis = orders.merge(
            self.customers[
                ["customer_id", "customer_unique_id"]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one"
        )

        # Add order-level merchandise and freight metrics
        orders_analysis = orders_analysis.merge(
            items_by_order,
            on="order_id",
            how="left",
            validate="one_to_one"
        )

        # Aggregate by underlying customer identity
        customer_orders = (
            orders_analysis
            .dropna(subset=["customer_unique_id"])
            .groupby("customer_unique_id", as_index=False)
            .agg(
                order_count=("order_id", "nunique"),
                merchandise_spend=("merchandise_value", "sum"),
                freight_spend=("freight_value", "sum"),
                first_purchase=("order_purchase_timestamp", "min"),
                last_purchase=("order_purchase_timestamp", "max"),
                average_order_value=("merchandise_value", "mean")
            )
        )

        # Identify repeat customers
        customer_orders["repeat_customer"] = (
            customer_orders["order_count"] > 1
        )

        # Calculate observed purchasing period
        customer_orders["observed_purchase_span_days"] = (
            customer_orders["last_purchase"]
            - customer_orders["first_purchase"]
        ).dt.total_seconds() / 86400

        self.customer_state = customer_orders

        return self.customer_state.copy(deep=True)

    
    def build_monthly_state(self):
        """
        Construct monthly customer purchasing activity.
        Groups orders by purchase month and underlying customer identity.
        """

        if not self.validate_data():
            raise RuntimeError("Customer data validation failed.")

        orders = self.orders.copy(deep=True)
        items = self.order_items.copy(deep=True)

        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"],
            errors="raise"
        )

        if orders["order_purchase_timestamp"].isna().any():
            raise ValueError(
                "Invalid or missing order purchase timestamps found."
            )

        items["price"] = pd.to_numeric(items["price"])
        items["freight_value"] = pd.to_numeric(
            items["freight_value"]
        )

        # Aggregate items to order level.
        items_by_order = (
            items.groupby("order_id", as_index=False)
            .agg(
                item_count=("order_item_id", "count"),
                merchandise_spend=("price", "sum"),
                freight_spend=("freight_value", "sum")
            )
        )

        # Attach customer identity to orders.
        orders_analysis = orders.merge(
            self.customers[
                ["customer_id", "customer_unique_id"]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one"
        )

        # Attach order-level financial metrics.
        orders_analysis = orders_analysis.merge(
            items_by_order,
            on="order_id",
            how="left",
            validate="one_to_one"
        )

        numeric_columns = [
            "item_count",
            "merchandise_spend",
            "freight_spend"
        ]

        orders_analysis[numeric_columns] = (
            orders_analysis[numeric_columns].fillna(0)
        )

        orders_analysis["has_order_items"] = (
            orders_analysis["item_count"] > 0
        )

        orders_analysis["purchase_month"] = (
            orders_analysis["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        # Monthly customer activity.
        monthly_state = (
            orders_analysis
            .dropna(subset=["customer_unique_id"])
            .groupby("purchase_month", as_index=False)
            .agg(
                total_orders=("order_id", "nunique"),
                active_customers=("customer_unique_id", "nunique"),
                orders_with_items=("has_order_items", "sum"),
                item_count=("item_count", "sum"),
                merchandise_spend=("merchandise_spend", "sum"),
                freight_spend=("freight_spend", "sum")
            )
        )

        monthly_state["average_order_value"] = (
            monthly_state["merchandise_spend"]
            / monthly_state["orders_with_items"].replace(0, pd.NA)
        ).fillna(0)

        monthly_state = monthly_state.sort_values(
            "purchase_month"
        ).reset_index(drop=True)

        self.monthly_state = monthly_state.copy(deep=True)

        return self.monthly_state.copy(deep=True)


    def get_summary(self):
        """
        Generate historical customer business metrics.
        """

        if self.customer_state is None:
            raise RuntimeError(
                "Build customer state before requesting summary."
            )

        state = self.customer_state

        total_customers = state["customer_unique_id"].nunique()

        return {
            "total_customers": int(total_customers),

            "single_order_customers": int(
                (state["order_count"] == 1).sum()
            ),

            "repeat_customers": int(
                state["repeat_customer"].sum()
            ),

            "repeat_customer_share": float(
                state["repeat_customer"].mean()
            ),

            "mean_orders_per_customer": float(
                state["order_count"].mean()
            ),

            "median_merchandise_spend_per_customer": float(
                state["merchandise_spend"].median()
            )
        }
