
import math
import pandas as pd


class SellerScenarioEngine:
    """
    Executes hypothetical seller profitability scenarios.

    These are illustrative estimates, not actual accounting profits.
    """

    BUSINESS_RULES = {
        "SM01": "Every seller must have a unique seller_id.",
        "SM02": "Every order-item seller_id must reference a valid seller.",
        "SM03": "One seller can participate in multiple orders.",
        "SM04": "Seller-order relationships are established through order_items.",
        "SM05": "Merchandise value and freight value must be tracked separately.",
        "SM06": "Delivered performance must use delivered orders only.",
        "SM07": "Historical records must remain unchanged during scenario simulation.",
        "SM08": "Scenario cost and selling prices must be non-negative.",
        "SM09": "Platform commission must be between 0 and 100 percent.",
        "SM10": "Negative estimated profit must trigger a loss alert.",
        "SM11": "Zero estimated profit must trigger a break-even status.",
        "SM12": "Profit calculations must disclose all included and excluded costs."
    }

    EXCLUDED_COSTS = [
        "Taxes",
        "Packaging expenses",
        "Returns and refunds",
        "Other operating expenses"
    ]

    def __init__(self):
        self.scenario_results = None

    # --------------------------------------------------
    # 1. INPUT VALIDATION
    # --------------------------------------------------

    @staticmethod
    def validate_scenario_inputs(
        selling_price,
        cost_price,
        freight_collected,
        freight_cost,
        platform_commission_rate
    ):
        values = {
            "selling_price": selling_price,
            "cost_price": cost_price,
            "freight_collected": freight_collected,
            "freight_cost": freight_cost,
            "platform_commission_rate": platform_commission_rate
        }

        for name, value in values.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(
                    f"{name} must be a valid finite number."
                )

        for name in [
            "selling_price",
            "cost_price",
            "freight_collected",
            "freight_cost"
        ]:
            if values[name] < 0:
                raise ValueError(f"{name} cannot be negative.")

        if not 0 <= platform_commission_rate <= 1:
            raise ValueError(
                "Commission rate must be between 0 and 1 (0% to 100%)."
            )

        return True

    # --------------------------------------------------
    # 2. PROFIT CALCULATION
    # --------------------------------------------------

    def calculate_seller_profit(
        self,
        selling_price,
        cost_price,
        freight_collected,
        freight_cost,
        platform_commission_rate
    ):

        self.validate_scenario_inputs(
            selling_price,
            cost_price,
            freight_collected,
            freight_cost,
            platform_commission_rate
        )

        platform_commission = (
            selling_price * platform_commission_rate
        )

        estimated_profit = (
            selling_price
            + freight_collected
            - cost_price
            - freight_cost
            - platform_commission
        )

        profit_margin_pct = (
            estimated_profit / selling_price * 100
            if selling_price > 0 else 0
        )

        if estimated_profit < 0:
            status = "LOSS ALERT"
        elif estimated_profit == 0:
            status = "BREAK-EVEN"
        else:
            status = "PROFITABLE"

        return {
            "selling_price": selling_price,
            "cost_price": cost_price,
            "freight_collected": freight_collected,
            "freight_cost": freight_cost,
            "platform_commission_rate": platform_commission_rate,
            "platform_commission": platform_commission,
            "estimated_profit": estimated_profit,
            "profit_margin_pct": profit_margin_pct,
            "status": status
        }

    # --------------------------------------------------
    # 3. SCENARIO SIMULATION
    # --------------------------------------------------

    def run_scenarios(self, scenario_inputs=None):

        if scenario_inputs is None:

            scenario_inputs = {
                "Baseline": {
                    "selling_price": 750,
                    "cost_price": 500,
                    "freight_collected": 20,
                    "freight_cost": 40,
                    "platform_commission_rate": 0.10
                },

                "Increased Cost": {
                    "selling_price": 750,
                    "cost_price": 550,
                    "freight_collected": 20,
                    "freight_cost": 40,
                    "platform_commission_rate": 0.10
                },

                "Reduced Selling Price": {
                    "selling_price": 675,
                    "cost_price": 500,
                    "freight_collected": 20,
                    "freight_cost": 40,
                    "platform_commission_rate": 0.10
                },

                "Increased Freight": {
                    "selling_price": 750,
                    "cost_price": 500,
                    "freight_collected": 20,
                    "freight_cost": 60,
                    "platform_commission_rate": 0.10
                },

                "Loss Scenario": {
                    "selling_price": 450,
                    "cost_price": 500,
                    "freight_collected": 20,
                    "freight_cost": 40,
                    "platform_commission_rate": 0.10
                },

                "Break-even Validation": {
                    "selling_price": 100,
                    "cost_price": 70,
                    "freight_collected": 0,
                    "freight_cost": 20,
                    "platform_commission_rate": 0.10
                }
            }

        results = []

        for scenario_name, inputs in scenario_inputs.items():

            result = self.calculate_seller_profit(**inputs)

            results.append({
                "scenario": scenario_name,
                **result
            })

        self.scenario_results = pd.DataFrame(results)

        return self.scenario_results.copy(deep=True)

    # --------------------------------------------------
    # 4. HISTORICAL DATA IMMUTABILITY CHECK
    # --------------------------------------------------

    @staticmethod
    def verify_historical_data_unchanged(
        snapshots,
        current_data
    ):
        """
        Compare historical DataFrames against snapshots.
        Snapshots must be created before scenario execution.
        """

        for name, snapshot in snapshots.items():

            if name not in current_data:
                raise KeyError(
                    f"Missing historical dataset: {name}"
                )

            pd.testing.assert_frame_equal(
                snapshot,
                current_data[name],
                check_dtype=True
            )

        return True

    # --------------------------------------------------
    # 5. BUSINESS RULE VALIDATION
    # --------------------------------------------------

    def get_business_rule_results(self):

        if self.scenario_results is None:
            raise RuntimeError(
                "Run scenarios before testing scenario rules."
            )

        df = self.scenario_results

        checks = {

            "SM08": (
                df[
                    [
                        "selling_price",
                        "cost_price",
                        "freight_collected",
                        "freight_cost"
                    ]
                ].ge(0).all().all()
            ),

            "SM09": (
                df["platform_commission_rate"]
                .between(0, 1)
                .all()
            ),

            "SM10": (
                (
                    df.loc[
                        df["estimated_profit"] < 0,
                        "status"
                    ] == "LOSS ALERT"
                ).all()
            ),

            "SM11": (
                (
                    (df["estimated_profit"] == 0)
                    & (df["status"] == "BREAK-EVEN")
                ).any()
            ),

            "SM12": (
                len(self.EXCLUDED_COSTS) > 0
                and len(
                    self.get_cost_disclosure()["included_costs"]
                ) > 0
            )
        }

        results = []

        for rule_id, passed in checks.items():

            results.append({
                "rule_id": rule_id,
                "description": self.BUSINESS_RULES[rule_id],
                "status": "PASSED" if passed else "FAILED"
            })

        return pd.DataFrame(results)

    # --------------------------------------------------
    # 6. COST DISCLOSURE
    # --------------------------------------------------

    def get_cost_disclosure(self):

        return {
            "included_costs": [
                "Cost price",
                "Freight cost",
                "Platform commission"
            ],

            "included_revenue": [
                "Selling price",
                "Freight collected"
            ],

            "excluded_costs": self.EXCLUDED_COSTS.copy(),

            "disclaimer": (
                "Estimated seller contribution based only on "
                "specified scenario inputs. This is not "
                "accounting net profit."
            )
        }
