
from datetime import datetime, timezone

from src.components.base_component import BaseComponent
from src.components.customer_management import CustomerManagement


class CustomerComponent(BaseComponent):
    """Standardized Customer Management component."""

    def __init__(self, customers_df, orders_df, order_items_df):
        super().__init__("customer_management")

        self.manager = CustomerManagement(
            customers_df=customers_df,
            orders_df=orders_df,
            order_items_df=order_items_df,
        )

    def run(self):
        customer_state = self.manager.build_customer_state()
        summary = self.manager.get_summary()

        business_rules = [
            {
                "rule_id": "CM01",
                "description": "Customer state must contain unique underlying customer IDs.",
                "passed": customer_state["customer_unique_id"].is_unique,
            },
            {
                "rule_id": "CM02",
                "description": "Customer order counts must be positive.",
                "passed": (customer_state["order_count"] > 0).all(),
            },
            {
                "rule_id": "CM03",
                "description": "Repeat customer classification must match order counts.",
                "passed": (
                    customer_state["repeat_customer"]
                    == (customer_state["order_count"] > 1)
                ).all(),
            },
            {
                "rule_id": "CM04",
                "description": "Customer state count must match the summary.",
                "passed": (
                    len(customer_state) == summary["total_customers"]
                ),
            },
        ]

        output = {
            "component": self.component_name,

            "metadata": {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "currency": "BRL",
                "data_type": "historical_customer_analysis",
                "customer_count": len(customer_state),
                "source_customer_count": len(self.manager.customers),
                "order_count": len(self.manager.orders),
            },

            "historical_state": {
                "customers": customer_state.to_dict(
                    orient="records"
                ),
                "record_counts": {
                    "customers": len(customer_state),
                },
            },

            "business_metrics": summary,

            "scenario_results": [],

            "business_rule_results": business_rules,

            "status": (
                "SUCCESS"
                if all(rule["passed"] for rule in business_rules)
                else "FAILED"
            ),
        }

        self.set_output(output)

        return self.get_output()
