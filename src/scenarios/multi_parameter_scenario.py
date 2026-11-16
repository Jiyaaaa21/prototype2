from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd


class MultiParameterScenarioEngine:
    """
    Multi-parameter financial scenario engine for the Olist
    Commercial & Sales Digital Twin.

    Adjustable parameters:
        1. Product price adjustment
        2. Discount rate
        3. Seller cost rate
        4. Commission rate
        5. Freight adjustment

    Supported impact dimensions:
        1. Product
        2. Category
        3. Seller
        4. Customer
        5. Order
        6. Monthly

    Important:
        - No hypothetical business parameter is assigned a default.
        - Baseline and scenario configurations must be supplied explicitly.
        - Historical source DataFrames are never modified.
        - Demand, order volume, delivery time, and customer behaviour
          are not automatically predicted or changed.
    """

    REQUIRED_PARAMETERS = {
        "product_price_adjustment",
        "discount_rate",
        "seller_cost_rate",
        "commission_rate",
        "freight_adjustment",
    }

    DIMENSIONS = {
        "product": ["product_id"],
        "category": ["category_english"],
        "seller": ["seller_id"],
        "customer": ["customer_unique_id"],
        "order": ["order_id"],
        "monthly": ["purchase_month"],
    }

    REQUIRED_COLUMNS = {
        "products": {
            "product_id",
            "product_category_name",
        },
        "order_items": {
            "order_id",
            "product_id",
            "seller_id",
            "price",
            "freight_value",
        },
        "orders": {
            "order_id",
            "customer_id",
            "order_purchase_timestamp",
        },
        "customers": {
            "customer_id",
            "customer_unique_id",
        },
        "category_translation": {
            "product_category_name",
        },
    }

    MONEY_COLUMNS = [
        "gross_merchandise_value",
        "discount_amount",
        "net_merchandise_value",
        "freight_value",
        "commission",
        "seller_cost",
        "seller_payout",
        "seller_contribution",
    ]

    def __init__(
        self,
        products: pd.DataFrame,
        order_items: pd.DataFrame,
        orders: pd.DataFrame,
        customers: pd.DataFrame,
        category_translation: pd.DataFrame,
        baseline_parameters: dict[str, float],
        scenario_parameters: dict[str, float],
    ):
        """
        Initialize the scenario engine.

        Both configurations are mandatory. All five parameters must
        be explicitly supplied in each configuration.
        """

        self.products = products.copy(deep=True)
        self.order_items = order_items.copy(deep=True)
        self.orders = orders.copy(deep=True)
        self.customers = customers.copy(deep=True)
        self.category_translation = category_translation.copy(deep=True)

        self._original_products = products.copy(deep=True)
        self._original_order_items = order_items.copy(deep=True)
        self._original_orders = orders.copy(deep=True)
        self._original_customers = customers.copy(deep=True)
        self._original_category_translation = category_translation.copy(deep=True)

        # Normalize the standard Olist English category column.
        if (
            "category_english" not in self.category_translation.columns
            and "product_category_name_english"
            in self.category_translation.columns
        ):
            self.category_translation = (
                self.category_translation.rename(
                    columns={
                        "product_category_name_english": "category_english"
                    }
                )
            )

        self.baseline_parameters = self._validate_parameters(
            baseline_parameters,
            "baseline",
        )

        self.scenario_parameters = self._validate_parameters(
            scenario_parameters,
            "scenario",
        )

        self._validate_source_data()

        self.transactions = self._build_transactions()

        if self.transactions.empty:
            raise ValueError(
                "No valid transaction records were created from the "
                "provided Olist datasets."
            )

        # Preserve the merged historical transaction data.
        self._historical_transactions = self.transactions.copy(deep=True)

    # ---------------------------------------------------------
    # 1. PARAMETER VALIDATION
    # ---------------------------------------------------------

    @classmethod
    def _validate_parameters(
        cls,
        parameters: dict[str, float],
        configuration_name: str,
    ) -> dict[str, float]:

        if not isinstance(parameters, dict):
            raise TypeError(
                f"{configuration_name} parameters must be a dictionary."
            )

        missing = cls.REQUIRED_PARAMETERS - set(parameters.keys())

        extra = set(parameters.keys()) - cls.REQUIRED_PARAMETERS

        if missing:
            raise ValueError(
                f"Missing {configuration_name} parameters: "
                f"{sorted(missing)}"
            )

        if extra:
            raise ValueError(
                f"Unexpected {configuration_name} parameters: "
                f"{sorted(extra)}"
            )

        validated = {}

        for parameter in cls.REQUIRED_PARAMETERS:
            value = parameters[parameter]

            if isinstance(value, bool):
                raise ValueError(
                    f"{parameter} must be numeric, not boolean."
                )

            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{parameter} must be a valid numeric value."
                )

            if not np.isfinite(value):
                raise ValueError(
                    f"{parameter} must be finite."
                )

            validated[parameter] = value

        # Price adjustment must not reduce prices by 100% or more.
        if validated["product_price_adjustment"] <= -1:
            raise ValueError(
                "product_price_adjustment must be greater than -1."
            )

        # Freight adjustment must not reduce freight by 100% or more.
        if validated["freight_adjustment"] <= -1:
            raise ValueError(
                "freight_adjustment must be greater than -1."
            )

        rate_parameters = [
            "discount_rate",
            "seller_cost_rate",
            "commission_rate",
        ]

        for parameter in rate_parameters:
            if not 0 <= validated[parameter] <= 1:
                raise ValueError(
                    f"{parameter} must be between 0 and 1."
                )

        return validated

    # ---------------------------------------------------------
    # 2. SOURCE DATA VALIDATION
    # ---------------------------------------------------------

    def _validate_source_data(self) -> None:

        datasets = {
            "products": self.products,
            "order_items": self.order_items,
            "orders": self.orders,
            "customers": self.customers,
            "category_translation": self.category_translation,
        }

        for dataset_name, dataframe in datasets.items():

            if not isinstance(dataframe, pd.DataFrame):
                raise TypeError(
                    f"{dataset_name} must be a pandas DataFrame."
                )

            required = self.REQUIRED_COLUMNS[dataset_name]

            missing = required - set(dataframe.columns)

            if missing:
                raise ValueError(
                    f"{dataset_name} is missing required columns: "
                    f"{sorted(missing)}"
                )

        if "category_english" not in self.category_translation.columns:
            raise ValueError(
                "Category translation must contain either "
                "'category_english' or "
                "'product_category_name_english'."
            )

        # Check uniqueness of lookup keys.
        uniqueness_checks = [
            (self.products, "product_id", "products"),
            (self.orders, "order_id", "orders"),
            (self.customers, "customer_id", "customers"),
            (
                self.category_translation,
                "product_category_name",
                "category_translation",
            ),
        ]

        for dataframe, column, dataset_name in uniqueness_checks:

            if dataframe[column].duplicated().any():
                raise ValueError(
                    f"Duplicate {column} values found in {dataset_name}."
                )

        numeric_columns = [
            (self.order_items, "price"),
            (self.order_items, "freight_value"),
        ]

        for dataframe, column in numeric_columns:

            dataframe[column] = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

            if dataframe[column].isna().any():
                raise ValueError(
                    f"Invalid or missing numeric values found in "
                    f"{column}."
                )

            if not np.isfinite(dataframe[column]).all():
                raise ValueError(
                    f"Non-finite values found in {column}."
                )

            if (dataframe[column] < 0).any():
                raise ValueError(
                    f"Negative historical values found in {column}."
                )

        if self.order_items.empty:
            raise ValueError("The order_items dataset is empty.")

    # ---------------------------------------------------------
    # 3. HISTORICAL TRANSACTION CONSTRUCTION
    # ---------------------------------------------------------

    def _build_transactions(self) -> pd.DataFrame:

        transactions = self.order_items.merge(
            self.orders[
                [
                    "order_id",
                    "customer_id",
                    "order_purchase_timestamp",
                ]
            ],
            on="order_id",
            how="inner",
            validate="many_to_one",
        )

        transactions = transactions.merge(
            self.customers[
                [
                    "customer_id",
                    "customer_unique_id",
                ]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one",
        )

        transactions = transactions.merge(
            self.products[
                [
                    "product_id",
                    "product_category_name",
                ]
            ],
            on="product_id",
            how="left",
            validate="many_to_one",
        )

        transactions = transactions.merge(
            self.category_translation[
                [
                    "product_category_name",
                    "category_english",
                ]
            ],
            on="product_category_name",
            how="left",
            validate="many_to_one",
        )

        if transactions.empty:
            raise ValueError(
                "Transaction construction returned no records."
            )

        required_after_merge = [
            "product_id",
            "seller_id",
            "order_id",
            "customer_unique_id",
            "order_purchase_timestamp",
            "price",
            "freight_value",
        ]

        missing_values = transactions[
            required_after_merge
        ].isna().sum()

        missing_values = missing_values[
            missing_values > 0
        ]

        if not missing_values.empty:
            raise ValueError(
                "Missing values found in required transaction fields: "
                f"{missing_values.to_dict()}"
            )

        transactions["order_purchase_timestamp"] = pd.to_datetime(
            transactions["order_purchase_timestamp"],
            errors="coerce",
        )

        if transactions["order_purchase_timestamp"].isna().any():
            raise ValueError(
                "Invalid order_purchase_timestamp values found."
            )

        transactions["purchase_month"] = (
            transactions["order_purchase_timestamp"]
            .dt.to_period("M")
            .astype(str)
        )

        # Preserve historical values as the financial calculation base.
        transactions["historical_price"] = transactions["price"].astype(
            float
        )

        transactions["historical_freight"] = (
            transactions["freight_value"].astype(float)
        )

        return transactions.reset_index(drop=True)

    # ---------------------------------------------------------
    # 4. FINANCIAL CALCULATION
    # ---------------------------------------------------------

    @staticmethod
    def _calculate_financials(
        transactions: pd.DataFrame,
        parameters: dict[str, float],
    ) -> pd.DataFrame:

        result = transactions.copy(deep=True)

        price_adjustment = parameters[
            "product_price_adjustment"
        ]

        discount_rate = parameters["discount_rate"]

        seller_cost_rate = parameters["seller_cost_rate"]

        commission_rate = parameters["commission_rate"]

        freight_adjustment = parameters["freight_adjustment"]

        # Product price adjustment.
        result["adjusted_item_price"] = (
            result["historical_price"]
            * (1 + price_adjustment)
        )

        # Gross merchandise value after price adjustment.
        result["gross_merchandise_value"] = (
            result["adjusted_item_price"]
        )

        # Discount is calculated on adjusted gross merchandise value.
        result["discount_amount"] = (
            result["gross_merchandise_value"]
            * discount_rate
        )

        result["net_merchandise_value"] = (
            result["gross_merchandise_value"]
            - result["discount_amount"]
        )

        # Freight is calculated separately from merchandise value.
        result["freight_value"] = (
            result["historical_freight"]
            * (1 + freight_adjustment)
        )

        # Seller cost is based on historical item price.
        # It is not treated as an observed Olist cost.
        result["seller_cost"] = (
            result["historical_price"]
            * seller_cost_rate
        )

        # Olist's published commission is charged on the product value,
        # not on freight (see config/assumptions.py). The commission base
        # is therefore net merchandise value; freight is excluded.
        result["commission_base"] = result["net_merchandise_value"]
        result["commission"] = (
            result["commission_base"] * commission_rate
        )

        # Seller payout is merchandise value less total commission.
        # Freight is not added to payout as a seller revenue component.
        result["seller_payout"] = (
            result["net_merchandise_value"]
            - result["commission"]
        )

        # Seller contribution is payout minus estimated seller cost.
        result["seller_contribution"] = (
            result["seller_payout"]
            - result["seller_cost"]
        )

        # Each Olist order_items record represents one item line.
        result["item_line_count"] = 1

        return result

    # ---------------------------------------------------------
    # 5. DIMENSIONAL AGGREGATION
    # ---------------------------------------------------------

    def _aggregate_dimension(
        self,
        dataframe: pd.DataFrame,
        dimension_name: str,
        dimension_columns: list[str],
    ) -> pd.DataFrame:

        grouped = (
            dataframe
            .groupby(
                dimension_columns,
                dropna=False,
                as_index=False,
            )
            .agg(
                gross_merchandise_value=(
                    "gross_merchandise_value",
                    "sum",
                ),
                discount_amount=(
                    "discount_amount",
                    "sum",
                ),
                net_merchandise_value=(
                    "net_merchandise_value",
                    "sum",
                ),
                freight_value=(
                    "freight_value",
                    "sum",
                ),
                commission=(
                    "commission",
                    "sum",
                ),
                seller_cost=(
                    "seller_cost",
                    "sum",
                ),
                seller_payout=(
                    "seller_payout",
                    "sum",
                ),
                seller_contribution=(
                    "seller_contribution",
                    "sum",
                ),
                item_line_count=(
                    "item_line_count",
                    "sum",
                ),
            )
        )

        grouped.insert(
            0,
            "dimension",
            dimension_name,
        )

        return grouped

    def _aggregate_all_dimensions(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:

        results = {}

        for dimension_name, columns in self.DIMENSIONS.items():

            results[dimension_name] = (
                self._aggregate_dimension(
                    dataframe,
                    dimension_name,
                    columns,
                )
            )

        return results

    # ---------------------------------------------------------
    # 6. SUMMARY CALCULATION
    # ---------------------------------------------------------

    @staticmethod
    def _calculate_summary(
        dataframe: pd.DataFrame,
    ) -> dict[str, float]:

        return {
            "gross_merchandise_value": float(
                dataframe["gross_merchandise_value"].sum()
            ),
            "discount_amount": float(
                dataframe["discount_amount"].sum()
            ),
            "net_merchandise_value": float(
                dataframe["net_merchandise_value"].sum()
            ),
            "freight_value": float(
                dataframe["freight_value"].sum()
            ),
            "commission": float(
                dataframe["commission"].sum()
            ),
            "seller_cost": float(
                dataframe["seller_cost"].sum()
            ),
            "seller_payout": float(
                dataframe["seller_payout"].sum()
            ),
            "seller_contribution": float(
                dataframe["seller_contribution"].sum()
            ),
            "item_line_count": int(
                dataframe["item_line_count"].sum()
            ),
        }

    # ---------------------------------------------------------
    # 7. IMPACT CALCULATION
    # ---------------------------------------------------------

    def _calculate_impact(
        self,
        baseline_dimensions: dict[str, pd.DataFrame],
        scenario_dimensions: dict[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:

        impact_results = {}

        for dimension_name in self.DIMENSIONS:

            baseline = baseline_dimensions[
                dimension_name
            ].copy()

            scenario = scenario_dimensions[
                dimension_name
            ].copy()

            dimension_columns = self.DIMENSIONS[
                dimension_name
            ]

            merge_columns = dimension_columns + ["dimension"]

            baseline = baseline.rename(
                columns={
                    column: f"{column}_baseline"
                    for column in self.MONEY_COLUMNS + [
                        "item_line_count"
                    ]
                }
            )

            scenario = scenario.rename(
                columns={
                    column: f"{column}_scenario"
                    for column in self.MONEY_COLUMNS + [
                        "item_line_count"
                    ]
                }
            )

            merged = baseline.merge(
                scenario,
                on=merge_columns,
                how="outer",
            )

            value_columns = self.MONEY_COLUMNS + [
                "item_line_count"
            ]

            for column in value_columns:

                baseline_column = f"{column}_baseline"
                scenario_column = f"{column}_scenario"

                merged[baseline_column] = (
                    merged[baseline_column].fillna(0)
                )

                merged[scenario_column] = (
                    merged[scenario_column].fillna(0)
                )

                merged[f"{column}_impact"] = (
                    merged[scenario_column]
                    - merged[baseline_column]
                )

                if column != "item_line_count":

                    merged[f"{column}_impact_pct"] = np.where(
                        merged[baseline_column] != 0,
                        (
                            merged[f"{column}_impact"]
                            / merged[baseline_column]
                        ) * 100,
                        np.nan,
                    )

            impact_results[dimension_name] = merged

        return impact_results

    # ---------------------------------------------------------
    # 8. INDEPENDENT RECONCILIATION
    # ---------------------------------------------------------

    @staticmethod
    def _reconcile(
        transaction_results: pd.DataFrame,
        dimensional_results: dict[str, pd.DataFrame],
        summary: dict[str, float],
    ) -> dict[str, Any]:

        checks = {}

        tolerance = 1e-6

        # Independent transaction-level financial checks.
        expected_net = (
            transaction_results["gross_merchandise_value"]
            - transaction_results["discount_amount"]
        )

        expected_payout = (
            transaction_results["net_merchandise_value"]
            - transaction_results["commission"]
        )

        expected_contribution = (
            transaction_results["seller_payout"]
            - transaction_results["seller_cost"]
        )

        checks["net_merchandise_value"] = bool(
            np.allclose(
                transaction_results["net_merchandise_value"],
                expected_net,
                atol=tolerance,
            )
        )

        checks["seller_payout"] = bool(
            np.allclose(
                transaction_results["seller_payout"],
                expected_payout,
                atol=tolerance,
            )
        )

        checks["seller_contribution"] = bool(
            np.allclose(
                transaction_results["seller_contribution"],
                expected_contribution,
                atol=tolerance,
            )
        )

        # Compare transaction totals against independent dimensions.
        for metric in [
            "gross_merchandise_value",
            "discount_amount",
            "net_merchandise_value",
            "freight_value",
            "commission",
            "seller_cost",
            "seller_payout",
            "seller_contribution",
            "item_line_count",
        ]:

            transaction_total = float(
                transaction_results[metric].sum()
            )

            for dimension_name, dimension_data in (
                dimensional_results.items()
            ):

                dimension_total = float(
                    dimension_data[metric].sum()
                )

                checks[
                    f"{metric}_{dimension_name}_reconciliation"
                ] = bool(
                    np.isclose(
                        transaction_total,
                        dimension_total,
                        atol=tolerance,
                    )
                )

            checks[
                f"{metric}_summary_reconciliation"
            ] = bool(
                np.isclose(
                    transaction_total,
                    float(summary[metric]),
                    atol=tolerance,
                )
            )

        passed = all(checks.values())

        return {
            "passed": passed,
            "total_checks": len(checks),
            "passed_checks": sum(checks.values()),
            "failed_checks": [
                name
                for name, status in checks.items()
                if not status
            ],
            "checks": checks,
        }

    # ---------------------------------------------------------
    # 9. SOURCE IMMUTABILITY VALIDATION
    # ---------------------------------------------------------

    def validate_source_immutability(self) -> bool:

        return (
            self.products.equals(self._original_products)
            and self.order_items.equals(self._original_order_items)
            and self.orders.equals(self._original_orders)
            and self.customers.equals(self._original_customers)
            and self.category_translation.equals(
                self._original_category_translation
            )
        )

    # ---------------------------------------------------------
    # 10. RUN BASELINE AND SCENARIO
    # ---------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """
        Execute baseline and scenario calculations.

        Returns transaction-level results, six-dimensional
        aggregations, impacts, summaries, and validation reports.
        """

        # Baseline calculation.
        baseline_transactions = self._calculate_financials(
            self.transactions,
            self.baseline_parameters,
        )

        # Scenario calculation.
        scenario_transactions = self._calculate_financials(
            self.transactions,
            self.scenario_parameters,
        )

        # Six-dimensional aggregation.
        baseline_dimensions = self._aggregate_all_dimensions(
            baseline_transactions
        )

        scenario_dimensions = self._aggregate_all_dimensions(
            scenario_transactions
        )

        # Financial summaries.
        baseline_summary = self._calculate_summary(
            baseline_transactions
        )

        scenario_summary = self._calculate_summary(
            scenario_transactions
        )

        # Dimensional impacts.
        impact_dimensions = self._calculate_impact(
            baseline_dimensions,
            scenario_dimensions,
        )

        # Overall KPI impacts.
        overall_impact = {}

        for metric in baseline_summary:

            baseline_value = baseline_summary[metric]

            scenario_value = scenario_summary[metric]

            difference = scenario_value - baseline_value

            if metric == "item_line_count":
                percentage_change = (
                    (difference / baseline_value) * 100
                    if baseline_value != 0
                    else np.nan
                )
            else:
                percentage_change = (
                    (difference / baseline_value) * 100
                    if baseline_value != 0
                    else np.nan
                )

            overall_impact[metric] = {
                "baseline": baseline_value,
                "scenario": scenario_value,
                "impact": difference,
                "impact_pct": percentage_change,
            }

        # Independent reconciliation.
        baseline_validation = self._reconcile(
            baseline_transactions,
            baseline_dimensions,
            baseline_summary,
        )

        scenario_validation = self._reconcile(
            scenario_transactions,
            scenario_dimensions,
            scenario_summary,
        )

        # Verify historical transaction data was not modified.
        historical_unchanged = self.transactions.equals(
            self._historical_transactions
        )

        validation = {
            "baseline": baseline_validation,
            "scenario": scenario_validation,
            "historical_transactions_unchanged": (
                historical_unchanged
            ),
            "passed": (
                baseline_validation["passed"]
                and scenario_validation["passed"]
                and historical_unchanged
            ),
        }

        return {
            "status": (
                "success"
                if validation["passed"]
                else "validation_failed"
            ),
            "parameters": {
                "baseline": deepcopy(
                    self.baseline_parameters
                ),
                "scenario": deepcopy(
                    self.scenario_parameters
                ),
            },
            "baseline": {
                "summary": baseline_summary,
                "transactions": baseline_transactions,
                "dimensions": baseline_dimensions,
            },
            "scenario": {
                "summary": scenario_summary,
                "transactions": scenario_transactions,
                "dimensions": scenario_dimensions,
            },
            "impact": {
                "overall": overall_impact,
                "dimensions": impact_dimensions,
            },
            "validation": validation,
        }