
from datetime import datetime, timezone

from src.components.base_component import BaseComponent
from src.components.seller_management import SellerManagement
from src.components.seller_scenario_engine import SellerScenarioEngine


class SellerComponent(BaseComponent):
    """
    Unified Seller Management component.

    Coordinates historical seller analysis and hypothetical
    profitability scenarios.
    """

    def __init__(self, sellers_df, order_items_df, orders_df):

        super().__init__("seller_management")

        # Preserve independent copies of historical input data
        self.sellers_df = sellers_df.copy(deep=True)
        self.order_items_df = order_items_df.copy(deep=True)
        self.orders_df = orders_df.copy(deep=True)

        # Initialize subcomponents
        self.seller_management = SellerManagement(
            sellers_df=self.sellers_df,
            order_items_df=self.order_items_df,
            orders_df=self.orders_df
        )

        self.scenario_engine = SellerScenarioEngine()

    def run(self, scenario_inputs=None, include_scenarios=True):
        """
        Execute historical seller analysis and optional scenarios.
        """

        # 1. Validate historical data
        self.seller_management.validate_data()

        # 2. Build historical seller state
        seller_state = self.seller_management.build_seller_state()

        # 3. Generate historical business metrics
        summary = self.seller_management.get_summary()

        # 4. Execute hypothetical scenarios
        if include_scenarios:

            scenario_results = self.scenario_engine.run_scenarios(
                scenario_inputs=scenario_inputs
            )

            business_rule_results = (
                self.scenario_engine.get_business_rule_results()
            )

            scenario_data = scenario_results.to_dict(orient="records")
            rule_data = business_rule_results.to_dict(orient="records")
            cost_disclosure = self.scenario_engine.get_cost_disclosure()

        else:
            scenario_data = []
            rule_data = []
            cost_disclosure = {}

        # 5. Assemble standardised component output
        output = {
            "component": self.component_name,

            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "currency": "BRL",
                "data_type": "historical_analysis_and_illustrative_scenarios",
                "seller_count": int(
                    seller_state["seller_id"].nunique()
                ),
                "order_item_count": len(self.order_items_df),
                "order_count": int(
                    self.orders_df["order_id"].nunique()
                )
            },

            "historical_state": {
                "records": seller_state.to_dict(orient="records"),
                "record_count": len(seller_state),
                "columns": seller_state.columns.tolist()
            },

            "business_metrics": summary,

            "scenario_results": scenario_data,

            "business_rule_results": rule_data,

            "status": "SUCCESS",

            # Seller-specific additional information
            "cost_disclosure": cost_disclosure
        }

        # 6. Validate and store output through BaseComponent
        self.set_output(output)

        return self.get_output()

