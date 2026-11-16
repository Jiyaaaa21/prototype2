
from copy import deepcopy

import pandas as pd


class MonthlyStateAligner:
    """
    Align monthly component states to a common simulation timeline.

    Summary states have one row per month and are reindexed to the full
    timeline. Entity-level states remain sparse and retain their original
    entity-month grain.

    Each specification must define:
        entity_keys: [] for monthly summary states, or entity key columns
                     for sparse entity-level states.
        zero_fill_columns: columns to set to zero only when a timeline
                           month is absent from a summary state.
    """

    MONTH_COLUMN = "purchase_month"

    def __init__(self, timeline, specifications):
        if not isinstance(specifications, dict) or not specifications:
            raise ValueError("Specifications must be a non-empty dictionary.")

        self.timeline = self._normalize_timeline(timeline)
        self.specifications = deepcopy(specifications)

    @classmethod
    def _normalize_month(cls, values):
        try:
            return pd.PeriodIndex(
                pd.to_datetime(values, errors="raise"),
                freq="M"
            ).astype(str)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "purchase_month values must be valid monthly dates "
                "or YYYY-MM strings."
            ) from exc

    @classmethod
    def _normalize_timeline(cls, timeline):
        if isinstance(timeline, pd.PeriodIndex):
            periods = timeline.asfreq("M")
        else:
            try:
                periods = pd.PeriodIndex(
                    pd.to_datetime(list(timeline), errors="raise"),
                    freq="M"
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid simulation timeline.") from exc

        if len(periods) == 0:
            raise ValueError("Simulation timeline cannot be empty.")

        if periods.has_duplicates:
            raise ValueError("Simulation timeline contains duplicate months.")

        periods = periods.sort_values()

        expected = pd.period_range(
            start=periods.min(),
            end=periods.max(),
            freq="M"
        )

        if not periods.equals(expected):
            raise ValueError("Simulation timeline must be continuous.")

        return periods.astype(str).tolist()

    def _validate_specification(self, name, specification):
        if not isinstance(specification, dict):
            raise TypeError(f"{name}: specification must be a dictionary.")

        entity_keys = specification.get("entity_keys")
        zero_fill_columns = specification.get("zero_fill_columns", [])

        if not isinstance(entity_keys, list):
            raise ValueError(
                f"{name}: entity_keys must be a list. "
                "Use [] for monthly summary states."
            )

        if not isinstance(zero_fill_columns, list):
            raise ValueError(
                f"{name}: zero_fill_columns must be a list."
            )

        if len(set(entity_keys)) != len(entity_keys):
            raise ValueError(f"{name}: duplicate entity key columns.")

        if len(set(zero_fill_columns)) != len(zero_fill_columns):
            raise ValueError(f"{name}: duplicate zero-fill columns.")

        if self.MONTH_COLUMN in entity_keys:
            raise ValueError(
                f"{name}: purchase_month is managed by the aligner "
                "and must not be included in entity_keys."
            )

        if entity_keys and zero_fill_columns:
            raise ValueError(
                f"{name}: zero_fill_columns applies only to monthly "
                "summary states, not sparse entity states."
            )

        return entity_keys, zero_fill_columns

    def _validate_frame(self, name, frame, entity_keys):
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f"{name}: monthly state must be a DataFrame.")

        if frame.empty:
            raise ValueError(f"{name}: monthly state cannot be empty.")

        if self.MONTH_COLUMN not in frame.columns:
            raise ValueError(
                f"{name}: missing required column '{self.MONTH_COLUMN}'."
            )

        required_keys = [self.MONTH_COLUMN] + entity_keys
        missing = set(required_keys) - set(frame.columns)

        if missing:
            raise ValueError(
                f"{name}: missing key columns {sorted(missing)}."
            )

        if frame[required_keys].isna().any().any():
            raise ValueError(f"{name}: null values found in key columns.")

        result = frame.copy(deep=True)
        result[self.MONTH_COLUMN] = self._normalize_month(
            result[self.MONTH_COLUMN]
        )

        outside_timeline = (
            set(result[self.MONTH_COLUMN]) - set(self.timeline)
        )

        if outside_timeline:
            raise ValueError(
                f"{name}: months outside simulation timeline: "
                f"{sorted(outside_timeline)}."
            )

        duplicate_keys = required_keys

        if result.duplicated(duplicate_keys).any():
            raise ValueError(
                f"{name}: duplicate records found for "
                f"{duplicate_keys}."
            )

        return result

    def _align_summary(self, name, frame, zero_fill_columns):
        missing_columns = (
            set(zero_fill_columns) - set(frame.columns)
        )

        if missing_columns:
            raise ValueError(
                f"{name}: zero-fill columns not found: "
                f"{sorted(missing_columns)}."
            )

        for column in zero_fill_columns:
            if not pd.api.types.is_numeric_dtype(frame[column]):
                raise TypeError(
                    f"{name}: zero-fill column '{column}' must be numeric."
                )

        indexed = frame.set_index(self.MONTH_COLUMN)

        aligned = indexed.reindex(self.timeline)
        missing_month_mask = ~aligned.index.isin(indexed.index)

        for column in zero_fill_columns:
            aligned.loc[missing_month_mask, column] = 0

        aligned.index.name = self.MONTH_COLUMN

        return aligned.reset_index()

    def _preserve_sparse_state(self, frame, entity_keys):
        sort_columns = [self.MONTH_COLUMN] + entity_keys

        return (
            frame.sort_values(sort_columns)
            .reset_index(drop=True)
            .copy(deep=True)
        )

    def align(self, monthly_states):
        """
        Return aligned monthly states as independent DataFrame copies.
        """

        if not isinstance(monthly_states, dict):
            raise TypeError("monthly_states must be a dictionary.")

        if set(monthly_states) != set(self.specifications):
            missing = set(self.specifications) - set(monthly_states)
            unexpected = set(monthly_states) - set(self.specifications)

            raise ValueError(
                f"Monthly state keys mismatch. "
                f"Missing: {sorted(missing)}; "
                f"unexpected: {sorted(unexpected)}."
            )

        aligned_states = {}

        for name, frame in monthly_states.items():
            specification = self.specifications[name]

            entity_keys, zero_fill_columns = (
                self._validate_specification(name, specification)
            )

            validated = self._validate_frame(
                name,
                frame,
                entity_keys
            )

            if entity_keys:
                aligned = self._preserve_sparse_state(
                    validated,
                    entity_keys
                )
            else:
                aligned = self._align_summary(
                    name,
                    validated,
                    zero_fill_columns
                )

            aligned_states[name] = aligned

        return aligned_states
