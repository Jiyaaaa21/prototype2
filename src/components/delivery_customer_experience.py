
import pandas as pd


class DeliveryCustomerExperience:
    """
    Builds historical delivery and customer-experience states
    from the Olist dataset.

    Primary grain: one record per order_id.
    Secondary grain: one record per order_id-seller_id pair.
    """

    REQUIRED_COLUMNS = {
        "orders": {
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        },
        "order_items": {"order_id", "seller_id"},
        "reviews": {"order_id", "review_score"},
        "customers": {"customer_id", "customer_unique_id"},
        "sellers": {"seller_id"},
    }

    def __init__(
        self,
        orders_df,
        order_items_df,
        reviews_df,
        customers_df,
        sellers_df,
    ):
        self.orders_df = orders_df.copy(deep=True)
        self.order_items_df = order_items_df.copy(deep=True)
        self.reviews_df = reviews_df.copy(deep=True)
        self.customers_df = customers_df.copy(deep=True)
        self.sellers_df = sellers_df.copy(deep=True)

        self.order_state = None
        self.monthly_state = None
        self.seller_state = None
        self.summary = None

        self._validate_inputs()

    @staticmethod
    def _validate_columns(df, required_columns, dataset_name):
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"{dataset_name} is missing columns: {sorted(missing)}"
            )

    @staticmethod
    def _parse_dates(series, column_name):
        parsed = pd.to_datetime(series, errors="coerce")

        invalid = series.notna() & parsed.isna()

        if invalid.any():
            raise ValueError(
                f"{column_name} contains {int(invalid.sum())} invalid dates."
            )

        return parsed

    @staticmethod
    def _validate_unique_non_null(df, column, dataset_name):
        if df[column].isna().any():
            raise ValueError(
                f"{dataset_name}.{column} contains null values."
            )

        if df[column].duplicated().any():
            raise ValueError(
                f"{dataset_name}.{column} must contain unique values."
            )

    def _validate_inputs(self):
        datasets = {
            "orders": self.orders_df,
            "order_items": self.order_items_df,
            "reviews": self.reviews_df,
            "customers": self.customers_df,
            "sellers": self.sellers_df,
        }

        for name, df in datasets.items():
            self._validate_columns(
                df,
                self.REQUIRED_COLUMNS[name],
                name,
            )

        # Primary-key validation
        self._validate_unique_non_null(
            self.orders_df, "order_id", "orders"
        )

        self._validate_unique_non_null(
            self.customers_df, "customer_id", "customers"
        )

        self._validate_unique_non_null(
            self.sellers_df, "seller_id", "sellers"
        )

        # customer_unique_id is intentionally NOT required to be unique.
        # Multiple customer_id records can represent the same customer.

        if self.customers_df["customer_unique_id"].isna().any():
            raise ValueError(
                "customers.customer_unique_id contains null values."
            )

        if self.order_items_df[
            ["order_id", "seller_id"]
        ].isna().any().any():
            raise ValueError(
                "Order items contain null order_id or seller_id values."
            )

        if self.reviews_df["order_id"].isna().any():
            raise ValueError("Reviews contain null order_id values.")

        if not set(self.orders_df["customer_id"]).issubset(
            set(self.customers_df["customer_id"])
        ):
            raise ValueError(
                "Orders contain customer_id values missing from customers."
            )

        if not set(self.order_items_df["order_id"]).issubset(
            set(self.orders_df["order_id"])
        ):
            raise ValueError(
                "Order items contain order_id values missing from orders."
            )

        if not set(self.order_items_df["seller_id"]).issubset(
            set(self.sellers_df["seller_id"])
        ):
            raise ValueError(
                "Order items contain seller_id values missing from sellers."
            )

        if not set(self.reviews_df["order_id"]).issubset(
            set(self.orders_df["order_id"])
        ):
            raise ValueError(
                "Reviews contain order_id values missing from orders."
            )

        self.orders_df["order_purchase_timestamp"] = (
            self._parse_dates(
                self.orders_df["order_purchase_timestamp"],
                "order_purchase_timestamp",
            )
        )

        self.orders_df["order_delivered_customer_date"] = (
            self._parse_dates(
                self.orders_df["order_delivered_customer_date"],
                "order_delivered_customer_date",
            )
        )

        self.orders_df["order_estimated_delivery_date"] = (
            self._parse_dates(
                self.orders_df["order_estimated_delivery_date"],
                "order_estimated_delivery_date",
            )
        )

        self.reviews_df["review_score"] = pd.to_numeric(
            self.reviews_df["review_score"],
            errors="coerce",
        )

        invalid_scores = (
            self.reviews_df["review_score"].notna()
            & ~self.reviews_df["review_score"].between(1, 5)
        )

        if invalid_scores.any():
            raise ValueError(
                "Review scores must be between 1 and 5."
            )

    def _build_review_state(self):
        """
        Aggregate reviews before joining them to orders.
        This prevents multiple reviews from duplicating order records.
        """
        review_state = (
            self.reviews_df.groupby("order_id")
            .agg(review_record_count=("order_id", "size"))
        )

        valid_reviews = self.reviews_df[
            self.reviews_df["review_score"].notna()
        ]

        average_scores = (
            valid_reviews.groupby("order_id")["review_score"]
            .mean()
            .rename("average_review_score")
        )

        review_state = review_state.join(average_scores)

        return review_state.reset_index()

    def build_order_state(self):
        orders = self.orders_df.copy()

        customer_lookup = self.customers_df[
            ["customer_id", "customer_unique_id"]
        ]

        orders = orders.merge(
            customer_lookup,
            on="customer_id",
            how="left",
            validate="many_to_one",
        )

        review_state = self._build_review_state()

        orders = orders.merge(
            review_state,
            on="order_id",
            how="left",
            validate="one_to_one",
        )

        orders["review_record_count"] = (
            orders["review_record_count"].fillna(0).astype(int)
        )

        orders["delivery_duration_days"] = (
            orders["order_delivered_customer_date"]
            - orders["order_purchase_timestamp"]
        ).dt.total_seconds() / 86400

        orders["delivery_delay_days"] = (
            orders["order_delivered_customer_date"]
            - orders["order_estimated_delivery_date"]
        ).dt.total_seconds() / 86400

        delivered = (
            orders["order_status"].eq("delivered")
            & orders["order_delivered_customer_date"].notna()
        )

        has_estimate = (
            orders["order_estimated_delivery_date"].notna()
        )

        unavailable = orders["order_status"].isin(
            ["canceled", "unavailable"]
        )

        orders["delivery_performance"] = "pending"

        orders.loc[
            unavailable, "delivery_performance"
        ] = "unavailable"

        orders.loc[
            orders["order_status"].eq("delivered")
            & orders["order_delivered_customer_date"].isna(),
            "delivery_performance",
        ] = "delivery_date_missing"

        orders.loc[
            delivered & ~has_estimate,
            "delivery_performance",
        ] = "estimate_unavailable"

        orders.loc[
            delivered
            & has_estimate
            & orders["delivery_delay_days"].le(0),
            "delivery_performance",
        ] = "on_time"

        orders.loc[
            delivered
            & has_estimate
            & orders["delivery_delay_days"].gt(0),
            "delivery_performance",
        ] = "late"

        orders["is_delivered"] = delivered
        orders["is_late"] = (
            orders["delivery_performance"].eq("late")
        )

        orders["purchase_month"] = (
            orders["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        selected_columns = [
            "order_id",
            "customer_id",
            "customer_unique_id",
            "order_status",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
            "purchase_month",
            "delivery_duration_days",
            "delivery_delay_days",
            "delivery_performance",
            "is_delivered",
            "is_late",
            "review_record_count",
            "average_review_score",
        ]

        self.order_state = orders[selected_columns].copy()

        return self.order_state.copy()

    def build_monthly_state(self):
        if self.order_state is None:
            self.build_order_state()

        monthly = (
            self.order_state.groupby("purchase_month")
            .agg(
                total_orders=("order_id", "nunique"),
                delivered_orders=("is_delivered", "sum"),
                late_orders=("is_late", "sum"),
                average_delivery_duration_days=(
                    "delivery_duration_days", "mean"
                ),
                average_delivery_delay_days=(
                    "delivery_delay_days", "mean"
                ),
                reviewed_orders=("average_review_score", "count"),
                average_review_score=(
                    "average_review_score", "mean"
                ),
            )
            .reset_index()
        )

        on_time_counts = (
            self.order_state[
                self.order_state["delivery_performance"].eq("on_time")
            ]
            .groupby("purchase_month")["order_id"]
            .nunique()
        )

        monthly["on_time_orders"] = (
            monthly["purchase_month"]
            .map(on_time_counts)
            .fillna(0)
            .astype(int)
        )

        self.monthly_state = monthly

        return self.monthly_state.copy()

    def build_seller_state(self):
        if self.order_state is None:
            self.build_order_state()

        order_seller_pairs = (
            self.order_items_df[["order_id", "seller_id"]]
            .drop_duplicates()
        )

        seller_orders = order_seller_pairs.merge(
            self.order_state[
                [
                    "order_id",
                    "purchase_month",
                    "delivery_duration_days",
                    "delivery_performance",
                    "is_delivered",
                    "is_late",
                    "average_review_score",
                ]
            ],
            on="order_id",
            how="left",
            validate="many_to_one",
        )

        seller_state = (
            seller_orders.groupby("seller_id")
            .agg(
                associated_orders=("order_id", "nunique"),
                delivered_orders=("is_delivered", "sum"),
                late_orders=("is_late", "sum"),
                average_delivery_duration_days=(
                    "delivery_duration_days", "mean"
                ),
                average_review_score=(
                    "average_review_score", "mean"
                ),
            )
            .reset_index()
        )

        self.seller_state = seller_state

        return self.seller_state.copy()

    def build_all_states(self):
        self.build_order_state()
        self.build_monthly_state()
        self.build_seller_state()
        self._build_summary()

        return {
            "orders": self.order_state.copy(),
            "monthly": self.monthly_state.copy(),
            "sellers": self.seller_state.copy(),
        }

    def _build_summary(self):
        state = self.order_state

        delivered = state[state["is_delivered"]]
        review_scores = state["average_review_score"]

        self.summary = {
            "total_orders": int(state["order_id"].nunique()),
            "delivered_orders": int(state["is_delivered"].sum()),
            "late_orders": int(state["is_late"].sum()),
            "on_time_orders": int(
                state["delivery_performance"].eq("on_time").sum()
            ),
            "pending_orders": int(
                state["delivery_performance"].eq("pending").sum()
            ),
            "unavailable_orders": int(
                state["delivery_performance"].eq("unavailable").sum()
            ),
            "average_delivery_duration_days": (
                float(delivered["delivery_duration_days"].mean())
                if delivered["delivery_duration_days"].notna().any()
                else None
            ),
            "average_delivery_delay_days": (
                float(delivered["delivery_delay_days"].mean())
                if delivered["delivery_delay_days"].notna().any()
                else None
            ),
            "orders_with_reviews": int(review_scores.notna().sum()),
            "average_review_score": (
                float(review_scores.mean())
                if review_scores.notna().any()
                else None
            ),
            "total_review_records": int(
                self.reviews_df.shape[0]
            ),
            "distinct_sellers": int(
                self.seller_state["seller_id"].nunique()
            ),
        }

    def get_summary(self):
        if self.summary is None:
            raise RuntimeError(
                "Build component states before requesting the summary."
            )

        return self.summary.copy()

