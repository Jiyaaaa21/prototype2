
import numpy as np
import pandas as pd

from src.scenarios.scenario_definition import ScenarioDefinition
from src.scenarios.scenario_execution_engine import ScenarioExecutionEngine


class ProductPriceScenarioEngine:
    """
    Simulates a product-level price increase while keeping historical
    quantities and freight values unchanged.

    The scenario is a deterministic counterfactual, not a demand forecast.
    Historical source DataFrames are never modified.
    """

    REQUIRED_COLUMNS = {
        "products": {"product_id"},
        "order_items": {
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "price",
            "freight_value"
        },
        "orders": {
            "order_id",
            "customer_id",
            "order_purchase_timestamp"
        },
        "customers": {
            "customer_id",
            "customer_unique_id"
        },
        "category_translation": {
            "product_category_name",
            "category_english"
        }
    }

    DIMENSIONS = {
        "product": ["product_id"],
        "category": ["category_english"],
        "seller": ["seller_id"],
        "customer": ["customer_unique_id"],
        "order": ["order_id"],
        "monthly": ["purchase_month"]
    }

    def __init__(
        self,
        products,
        order_items,
        orders,
        customers,
        category_translation,
        adjustment_rate=0.05,
        scenario_definition=None
    ):
        self.products = products.copy(deep=True)
        self.order_items = order_items.copy(deep=True)
        self.orders = orders.copy(deep=True)
        self.customers = customers.copy(deep=True)
        self.category_translation = category_translation.copy(deep=True)

        if (
            "category_english" not in self.category_translation.columns
            and "product_category_name_english"
            in self.category_translation.columns
        ):
            self.category_translation = self.category_translation.rename(
                columns={
                    "product_category_name_english": "category_english"
                }
            )

        if (
            isinstance(adjustment_rate, bool)
            or not isinstance(adjustment_rate, (int, float))
        ):
            raise TypeError("Adjustment rate must be numeric.")

        if not 0 < adjustment_rate <= 1:
            raise ValueError(
                "Adjustment rate must be greater than 0 and at most 1."
            )

        if scenario_definition is None:
            scenario_definition = ScenarioDefinition(
                scenario_id="SCN-001",
                name="Product Price Adjustment",
                target_component="product_management",
                target_variable="price",
                adjustment_type="percentage_increase",
                adjustment_value=float(adjustment_rate) * 100,
                scope={
                    "type": "all_products_with_historical_sales"
                },
                assumptions=(
                    "Historical quantities remain unchanged.",
                    "Freight values remain unchanged.",
                    "Demand response is not modelled.",
                    "Only products with historical sales are in scope."
                )
            )

        if not isinstance(scenario_definition, ScenarioDefinition):
            raise TypeError(
                "scenario_definition must be a ScenarioDefinition instance."
            )

        if (
            scenario_definition.target_component != "product_management"
            or scenario_definition.target_variable != "price"
            or scenario_definition.adjustment_type
            != "percentage_increase"
            or scenario_definition.scope.get("type")
            != "all_products_with_historical_sales"
        ):
            raise ValueError(
                "Invalid definition for the product price increase scenario."
            )

        self.scenario_definition = scenario_definition

        self.adjustment_rate = (
            scenario_definition.adjustment_value / 100
        )

        self.scenario_execution_engine = ScenarioExecutionEngine()

        self._validate_inputs()

    def _validate_inputs(self):
        frames = {
            "products": self.products,
            "order_items": self.order_items,
            "orders": self.orders,
            "customers": self.customers,
            "category_translation": self.category_translation
        }

        for name, frame in frames.items():
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(
                    f"{name} must be a pandas DataFrame."
                )

            missing = self.REQUIRED_COLUMNS[name] - set(frame.columns)

            if missing:
                raise ValueError(
                    f"{name} is missing required columns: {sorted(missing)}"
                )

        if self.products["product_id"].duplicated().any():
            raise ValueError("Product IDs must be unique.")

        if self.orders["order_id"].duplicated().any():
            raise ValueError("Order IDs must be unique.")

        if self.customers["customer_id"].duplicated().any():
            raise ValueError("Customer IDs must be unique.")

        if self.category_translation[
            "product_category_name"
        ].duplicated().any():
            raise ValueError("Category translation keys must be unique.")

        if self.order_items.empty:
            raise ValueError("Order items cannot be empty.")

        for column in ["price", "freight_value"]:
            values = pd.to_numeric(
                self.order_items[column],
                errors="raise"
            )

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{column} contains non-finite values."
                )

            if (values < 0).any():
                raise ValueError(
                    f"{column} cannot contain negative values."
                )

    def _build_transactions(self, order_items=None):
        """
        Build one transaction-level record per historical order-item line.
        """

        source_items = (
            self.order_items
            if order_items is None
            else order_items
        )

        transactions = source_items.copy(deep=True)

        transactions["price"] = pd.to_numeric(
            transactions["price"],
            errors="raise"
        )

        transactions["freight_value"] = pd.to_numeric(
            transactions["freight_value"],
            errors="raise"
        )

        transactions = transactions.merge(
            self.orders[
                [
                    "order_id",
                    "customer_id",
                    "order_purchase_timestamp"
                ]
            ],
            on="order_id",
            how="left",
            validate="many_to_one"
        )

        transactions = transactions.merge(
            self.customers[
                ["customer_id", "customer_unique_id"]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one"
        )

        transactions = transactions.merge(
            self.products[
                ["product_id", "product_category_name"]
            ],
            on="product_id",
            how="left",
            validate="many_to_one"
        )

        transactions = transactions.merge(
            self.category_translation,
            on="product_category_name",
            how="left",
            validate="many_to_one"
        )

        required_keys = [
            "product_id",
            "seller_id",
            "order_id",
            "customer_unique_id",
            "order_purchase_timestamp"
        ]

        if transactions[required_keys].isna().any().any():
            raise ValueError(
                "Transaction data contains missing or unresolved references."
            )

        # Preserve the original category when no English translation exists.
        transactions["category_english"] = (
            transactions["category_english"]
            .fillna(transactions["product_category_name"])
            .fillna("Unknown")
        )

        transactions["purchase_month"] = (
            pd.to_datetime(
                transactions["order_purchase_timestamp"],
                errors="raise"
            )
            .dt.to_period("M")
            .astype(str)
        )

        if transactions["purchase_month"].isna().any():
            raise ValueError(
                "Purchase month contains missing values."
            )

        if len(transactions) != len(source_items):
            raise RuntimeError(
                "Transaction joins changed the original item-line count."
            )

        return transactions

    @staticmethod
    def _aggregate_transactions(transactions, dimension):
        keys = ProductPriceScenarioEngine.DIMENSIONS[dimension]

        result = (
            transactions
            .groupby(
                keys,
                dropna=False,
                as_index=False
            )
            .agg(
                item_line_count=("order_id", "size"),
                distinct_orders=("order_id", "nunique"),
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
            .sort_values(keys)
            .reset_index(drop=True)
        )

        return result

    @staticmethod
    def _calculate_impact(baseline, scenario, dimension):
        keys = ProductPriceScenarioEngine.DIMENSIONS[dimension]

        merged = baseline.merge(
            scenario,
            on=keys,
            how="outer",
            suffixes=("_baseline", "_scenario"),
            validate="one_to_one",
            indicator=True
        )

        if not (merged["_merge"] == "both").all():
            raise RuntimeError(
                f"{dimension} baseline and scenario groups do not align."
            )

        merged = merged.drop(columns="_merge")

        merged["merchandise_value_change"] = (
            merged["merchandise_value_scenario"]
            - merged["merchandise_value_baseline"]
        )

        merged["merchandise_value_change_pct"] = np.where(
            merged["merchandise_value_baseline"] != 0,
            (
                merged["merchandise_value_change"]
                / merged["merchandise_value_baseline"]
            ) * 100,
            0.0
        )

        merged["freight_value_change"] = (
            merged["freight_value_scenario"]
            - merged["freight_value_baseline"]
        )

        return merged

    def run(self):
        """
        Execute the defined price scenario and return baseline,
        scenario, impact, execution report, and transaction-level data.
        """

        # Build the original historical transaction records.
        baseline_transactions = self._build_transactions()

        # Apply the scenario through the generic execution engine.
        # This is the only place where the price adjustment is applied.
        execution_result = self.scenario_execution_engine.execute(
            self.scenario_definition,
            {
                "product_management": self.order_items
            }
        )

        scenario_order_items = execution_result[
            "scenario_states"
        ]["product_management"]

        # Enrich the transformed order-item records.
        scenario_transactions = self._build_transactions(
            scenario_order_items
        )

        sold_products = set(
            baseline_transactions["product_id"].unique()
        )

        catalogue_products = set(
            self.products["product_id"].unique()
        )

        baseline = {}
        scenario = {}
        impact = {}

        for dimension in self.DIMENSIONS:
            baseline[dimension] = self._aggregate_transactions(
                baseline_transactions,
                dimension
            )

            scenario[dimension] = self._aggregate_transactions(
                scenario_transactions,
                dimension
            )

            impact[dimension] = self._calculate_impact(
                baseline[dimension],
                scenario[dimension],
                dimension
            )

        baseline_total = float(
            baseline_transactions["price"].sum()
        )

        scenario_total = float(
            scenario_transactions["price"].sum()
        )

        merchandise_change = scenario_total - baseline_total

        change_percentage = (
            merchandise_change / baseline_total * 100
            if baseline_total != 0
            else 0.0
        )

        # Reconcile merchandise value changes across all six dimensions.
        for dimension, impact_frame in impact.items():
            dimension_change = impact_frame[
                "merchandise_value_change"
            ].sum()

            if not np.isclose(
                dimension_change,
                merchandise_change,
                atol=0.01
            ):
                raise RuntimeError(
                    f"{dimension} impact does not reconcile."
                )

        summary = {
            "scenario_id": self.scenario_definition.scenario_id,
            "scenario_name": self.scenario_definition.name,
            "adjustment_rate": self.adjustment_rate,
            "adjustment_percentage": self.adjustment_rate * 100,
            "adjustment_type": (
                self.scenario_definition.adjustment_type
            ),
            "adjustment_value": (
                self.scenario_definition.adjustment_value
            ),
            "assumptions": list(
                self.scenario_definition.assumptions
            ),
            "total_catalogue_products": len(catalogue_products),
            "products_with_historical_sales": len(sold_products),
            "products_without_historical_sales": len(
                catalogue_products - sold_products
            ),
            "adjusted_item_lines": len(scenario_transactions),
            "baseline_merchandise_value": baseline_total,
            "scenario_merchandise_value": scenario_total,
            "merchandise_value_change": merchandise_change,
            "merchandise_value_change_pct": change_percentage,
            "quantity_assumption": "Fixed at historical quantities",
            "demand_response_modelled": False,
            "historical_data_modified": False
        }

        results = {
            "summary": summary,
            "execution_report": execution_result["execution_report"],
            "baseline": baseline,
            "scenario": scenario,
            "impact": impact,
            "baseline_transactions": baseline_transactions.copy(
                deep=True
            ),
            "scenario_transactions": scenario_transactions.copy(
                deep=True
            )
        }

        return results
