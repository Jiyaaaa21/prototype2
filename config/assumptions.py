"""
Assumption register for the Commercial & Sales Digital Twin (BizTwin).

Single source of truth for every scenario parameter's BASELINE value and
where that value comes from. Nothing here is a hidden default: each entry
states whether it is observed in Olist data, taken from an external
published source, or an unverified user-set assumption.

Status values
-------------
DATA_OBSERVED        Directly observable / derivable from the Olist CSVs.
EXTERNAL_SOURCED     Taken from a published external source (cited).
USER_SET_UNVERIFIED  No primary source confirmed. Must be shown to the
                     user as an assumption and tested with a sensitivity range.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

DATA_OBSERVED = "DATA_OBSERVED"
EXTERNAL_SOURCED = "EXTERNAL_SOURCED"
USER_SET_UNVERIFIED = "USER_SET_UNVERIFIED"

VALID_STATUSES = (DATA_OBSERVED, EXTERNAL_SOURCED, USER_SET_UNVERIFIED)


@dataclass(frozen=True)
class Assumption:
    key: str
    label: str
    baseline: float
    status: str
    derivation: str
    source: str
    evidence_range: Optional[Tuple[float, float]] = None
    caveats: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(f"{self.key}: invalid status {self.status}")
        if not self.derivation.strip() or not self.source.strip():
            raise ValueError(f"{self.key}: derivation and source are required")
        if self.evidence_range is not None:
            low, high = self.evidence_range
            if not low <= self.baseline <= high:
                raise ValueError(f"{self.key}: baseline outside evidence range")


# ---------------------------------------------------------------------
# External figure: IBGE Pesquisa Anual de Comercio (PAC), retail trade.
# "Taxa de margem de comercializacao" = trade margin / cost of goods sold.
# So cost-of-goods as a share of sales = 1 / (1 + margin rate).
# ---------------------------------------------------------------------
IBGE_PAC_RETAIL_MARGIN_RATE = {2016: 0.384, 2017: 0.391, 2018: 0.376}


def cost_to_sales_from_margin_rate(margin_rate: float) -> float:
    return 1.0 / (1.0 + margin_rate)


_COST_2018 = cost_to_sales_from_margin_rate(IBGE_PAC_RETAIL_MARGIN_RATE[2018])
_COST_RANGE = (
    min(cost_to_sales_from_margin_rate(v) for v in IBGE_PAC_RETAIL_MARGIN_RATE.values()),
    max(cost_to_sales_from_margin_rate(v) for v in IBGE_PAC_RETAIL_MARGIN_RATE.values()),
)


ASSUMPTIONS = {
    "product_price_adjustment": Assumption(
        key="product_price_adjustment",
        label="Product price adjustment",
        baseline=0.0,
        status=DATA_OBSERVED,
        derivation="Baseline = historical item-line price in order_items (no change).",
        source="Olist order_items.price",
        caveats=(
            "Scenario values are what-if inputs, not forecasts.",
            "Quantities are held constant: no demand response is modelled.",
        ),
    ),
    "discount_rate": Assumption(
        key="discount_rate",
        label="Discount rate",
        baseline=0.0,
        status=DATA_OBSERVED,
        derivation=(
            "Olist has no discount field. Payment totals equal items + freight "
            "in ~99.6% of orders, so observed prices are already net of any discount. "
            "Baseline discount is therefore 0."
        ),
        source="Olist order_payments vs order_items (verified by scripts/verify_assumptions.py)",
        caveats=("Scenario discount is a user-set what-if; Olist gives no empirical range.",),
    ),
    "seller_cost_rate": Assumption(
        key="seller_cost_rate",
        label="Seller cost rate (cost of goods / sales)",
        baseline=_COST_2018,
        status=EXTERNAL_SOURCED,
        derivation=(
            "IBGE PAC 2018 retail trade margin rate 37.6% (margin / COGS). "
            "Cost-to-sales = 1 / (1 + 0.376). Range uses PAC 2016-2018 (38.4%, 39.1%, 37.6%)."
        ),
        source=(
            "IBGE, Pesquisa Anual de Comercio (PAC) 2016, 2017, 2018 - "
            "taxa de margem de comercializacao, comercio varejista"
        ),
        evidence_range=_COST_RANGE,
        caveats=(
            "Economy-wide retail average, not Olist-specific.",
            "Gross trade margin only; excludes operating expenses, taxes, returns.",
        ),
    ),
    "commission_rate": Assumption(
        key="commission_rate",
        label="Platform commission rate",
        baseline=0.20,
        status=EXTERNAL_SOURCED,
        derivation=(
            "Olist's published commission by seller plan: 20% (Exame, ~2019, plus "
            "monthly/installation fees) and 19-21% depending on plan in 2020 "
            "(Exame, 2020: Pro 19%, Basic 20%, Lite 21%). Baseline = 20% reference rate; "
            "range = 19-21%."
        ),
        source=(
            "Exame, 'Olist, marketplace de marketplaces, recebe R$ 190 mi do SoftBank' "
            "(20%); Exame, 'Olist ... recebe novos R$ 310 mi do SoftBank' (19-21% by plan); "
            "Olist blog 'Vender com o Olist: quanto custa, preco e comissao' (Lite 21%)."
        ),
        evidence_range=(0.19, 0.21),
        caveats=(
            "Not directly observed in the Olist transaction dataset (no commission field).",
            "Sources are 2019-2020 press reports; a 2017 figure was not independently "
            "confirmed. The dataset covers 2016-2018, so seller plan terms may differ.",
            "Commission base = net merchandise value, freight excluded, following several "
            "secondary sources. No Olist primary document confirming this was found.",
            "A third-party analysis claims 10% of product price plus R$80/month; no "
            "primary source found for that claim.",
        ),
    ),
    "freight_adjustment": Assumption(
        key="freight_adjustment",
        label="Freight adjustment",
        baseline=0.0,
        status=DATA_OBSERVED,
        derivation="Baseline = historical freight_value per item line (no change).",
        source="Olist order_items.freight_value",
        caveats=("Scenario values are what-if inputs.",),
    ),
}


def get_baseline_parameters() -> dict:
    """Baseline parameter dict in the form MultiParameterScenarioEngine expects."""
    return {key: a.baseline for key, a in ASSUMPTIONS.items()}


def get_assumption(key: str) -> Assumption:
    if key not in ASSUMPTIONS:
        raise KeyError(f"Unknown parameter: {key}")
    return ASSUMPTIONS[key]


def unverified_parameters() -> tuple:
    return tuple(k for k, a in ASSUMPTIONS.items() if a.status == USER_SET_UNVERIFIED)
