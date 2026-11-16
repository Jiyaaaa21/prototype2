
from datetime import datetime, timezone

from src.components.base_component import BaseComponent
from src.components.delivery_customer_experience import (
    DeliveryCustomerExperience,
)


class DeliveryComponent(BaseComponent):
    """
    Standardized component wrapper for Delivery & Customer Experience.
    """

    def __init__(
        self,
        orders_df,
        order_items_df,
        reviews_df,
        customers_df,
        sellers_df,
    ):
        super().__init__("delivery_customer_experience")

        self.manager = DeliveryCustomerExperience(
            orders_df=orders_df,
            order_items_df=order_items_df,
            reviews_df=reviews_df,
            customers_df=customers_df,
            sellers_df=sellers_df,
        )

    def run(self):
        states = self.manager.build_all_states()
        summary = self.manager.get_summary()

        output = {
            "component": self.component_name,

            "metadata": {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "currency": "BRL",
                "data_type": "historical_delivery_and_customer_experience",
                "order_count": len(states["orders"]),
                "seller_count": len(states["sellers"]),
                "monthly_period_count": len(states["monthly"]),
                "review_record_count": summary[
                    "total_review_records"
                ],
            },

            "historical_state": {
                "orders": states["orders"].to_dict(
                    orient="records"
                ),
                "monthly": states["monthly"].to_dict(
                    orient="records"
                ),
                "sellers": states["sellers"].to_dict(
                    orient="records"
                ),
                "record_counts": {
                    "orders": len(states["orders"]),
                    "monthly": len(states["monthly"]),
                    "sellers": len(states["sellers"]),
                },
            },

            "business_metrics": summary,

            "scenario_results": [],

            "business_rule_results": [
                {
                    "rule_id": "DC01",
                    "description": "Order-level state must contain unique order IDs.",
                    "passed": states["orders"]["order_id"].is_unique,
                },
                {
                    "rule_id": "DC02",
                    "description": "Seller-level state must contain unique seller IDs.",
                    "passed": states["sellers"]["seller_id"].is_unique,
                },
                {
                    "rule_id": "DC03",
                    "description": "Monthly state must contain unique purchase months.",
                    "passed": states["monthly"]["purchase_month"].is_unique,
                },
                {
                    "rule_id": "DC04",
                    "description": "Review aggregation must preserve the source review record count.",
                    "passed": (
                        int(
                            states["orders"][
                                "review_record_count"
                            ].sum()
                        )
                        == summary["total_review_records"]
                    ),
                },
                {
                    "rule_id": "DC05",
                    "description": "Historical order count must match the source order count.",
                    "passed": (
                        len(states["orders"])
                        == summary["total_orders"]
                    ),
                },
            ],

            "status": "SUCCESS",
        }

        if not all(
            rule["passed"]
            for rule in output["business_rule_results"]
        ):
            output["status"] = "FAILED"

        self.set_output(output)

        return self.get_output()
