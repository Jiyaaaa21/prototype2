

from src.relationships.dependency_manager import DependencyManager
from src.simulation.state_manager import StateManager
from src.simulation.time_manager import TimeManager


class SimulationEngine:
    """
    Orchestrates Phase 1 historical execution of all six
    Commercial & Sales Digital Twin components.

    Responsibilities:
    - Execute components in dependency-aware order.
    - Continue independent execution after failures.
    - Skip components whose prerequisites did not succeed.
    - Register historical outputs only after all components succeed.
    - Initialize the simulation at the first historical month.
    """

    COMPONENTS = {
        "customer_management",
        "product_management",
        "seller_management",
        "order_sales_management",
        "payment_revenue_management",
        "delivery_customer_experience"
    }

    def __init__(
        self,
        components,
        dependency_manager,
        time_manager,
        state_manager
    ):

        if not isinstance(components, dict):
            raise TypeError("components must be a dictionary.")

        if set(components) != self.COMPONENTS:
            raise ValueError(
                "Exactly six component instances must be provided."
            )

        if not isinstance(dependency_manager, DependencyManager):
            raise TypeError(
                "dependency_manager must be a DependencyManager."
            )

        if not isinstance(time_manager, TimeManager):
            raise TypeError(
                "time_manager must be a TimeManager."
            )

        if not isinstance(state_manager, StateManager):
            raise TypeError(
                "state_manager must be a StateManager."
            )

        for name, component in components.items():

            if not callable(getattr(component, "run", None)):
                raise TypeError(
                    f"Component '{name}' must implement run()."
                )

            component_name = getattr(component, "component_name", None)

            if component_name != name:
                raise ValueError(
                    f"Component instance name mismatch for '{name}'."
                )

        self.components = components
        self.dependency_manager = dependency_manager
        self.time_manager = time_manager
        self.state_manager = state_manager

        self.execution_report = None
        self.monthly_replay_report = None

    def _get_prerequisites(self):
        """Build a dependent-to-prerequisites mapping."""

        prerequisites = {
            component: set()
            for component in self.COMPONENTS
        }

        dependencies = self.dependency_manager.get_dependencies()

        for prerequisite, dependents in dependencies.items():
            for dependent in dependents:
                prerequisites[dependent].add(prerequisite)

        return prerequisites

    def _validate_component_output(self, component_name, output):
        """Validate the standardized successful component output."""

        if not isinstance(output, dict):
            raise TypeError(
                "Component run() must return a dictionary."
            )

        required_keys = {
            "component",
            "metadata",
            "historical_state",
            "business_metrics",
            "scenario_results",
            "business_rule_results",
            "status"
        }

        missing_keys = required_keys - set(output)

        if missing_keys:
            raise ValueError(
                f"Component output is missing keys: {sorted(missing_keys)}"
            )

        if output["component"] != component_name:
            raise ValueError(
                "Component output name does not match its registered name."
            )

        if output["status"] != "SUCCESS":
            raise RuntimeError(
                f"Component returned status: {output['status']}"
            )

        return output

    def run_historical_execution(self):
        """
        Execute all eligible components and initialize the
        historical simulation baseline when all succeed.
        """

        if self.execution_report is not None:
            raise RuntimeError(
                "Historical execution has already been attempted."
            )

        self.dependency_manager.validate_dependencies()

        execution_order = self.dependency_manager.get_execution_order()
        prerequisites = self._get_prerequisites()

        component_outputs = {}
        execution_results = {}

        for component_name in execution_order:

            failed_prerequisites = [
                prerequisite
                for prerequisite in prerequisites[component_name]
                if execution_results.get(prerequisite, {}).get("status")
                != "SUCCESS"
            ]

            if failed_prerequisites:

                execution_results[component_name] = {
                    "status": "SKIPPED",
                    "reason": "Prerequisite execution failed or was skipped.",
                    "blocked_by": sorted(failed_prerequisites)
                }

                continue

            try:
                output = self.components[component_name].run()

                output = self._validate_component_output(
                    component_name,
                    output
                )

                component_outputs[component_name] = output

                execution_results[component_name] = {
                    "status": "SUCCESS",
                    "reason": None
                }

            except Exception as error:

                execution_results[component_name] = {
                    "status": "FAILED",
                    "reason": str(error)
                }

        successful_count = sum(
            result["status"] == "SUCCESS"
            for result in execution_results.values()
        )

        failed_count = sum(
            result["status"] == "FAILED"
            for result in execution_results.values()
        )

        skipped_count = sum(
            result["status"] == "SKIPPED"
            for result in execution_results.values()
        )

        historical_registered = False
        initial_period = None
        orchestration_error = None

        if successful_count == len(self.COMPONENTS):

            try:
                self.state_manager.register_all_historical_states(
                    component_outputs
                )

                initial_period = self.time_manager.get_current_period()

                self.state_manager.initialize_simulation_state(
                    initial_period
                )

                historical_registered = True

            except Exception as error:
                orchestration_error = str(error)

        report_status = (
            "SUCCESS"
            if historical_registered
            else "FAILED"
        )

        self.execution_report = {
            "status": report_status,
            "execution_order": execution_order,
            "execution_results": execution_results,
            "summary": {
                "total_components": len(self.COMPONENTS),
                "successful": successful_count,
                "failed": failed_count,
                "skipped": skipped_count
            },
            "historical_state_registered": historical_registered,
            "initial_simulation_period": initial_period,
            "orchestration_error": orchestration_error
        }

        return self.get_execution_report()

    
    def run_monthly_replay(self, payload_builder):
        """
        Replay all aligned monthly states across the historical timeline.

        Historical component outputs remain immutable.
        Each month's six component states are committed atomically.
        If replay fails, simulation snapshots are rolled back to the
        initial historical baseline.
        """

        if self.execution_report is None:
            raise RuntimeError(
                "Run historical execution before monthly replay."
            )

        if self.execution_report["status"] != "SUCCESS":
            raise RuntimeError(
                "Historical execution must succeed before monthly replay."
            )

        if self.monthly_replay_report is not None:
            raise RuntimeError(
                "Monthly replay has already been attempted."
            )

        if not callable(getattr(payload_builder, "build", None)):
            raise TypeError(
                "payload_builder must implement build(month)."
            )

        if not callable(getattr(payload_builder, "get_timeline", None)):
            raise TypeError(
                "payload_builder must implement get_timeline()."
            )

        timeline = tuple(
            str(month) for month in payload_builder.get_timeline()
        )

        manager_timeline = self.time_manager.get_timeline()

        if timeline != manager_timeline:
            raise ValueError(
                "Payload builder timeline does not match TimeManager."
            )

        if not timeline:
            raise ValueError("Monthly replay timeline cannot be empty.")

        initial_period = timeline[0]

        if self.time_manager.get_current_period() != initial_period:
            raise RuntimeError(
                "TimeManager is not positioned at the first month."
            )

        available_periods = self.state_manager.get_available_periods()

        if available_periods != (initial_period,):
            raise RuntimeError(
                "StateManager must contain only the initial baseline "
                "before monthly replay."
            )

        # Build and validate every payload before changing snapshots.
        monthly_payloads = {}

        for month in timeline:
            payload = payload_builder.build(month)

            if not isinstance(payload, dict):
                raise TypeError(
                    f"Payload for {month} must be a dictionary."
                )

            if set(payload) != self.COMPONENTS:
                raise ValueError(
                    f"Payload for {month} must contain exactly six "
                    "component states."
                )

            for component_name, component_state in payload.items():
                if not isinstance(component_state, dict):
                    raise TypeError(
                        f"{component_name} payload for {month} "
                        "must be a dictionary."
                    )

                if component_state.get("purchase_month") != month:
                    raise ValueError(
                        f"{component_name} payload month mismatch "
                        f"for {month}."
                    )

            monthly_payloads[month] = payload

        processed_months = []

        try:
            for index, month in enumerate(timeline):

                if index > 0:
                    next_period = self.time_manager.get_next_period()

                    if next_period != month:
                        raise RuntimeError(
                            "TimeManager progression mismatch. "
                            f"Expected {month}, got {next_period}."
                        )

                    self.state_manager.set_current_period(month)

                elif self.state_manager.get_simulation_state()[
                    "period"
                ] != month:
                    raise RuntimeError(
                        "StateManager is not positioned at the "
                        "initial replay month."
                    )

                self.state_manager.update_all_component_states(
                    monthly_payloads[month]
                )

                snapshot = self.state_manager.get_simulation_state()

                if snapshot["period"] != month:
                    raise RuntimeError(
                        f"Incorrect snapshot period for {month}."
                    )

                if set(snapshot["components"]) != self.COMPONENTS:
                    raise RuntimeError(
                        f"Incomplete component snapshot for {month}."
                    )

                processed_months.append(month)

            stored_periods = self.state_manager.get_available_periods()

            if stored_periods != timeline:
                raise RuntimeError(
                    "Stored simulation periods do not match "
                    "the complete historical timeline."
                )

            if not self.time_manager.is_complete():
                raise RuntimeError(
                    "TimeManager did not reach the final month."
                )

            self.monthly_replay_report = {
                "status": "SUCCESS",
                "total_months": len(timeline),
                "processed_months": len(processed_months),
                "start_period": timeline[0],
                "end_period": timeline[-1],
                "periods": list(processed_months),
                "snapshots_validated": True
            }

            return self.get_monthly_replay_report()

        except Exception as error:

            # Preserve historical outputs and restore the initial
            # simulation baseline after any replay failure.
            self.state_manager.reset_simulation_state()
            self.time_manager.reset()

            self.state_manager.initialize_simulation_state(
                initial_period
            )

            self.monthly_replay_report = {
                "status": "FAILED",
                "total_months": len(timeline),
                "processed_months": len(processed_months),
                "start_period": timeline[0],
                "end_period": timeline[-1],
                "periods": list(processed_months),
                "snapshots_validated": False,
                "error": str(error)
            }

            raise RuntimeError(
                f"Monthly replay failed and was rolled back: {error}"
            ) from error

    def get_monthly_replay_report(self):
        """Return a defensive copy of the monthly replay report."""

        if self.monthly_replay_report is None:
            raise RuntimeError(
                "Monthly replay has not been performed."
            )

        from copy import deepcopy

        return deepcopy(self.monthly_replay_report)


    def get_execution_report(self):
        """Return a defensive copy of the execution report."""

        if self.execution_report is None:
            raise RuntimeError(
                "Historical execution has not been performed."
            )

        from copy import deepcopy

        return deepcopy(self.execution_report)