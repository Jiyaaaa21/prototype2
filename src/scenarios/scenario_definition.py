
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScenarioDefinition:
    """
    Immutable definition of a business scenario.

    Stores scenario configuration and validates its structure
    before the scenario is passed to an execution engine.
    """

    scenario_id: str
    name: str
    target_component: str
    target_variable: str
    adjustment_type: str
    adjustment_value: float
    scope: dict[str, Any]
    assumptions: tuple[str, ...]

    VALID_ADJUSTMENT_TYPES = (
        "percentage_increase",
        "percentage_decrease",
        "absolute_increase",
        "absolute_decrease",
        "set_value"
    )

    VALID_COMPONENTS = (
        "customer_management",
        "product_management",
        "seller_management",
        "order_sales_management",
        "payment_revenue_management",
        "delivery_customer_experience"
    )

    def __post_init__(self):
        self.validate()

    def validate(self) -> bool:
        """Validate the scenario definition."""

        # Scenario ID
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError(
                "Scenario ID must be a non-empty string."
            )

        # Scenario name
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(
                "Scenario name must be a non-empty string."
            )

        # Target component
        if self.target_component not in self.VALID_COMPONENTS:
            raise ValueError(
                f"Invalid target component: {self.target_component}"
            )

        # Target variable
        if not isinstance(self.target_variable, str) or not self.target_variable.strip():
            raise ValueError(
                "Target variable must be a non-empty string."
            )

        # Adjustment type
        if self.adjustment_type not in self.VALID_ADJUSTMENT_TYPES:
            raise ValueError(
                f"Invalid adjustment type: {self.adjustment_type}"
            )

        # Adjustment value
        if isinstance(self.adjustment_value, bool) or not isinstance(
            self.adjustment_value, (int, float)
        ):
            raise TypeError(
                "Adjustment value must be numeric."
            )

        # Percentage validation
        if self.adjustment_type in (
            "percentage_increase",
            "percentage_decrease"
        ):
            if not 0 <= self.adjustment_value <= 100:
                raise ValueError(
                    "Percentage adjustment must be between 0 and 100."
                )

        # Absolute adjustment validation
        if self.adjustment_type in (
            "absolute_increase",
            "absolute_decrease",
            "set_value"
        ):
            if self.adjustment_value < 0:
                raise ValueError(
                    "Adjustment value cannot be negative."
                )

        # Scope validation
        if not isinstance(self.scope, dict):
            raise TypeError(
                "Scenario scope must be a dictionary."
            )

        # Assumptions validation
        if not isinstance(self.assumptions, tuple) or not self.assumptions:
            raise ValueError(
                "At least one explicit scenario assumption is required."
            )

        for assumption in self.assumptions:
            if not isinstance(assumption, str) or not assumption.strip():
                raise ValueError(
                    "Every assumption must be a non-empty string."
                )

        return True

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the scenario."""

        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "target_component": self.target_component,
            "target_variable": self.target_variable,
            "adjustment_type": self.adjustment_type,
            "adjustment_value": self.adjustment_value,
            "scope": dict(self.scope),
            "assumptions": list(self.assumptions)
        }
