
from copy import deepcopy

import pandas as pd


class MonthlyStatePayloadBuilder:
    """
    Extract aligned monthly DataFrame states into six component payloads.

    Summary states produce one dictionary per month.
    Sparse entity states produce lists of records and remain sparse.
    """

    MONTH_COLUMN = "purchase_month"

    STATE_KEYS = {
        "customer",
        "product",
        "category",
        "seller",
        "order_sales",
        "payment_revenue",
        "delivery_experience"
    }

    COMPONENT_KEYS = {
        "customer_management",
        "product_management",
        "seller_management",
        "order_sales_management",
        "payment_revenue_management",
        "delivery_customer_experience"
    }

    SUMMARY_STATES = {
        "customer": "customer_management",
        "order_sales": "order_sales_management",
        "payment_revenue": "payment_revenue_management",
        "delivery_experience": "delivery_customer_experience"
    }

    SPARSE_STATES = {
        "product": "product_management",
        "category": "product_management",
        "seller": "seller_management"
    }

    def __init__(self, aligned_states):
        if not isinstance(aligned_states, dict):
            raise TypeError(
                "aligned_states must be a dictionary."
            )

        if set(aligned_states) != self.STATE_KEYS:
            missing = self.STATE_KEYS - set(aligned_states)
            unexpected = set(aligned_states) - self.STATE_KEYS

            raise ValueError(
                f"Aligned state keys mismatch. "
                f"Missing: {sorted(missing)}; "
                f"unexpected: {sorted(unexpected)}."
            )

        self.aligned_states = {}

        for name, frame in aligned_states.items():
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(
                    f"{name}: aligned state must be a DataFrame."
                )

            if self.MONTH_COLUMN not in frame.columns:
                raise ValueError(
                    f"{name}: missing '{self.MONTH_COLUMN}' column."
                )

            if frame.empty:
                raise ValueError(
                    f"{name}: aligned state cannot be empty."
                )

            copied = frame.copy(deep=True)

            copied[self.MONTH_COLUMN] = (
                copied[self.MONTH_COLUMN].astype(str)
            )

            self.aligned_states[name] = copied

        self.timeline = self._build_timeline()

    def _build_timeline(self):
        """Validate and return the common monthly timeline."""

        summary_timelines = []

        for name in self.SUMMARY_STATES:
            months = (
                self.aligned_states[name][self.MONTH_COLUMN]
                .tolist()
            )

            if len(months) != len(set(months)):
                raise ValueError(
                    f"{name}: duplicate monthly summary records."
                )

            summary_timelines.append(months)

        reference = summary_timelines[0]

        for months in summary_timelines[1:]:
            if months != reference:
                raise ValueError(
                    "Summary states do not share the same timeline."
                )

        return reference.copy()

    @staticmethod
    def _records_for_month(frame, month):
        """Return independent record dictionaries for one month."""

        selected = frame.loc[
            frame["purchase_month"] == month
        ]

        return deepcopy(
            selected.drop(columns=["purchase_month"]).to_dict(
                orient="records"
            )
        )

    def _summary_for_month(self, state_name, month):
        """Extract exactly one summary record for a month."""

        frame = self.aligned_states[state_name]

        selected = frame.loc[
            frame[self.MONTH_COLUMN] == month
        ]

        if len(selected) != 1:
            raise ValueError(
                f"{state_name}: expected exactly one summary "
                f"record for {month}, found {len(selected)}."
            )

        return deepcopy(
            selected.drop(columns=[self.MONTH_COLUMN])
            .iloc[0]
            .to_dict()
        )

    def build(self, month):
        """
        Build the six-component payload for one simulation month.
        """

        month = str(month)

        if month not in self.timeline:
            raise ValueError(
                f"Month '{month}' is outside the aligned timeline."
            )

        payloads = {
            "customer_management": {
                "purchase_month": month,
                "summary": self._summary_for_month(
                    "customer", month
                )
            },

            "product_management": {
                "purchase_month": month,
                "products": self._records_for_month(
                    self.aligned_states["product"], month
                ),
                "categories": self._records_for_month(
                    self.aligned_states["category"], month
                )
            },

            "seller_management": {
                "purchase_month": month,
                "sellers": self._records_for_month(
                    self.aligned_states["seller"], month
                )
            },

            "order_sales_management": {
                "purchase_month": month,
                "summary": self._summary_for_month(
                    "order_sales", month
                )
            },

            "payment_revenue_management": {
                "purchase_month": month,
                "summary": self._summary_for_month(
                    "payment_revenue", month
                )
            },

            "delivery_customer_experience": {
                "purchase_month": month,
                "summary": self._summary_for_month(
                    "delivery_experience", month
                )
            }
        }

        if set(payloads) != self.COMPONENT_KEYS:
            raise RuntimeError(
                "Generated payload does not contain exactly "
                "six component states."
            )

        return deepcopy(payloads)

    def get_timeline(self):
        """Return an independent copy of the monthly timeline."""

        return self.timeline.copy()
