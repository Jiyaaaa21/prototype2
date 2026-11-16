from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from src.scenarios.multi_parameter_scenario import (
    MultiParameterScenarioEngine,
)
from src.scenarios.scenario_report_generator import (
    ScenarioReportGenerator,
)


class ScenarioOrchestrator:
    """
    Coordinates multi-parameter scenario execution, independent
    financial validation, and Excel/PDF report generation.

    Both baseline and scenario configurations must be supplied
    explicitly. No business parameter defaults are assumed.
    """

    DIMENSIONS = (
        "product",
        "category",
        "seller",
        "customer",
        "order",
        "monthly",
    )

    METRICS = (
        "gross_merchandise_value",
        "discount_amount",
        "net_merchandise_value",
        "freight_value",
        "commission",
        "seller_cost",
        "seller_payout",
        "seller_contribution",
        "item_line_count",
    )

    def __init__(
        self,
        products,
        order_items,
        orders,
        customers,
        category_translation,
        baseline_parameters,
        scenario_parameters,
        output_dir=None,
    ):
        datasets = {
            "products": products,
            "order_items": order_items,
            "orders": orders,
            "customers": customers,
            "category_translation": category_translation,
        }

        self._validate_datasets(datasets)

        # Isolated copies protect the caller's original DataFrames.
        self.products = products.copy(deep=True)
        self.order_items = order_items.copy(deep=True)
        self.orders = orders.copy(deep=True)
        self.customers = customers.copy(deep=True)
        self.category_translation = category_translation.copy(deep=True)

        self.baseline_parameters = deepcopy(baseline_parameters)
        self.scenario_parameters = deepcopy(scenario_parameters)

        self.output_dir = (
            Path(output_dir) if output_dir is not None else None
        )

        self.report_generator = ScenarioReportGenerator(
            output_dir=self.output_dir
        )

        self.last_run_report = None

    # ---------------------------------------------------------
    # INPUT VALIDATION
    # ---------------------------------------------------------

    @staticmethod
    def _validate_datasets(datasets):
        for name, frame in datasets.items():
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(
                    f"{name} must be a pandas DataFrame."
                )

            if frame.empty:
                raise ValueError(
                    f"{name} cannot be empty."
                )

    # ---------------------------------------------------------
    # INDEPENDENT FINANCIAL VALIDATION
    # ---------------------------------------------------------

    @classmethod
    def _independent_summary(cls, historical_transactions, parameters):
        """
        Independently recalculate financial totals from the engine's
        merged historical transaction base.

        This method intentionally does not use the engine's calculated
        financial columns or its summary method.
        """

        historical_price = historical_transactions[
            "historical_price"
        ].astype(float)

        historical_freight = historical_transactions[
            "historical_freight"
        ].astype(float)

        adjusted_price = historical_price * (
            1 + float(parameters["product_price_adjustment"])
        )

        gross = adjusted_price.sum()

        discount = gross * float(parameters["discount_rate"])
        net = gross - discount

        freight = (
            historical_freight
            * (1 + float(parameters["freight_adjustment"]))
        ).sum()

        seller_cost = (
            historical_price
            * float(parameters["seller_cost_rate"])
        ).sum()

        # Commission base follows the documented Olist benchmark:
        # net merchandise value plus adjusted freight.
        commission_base = net + freight
        commission = (
            commission_base * float(parameters["commission_rate"])
        )

        payout = net - commission
        contribution = payout - seller_cost

        return {
            "gross_merchandise_value": float(gross),
            "discount_amount": float(discount),
            "net_merchandise_value": float(net),
            "freight_value": float(freight),
            "commission": float(commission),
            "seller_cost": float(seller_cost),
            "seller_payout": float(payout),
            "seller_contribution": float(contribution),
            "item_line_count": int(len(historical_transactions)),
        }

    @classmethod
    def _validate_independent_results(cls, engine, results):
        checks = {}

        for config_name in ("baseline", "scenario"):
            parameters = results["parameters"][config_name]
            reported = results[config_name]["summary"]

            independently_calculated = cls._independent_summary(
                engine.transactions,
                parameters,
            )

            for metric in cls.METRICS:
                checks[
                    f"{config_name}_{metric}_independent_reconciliation"
                ] = bool(
                    np.isclose(
                        float(reported[metric]),
                        float(independently_calculated[metric]),
                        rtol=1e-9,
                        atol=0.01,
                    )
                )

        # Verify all six dimensional totals against transaction totals.
        for config_name in ("baseline", "scenario"):
            transaction_results = results[config_name]["transactions"]

            for metric in cls.METRICS:
                transaction_total = float(
                    transaction_results[metric].sum()
                )

                for dimension in cls.DIMENSIONS:
                    dimension_frame = results[config_name][
                        "dimensions"
                    ][dimension]

                    dimension_total = float(
                        dimension_frame[metric].sum()
                    )

                    checks[
                        f"{config_name}_{dimension}_{metric}_reconciliation"
                    ] = bool(
                        np.isclose(
                            transaction_total,
                            dimension_total,
                            rtol=1e-9,
                            atol=0.01,
                        )
                    )

        failed = [
            name for name, passed in checks.items() if not passed
        ]

        return {
            "passed": not failed,
            "total_checks": len(checks),
            "passed_checks": sum(checks.values()),
            "failed_checks": failed,
            "checks": checks,
        }

    # ---------------------------------------------------------
    # EXECUTION
    # ---------------------------------------------------------

    def run(self):
        """
        Execute the complete multi-parameter scenario workflow.

        Returns:
            status
            execution_summary
            scenario_results
            independent_validation
            report_paths
        """

        if self.last_run_report is not None:
            raise RuntimeError(
                "This orchestrator instance has already been executed. "
                "Create a new instance for another scenario run."
            )

        try:
            # STEP 1: Initialize the multi-parameter engine.
            engine = MultiParameterScenarioEngine(
                products=self.products,
                order_items=self.order_items,
                orders=self.orders,
                customers=self.customers,
                category_translation=self.category_translation,
                baseline_parameters=self.baseline_parameters,
                scenario_parameters=self.scenario_parameters,
            )

            # STEP 2: Execute baseline and scenario calculations.
            scenario_results = engine.run()

            if scenario_results["status"] != "success":
                raise ValueError(
                    "Scenario engine validation failed."
                )

            # STEP 3: Independently recalculate financial totals and
            # validate all six dimensional aggregations.
            independent_validation = self._validate_independent_results(
                engine,
                scenario_results,
            )

            if not independent_validation["passed"]:
                raise ValueError(
                    "Independent scenario validation failed: "
                    f"{independent_validation['failed_checks']}"
                )

            # STEP 4: Confirm the engine's historical transaction base
            # was not modified.
            historical_unchanged = engine.transactions.equals(
                engine._historical_transactions
            )

            if not historical_unchanged:
                raise ValueError(
                    "Historical transaction data was modified."
                )

            # STEP 5: Attach orchestration-level validation.
            scenario_results["orchestration_validation"] = (
                independent_validation
            )

            scenario_results["validation"]["independent"] = (
                independent_validation
            )

            scenario_results["validation"][
                "historical_transactions_unchanged"
            ] = historical_unchanged

            scenario_results["validation"]["passed"] = (
                scenario_results["validation"]["passed"]
                and independent_validation["passed"]
                and historical_unchanged
            )

            if not scenario_results["validation"]["passed"]:
                raise ValueError(
                    "Combined scenario validation did not pass."
                )

            # STEP 6: Generate reports only after every check passes.
            report_paths = self.report_generator.generate(
                scenario_results
            )

            baseline_summary = scenario_results["baseline"]["summary"]
            scenario_summary = scenario_results["scenario"]["summary"]
            overall_impact = scenario_results["impact"]["overall"]

            execution_summary = {
                "status": "SUCCESS",
                "transaction_records": scenario_summary["item_line_count"],
                "validated_dimensions": list(self.DIMENSIONS),
                "independent_validation": "PASSED",
                "independent_checks_passed": (
                    independent_validation["passed_checks"]
                ),
                "independent_checks_total": (
                    independent_validation["total_checks"]
                ),
                "historical_transactions_unchanged": historical_unchanged,
                "baseline_summary": baseline_summary.copy(),
                "scenario_summary": scenario_summary.copy(),
                "overall_impact": deepcopy(overall_impact),
                "excel_report": str(report_paths["excel"]),
                "pdf_report": str(report_paths["pdf"]),
            }

            self.last_run_report = deepcopy(execution_summary)

            return {
                "status": "SUCCESS",
                "execution_summary": execution_summary,
                "scenario_results": scenario_results,
                "independent_validation": independent_validation,
                "report_paths": {
                    name: str(path)
                    for name, path in report_paths.items()
                },
            }

        except Exception as exc:
            self.last_run_report = {
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

            raise RuntimeError(
                "Scenario orchestration failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    # ---------------------------------------------------------
    # EXECUTION STATUS
    # ---------------------------------------------------------

    def get_last_run_report(self):
        """Return a defensive copy of the latest execution report."""
        if self.last_run_report is None:
            return None

        return deepcopy(self.last_run_report)
