
from datetime import datetime, timezone

import numpy as np

from src.components.base_component import BaseComponent
from src.components.payment_revenue_management import (
    PaymentRevenueManagement
)


class PaymentComponent(BaseComponent):

    def __init__(self, orders_df, payments_df):

        super().__init__("payment_revenue_management")

        self.orders_df = orders_df.copy(deep=True)
        self.payments_df = payments_df.copy(deep=True)

        self.payment_manager = PaymentRevenueManagement(
            orders_df=self.orders_df,
            payments_df=self.payments_df
        )

    def run(self):

        states = self.payment_manager.build_payment_state()
        summary = self.payment_manager.get_summary()

        order_state = states["order_state"]
        monthly_state = states["monthly_state"]
        payment_method_state = states["payment_method_state"]

        # Payment component business rules
        business_rules = [
            {
                "rule_id": "PR01",
                "description": "Order identifiers must be unique and non-null.",
                "passed": bool(
                    self.orders_df["order_id"].notna().all()
                    and self.orders_df["order_id"].is_unique
                )
            },
            {
                "rule_id": "PR02",
                "description": "Payment records must have unique order and sequence combinations.",
                "passed": bool(
                    not self.payments_df.duplicated(
                        subset=["order_id", "payment_sequential"]
                    ).any()
                )
            },
            {
                "rule_id": "PR03",
                "description": "Every payment record must reference an existing order.",
                "passed": bool(
                    self.payments_df["order_id"]
                    .isin(self.orders_df["order_id"]).all()
                )
            },
            {
                "rule_id": "PR04",
                "description": "Payment values must be non-negative.",
                "passed": bool(
                    self.payments_df["payment_value"].notna().all()
                    and (self.payments_df["payment_value"] >= 0).all()
                )
            },
            {
                "rule_id": "PR05",
                "description": "Order payment state must contain one record per source order.",
                "passed": bool(
                    len(order_state) == len(self.orders_df)
                    and order_state["order_id"].is_unique
                )
            },
            {
                "rule_id": "PR06",
                "description": "Payment record counts must reconcile with the source payment dataset.",
                "passed": bool(
                    order_state["payment_record_count"].sum()
                    == len(self.payments_df)
                )
            },
            {
                "rule_id": "PR07",
                "description": "Order-level payment values must reconcile with source payment values.",
                "passed": bool(
                    np.isclose(
                        order_state["total_payment_value"].sum(),
                        self.payments_df["payment_value"].sum()
                    )
                )
            },
            {
                "rule_id": "PR08",
                "description": "Monthly and payment-method values must reconcile with source payment values.",
                "passed": bool(
                    np.isclose(
                        monthly_state["total_payment_value"].sum(),
                        self.payments_df["payment_value"].sum()
                    )
                    and np.isclose(
                        payment_method_state[
                            "total_payment_value"
                        ].sum(),
                        self.payments_df["payment_value"].sum()
                    )
                )
            }
        ]

        all_rules_passed = all(
            rule["passed"] for rule in business_rules
        )

        output = {
            "component": self.component_name,

            "metadata": {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "currency": "BRL",
                "data_type": "historical_payment_analysis",
                "order_count": summary["total_orders"],
                "payment_record_count": (
                    summary["total_payment_records"]
                ),
                "payment_method_count": (
                    summary["distinct_payment_methods"]
                )
            },

            "historical_state": {
                "orders": order_state.to_dict(
                    orient="records"
                ),
                "monthly": monthly_state.to_dict(
                    orient="records"
                ),
                "payment_methods": (
                    payment_method_state.to_dict(
                        orient="records"
                    )
                ),
                "record_counts": {
                    "orders": len(order_state),
                    "monthly": len(monthly_state),
                    "payment_methods": len(payment_method_state)
                }
            },

            "business_metrics": summary,

            "scenario_results": [],

            "business_rule_results": business_rules,

            "status": (
                "SUCCESS" if all_rules_passed else "FAILED"
            )
        }

        self.set_output(output)

        return self.get_output()
