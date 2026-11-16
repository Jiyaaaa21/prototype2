
import pandas as pd


class PaymentRevenueManagement:

    def __init__(self, orders_df, payments_df):

        self.orders = orders_df.copy(deep=True)
        self.payments = payments_df.copy(deep=True)

        self.order_state = None
        self.monthly_state = None
        self.payment_method_state = None

    def validate_data(self):

        required_orders = {
            "order_id",
            "order_purchase_timestamp"
        }

        required_payments = {
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value"
        }

        missing_orders = required_orders - set(self.orders.columns)
        missing_payments = required_payments - set(self.payments.columns)

        if missing_orders:
            raise ValueError(
                f"Orders dataset is missing columns: "
                f"{sorted(missing_orders)}"
            )

        if missing_payments:
            raise ValueError(
                f"Payments dataset is missing columns: "
                f"{sorted(missing_payments)}"
            )

        # Primary key validation
        if self.orders["order_id"].isna().any():
            raise ValueError("Orders contain null order IDs.")

        if self.orders["order_id"].duplicated().any():
            raise ValueError("Orders contain duplicate order IDs.")

        # Payment transaction key validation
        payment_keys = [
            "order_id",
            "payment_sequential"
        ]

        if self.payments[payment_keys].isna().any().any():
            raise ValueError(
                "Payment records contain null transaction key values."
            )

        if self.payments.duplicated(
            subset=payment_keys
        ).any():
            raise ValueError(
                "Duplicate order_id and payment_sequential combinations."
            )

        # Foreign key validation
        if not self.payments["order_id"].isin(
            self.orders["order_id"]
        ).all():
            raise ValueError(
                "Payments contain order IDs not present in the orders dataset."
            )

        # Payment value validation
        payment_values = pd.to_numeric(
            self.payments["payment_value"],
            errors="coerce"
        )

        if payment_values.isna().any():
            raise ValueError(
                "Payment values contain invalid or missing values."
            )

        if (payment_values < 0).any():
            raise ValueError(
                "Payment values cannot be negative."
            )

        # Installment validation
        installments = pd.to_numeric(
            self.payments["payment_installments"],
            errors="coerce"
        )

        if installments.isna().any():
            raise ValueError(
                "Payment installments contain invalid or missing values."
            )

        if (installments < 0).any():
            raise ValueError(
                "Payment installments cannot be negative."
            )

        # Timestamp validation
        timestamps = pd.to_datetime(
            self.orders["order_purchase_timestamp"],
            errors="coerce"
        )

        if timestamps.isna().any():
            raise ValueError(
                "Orders contain invalid or missing purchase timestamps."
            )

        return True

    def build_payment_state(self):

        self.validate_data()

        orders = self.orders.copy(deep=True)
        payments = self.payments.copy(deep=True)

        payments["payment_value"] = pd.to_numeric(
            payments["payment_value"]
        )

        payments["payment_installments"] = pd.to_numeric(
            payments["payment_installments"]
        )

        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"],
            errors="raise"
        )

        # Normalize missing payment method labels.
        payments["payment_type"] = (
            payments["payment_type"]
            .fillna("unknown")
            .replace("", "unknown")
        )

        orders["purchase_month"] = (
            orders["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        # --------------------------------------------------
        # 1. ORDER-LEVEL PAYMENT STATE
        # --------------------------------------------------

        order_payment_metrics = (
            payments.groupby("order_id", as_index=False)
            .agg(
                payment_record_count=("payment_sequential", "count"),
                distinct_payment_methods=("payment_type", "nunique"),
                total_payment_value=("payment_value", "sum"),
                total_installments=("payment_installments", "sum"),
                maximum_installments=("payment_installments", "max")
            )
        )

        order_state = orders[
            [
                "order_id",
                "order_purchase_timestamp",
                "purchase_month"
            ]
        ].merge(
            order_payment_metrics,
            on="order_id",
            how="left",
            validate="one_to_one"
        )

        numeric_columns = [
            "payment_record_count",
            "distinct_payment_methods",
            "total_payment_value",
            "total_installments",
            "maximum_installments"
        ]

        order_state[numeric_columns] = (
            order_state[numeric_columns].fillna(0)
        )

        order_state["has_payment"] = (
            order_state["payment_record_count"] > 0
        )

        # --------------------------------------------------
        # 2. MONTHLY PAYMENT STATE
        # --------------------------------------------------

        monthly_order_metrics = (
            order_state.groupby("purchase_month", as_index=False)
            .agg(
                total_orders=("order_id", "nunique"),
                orders_with_payments=("has_payment", "sum"),
                payment_record_count=("payment_record_count", "sum"),
                total_payment_value=("total_payment_value", "sum")
            )
        )

        monthly_order_metrics["average_payment_per_order"] = (
            monthly_order_metrics["total_payment_value"]
            / monthly_order_metrics[
                "orders_with_payments"
            ].replace(0, pd.NA)
        ).fillna(0)

        # Payment method distribution by month.
        payment_transactions = payments.merge(
            orders[["order_id", "purchase_month"]],
            on="order_id",
            how="left",
            validate="many_to_one"
        )

        monthly_method_metrics = (
            payment_transactions.groupby(
                ["purchase_month", "payment_type"]
            )
            .agg(
                payment_records=("payment_sequential", "count"),
                method_payment_value=("payment_value", "sum")
            )
            .reset_index()
        )

        monthly_state = monthly_order_metrics.merge(
            monthly_method_metrics.pivot(
                index="purchase_month",
                columns="payment_type",
                values="method_payment_value"
            ).fillna(0).add_prefix("method_value_").reset_index(),
            on="purchase_month",
            how="left",
            validate="one_to_one"
        )

        # --------------------------------------------------
        # 3. PAYMENT METHOD CONTRIBUTION
        # --------------------------------------------------

        payment_method_state = (
            payments.groupby("payment_type", as_index=False)
            .agg(
                payment_record_count=("payment_sequential", "count"),
                distinct_orders=("order_id", "nunique"),
                total_payment_value=("payment_value", "sum"),
                average_payment_value=("payment_value", "mean"),
                average_installments=("payment_installments", "mean"),
                maximum_installments=("payment_installments", "max")
            )
            .sort_values(
                "total_payment_value",
                ascending=False
            )
            .reset_index(drop=True)
        )

        # --------------------------------------------------
        # 4. STORE HISTORICAL STATES
        # --------------------------------------------------

        self.order_state = order_state.copy(deep=True)
        self.monthly_state = monthly_state.copy(deep=True)
        self.payment_method_state = (
            payment_method_state.copy(deep=True)
        )

        return {
            "order_state": self.order_state.copy(deep=True),
            "monthly_state": self.monthly_state.copy(deep=True),
            "payment_method_state": (
                self.payment_method_state.copy(deep=True)
            )
        }

    def get_summary(self):

        if self.order_state is None:
            raise RuntimeError(
                "Build payment state before requesting the summary."
            )

        total_payment_value = float(
            self.payments["payment_value"].sum()
        )

        total_orders = int(
            self.order_state["order_id"].nunique()
        )

        orders_with_payments = int(
            self.order_state["has_payment"].sum()
        )

        total_payment_records = int(
            len(self.payments)
        )

        return {
            "total_orders": total_orders,
            "orders_with_payments": orders_with_payments,
            "orders_without_payments": (
                total_orders - orders_with_payments
            ),
            "total_payment_records": total_payment_records,
            "total_payment_value": total_payment_value,
            "average_payment_per_order": (
                total_payment_value / orders_with_payments
                if orders_with_payments > 0
                else 0
            ),
            "distinct_payment_methods": int(
                self.payments["payment_type"].nunique()
            ),
            "monthly_periods": int(
                self.order_state["purchase_month"].nunique()
            )
        }
