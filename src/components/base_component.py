
from abc import ABC, abstractmethod
from copy import deepcopy


class BaseComponent(ABC):
    """
    Base interface for all Commercial & Sales Digital Twin components.
    """

    REQUIRED_OUTPUT_KEYS = {
        "component",
        "metadata",
        "historical_state",
        "business_metrics",
        "scenario_results",
        "business_rule_results",
        "status"
    }

    def __init__(self, component_name):
        self.component_name = component_name
        self.output = None

    @abstractmethod
    def run(self, *args, **kwargs):
        """
        Execute component analysis and scenario logic.
        Every component must implement this method.
        """
        pass

    def set_output(self, output):
        """
        Validate and store the component output.
        """
        if not isinstance(output, dict):
            raise TypeError("Component output must be a dictionary.")

        missing_keys = self.REQUIRED_OUTPUT_KEYS - set(output.keys())

        if missing_keys:
            raise ValueError(
                f"Missing required output keys: {sorted(missing_keys)}"
            )

        if output["component"] != self.component_name:
            raise ValueError("Component name mismatch in output.")

        if output["status"] not in {"SUCCESS", "FAILED"}:
            raise ValueError("Invalid component execution status.")

        self.output = deepcopy(output)

    def get_output(self):
        """
        Return a copy of the component output.
        """
        if self.output is None:
            raise RuntimeError(
                f"{self.component_name} has not been executed yet."
            )

        return deepcopy(self.output)
