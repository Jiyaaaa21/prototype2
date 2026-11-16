
import pandas as pd


class SellerManagement:

    def __init__(self, sellers_df, order_items_df, orders_df):
        self.sellers = sellers_df.copy(deep=True)
        self.order_items = order_items_df.copy(deep=True)
        self.orders = orders_df.copy(deep=True)

        self.seller_state = None
        self.monthly_state = None

    def validate_data(self):
        """Validate seller IDs and transaction references."""

        if self.sellers["seller_id"].duplicated().any():
            raise ValueError("Duplicate seller IDs found.")

        invalid_sellers = (
            set(self.order_items["seller_id"].dropna())
            - set(self.sellers["seller_id"].dropna())
        )

        if invalid_sellers:
            raise ValueError(
                f"Invalid seller references: {len(invalid_sellers)}"
            )

        invalid_orders = (
            set(self.order_items["order_id"].dropna())
            - set(self.orders["order_id"].dropna())
        )

        if invalid_orders:
            raise ValueError(
                f"Invalid order references: {len(invalid_orders)}"
            )

        return True

    def build_seller_state(self):
        """Construct seller-level historical performance."""

        transactions = self.order_items.merge(
            self.orders[
                ["order_id", "order_status", "order_purchase_timestamp"]
            ],
            on="order_id",
            how="left",
            validate="many_to_one"
        )

        seller_metrics = (
            transactions.groupby("seller_id")
            .agg(
                total_order_items=("order_item_id", "count"),
                distinct_orders=("order_id", "nunique"),
                distinct_products=("product_id", "nunique"),
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
            .reset_index()
        )

        delivered = transactions[
            transactions["order_status"] == "delivered"
        ]

        delivered_metrics = (
            delivered.groupby("seller_id")
            .agg(
                delivered_order_items=("order_item_id", "count"),
                delivered_orders=("order_id", "nunique"),
                delivered_merchandise_value=("price", "sum"),
                associated_freight_value=("freight_value", "sum")
            )
            .reset_index()
        )

        state = self.sellers.merge(
            seller_metrics,
            on="seller_id",
            how="left",
            validate="one_to_one"
        )

        state = state.merge(
            delivered_metrics,
            on="seller_id",
            how="left",
            validate="one_to_one"
        )

        metric_columns = [
            "total_order_items",
            "distinct_orders",
            "distinct_products",
            "merchandise_value",
            "freight_value",
            "delivered_order_items",
            "delivered_orders",
            "delivered_merchandise_value",
            "associated_freight_value"
        ]

        state[metric_columns] = state[metric_columns].fillna(0)

        self.seller_state = state

        return self.seller_state

    def build_monthly_state(self):
        """
        Build seller-level monthly activity using order purchase month.

        Each row represents one seller in one purchase month.
        Delivery metrics are retrospective outcomes for that purchase cohort.
        """

        self.validate_data()

        items = self.order_items.copy(deep=True)
        orders = self.orders.copy(deep=True)

        items["price"] = pd.to_numeric(
            items["price"], errors="raise"
        )
        items["freight_value"] = pd.to_numeric(
            items["freight_value"], errors="raise"
        )

        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"], errors="raise"
        )

        if orders["order_purchase_timestamp"].isna().any():
            raise ValueError(
                "Order purchase timestamps contain missing values."
            )

        orders["purchase_month"] = (
            orders["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        transactions = items.merge(
            orders[
                ["order_id", "purchase_month", "order_status"]
            ],
            on="order_id",
            how="left",
            validate="many_to_one"
        )

        if transactions["purchase_month"].isna().any():
            raise ValueError(
                "Some order items could not be assigned to a month."
            )

        transactions["is_delivered"] = (
            transactions["order_status"] == "delivered"
        )

        transactions["delivered_order_id"] = (
            transactions["order_id"].where(
                transactions["is_delivered"]
            )
        )

        transactions["delivered_price"] = (
            transactions["price"].where(
                transactions["is_delivered"], 0
            )
        )

        transactions["delivered_freight"] = (
            transactions["freight_value"].where(
                transactions["is_delivered"], 0
            )
        )

        monthly_state = (
            transactions.groupby(
                ["purchase_month", "seller_id"], as_index=False
            )
            .agg(
                item_line_count=("order_item_id", "count"),
                distinct_orders=("order_id", "nunique"),
                distinct_products=("product_id", "nunique"),
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum"),
                delivered_item_lines=("is_delivered", "sum"),
                delivered_orders=("delivered_order_id", "nunique"),
                delivered_merchandise_value=(
                    "delivered_price", "sum"
                ),
                associated_freight_value=(
                    "delivered_freight", "sum"
                )
            )
        )

        monthly_totals = monthly_state.groupby(
            "purchase_month"
        )["merchandise_value"].transform("sum")

        monthly_state["merchandise_share"] = (
            monthly_state["merchandise_value"]
            / monthly_totals.replace(0, pd.NA)
        ).fillna(0)

        monthly_state = (
            monthly_state
            .sort_values(["purchase_month", "seller_id"])
            .reset_index(drop=True)
        )

        self.monthly_state = monthly_state

        return monthly_state.copy(deep=True)

    def get_summary(self):
        """Return aggregate seller performance."""

        if self.seller_state is None:
            raise RuntimeError(
                "Build seller state before requesting summary."
            )

        return {
            "total_sellers": int(
                self.seller_state["seller_id"].nunique()
            ),
            "total_merchandise_value": float(
                self.seller_state["merchandise_value"].sum()
            ),
            "total_freight_value": float(
                self.seller_state["freight_value"].sum()
            ),
            "delivered_merchandise_value": float(
                self.seller_state[
                    "delivered_merchandise_value"
                ].sum()
            )
        }
