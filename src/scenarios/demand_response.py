"""
Optional demand-response assumption.

Customers react to what they pay in total for the goods: product price after
discount PLUS freight. For a scope (one product, or the whole business):

    outlay_factor     f = (scenario merchandise + scenario freight)
                          / (baseline merchandise + baseline freight)   [constant volume]
    volume_multiplier m = f ** elasticity

elasticity = 0 means no response (historical volumes). The elasticity is a
USER-SET ASSUMPTION. It is not estimated from Olist (no quantity field, and
price variation cannot identify it). One value is applied to the whole scope.
Commission and seller-cost changes do not move volume in this model.
"""
from __future__ import annotations

import math


def outlay_factor(baseline_summary: dict, scenario_summary: dict) -> float:
    b = baseline_summary["net_merchandise_value"] + baseline_summary["freight_value"]
    s = scenario_summary["net_merchandise_value"] + scenario_summary["freight_value"]
    if b <= 0 or s <= 0:
        raise ValueError("Customer outlay must be positive.")
    return s / b


def volume_multiplier(factor: float, elasticity: float) -> float:
    if elasticity > 0:
        raise ValueError("Price elasticity of demand must be <= 0.")
    if factor <= 0:
        raise ValueError("Outlay factor must be positive.")
    return factor ** elasticity


def break_even_elasticity(metric_ratio: float, factor: float) -> float | None:
    """
    Elasticity at which a metric equals its baseline.

    metric_ratio = scenario / baseline of the metric at constant volume.
    With volume response the ratio becomes metric_ratio * factor**elasticity,
    which equals 1 at  elasticity* = -ln(metric_ratio) / ln(factor).

    None when there is no customer-outlay change (factor 1) or the ratio is
    not positive.
    """
    if abs(factor - 1.0) < 1e-12 or metric_ratio <= 0 or factor <= 0:
        return None
    return -math.log(metric_ratio) / math.log(factor)
