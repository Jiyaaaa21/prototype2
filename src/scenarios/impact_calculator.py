
import numpy as np
import pandas as pd


class CrossComponentImpactCalculator:
    """
    Calculates the impact of a business scenario across six
    business dimensions using transaction-level data.

    This class does not modify its input DataFrames.
    """

    DIMENSIONS = {
        "product": ["product_id"],
        "category": ["category_english"],
        "seller": ["seller_id"],
        "customer": ["customer_unique_id"],
        "order": ["order_id"],
        "monthly": ["purchase_month"]
    }

    REQUIRED_COLUMNS = {
        "product_id",
        "category_english",
        "seller_id",
        "customer_unique_id",
        "order_id",
        "purchase_month",
        "price",
        "freight_value"
    }

    def calculate(
        self,
        baseline_transactions: pd.DataFrame,
        scenario_transactions: pd.DataFrame
    ) -> dict:
        """
        Calculate baseline, scenario, and impact aggregates
        for all six business dimensions.
        """

        self._validate_inputs(
            baseline_transactions,
            scenario_transactions
        )

        baseline = baseline_transactions.copy(deep=True)
        scenario = scenario_transactions.copy(deep=True)

        self._validate_transaction_alignment(
            baseline,
            scenario
        )

        baseline["price"] = pd.to_numeric(
            baseline["price"],
            errors="raise"
        )

        scenario["price"] = pd.to_numeric(
            scenario["price"],
            errors="raise"
        )

        baseline["freight_value"] = pd.to_numeric(
            baseline["freight_value"],
            errors="raise"
        )

        scenario["freight_value"] = pd.to_numeric(
            scenario["freight_value"],
            errors="raise"
        )

        self._validate_numeric_values(baseline, "baseline")
        self._validate_numeric_values(scenario, "scenario")

        baseline_results = {}
        scenario_results = {}
        impact_results = {}

        for dimension, keys in self.DIMENSIONS.items():

            baseline_aggregate = self._aggregate(
                baseline,
                keys
            )

            scenario_aggregate = self._aggregate(
                scenario,
                keys
            )

            impact = self._calculate_impact(
                baseline_aggregate,
                scenario_aggregate,
                keys
            )

            baseline_results[dimension] = baseline_aggregate
            scenario_results[dimension] = scenario_aggregate
            impact_results[dimension] = impact

        self._validate_reconciliation(impact_results)

        return {
            "baseline": baseline_results,
            "scenario": scenario_results,
            "impact": impact_results,
            "summary": self._build_summary(impact_results)
        }

    def _validate_inputs(
        self,
        baseline: pd.DataFrame,
        scenario: pd.DataFrame
    ) -> None:
        """Validate transaction-level input DataFrames."""

        if not isinstance(baseline, pd.DataFrame):
            raise TypeError(
                "Baseline transactions must be a DataFrame."
            )

        if not isinstance(scenario, pd.DataFrame):
            raise TypeError(
                "Scenario transactions must be a DataFrame."
            )

        missing_baseline = self.REQUIRED_COLUMNS - set(baseline.columns)
        missing_scenario = self.REQUIRED_COLUMNS - set(scenario.columns)

        if missing_baseline:
            raise ValueError(
                f"Baseline missing columns: {sorted(missing_baseline)}"
            )

        if missing_scenario:
            raise ValueError(
                f"Scenario missing columns: {sorted(missing_scenario)}"
            )

        if baseline.empty or scenario.empty:
            raise ValueError(
                "Baseline and scenario transactions cannot be empty."
            )

    @staticmethod
    def _validate_transaction_alignment(
        baseline: pd.DataFrame,
        scenario: pd.DataFrame
    ) -> None:
        """
        Ensure both datasets contain the same transaction records
        in the same order.
        """

        if len(baseline) != len(scenario):
            raise ValueError(
                "Baseline and scenario transaction counts differ."
            )

        alignment_columns = [
            "product_id",
            "category_english",
            "seller_id",
            "customer_unique_id",
            "order_id",
            "purchase_month",
            "freight_value"
        ]

        for column in alignment_columns:

            left = baseline[column].reset_index(drop=True)
            right = scenario[column].reset_index(drop=True)

            if not left.equals(right):
                raise ValueError(
                    f"Transaction alignment failed for column: {column}"
                )

    @staticmethod
    def _validate_numeric_values(
        frame: pd.DataFrame,
        label: str
    ) -> None:
        """Reject missing, non-finite, or negative financial values."""

        for column in ["price", "freight_value"]:

            values = frame[column].to_numpy(dtype=float)

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{label} {column} contains non-finite values."
                )

            if (values < 0).any():
                raise ValueError(
                    f"{label} {column} contains negative values."
                )

    @staticmethod
    def _aggregate(
        transactions: pd.DataFrame,
        keys: list
    ) -> pd.DataFrame:
        """Aggregate transaction data at a specified business grain."""

        result = (
            transactions
            .groupby(keys, dropna=False, as_index=False)
            .agg(
                item_line_count=("order_id", "size"),
                distinct_orders=("order_id", "nunique"),
                merchandise_value=("price", "sum"),
                freight_value=("freight_value", "sum")
            )
        )

        return result.sort_values(
            keys,
            na_position="last"
        ).reset_index(drop=True)

    @staticmethod
    def _calculate_impact(
        baseline: pd.DataFrame,
        scenario: pd.DataFrame,
        keys: list
    ) -> pd.DataFrame:
        """Compare baseline and scenario aggregates."""

        comparison = baseline.merge(
            scenario,
            on=keys,
            how="outer",
            suffixes=("_baseline", "_scenario"),
            indicator=True,
            validate="one_to_one"
        )

        if not (comparison["_merge"] == "both").all():
            raise ValueError(
                "Baseline and scenario business dimensions do not align."
            )

        comparison.drop(columns="_merge", inplace=True)

        comparison["merchandise_value_change"] = (
            comparison["merchandise_value_scenario"]
            - comparison["merchandise_value_baseline"]
        )

        comparison["merchandise_value_change_pct"] = np.where(
            comparison["merchandise_value_baseline"] != 0,
            (
                comparison["merchandise_value_change"]
                / comparison["merchandise_value_baseline"]
            ) * 100,
            np.nan
        )

        comparison["freight_value_change"] = (
            comparison["freight_value_scenario"]
            - comparison["freight_value_baseline"]
        )

        return comparison

    @staticmethod
    def _validate_reconciliation(
        impacts: dict
    ) -> None:
        """Ensure every dimension reconciles to the same total change."""

        totals = {
            dimension: float(
                frame["merchandise_value_change"].sum()
            )
            for dimension, frame in impacts.items()
        }

        reference = totals["order"]

        for dimension, total in totals.items():

            if not np.isclose(
                total,
                reference,
                rtol=1e-9,
                atol=0.01
            ):
                raise ValueError(
                    f"Merchandise value reconciliation failed for "
                    f"{dimension}: {total} != {reference}"
                )

        for dimension, frame in impacts.items():

            if not np.allclose(
                frame["freight_value_change"].to_numpy(dtype=float),
                0.0,
                atol=0.01
            ):
                raise ValueError(
                    f"Unexpected freight change in {dimension} impact."
                )

    @staticmethod
    def _build_summary(impacts: dict) -> dict:
        """Build a summary of cross-component impacts."""

        order_impact = impacts["order"]

        baseline_value = float(
            order_impact["merchandise_value_baseline"].sum()
        )

        scenario_value = float(
            order_impact["merchandise_value_scenario"].sum()
        )

        change = scenario_value - baseline_value

        percentage = (
            (change / baseline_value) * 100
            if baseline_value != 0
            else None
        )

        return {
            "baseline_merchandise_value": baseline_value,
            "scenario_merchandise_value": scenario_value,
            "merchandise_value_change": change,
            "merchandise_value_change_pct": percentage,
            "dimensions_validated": list(impacts.keys()),
            "reconciliation_status": "PASSED"
        }
