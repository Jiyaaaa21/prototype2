
import numpy as np
import pandas as pd

from copy import deepcopy

from src.scenarios.scenario_definition import ScenarioDefinition


class ScenarioExecutionEngine:
    """
    Executes validated business scenarios against component-state
    DataFrames without modifying the original input states.
    """

    SUPPORTED_SCOPES = (
        "all_records",
        "all_products_with_historical_sales",
        "filter"
    )

    def execute(
        self,
        definition: ScenarioDefinition,
        component_states: dict[str, pd.DataFrame]
    ) -> dict:
        """
        Execute a scenario and return isolated baseline and scenario states.
        """

        if not isinstance(definition, ScenarioDefinition):
            raise TypeError(
                "definition must be a ScenarioDefinition instance."
            )

        definition.validate()

        if not isinstance(component_states, dict):
            raise TypeError("Component states must be a dictionary.")

        if definition.target_component not in component_states:
            raise KeyError(
                f"Target component not found: {definition.target_component}"
            )

        for component_name, frame in component_states.items():
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(
                    f"State for {component_name} must be a DataFrame."
                )

        target_state = component_states[definition.target_component]

        if definition.target_variable not in target_state.columns:
            raise KeyError(
                f"Target variable '{definition.target_variable}' "
                f"not found in {definition.target_component} state."
            )

        baseline_states = {
            name: frame.copy(deep=True)
            for name, frame in component_states.items()
        }

        scenario_states = {
            name: frame.copy(deep=True)
            for name, frame in component_states.items()
        }

        scenario_target = scenario_states[definition.target_component]

        selected_mask = self._resolve_scope(
            definition.scope,
            scenario_target
        )

        affected_records = int(selected_mask.sum())

        if affected_records == 0:
            raise ValueError(
                "Scenario scope selected zero records."
            )

        selected_values = pd.to_numeric(
            scenario_target.loc[
                selected_mask,
                definition.target_variable
            ],
            errors="coerce"
        )

        if selected_values.isna().any():
            raise ValueError(
                "Target variable contains missing or non-numeric "
                "values in the selected scope."
            )

        if not np.isfinite(selected_values.to_numpy(dtype=float)).all():
            raise ValueError(
                "Target variable contains non-finite values."
            )

        baseline_values = selected_values.copy(deep=True)

        adjusted_values = self._apply_adjustment(
            baseline_values,
            definition.adjustment_type,
            definition.adjustment_value
        )

        if not np.isfinite(adjusted_values.to_numpy(dtype=float)).all():
            raise ValueError(
                "Scenario produced non-finite values."
            )

        if (adjusted_values < 0).any():
            raise ValueError(
                "Scenario cannot produce negative target values."
            )

        scenario_target.loc[
            selected_mask,
            definition.target_variable
        ] = adjusted_values

        scenario_values = scenario_target.loc[
            selected_mask,
            definition.target_variable
        ].copy(deep=True)

        return {
            "execution_report": {
                "scenario_id": definition.scenario_id,
                "scenario_name": definition.name,
                "status": "SUCCESS",
                "target_component": definition.target_component,
                "target_variable": definition.target_variable,
                "adjustment_type": definition.adjustment_type,
                "adjustment_value": definition.adjustment_value,
                "scope": deepcopy(definition.scope),
                "affected_records": affected_records
            },
            "baseline_states": baseline_states,
            "scenario_states": scenario_states,
            "baseline_values": baseline_values.copy(deep=True),
            "scenario_values": scenario_values.copy(deep=True)
        }

    def _resolve_scope(
        self,
        scope: dict,
        state: pd.DataFrame
    ) -> pd.Series:
        """Resolve the records affected by a scenario."""

        scope_type = scope.get("type")

        if scope_type not in self.SUPPORTED_SCOPES:
            raise ValueError(
                f"Unsupported scenario scope: {scope_type}"
            )

        if scope_type == "all_records":
            return pd.Series(True, index=state.index)

        if scope_type == "all_products_with_historical_sales":

            if "item_line_count" in state.columns:
                return (
                    pd.to_numeric(
                        state["item_line_count"],
                        errors="coerce"
                    ).fillna(0) > 0
                )

            if "product_id" in state.columns:
                return state["product_id"].notna()

            raise ValueError(
                "Historical-sales scope requires either "
                "'item_line_count' or 'product_id'."
            )

        if scope_type == "filter":

            filters = scope.get("filters")

            if not isinstance(filters, dict) or not filters:
                raise ValueError(
                    "Filter scope requires a non-empty filters dictionary."
                )

            mask = pd.Series(True, index=state.index)

            for column, expected_value in filters.items():

                if column not in state.columns:
                    raise KeyError(
                        f"Scope filter column not found: {column}"
                    )

                if isinstance(expected_value, list):
                    mask &= state[column].isin(expected_value)
                else:
                    mask &= state[column].eq(expected_value)

            return mask

        raise ValueError("Unable to resolve scenario scope.")

    @staticmethod
    def _apply_adjustment(
        values: pd.Series,
        adjustment_type: str,
        adjustment_value: float
    ) -> pd.Series:
        """Apply the requested adjustment to selected values."""

        if adjustment_type == "percentage_increase":
            return values * (1 + adjustment_value / 100)

        if adjustment_type == "percentage_decrease":
            return values * (1 - adjustment_value / 100)

        if adjustment_type == "absolute_increase":
            return values + adjustment_value

        if adjustment_type == "absolute_decrease":
            return values - adjustment_value

        if adjustment_type == "set_value":
            return pd.Series(
                adjustment_value,
                index=values.index,
                dtype=float
            )

        raise ValueError(
            f"Unsupported adjustment type: {adjustment_type}"
        )
