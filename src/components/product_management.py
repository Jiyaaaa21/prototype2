import pandas as pd




class ProductManagement:
    """
    Handles historical product catalogue and performance analysis
    for the Commercial & Sales Digital Twin.
    """

    def __init__(self, products_df, order_items_df, category_translation_df):

        # Preserve independent copies of historical data
        self.products = products_df.copy(deep=True)
        self.order_items = order_items_df.copy(deep=True)
        self.category_translation = category_translation_df.copy(deep=True)

        self.product_state = None
        self.category_state = None

    def validate_data(self):
        """Validate product, order-item, and category relationships."""

        required_columns = {
            "products": {
                "product_id",
                "product_category_name",
                "product_weight_g",
                "product_length_cm",
                "product_height_cm",
                "product_width_cm"
            },
            "order_items": {
                "order_id",
                "order_item_id",
                "product_id",
                "price",
                "freight_value"
            },
            "category_translation": {
                "product_category_name",
                "product_category_name_english"
            }
        }

        datasets = {
            "products": self.products,
            "order_items": self.order_items,
            "category_translation": self.category_translation
        }

        for name, required in required_columns.items():
            missing = required - set(datasets[name].columns)

            if missing:
                raise ValueError(
                    f"{name} dataset is missing columns: {sorted(missing)}"
                )

        # Product identifier validation
        if self.products["product_id"].isna().any():
            raise ValueError("Missing product_id values found.")

        if self.products["product_id"].duplicated().any():
            raise ValueError("Duplicate product_id values found.")

        # Order-item validation
        if self.order_items["product_id"].isna().any():
            raise ValueError("Order items contain missing product_id values.")

        if self.order_items["order_id"].isna().any():
            raise ValueError("Order items contain missing order_id values.")

        if self.order_items["order_item_id"].isna().any():
            raise ValueError("Order items contain missing order_item_id values.")

        valid_products = set(self.products["product_id"])

        invalid_products = (
            set(self.order_items["product_id"]) - valid_products
        )

        if invalid_products:
            raise ValueError(
                f"Invalid product references found: {len(invalid_products)}"
            )

        # Category translation validation
        translation = self.category_translation

        if translation["product_category_name"].isna().any():
            raise ValueError(
                "Missing category names found in translation dataset."
            )

        if translation["product_category_name"].duplicated().any():
            raise ValueError(
                "Duplicate category names found in translation dataset."
            )

        # Financial field validation
        for column in ["price", "freight_value"]:

            numeric_values = pd.to_numeric(
                self.order_items[column],
                errors="coerce"
            )

            if numeric_values.isna().any():
                raise ValueError(
                    f"Missing or non-numeric values in order_items.{column}"
                )

            if (numeric_values < 0).any():
                raise ValueError(
                    f"Negative values found in order_items.{column}"
                )

        return True

    def build_product_state(self):
        """Construct one historical performance record per product."""

        self.validate_data()

        products = self.products.copy(deep=True)
        items = self.order_items.copy(deep=True)
        translation = self.category_translation.copy(deep=True)

        # Ensure financial fields have numeric dtype
        items["price"] = pd.to_numeric(items["price"])
        items["freight_value"] = pd.to_numeric(items["freight_value"])

        # Aggregate sales at product level
        product_metrics = (
            items.groupby("product_id", as_index=False)
            .agg(
                item_line_count=("order_item_id", "count"),
                distinct_orders=("order_id", "nunique"),
                units_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        # Join product catalogue with historical sales
        product_state = products.merge(
            product_metrics,
            on="product_id",
            how="left",
            validate="one_to_one"
        )

        metric_columns = [
            "item_line_count",
            "distinct_orders",
            "units_value",
            "freight_value"
        ]

        product_state[metric_columns] = (
            product_state[metric_columns].fillna(0)
        )

        # Add translated category where available
        product_state = product_state.merge(
            translation,
            on="product_category_name",
            how="left",
            validate="many_to_one"
        )

        product_state["category_english"] = (
            product_state["product_category_name_english"]
            .fillna(product_state["product_category_name"])
            .fillna("unknown")
        )

        # Calculate product contribution to merchandise value
        total_merchandise_value = product_state["units_value"].sum()

        if total_merchandise_value > 0:
            product_state["merchandise_share"] = (
                product_state["units_value"]
                / total_merchandise_value
            )
        else:
            product_state["merchandise_share"] = 0.0

        self.product_state = product_state

        # Construct category-level performance
        self.category_state = (
            product_state.groupby("category_english", as_index=False)
            .agg(
                item_line_count=("item_line_count", "sum"),
                distinct_orders=("distinct_orders", "sum"),
                distinct_products=("product_id", "nunique"),
                merchandise_value=("units_value", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        # Category distinct orders must be counted from original item rows
        category_orders = (
            items.merge(
                products[["product_id", "product_category_name"]],
                on="product_id",
                how="left",
                validate="many_to_one"
            )
            .merge(
                translation,
                on="product_category_name",
                how="left",
                validate="many_to_one"
            )
        )

        category_orders["category_english"] = (
            category_orders["product_category_name_english"]
            .fillna(category_orders["product_category_name"])
            .fillna("unknown")
        )

        distinct_orders_by_category = (
            category_orders.groupby("category_english")["order_id"]
            .nunique()
        )

        self.category_state["distinct_orders"] = (
            self.category_state["category_english"]
            .map(distinct_orders_by_category)
            .fillna(0)
            .astype(int)
        )

        total_category_value = self.category_state["merchandise_value"].sum()

        if total_category_value > 0:
            self.category_state["merchandise_share"] = (
                self.category_state["merchandise_value"]
                / total_category_value
            )
        else:
            self.category_state["merchandise_share"] = 0.0

        return {
            "product_state": self.product_state.copy(deep=True),
            "category_state": self.category_state.copy(deep=True)
        }

    
    def build_monthly_state(self):
        """
        Construct monthly product and category performance states.
        Monthly attribution is based on order purchase timestamp.
        """

        self.validate_data()

        products = self.products.copy(deep=True)
        items = self.order_items.copy(deep=True)
        orders = self.orders.copy(deep=True)
        translation = self.category_translation.copy(deep=True)

        items["price"] = pd.to_numeric(items["price"])
        items["freight_value"] = pd.to_numeric(items["freight_value"])

        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"],
            errors="raise"
        )

        if orders["order_purchase_timestamp"].isna().any():
            raise ValueError("Invalid order purchase timestamps found.")

        orders["purchase_month"] = (
            orders["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        # Attach purchase month to every order item.
        transactions = items.merge(
            orders[["order_id", "purchase_month"]],
            on="order_id",
            how="left",
            validate="many_to_one"
        )

        # Attach product category.
        transactions = transactions.merge(
            products[["product_id", "product_category_name"]],
            on="product_id",
            how="left",
            validate="many_to_one"
        )

        transactions = transactions.merge(
            translation,
            on="product_category_name",
            how="left",
            validate="many_to_one"
        )

        transactions["category_english"] = (
            transactions["product_category_name_english"]
            .fillna(transactions["product_category_name"])
            .fillna("unknown")
        )

        # Product-level monthly activity.
        product_monthly_state = (
            transactions.groupby(
                ["purchase_month", "product_id"],
                as_index=False
            )
            .agg(
                item_line_count=("order_item_id", "count"),
                distinct_orders=("order_id", "nunique"),
                units_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        monthly_product_totals = (
            product_monthly_state.groupby("purchase_month")[
                "units_value"
            ].transform("sum")
        )

        product_monthly_state["merchandise_share"] = (
            product_monthly_state["units_value"]
            / monthly_product_totals.replace(0, pd.NA)
        ).fillna(0)

        # Category-level monthly activity.
        category_monthly_state = (
            transactions.groupby(
                ["purchase_month", "category_english"],
                as_index=False
            )
            .agg(
                item_line_count=("order_item_id", "count"),
                distinct_orders=("order_id", "nunique"),
                distinct_products=("product_id", "nunique"),
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        monthly_category_totals = (
            category_monthly_state.groupby("purchase_month")[
                "merchandise_value"
            ].transform("sum")
        )

        category_monthly_state["merchandise_share"] = (
            category_monthly_state["merchandise_value"]
            / monthly_category_totals.replace(0, pd.NA)
        ).fillna(0)

        product_monthly_state = (
            product_monthly_state.sort_values(
                ["purchase_month", "product_id"]
            ).reset_index(drop=True)
        )

        category_monthly_state = (
            category_monthly_state.sort_values(
                ["purchase_month", "category_english"]
            ).reset_index(drop=True)
        )

        self.product_monthly_state = product_monthly_state.copy(
            deep=True
        )
        self.category_monthly_state = category_monthly_state.copy(
            deep=True
        )

        return {
            "product_monthly_state": self.product_monthly_state.copy(
                deep=True
            ),
            "category_monthly_state": self.category_monthly_state.copy(
                deep=True
            )
        }


    def get_summary(self):
        """Generate historical product business metrics."""

        if self.product_state is None or self.category_state is None:
            raise RuntimeError(
                "Build product state before requesting summary."
            )

        products = self.product_state
        categories = self.category_state

        return {
            "total_catalogue_products": int(
                products["product_id"].nunique()
            ),

            "distinct_product_categories": int(
                products["category_english"].nunique()
            ),

            "total_item_lines": int(
                products["item_line_count"].sum()
            ),

            "total_distinct_orders": int(
                self.order_items["order_id"].nunique()
            ),

            "total_merchandise_value": float(
                products["units_value"].sum()
            ),

            "total_freight_value": float(
                products["freight_value"].sum()
            ),

            "products_with_sales": int(
                (products["item_line_count"] > 0).sum()
            )
        }

