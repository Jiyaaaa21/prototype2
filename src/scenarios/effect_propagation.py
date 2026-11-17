"""
Effect propagation layer (design A: accounting propagation only).

Traces one scenario change through the business components using Olist
fields and the scenario engine's own results. No behavioural assumption
is made: order counts, item lines, delivery times and customer behaviour
are NOT changed.

Chain (follows the relationship registry):
  Stage 1  Product & Seller      price, discount, freight, commission, cost
  Stage 2  Order & Sales         order value = net merchandise value + freight
  Stage 3  Payment & Revenue     scenario payments = recorded payments + order-value change
  Stage 4  Customer              spend change per customer_unique_id
  Stage 5  Delivery & Experience explicitly unchanged (no behavioural link)
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

TOL = 0.01  # BRL


class EffectPropagator:

    def __init__(self, engine_result: dict[str, Any], payments: pd.DataFrame,
                 volume_multiplier: float = 1.0):
        if volume_multiplier <= 0:
            raise ValueError("volume_multiplier must be positive.")
        self.m = float(volume_multiplier)
        if engine_result.get("status") != "success":
            raise ValueError("Engine result must have status 'success'.")
        if not {"order_id", "payment_value"} <= set(payments.columns):
            raise ValueError("payments needs order_id and payment_value.")
        self.result = engine_result
        self.payments = payments[["order_id", "payment_value"]].copy()

    # ------------------------------------------------------------
    def _order_table(self) -> pd.DataFrame:
        b = self.result["baseline"]["transactions"]
        s = self.result["scenario"]["transactions"]
        if len(b) != len(s) or not (b["order_id"].values == s["order_id"].values).all():
            raise ValueError("Baseline and scenario rows are not aligned.")

        base = b[["order_id", "customer_unique_id"]].copy()
        base["base_nmv"] = b["net_merchandise_value"].values
        base["base_freight"] = b["freight_value"].values
        base["scen_nmv"] = s["net_merchandise_value"].values
        base["scen_freight"] = s["freight_value"].values
        base["base_comm"] = b["commission"].values
        base["scen_comm"] = s["commission"].values

        g = base.groupby("order_id", as_index=False).agg(
            customer_unique_id=("customer_unique_id", "first"),
            base_nmv=("base_nmv", "sum"), base_freight=("base_freight", "sum"),
            scen_nmv=("scen_nmv", "sum"), scen_freight=("scen_freight", "sum"),
            base_comm=("base_comm", "sum"), scen_comm=("scen_comm", "sum"),
        )
        m = self.m
        g["base_order_value"] = g["base_nmv"] + g["base_freight"]
        # Unit-level change at constant volume (verified accounting).
        g["unit_change"] = (g["scen_nmv"] + g["scen_freight"]) - g["base_order_value"]
        # Scenario values are scaled by the volume multiplier (m = 1: no response).
        for col in ("scen_nmv", "scen_freight", "scen_comm"):
            g[col] = g[col] * m
        g["scen_order_value"] = g["scen_nmv"] + g["scen_freight"]
        g["order_value_change"] = g["scen_order_value"] - g["base_order_value"]

        paid = self.payments.groupby("order_id", as_index=False).agg(
            recorded_paid=("payment_value", "sum"))
        g = g.merge(paid, on="order_id", how="left")
        g["has_payment"] = g["recorded_paid"].notna()
        g["recorded_paid"] = g["recorded_paid"].fillna(0.0)
        g["scenario_paid"] = np.where(
            g["has_payment"], m * (g["recorded_paid"] + g["unit_change"]), 0.0)
        return g

    # ------------------------------------------------------------
    @staticmethod
    def _step(name, component, fields, formula, baseline, scenario):
        return {
            "stage": name, "component": component, "fields": fields,
            "formula": formula, "baseline": float(baseline),
            "scenario": float(scenario), "change": float(scenario - baseline),
        }

    def propagate(self) -> dict[str, Any]:
        o = self._order_table()
        bs = self.result["baseline"]["summary"]
        m = self.m
        ss = {k: v * m for k, v in self.result["scenario"]["summary"].items()}
        paid_o = o[o["has_payment"]]
        unpaid_o = o[~o["has_payment"]]

        stages = [
            {"stage": "1. Product & Seller (direct)", "steps": [
                self._step("Net merchandise value", "product_management",
                           "order_items.price",
                           "price x (1+price_adj) x (1-discount)",
                           bs["net_merchandise_value"], ss["net_merchandise_value"]),
                self._step("Freight", "seller_management",
                           "order_items.freight_value",
                           "freight x (1+freight_adj)",
                           bs["freight_value"], ss["freight_value"]),
                self._step("Platform commission", "seller_management",
                           "net merchandise value",
                           "NMV x commission_rate (freight excluded)",
                           bs["commission"], ss["commission"]),
                self._step("Seller payout", "seller_management",
                           "NMV, commission", "NMV - commission",
                           bs["seller_payout"], ss["seller_payout"]),
                self._step("Seller margin (proxy)", "seller_management",
                           "payout, historical price",
                           "payout - price x seller_cost_rate (proxy)",
                           bs["seller_contribution"], ss["seller_contribution"]),
            ]},
            {"stage": "2. Order & Sales (direct, via order_id)", "steps": [
                self._step("Order value (all orders with items)", "order_sales_management",
                           "order_items by order_id",
                           "sum(NMV) + sum(freight) per order",
                           o["base_order_value"].sum(), o["scen_order_value"].sum()),
                self._step("Orders", "order_sales_management", "orders.order_id",
                           "base x volume multiplier (1 = no demand model)",
                           len(o), len(o) * m),
                self._step("Item lines", "order_sales_management", "order_items rows",
                           "base x volume multiplier (1 = no demand model)",
                           bs["item_line_count"], ss["item_line_count"]),
            ]},
            {"stage": "3. Payment & Revenue (direct, via order_id)", "steps": [
                self._step("Customer payments, orders with a payment record",
                           "payment_revenue_management",
                           "order_payments.payment_value",
                           "volume x (recorded payment + unit order-value change)",
                           paid_o["recorded_paid"].sum(), paid_o["scenario_paid"].sum()),
                self._step("Order-value change on orders with NO payment record",
                           "payment_revenue_management", "orders without payments",
                           "reported separately, not added to payments",
                           0.0, unpaid_o["order_value_change"].sum()),
                self._step("Platform revenue (commission)", "payment_revenue_management",
                           "commission", "same as Stage 1",
                           o["base_comm"].sum(), o["scen_comm"].sum()),
            ]},
            {"stage": "4. Customer (indirect, via order_id)", "steps": [
                self._step("Customer spend (order value)", "customer_management",
                           "orders.customer_id -> customer_unique_id",
                           "sum of order value per customer",
                           o["base_order_value"].sum(), o["scen_order_value"].sum()),
                self._step("Customers", "customer_management", "customer_unique_id",
                           "base x volume multiplier (1 = no behavioural link)",
                           o["customer_unique_id"].nunique(),
                           o["customer_unique_id"].nunique() * m),
            ]},
            {"stage": "5. Delivery & Experience", "steps": [
                {"stage": "Delivery time and reviews", "component":
                 "delivery_customer_experience", "fields": "-",
                 "formula": "NO EFFECT: no behavioural link in design A",
                 "baseline": None, "scenario": None, "change": 0.0},
            ]},
        ]

        return {"stages": stages, "volume_multiplier": m,
                "checks": self._checks(o, bs, ss, paid_o, unpaid_o), "orders": o}

    # ------------------------------------------------------------
    def _checks(self, o, bs, ss, paid_o, unpaid_o) -> list[tuple[str, bool]]:
        c = []
        def ok(name, cond): c.append((name, bool(cond)))

        ok("Order value baseline = NMV + freight (engine summary)",
           abs(o["base_order_value"].sum()
               - (bs["net_merchandise_value"] + bs["freight_value"])) <= TOL)
        ok("Order value scenario = NMV + freight (engine summary)",
           abs(o["scen_order_value"].sum()
               - (ss["net_merchandise_value"] + ss["freight_value"])) <= TOL)
        ok("Order commission total = engine commission (baseline)",
           abs(o["base_comm"].sum() - bs["commission"]) <= TOL)
        ok("Order commission total = engine commission (scenario)",
           abs(o["scen_comm"].sum() - ss["commission"]) <= TOL)
        m = self.m
        gap = (paid_o["recorded_paid"] - paid_o["base_order_value"]).sum()
        ok("Payment change = order-value change + recorded-gap scaling "
           "+ unpaid-order change (reconciled)",
           abs((paid_o["scenario_paid"].sum() - paid_o["recorded_paid"].sum())
               - (paid_o["order_value_change"].sum() + (m - 1) * gap)) <= TOL)
        ok("Item lines = baseline x volume multiplier",
           abs(ss["item_line_count"] - bs["item_line_count"] * self.m) <= 1e-6)
        ok("No payment recorded for an order is never invented",
           (unpaid_o["scenario_paid"] == 0).all())
        ok("Recorded payments equal source payments for in-scope orders",
           abs(paid_o["recorded_paid"].sum() - self.payments[
               self.payments["order_id"].isin(o["order_id"])]["payment_value"].sum())
           <= TOL)
        return c
