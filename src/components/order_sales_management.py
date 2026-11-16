
import pandas as pd


class OrderSalesManagement:

    def __init__(
        self,
        orders_df,
        order_items_df,
        customers_df,
        products_df,
        sellers_df
    ):
        self.orders = orders_df.copy(deep=True)
        self.order_items = order_items_df.copy(deep=True)
        self.customers = customers_df.copy(deep=True)
        self.products = products_df.copy(deep=True)
        self.sellers = sellers_df.copy(deep=True)

        self.order_state = None
        self.monthly_state = None
        self.contribution_state = None

    def validate_data(self):

        required = {
            "orders": [
                "order_id",
                "customer_id",
                "order_status",
                "order_purchase_timestamp"
            ],
            "order_items": [
                "order_id",
                "order_item_id",
                "product_id",
                "seller_id",
                "price",
                "freight_value"
            ],
            "customers": [
                "customer_id",
                "customer_unique_id"
            ],
            "products": [
                "product_id",
                "product_category_name"
            ],
            "sellers": [
                "seller_id"
            ]
        }

        datasets = {
            "orders": self.orders,
            "order_items": self.order_items,
            "customers": self.customers,
            "products": self.products,
            "sellers": self.sellers
        }

        for name, columns in required.items():
            missing = set(columns) - set(datasets[name].columns)

            if missing:
                raise ValueError(
                    f"{name} is missing columns: {sorted(missing)}"
                )

        primary_keys = {
            "orders": ["order_id"],
            "customers": ["customer_id"],
            "products": ["product_id"],
            "sellers": ["seller_id"]
        }

        for name, keys in primary_keys.items():
            for key in keys:
                series = datasets[name][key]

                if series.isna().any():
                    raise ValueError(
                        f"{name}.{key} contains null values."
                    )

                if series.duplicated().any():
                    raise ValueError(
                        f"{name}.{key} contains duplicate values."
                    )

        if self.order_items[
            ["order_id", "order_item_id"]
        ].isna().any().any():
            raise ValueError(
                "Order items contain null composite key values."
            )

        if self.order_items.duplicated(
            subset=["order_id", "order_item_id"]
        ).any():
            raise ValueError(
                "Duplicate order_id and order_item_id combinations."
            )

        foreign_key_checks = [
            (
                self.order_items["order_id"],
                self.orders["order_id"],
                "Order items contain invalid order references."
            ),
            (
                self.orders["customer_id"],
                self.customers["customer_id"],
                "Orders contain invalid customer references."
            ),
            (
                self.order_items["product_id"],
                self.products["product_id"],
                "Order items contain invalid product references."
            ),
            (
                self.order_items["seller_id"],
                self.sellers["seller_id"],
                "Order items contain invalid seller references."
            )
        ]

        for source, target, message in foreign_key_checks:
            if not source.isin(target).all():
                raise ValueError(message)

        for column in ["price", "freight_value"]:
            values = pd.to_numeric(
                self.order_items[column],
                errors="coerce"
            )

            if values.isna().any():
                raise ValueError(
                    f"Invalid or missing values in {column}."
                )

            if (values < 0).any():
                raise ValueError(
                    f"Negative values found in {column}."
                )

        timestamps = pd.to_datetime(
            self.orders["order_purchase_timestamp"],
            errors="coerce"
        )

        if timestamps.isna().any():
            raise ValueError(
                "Invalid or missing order purchase timestamps."
            )

        return True

    def build_order_state(self):

        self.validate_data()

        orders = self.orders.copy(deep=True)
        items = self.order_items.copy(deep=True)

        items["price"] = pd.to_numeric(items["price"])
        items["freight_value"] = pd.to_numeric(
            items["freight_value"]
        )

        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"],
            errors="raise"
        )

        orders["order_status"] = (
            orders["order_status"]
            .fillna("unknown")
            .replace("", "unknown")
        )

        # 1. ORDER-LEVEL STATE

        item_metrics = (
            items.groupby("order_id", as_index=False)
            .agg(
                item_count=("order_item_id", "count"),
                distinct_products=("product_id", "nunique"),
                distinct_sellers=("seller_id", "nunique"),
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        order_state = orders.merge(
            item_metrics,
            on="order_id",
            how="left",
            validate="one_to_one"
        )

        numeric_columns = [
            "item_count",
            "distinct_products",
            "distinct_sellers",
            "merchandise_value",
            "freight_value"
        ]

        order_state[numeric_columns] = (
            order_state[numeric_columns].fillna(0)
        )

        order_state["has_order_items"] = (
            order_state["item_count"] > 0
        )

        order_state["purchase_month"] = (
            order_state["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        # 2. MONTHLY STATE

        monthly_state = (
            order_state.groupby("purchase_month", as_index=False)
            .agg(
                order_count=("order_id", "nunique"),
                orders_with_items=("has_order_items", "sum"),
                merchandise_value=("merchandise_value", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        monthly_state["average_order_value"] = (
            monthly_state["merchandise_value"]
            / monthly_state["orders_with_items"].replace(0, pd.NA)
        ).fillna(0)

        # Count each order once under its recorded status.
        status_counts = (
            order_state.groupby(
                ["purchase_month", "order_status"]
            )["order_id"]
            .nunique()
            .unstack(fill_value=0)
        )

        # Prefix status columns to distinguish them from KPIs.
        status_counts.columns = [
            f"status_{str(column)}"
            for column in status_counts.columns
        ]

        status_counts = status_counts.reset_index()

        monthly_state = monthly_state.merge(
            status_counts,
            on="purchase_month",
            how="left",
            validate="one_to_one"
        )

        # Explicit integrity check inside the component.
        status_columns = [
            column for column in monthly_state.columns
            if column.startswith("status_")
        ]

        status_totals = monthly_state[status_columns].sum(axis=1)

        if not status_totals.equals(
            monthly_state["order_count"].astype(status_totals.dtype)
        ):
            if not (
                status_totals.to_numpy()
                == monthly_state["order_count"].to_numpy()
            ).all():
                raise ValueError(
                    "Monthly status counts do not match monthly order counts."
                )

        # 3. CONTRIBUTION ANALYSIS

        transaction_data = items.merge(
            orders[["order_id", "customer_id"]],
            on="order_id",
            how="left",
            validate="many_to_one"
        )

        transaction_data = transaction_data.merge(
            self.customers[
                ["customer_id", "customer_unique_id"]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one"
        )

        transaction_data = transaction_data.merge(
            self.products[
                ["product_id", "product_category_name"]
            ],
            on="product_id",
            how="left",
            validate="many_to_one"
        )

        transaction_data["product_category_name"] = (
            transaction_data["product_category_name"]
            .fillna("unknown")
            .replace("", "unknown")
        )

        product_contribution = (
            transaction_data.groupby("product_id", as_index=False)
            .agg(
                item_lines=("order_item_id", "count"),
                merchandise_value=("price", "sum")
            )
        )

        category_contribution = (
            transaction_data.groupby(
                "product_category_name",
                as_index=False
            )
            .agg(
                item_lines=("order_item_id", "count"),
                distinct_products=("product_id", "nunique"),
                distinct_orders=("order_id", "nunique"),
                merchandise_value=("price", "sum")
            )
        )

        seller_contribution = (
            transaction_data.groupby("seller_id", as_index=False)
            .agg(
                item_lines=("order_item_id", "count"),
                merchandise_value=("price", "sum")
            )
        )

        customer_contribution = (
            transaction_data.groupby(
                "customer_unique_id",
                as_index=False
            )
            .agg(
                item_lines=("order_item_id", "count"),
                distinct_orders=("order_id", "nunique"),
                merchandise_value=("price", "sum")
            )
        )

        contribution_state = {
            "products": product_contribution,
            "categories": category_contribution,
            "sellers": seller_contribution,
            "customers": customer_contribution
        }

        # 4. STORE STATES

        self.order_state = order_state.copy(deep=True)
        self.monthly_state = monthly_state.copy(deep=True)

        self.contribution_state = {
            key: value.copy(deep=True)
            for key, value in contribution_state.items()
        }

        return {
            "order_state": self.order_state.copy(deep=True),
            "monthly_state": self.monthly_state.copy(deep=True),
            "contribution_state": {
                key: value.copy(deep=True)
                for key, value in self.contribution_state.items()
            }
        }

    def get_summary(self):

        if self.order_state is None:
            raise RuntimeError(
                "Build order state before requesting the summary."
            )

        orders_with_items = int(
            self.order_state["has_order_items"].sum()
        )

        total_merchandise_value = float(
            self.order_state["merchandise_value"].sum()
        )

        total_freight_value = float(
            self.order_state["freight_value"].sum()
        )

        return {
            "total_orders": int(
                self.order_state["order_id"].nunique()
            ),
            "orders_with_items": orders_with_items,
            "total_orders_without_items": int(
                (~self.order_state["has_order_items"]).sum()
            ),
            "total_order_items": int(
                self.order_state["item_count"].sum()
            ),
            "total_merchandise_value": total_merchandise_value,
            "total_freight_value": total_freight_value,
            "average_order_value": (
                total_merchandise_value / orders_with_items
                if orders_with_items > 0
                else 0
            ),
            "delivered_orders": int(
                (
                    self.order_state["order_status"] == "delivered"
                ).sum()
            ),
            "cancelled_orders": int(
                (
                    self.order_state["order_status"] == "canceled"
                ).sum()
            ),
            "monthly_periods": int(
                self.order_state["purchase_month"].nunique()
            )
        }
