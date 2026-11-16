from copy import deepcopy

import pandas as pd


class StateManager:
    """
    Maintains immutable historical component outputs and
    separate monthly simulation states.

    Historical outputs are never modified by simulation updates.
    """

    COMPONENTS = {
        "customer_management",
        "product_management",
        "seller_management",
        "order_sales_management",
        "payment_revenue_management",
        "delivery_customer_experience"
    }

    REQUIRED_OUTPUT_KEYS = {
        "component",
        "metadata",
        "historical_state",
        "business_metrics",
        "scenario_results",
        "business_rule_results",
        "status"
    }

    def __init__(self):

        self._historical_states = {}
        self._simulation_states = {}
        self._current_period = None
        self._current_state = None

    def _validate_component(self, component_name):

        if component_name not in self.COMPONENTS:
            raise ValueError(
                f"Unknown component: {component_name}"
            )

    def _validate_output(self, component_name, output):

        if not isinstance(output, dict):
            raise TypeError(
                "Component output must be a dictionary."
            )

        missing_keys = self.REQUIRED_OUTPUT_KEYS - set(output)

        if missing_keys:
            raise ValueError(
                f"Missing output keys: {sorted(missing_keys)}"
            )

        if output["component"] != component_name:
            raise ValueError(
                "Component name does not match output."
            )

        if output["status"] != "SUCCESS":
            raise ValueError(
                "Only successfully executed component outputs "
                "can be registered as historical states."
            )

        expected_types = {
            "metadata": dict,
            "historical_state": dict,
            "business_metrics": dict,
            "scenario_results": list,
            "business_rule_results": list
        }

        for key, expected_type in expected_types.items():
            if not isinstance(output[key], expected_type):
                raise TypeError(
                    f"Output field '{key}' must be "
                    f"{expected_type.__name__}."
                )

    def register_historical_state(self, component_name, output):
        """Register one successfully executed component output."""

        self._validate_component(component_name)
        self._validate_output(component_name, output)

        if self._current_state is not None:
            raise RuntimeError(
                "Cannot register historical outputs after "
                "simulation initialization."
            )

        if component_name in self._historical_states:
            raise ValueError(
                f"Historical state already registered: {component_name}"
            )

        self._historical_states[component_name] = deepcopy(output)

        return True

    def register_all_historical_states(self, component_outputs):
        """Register outputs for all six components."""

        if not isinstance(component_outputs, dict):
            raise TypeError(
                "component_outputs must be a dictionary."
            )

        if set(component_outputs) != self.COMPONENTS:
            raise ValueError(
                "Exactly six registered component outputs are required."
            )

        if self._historical_states:
            raise RuntimeError(
                "Historical states have already been registered."
            )

        for component_name, output in component_outputs.items():
            self._validate_component(component_name)
            self._validate_output(component_name, output)

        self._historical_states = deepcopy(component_outputs)

        return True

    def initialize_simulation_state(self, period):
        """Create the first independent simulation state."""

        if set(self._historical_states) != self.COMPONENTS:
            raise RuntimeError(
                "All six historical component states must be "
                "registered before simulation initialization."
            )

        if self._current_state is not None:
            raise RuntimeError(
                "Simulation state has already been initialized."
            )

        normalized_period = str(pd.Period(period, freq="M"))

        self._current_period = normalized_period
        self._current_state = deepcopy(self._historical_states)

        self._simulation_states[normalized_period] = deepcopy(
            self._current_state
        )

        return self.get_simulation_state()

    def set_current_period(self, period):
        """
        Move to a monthly simulation period.

        Existing snapshots are restored. A new period inherits
        the previous current simulation state.
        """

        if self._current_state is None:
            raise RuntimeError(
                "Initialize simulation state first."
            )

        normalized_period = str(pd.Period(period, freq="M"))

        if normalized_period in self._simulation_states:
            self._current_state = deepcopy(
                self._simulation_states[normalized_period]
            )

        else:
            requested = pd.Period(normalized_period, freq="M")
            current = pd.Period(self._current_period, freq="M")

            if requested <= current:
                raise ValueError(
                    "A new simulation period must be later than "
                    "the current period."
                )

            self._simulation_states[normalized_period] = deepcopy(
                self._current_state
            )

            self._current_state = deepcopy(
                self._simulation_states[normalized_period]
            )

        self._current_period = normalized_period

        return self.get_simulation_state()

    def update_component_state(self, component_name, state):
        """Update one component in the current simulation period."""

        self._validate_component(component_name)

        if self._current_state is None:
            raise RuntimeError(
                "Initialize simulation state first."
            )

        if not isinstance(state, dict):
            raise TypeError(
                "Simulation component state must be a dictionary."
            )

        self._current_state[component_name] = deepcopy(state)

        self._simulation_states[self._current_period] = deepcopy(
            self._current_state
        )

        return True

    
    def update_all_component_states(self, component_states):
        """
        Atomically update all six component states for the current month.

        The historical component outputs remain unchanged.
        No partial update is committed if validation fails.
        """

        if self._current_state is None:
            raise RuntimeError(
                "Initialize simulation state first."
            )

        if not isinstance(component_states, dict):
            raise TypeError(
                "component_states must be a dictionary."
            )

        if set(component_states) != self.COMPONENTS:
            missing = self.COMPONENTS - set(component_states)
            unexpected = set(component_states) - self.COMPONENTS

            raise ValueError(
                f"Component state keys mismatch. "
                f"Missing: {sorted(missing)}; "
                f"unexpected: {sorted(unexpected)}."
            )

        for component_name, state in component_states.items():
            if not isinstance(state, dict):
                raise TypeError(
                    f"{component_name}: state must be a dictionary."
                )

        updated_state = deepcopy(component_states)

        self._current_state = updated_state
        self._simulation_states[self._current_period] = deepcopy(
            updated_state
        )

        return True


    def get_historical_state(self, component_name=None):
        """Return historical outputs without exposing internal objects."""

        if component_name is not None:
            self._validate_component(component_name)

            if component_name not in self._historical_states:
                raise KeyError(
                    f"No historical state registered for {component_name}."
                )

            return deepcopy(self._historical_states[component_name])

        return deepcopy(self._historical_states)

    def get_simulation_state(self, period=None):
        """Return the current or requested monthly simulation snapshot."""

        if self._current_state is None:
            raise RuntimeError(
                "Simulation state has not been initialized."
            )

        if period is None:
            return {
                "period": self._current_period,
                "components": deepcopy(self._current_state)
            }

        normalized_period = str(pd.Period(period, freq="M"))

        if normalized_period not in self._simulation_states:
            raise KeyError(
                f"No simulation snapshot exists for {normalized_period}."
            )

        return {
            "period": normalized_period,
            "components": deepcopy(
                self._simulation_states[normalized_period]
            )
        }

    def get_available_periods(self):
        """Return all stored simulation periods in chronological order."""

        return tuple(
            sorted(self._simulation_states.keys())
        )

    def reset_simulation_state(self):
        """Discard simulation snapshots and restore historical baseline."""

        if not self._historical_states:
            raise RuntimeError(
                "No historical states are registered."
            )

        self._simulation_states = {}
        self._current_period = None
        self._current_state = None

        return True