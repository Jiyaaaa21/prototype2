import pandas as pd


class TimeManager:
    """
    Manages monthly historical replay for the
    Commercial & Sales Digital Twin.

    The historical date range is derived from
    order_purchase_timestamp in the supplied dataset.
    """

    REQUIRED_COLUMNS = {"order_purchase_timestamp"}

    def __init__(self, orders_df):

        if not isinstance(orders_df, pd.DataFrame):
            raise TypeError("orders_df must be a pandas DataFrame.")

        missing_columns = self.REQUIRED_COLUMNS - set(orders_df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        if orders_df.empty:
            raise ValueError("Orders DataFrame cannot be empty.")

        timestamps = pd.to_datetime(
            orders_df["order_purchase_timestamp"],
            errors="coerce"
        )

        valid_timestamps = timestamps.dropna()

        if valid_timestamps.empty:
            raise ValueError(
                "No valid order purchase timestamps were found."
            )

        self.invalid_timestamp_count = int(timestamps.isna().sum())

        self.start_timestamp = valid_timestamps.min()
        self.end_timestamp = valid_timestamps.max()

        self.start_period = self.start_timestamp.to_period("M")
        self.end_period = self.end_timestamp.to_period("M")

        self._timeline = pd.period_range(
            start=self.start_period,
            end=self.end_period,
            freq="M"
        )

        self._current_index = 0

    def get_date_range(self):
        """Return the derived historical date range."""

        return {
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "start_period": str(self.start_period),
            "end_period": str(self.end_period),
            "total_months": len(self._timeline),
            "invalid_timestamp_count": self.invalid_timestamp_count
        }

    def get_timeline(self):
        """Return the complete chronological monthly timeline."""

        return tuple(str(period) for period in self._timeline)

    def get_current_period(self):
        """Return the current simulation month."""

        return str(self._timeline[self._current_index])

    def get_next_period(self):
        """
        Advance the simulation by one month.

        Return None when the historical timeline is complete.
        """

        if self._current_index >= len(self._timeline) - 1:
            return None

        self._current_index += 1

        return self.get_current_period()

    def reset(self):
        """Reset the simulation to the first historical month."""

        self._current_index = 0

        return self.get_current_period()

    def validate_period(self, period):
        """Check whether a requested month falls within history."""

        try:
            requested_period = pd.Period(period, freq="M")
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid monthly period: {period}"
            )

        if not self.start_period <= requested_period <= self.end_period:
            raise ValueError(
                f"Period {requested_period} is outside the historical "
                f"range {self.start_period} to {self.end_period}."
            )

        return True

    def set_current_period(self, period):
        """Set the simulation to a validated historical month."""

        self.validate_period(period)

        requested_period = pd.Period(period, freq="M")

        self._current_index = self._timeline.get_loc(requested_period)

        return self.get_current_period()

    def is_complete(self):
        """Check whether the final historical month has been reached."""

        return self._current_index == len(self._timeline) - 1