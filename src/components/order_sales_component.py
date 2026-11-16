
from datetime import datetime, timezone

from src.components.base_component import BaseComponent
from src.components.order_sales_management import OrderSalesManagement


class OrderSalesComponent(BaseComponent):
    """Standardized Order & Sales Management component."""

    def __init__(
        self,
        orders_df,
        order_items_df,
        customers_df,
        products_df,
        sellers_df,
    ):
        super().__init__("order_sales_management")

        self.manager = OrderSalesManagement(
            orders_df=orders_df,
            order_items_df=order_items_df,
            customers_df=customers_df,
            products_df=products_df,
            sellers_df=sellers_df,
        )

    def run(self):
        states = self.manager.build_order_state()
        summary = self.manager.get_summary()

        order_state = states["order_state"]
        monthly_state = states["monthly_state"]
        contributions = states["contribution_state"]

        business_rules = [
            {
                "rule_id": "OS01",
                "description": "Order-level state must contain unique order IDs.",
                "passed": order_state["order_id"].is_unique,
            },
            {
                "rule_id": "OS02",
                "description": "Monthly state must contain unique purchase months.",
                "passed": monthly_state["purchase_month"].is_unique,
            },
            {
                "rule_id": "OS03",
                "description": "Monthly order counts must reconcile with total orders.",
                "passed": (
                    int(monthly_state["order_count"].sum())
                    == summary["total_orders"]
                ),
            },
            {
                "rule_id": "OS04",
                "description": "Orders with and without items must reconcile with total orders.",
                "passed": (
                    summary["orders_with_items"]
                    + summary["total_orders_without_items"]
                    == summary["total_orders"]
                ),
            },
            {
                "rule_id": "OS05",
                "description": "Contribution states must contain the expected business dimensions.",
                "passed": (
                    set(contributions.keys())
                    == {
                        "products",
                        "categories",
                        "sellers",
                        "customers",
                    }
                ),
            },
        ]

        historical_state = {
            "orders": order_state.to_dict(orient="records"),
            "monthly": monthly_state.to_dict(orient="records"),
            "contributions": {
                name: dataframe.to_dict(orient="records")
                for name, dataframe in contributions.items()
            },
            "record_counts": {
                "orders": len(order_state),
                "monthly": len(monthly_state),
                "products": len(contributions["products"]),
                "categories": len(contributions["categories"]),
                "sellers": len(contributions["sellers"]),
                "customers": len(contributions["customers"]),
            },
        }

        output = {
            "component": self.component_name,

            "metadata": {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "currency": "BRL",
                "data_type": "historical_order_and_sales_analysis",
                "order_count": len(order_state),
                "monthly_period_count": len(monthly_state),
                "order_item_count": summary["total_order_items"],
            },

            "historical_state": historical_state,

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
