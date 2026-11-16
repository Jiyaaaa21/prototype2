
from datetime import datetime, timezone

import numpy as np

from src.components.base_component import BaseComponent
from src.components.product_management import ProductManagement


class ProductComponent(BaseComponent):

    def __init__(
        self,
        products_df,
        order_items_df,
        category_translation_df
    ):
        super().__init__("product_management")

        self.products_df = products_df.copy(deep=True)
        self.order_items_df = order_items_df.copy(deep=True)
        self.category_translation_df = (
            category_translation_df.copy(deep=True)
        )

        self.product_management = ProductManagement(
            products_df=self.products_df,
            order_items_df=self.order_items_df,
            category_translation_df=self.category_translation_df
        )

    def run(self):

        self.product_management.validate_data()

        states = self.product_management.build_product_state()

        product_state = states["product_state"]
        category_state = states["category_state"]

        summary = self.product_management.get_summary()

        # Product component business rules
        business_rules = [
            {
                "rule_id": "PM01",
                "description": "Product identifiers must be unique and non-null.",
                "passed": bool(
                    self.products_df["product_id"].notna().all()
                    and self.products_df["product_id"].is_unique
                )
            },
            {
                "rule_id": "PM02",
                "description": "Every order item must reference an existing product.",
                "passed": bool(
                    self.order_items_df["product_id"]
                    .isin(self.products_df["product_id"]).all()
                )
            },
            {
                "rule_id": "PM03",
                "description": "Category translation source names must be unique and non-null.",
                "passed": bool(
                    self.category_translation_df[
                        "product_category_name"
                    ].notna().all()
                    and self.category_translation_df[
                        "product_category_name"
                    ].is_unique
                )
            },
            {
                "rule_id": "PM04",
                "description": "Product state must contain one record per catalogue product.",
                "passed": bool(
                    len(product_state) == len(self.products_df)
                    and product_state["product_id"].is_unique
                )
            },
            {
                "rule_id": "PM05",
                "description": "Product and category item-line counts must reconcile with source order items.",
                "passed": bool(
                    product_state["item_line_count"].sum()
                    == len(self.order_items_df)
                    and category_state["item_line_count"].sum()
                    == len(self.order_items_df)
                )
            },
            {
                "rule_id": "PM06",
                "description": "Product merchandise value must reconcile with source order-item prices.",
                "passed": bool(
                    np.isclose(
                        product_state["units_value"].sum(),
                        self.order_items_df["price"].sum()
                    )
                )
            },
            {
                "rule_id": "PM07",
                "description": "Category merchandise value must reconcile with source order-item prices.",
                "passed": bool(
                    np.isclose(
                        category_state["merchandise_value"].sum(),
                        self.order_items_df["price"].sum()
                    )
                )
            },
            {
                "rule_id": "PM08",
                "description": "Product and category freight values must reconcile with source order items.",
                "passed": bool(
                    np.isclose(
                        product_state["freight_value"].sum(),
                        self.order_items_df["freight_value"].sum()
                    )
                    and np.isclose(
                        category_state["freight_value"].sum(),
                        self.order_items_df["freight_value"].sum()
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
                "data_type": "historical_product_analysis",
                "product_count": len(product_state),
                "category_count": len(category_state),
                "order_item_count": len(self.order_items_df)
            },

            "historical_state": {
                "products": product_state.to_dict(
                    orient="records"
                ),
                "categories": category_state.to_dict(
                    orient="records"
                ),
                "product_record_count": len(product_state),
                "category_record_count": len(category_state)
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
