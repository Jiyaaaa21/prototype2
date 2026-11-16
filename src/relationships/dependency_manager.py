from collections import defaultdict
from typing import Dict, List, Set, Tuple


class DependencyManager:
    """
    Manages hard execution dependencies and coordination stages
    for the Commercial & Sales Digital Twin.

    A dependency A -> B means B requires A to complete successfully.

    Coordination stages define preferred execution order.
    They do not automatically create hard dependencies.
    """

    COMPONENTS = {
        "customer_management",
        "product_management",
        "seller_management",
        "order_sales_management",
        "payment_revenue_management",
        "delivery_customer_experience"
    }

    def __init__(self):

        self._stages = (
            (
                "customer_management",
                "product_management",
                "seller_management"
            ),
            (
                "order_sales_management",
            ),
            (
                "payment_revenue_management",
                "delivery_customer_experience"
            )
        )

        # prerequisite -> dependent components
        self._dependencies: Dict[str, Set[str]] = {
            component: set()
            for component in self.COMPONENTS
        }

        self._validate_stages()

    def _validate_component(self, component_name):
        if component_name not in self.COMPONENTS:
            raise ValueError(
                f"Unknown component: {component_name}"
            )

    def _validate_stages(self):
        registered = [
            component
            for stage in self._stages
            for component in stage
        ]

        if len(registered) != len(set(registered)):
            raise ValueError(
                "A component cannot appear in multiple stages."
            )

        if set(registered) != self.COMPONENTS:
            raise ValueError(
                "Coordination stages must include all components exactly once."
            )

    def add_dependency(self, prerequisite, dependent):
        """
        Register a hard execution dependency.

        The prerequisite must execute successfully before
        the dependent component can execute.
        """

        self._validate_component(prerequisite)
        self._validate_component(dependent)

        if prerequisite == dependent:
            raise ValueError(
                "A component cannot depend on itself."
            )

        self._dependencies[prerequisite].add(dependent)

        try:
            self.validate_dependencies()
        except ValueError:
            self._dependencies[prerequisite].remove(dependent)
            raise

    def validate_dependencies(self):
        """Validate references, stage ordering and circular dependencies."""

        stage_index = {
            component: index
            for index, stage in enumerate(self._stages)
            for component in stage
        }

        for prerequisite, dependents in self._dependencies.items():

            self._validate_component(prerequisite)

            for dependent in dependents:
                self._validate_component(dependent)

                if stage_index[prerequisite] > stage_index[dependent]:
                    raise ValueError(
                        f"Dependency {prerequisite} -> {dependent} "
                        "conflicts with the coordination stage order."
                    )

        self._topological_order()
        return True

    def _topological_order(self):
        """Return a valid topological execution order."""

        in_degree = {
            component: 0
            for component in self.COMPONENTS
        }

        for dependents in self._dependencies.values():
            for dependent in dependents:
                in_degree[dependent] += 1

        stage_order = {
            component: index
            for index, stage in enumerate(self._stages)
            for component in stage
        }

        ready = [
            component
            for component, degree in in_degree.items()
            if degree == 0
        ]

        result = []

        while ready:
            ready.sort(
                key=lambda component: (
                    stage_order[component],
                    component
                )
            )

            current = ready.pop(0)
            result.append(current)

            for dependent in sorted(self._dependencies[current]):
                in_degree[dependent] -= 1

                if in_degree[dependent] == 0:
                    ready.append(dependent)

        if len(result) != len(self.COMPONENTS):
            raise ValueError(
                "Circular dependency detected."
            )

        return tuple(result)

    def get_execution_order(self):
        """Return the valid execution order of all components."""

        self.validate_dependencies()
        return self._topological_order()

    def get_parallel_execution_batches(self):
        """
        Return batches of components that can execute in parallel.

        Components in the same batch have no unresolved hard
        dependency on one another.
        """

        self.validate_dependencies()

        batches = []

        for stage in self._stages:

            remaining = set(stage)
            completed = set()

            while remaining:

                ready = sorted(
                    component
                    for component in remaining
                    if all(
                        prerequisite in completed
                        or prerequisite not in stage
                        for prerequisite in self._get_prerequisites(component)
                    )
                )

                if not ready:
                    raise ValueError(
                        "Unable to resolve execution batch."
                    )

                batches.append(tuple(ready))
                completed.update(ready)
                remaining.difference_update(ready)

        return tuple(batches)

    def _get_prerequisites(self, component_name):
        """Return all hard prerequisites for a component."""

        return tuple(
            prerequisite
            for prerequisite, dependents in self._dependencies.items()
            if component_name in dependents
        )

    def get_dependencies(self):
        """Return a read-only-style copy of registered dependencies."""

        return {
            prerequisite: tuple(sorted(dependents))
            for prerequisite, dependents in self._dependencies.items()
        }

    def get_coordination_stages(self):
        """Return the preferred coordination stages."""

        return self._stages

    def get_execution_plan(self):
        """Return the complete execution plan."""

        self.validate_dependencies()

        return {
            "components": tuple(sorted(self.COMPONENTS)),
            "coordination_stages": self.get_coordination_stages(),
            "hard_dependencies": self.get_dependencies(),
            "execution_order": self.get_execution_order(),
            "parallel_execution_batches": (
                self.get_parallel_execution_batches()
            )
        }