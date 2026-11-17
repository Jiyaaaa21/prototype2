"""
Scenario Analysis page: product-wise what-if analysis for the Commercial &
Sales Digital Twin.

Pick a product, change a business decision, run it, and see the effect on the
product's customers, sellers, platform commission and orders. Optionally apply
a user-set demand assumption, compare saved scenarios, and apply the same
scenario to every product.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.assumptions import ASSUMPTIONS, get_baseline_parameters
from src.dashboard.component_map import build_component_map
from src.dashboard.theme import (
    COLORS, compact_money, kpi_card, kpi_row, page_header, section, style_fig,
)
from src.scenarios.demand_response import break_even_elasticity
from src.scenarios.product_analysis import (
    impact_by_month, impact_by_seller, portfolio_comparison, product_profile,
    run_product_scenario,
)
from src.scenarios.product_focus import focus_on_product, product_candidates
from src.scenarios.scenario_orchestrator import ScenarioOrchestrator

DEFAULT_PRODUCT = "53b36df67ebb7c41585e8d54d6772e08"   # watches_gifts, 3 sellers

PRESETS = {
    "Custom": {},
    "Price increase +10%": {"price": 10.0},
    "Price increase +10% with demand response (assumed elasticity -1.0)": {
        "price": 10.0, "elasticity": -1.0},
    "Promotion: 15% discount": {"discount": 15.0},
    "Freight subsidy: -50% shipping charge": {"freight": -50.0},
    "Seller moves to Lite plan (21% commission)": {"commission": 21.0},
    "Combined: price +5%, discount 5%, freight -10%": {
        "price": 5.0, "discount": 5.0, "freight": -10.0},
}

STATUS_LABEL = {
    "DATA_OBSERVED": "Observed in Olist data",
    "EXTERNAL_SOURCED": "External published source",
    "USER_SET_UNVERIFIED": "Unverified assumption",
}

COMPARE_ROWS = {
    "Order value": "Order value (all orders with items)",
    "Customer payments": "Customer payments, orders with a payment record",
    "Platform commission": "Platform commission",
    "Seller payout": "Seller payout",
    "Seller margin (proxy)": "Seller margin (proxy)",
    "Orders": "Orders",
    "Customers": "Customers",
}

SENSITIVITY_METRICS = {
    "Customer order value": ("net_merchandise_value", "freight_value"),
    "Platform commission": ("commission",),
    "Seller payout": ("seller_payout",),
}
BREAK_EVEN_METRICS = ["Platform commission", "Seller payout"]


# ------------------------------------------------------------------ state
def _baseline_pct() -> dict:
    b = get_baseline_parameters()
    return {
        "price": 0.0, "discount": 0.0, "freight": 0.0, "elasticity": 0.0,
        "commission": round(b["commission_rate"] * 100, 2),
        "cost": round(b["seller_cost_rate"] * 100, 2),
    }


def _init_state() -> None:
    for key, value in _baseline_pct().items():
        st.session_state.setdefault(f"sc_{key}", value)
    st.session_state.setdefault("sc_name", "Scenario 1")
    st.session_state.setdefault("saved_scenarios", {})


def _apply_preset() -> None:
    values = _baseline_pct()
    values.update(PRESETS[st.session_state["sc_preset"]])
    for key, value in values.items():
        st.session_state[f"sc_{key}"] = value


def _scenario_parameters() -> dict:
    s = st.session_state
    return {
        **get_baseline_parameters(),
        "product_price_adjustment": s["sc_price"] / 100,
        "discount_rate": s["sc_discount"] / 100,
        "freight_adjustment": s["sc_freight"] / 100,
        "commission_rate": s["sc_commission"] / 100,
        "seller_cost_rate": s["sc_cost"] / 100,
    }


def _signature(params: dict, elasticity: float) -> str:
    return repr((sorted(params.items()), elasticity))


# --------------------------------------------------------------- selection
def _candidates(data: dict) -> pd.DataFrame:
    if "product_candidates" not in st.session_state:
        st.session_state["product_candidates"] = product_candidates(
            data["items"], data["orders"], data["products"], data["translation"])
    return st.session_state["product_candidates"]


def _focus_selector(data: dict) -> tuple[dict, dict | None, str]:
    focus = st.radio("Focus", ["One product", "Whole business"], horizontal=True,
                     key="sc_focus")
    if focus == "Whole business":
        return data, None, "whole"
    cands = _candidates(data)
    if cands.empty:
        st.error("No product has enough single-product orders for a clean focus.")
        return data, None, "whole"
    labels = {pid: f"{row.category} | {pid[:8]} | {row.pure_orders} orders | "
                   f"{row.sellers} seller(s)" for pid, row in cands.iterrows()}
    ids = list(cands.index)
    default = ids.index(DEFAULT_PRODUCT) if DEFAULT_PRODUCT in ids else 0
    pid = st.selectbox("Product", ids, index=default,
                       format_func=lambda i: labels[i], key="sc_product")
    scoped, info = focus_on_product(data, pid)
    st.markdown(f"**{info['orders_in_scope']:,}** of {info['orders_total']:,} orders in "
                f"scope ({info['scope_share']:.1%})")
    return scoped, info, pid


# ----------------------------------------------------------------- results
def _run(sim_data: dict, scenario: dict, elasticity: float, name: str) -> dict:
    result, f, m, chain = run_product_scenario(sim_data, scenario, elasticity)
    return {"engine": result, "chain": chain, "parameters": scenario,
            "elasticity": elasticity, "factor": f, "multiplier": m, "name": name}


def _steps(chain: dict) -> dict:
    return {s["stage"]: s for stage in chain["stages"] for s in stage["steps"]}


def _pct(step: dict) -> float | None:
    b = step["baseline"]
    return None if not b else step["change"] / b * 100


def _fmt_pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:+.1f}%"


def _period(orders: pd.DataFrame) -> str:
    t = pd.to_datetime(orders["order_purchase_timestamp"])
    return f"{t.min():%b %Y} to {t.max():%b %Y}"


def _delta_text(change: float, pct: float | None, is_count: bool, with_pct: bool) -> str:
    if abs(change) < 0.005:
        return "0" if is_count else "R$ 0.00"
    core = f"{change:+,.0f}" if is_count else (
        ("+" if change > 0 else "") + compact_money(change))
    return f"{core} ({_fmt_pct(pct)})" if with_pct else core


def _result_cards(out: dict) -> list[str]:
    steps = _steps(out["chain"])
    cards = []

    def card(label, key, sub="", is_count=False, with_pct=True):
        s_ = steps[key]
        flat = abs(s_["change"]) < 0.005
        direction = "flat" if flat else ("up" if s_["change"] > 0 else "down")
        val = f"{s_['scenario']:,.0f}" if is_count else compact_money(s_["scenario"])
        return kpi_card(label, val, sub,
                        _delta_text(s_["change"], _pct(s_), is_count, with_pct), direction)

    ov = steps["Order value (all orders with items)"]
    orders = steps["Orders"]
    sub = (f"Orders {orders['baseline']:,.0f} to {orders['scenario']:,.0f}"
           if abs(orders["change"]) > 0.5 else f"Orders {orders['baseline']:,.0f}")
    cards.append(card("Customer order value", ov["stage"], sub))
    cards.append(card("Platform commission", "Platform commission"))
    cards.append(card("Seller payout", "Seller payout"))
    nmv = steps["Net merchandise value"]
    mg = steps["Seller margin (proxy)"]
    rate_b = mg["baseline"] / nmv["baseline"] * 100 if nmv["baseline"] else 0
    rate_s = mg["scenario"] / nmv["scenario"] * 100 if nmv["scenario"] else 0
    cards.append(card("Seller margin (proxy)", "Seller margin (proxy)",
                      f"Margin rate {rate_b:.1f}% to {rate_s:.1f}%", with_pct=False))
    return cards


def _propagation_map(chain: dict):
    """Where the value moves. Edges follow the model's real calculation path."""
    st_ = _steps(chain)

    def moved(step):
        return abs(step["change"]) > 1e-9

    def note(label, step):
        return f"{label} {_fmt_pct(_pct(step))}" if moved(step) else f"{label}: no change"

    prod = st_["Net merchandise value"]
    order = st_["Order value (all orders with items)"]
    pay = st_["Customer payments, orders with a payment record"]
    comm = st_["Platform commission"]
    payout = st_["Seller payout"]
    spend = st_["Customer spend (order value)"]

    notes = {
        "product_management": note("Merchandise", prod),
        "seller_management": note("Payout", payout),
        "order_sales_management": _fmt_pct(_pct(order)) if moved(order) else "no change",
        "payment_revenue_management": note("Payments", pay) + "<br>" + note("Commission", comm),
        "customer_management": note("Spend", spend),
        "delivery_customer_experience": "No effect (not modelled)",
    }
    active = set()
    if moved(prod): active.add("product_management")
    if moved(payout): active.add("seller_management")
    if moved(order): active.add("order_sales_management")
    if moved(pay) or moved(comm): active.add("payment_revenue_management")
    if moved(spend): active.add("customer_management")

    pairs = [("product_management", "order_sales_management"),
             ("order_sales_management", "payment_revenue_management"),
             ("seller_management", "payment_revenue_management"),
             ("order_sales_management", "customer_management"),
             ("order_sales_management", "delivery_customer_experience")]
    edges = [(a, b, "active" if a in active and b in active else "inactive")
             for a, b in pairs]
    return build_component_map(edges, notes, active, height=540)


def _baseline_vs_scenario(chain: dict):
    st_ = _steps(chain)
    labels = ["Order value", "Customer payments", "Platform commission",
              "Seller payout", "Seller margin (proxy)"]
    base = [st_[COMPARE_ROWS[x]]["baseline"] for x in labels]
    scen = [st_[COMPARE_ROWS[x]]["scenario"] for x in labels]
    fig = go.Figure()
    fig.add_bar(name="Baseline", x=labels, y=base, marker_color=COLORS["slate"],
                hovertemplate="%{x}<br>Baseline R$ %{y:,.0f}<extra></extra>")
    fig.add_bar(name="Scenario", x=labels, y=scen, marker_color=COLORS["blue"],
                hovertemplate="%{x}<br>Scenario R$ %{y:,.0f}<extra></extra>")
    fig.update_layout(barmode="group")
    return style_fig(fig, 420)


def _seller_figure(out: dict):
    g = impact_by_seller(out["engine"], out["multiplier"]).head(8)
    fig = go.Figure()
    fig.add_bar(name="Baseline", x=g["label"], y=g["base_payout"], marker_color=COLORS["slate"],
                hovertemplate="Seller %{x}<br>Baseline payout R$ %{y:,.0f}<extra></extra>")
    fig.add_bar(name="Scenario", x=g["label"], y=g["scen_payout"], marker_color=COLORS["cyan"],
                hovertemplate="Seller %{x}<br>Scenario payout R$ %{y:,.0f}<extra></extra>")
    fig.update_layout(barmode="group")
    return style_fig(fig, 420)


def _month_figure(out: dict):
    g = impact_by_month(out["engine"], out["multiplier"])
    fig = go.Figure()
    fig.add_scatter(name="Baseline", x=g["month"], y=g["baseline"], mode="lines+markers",
                    line=dict(color=COLORS["slate"], width=2.5),
                    hovertemplate="%{x}<br>Baseline R$ %{y:,.0f}<extra></extra>")
    fig.add_scatter(name="Scenario", x=g["month"], y=g["scenario"], mode="lines+markers",
                    line=dict(color=COLORS["blue"], width=2.5),
                    hovertemplate="%{x}<br>Scenario R$ %{y:,.0f}<extra></extra>")
    return style_fig(fig, 420)


def _break_even_table(out: dict) -> pd.DataFrame | None:
    f = out["factor"]
    if abs(f - 1.0) < 1e-12:
        return None
    bs = out["engine"]["baseline"]["summary"]
    ss = out["engine"]["scenario"]["summary"]
    rows = []
    for label in BREAK_EVEN_METRICS:
        keys = SENSITIVITY_METRICS[label]
        b, s_ = sum(bs[k] for k in keys), sum(ss[k] for k in keys)
        if b <= 0 or s_ <= 0:
            continue
        e = break_even_elasticity(s_ / b, f)
        rows.append({"Metric": label,
                     "Break-even elasticity": "none" if e is None or e > 0 else f"{e:.2f}"})
    return pd.DataFrame(rows) if rows else None


def _sensitivity_frame(out: dict) -> pd.DataFrame | None:
    f = out["factor"]
    if abs(f - 1.0) < 1e-12:
        return None
    bs = out["engine"]["baseline"]["summary"]
    ss = out["engine"]["scenario"]["summary"]
    grid = np.round(np.arange(0.0, -3.01, -0.1), 2)
    data = {}
    for label, keys in SENSITIVITY_METRICS.items():
        b, s_ = sum(bs[k] for k in keys), sum(ss[k] for k in keys)
        if b > 0:
            data[label] = [((s_ * f ** e) / b - 1) * 100 for e in grid]
    return pd.DataFrame(data, index=pd.Index(grid, name="Assumed price elasticity")) if data else None


def _sensitivity_figure(sens: pd.DataFrame, current: float):
    fig = go.Figure()
    for col in sens.columns:
        fig.add_scatter(x=sens.index, y=sens[col], name=col, mode="lines",
                        hovertemplate=f"{col}<br>elasticity %{{x}}<br>%{{y:+.1f}}%<extra></extra>")
    fig.add_hline(y=0, line=dict(color=COLORS["muted"], width=1, dash="dot"))
    if current != 0:
        fig.add_vline(x=current, line=dict(color=COLORS["amber"], width=1.5, dash="dash"),
                      annotation_text="assumed", annotation_font_color=COLORS["amber"])
    fig.update_xaxes(title="Assumed price elasticity (more negative = customers react more)")
    fig.update_yaxes(title="Change vs baseline (%)", ticksuffix="%")
    return style_fig(fig, 400)


# ------------------------------------------------------------- comparison
def _save_scenario(out: dict) -> None:
    steps = _steps(out["chain"])
    saved = st.session_state["saved_scenarios"]
    if "Baseline" not in saved:
        saved["Baseline"] = {k: steps[v]["baseline"] for k, v in COMPARE_ROWS.items()}
    saved[out["name"]] = {k: steps[v]["scenario"] for k, v in COMPARE_ROWS.items()}


def _render_comparison() -> None:
    saved = st.session_state["saved_scenarios"]
    if len(saved) < 2:
        return
    with st.container(border=True):
        section("Scenario comparison")
        frame = pd.DataFrame(saved)
        shown = frame.copy()
        for col in shown.columns:
            shown[col] = [f"{v:,.2f}" if k not in ("Orders", "Customers") else f"{v:,.0f}"
                          for k, v in frame[col].items()]
        pct = pd.DataFrame({
            name: ((frame[name] / frame["Baseline"] - 1) * 100)
            for name in frame.columns if name != "Baseline"})
        pct = pct.drop(index="Seller margin (proxy)", errors="ignore")
        fig = go.Figure()
        for name in pct.columns:
            fig.add_bar(name=name, x=pct.index, y=pct[name],
                        hovertemplate=f"{name}<br>%{{x}}<br>%{{y:+.1f}}%<extra></extra>")
        fig.update_layout(barmode="group")
        fig.update_yaxes(ticksuffix="%", title="Change vs baseline")
        st.plotly_chart(style_fig(fig, 420), use_container_width=True)
        st.dataframe(shown, use_container_width=True)
        if st.button("Clear saved scenarios"):
            st.session_state["saved_scenarios"] = {}
            st.rerun()


# ----------------------------------------------------------- product views
def _profile_section(sim_data: dict) -> None:
    p = product_profile(sim_data)
    st.session_state["profile_period"] = f"{p['first_month']} to {p['last_month']}"
    with st.container(border=True):
        section("Product profile", basis="observed")
        kpi_row([
            kpi_card("Baseline order value", compact_money(p["order_value"]),
                     f"{p['first_month']} to {p['last_month']}"),
            kpi_card("Orders", f"{p['orders']:,}", f"{p['sellers']} sellers"),
            kpi_card("Average price", f"R$ {p['avg_price']:,.2f}",
                     f"R$ {p['price_min']:,.2f} to R$ {p['price_max']:,.2f}"),
            kpi_card("Freight share", f"{p['freight_share'] * 100:.1f}%", "of order value"),
        ])
        h = p["history"]
        fig = go.Figure()
        fig.add_bar(x=h["month"], y=h["orders"], name="Orders", marker_color=COLORS["blue"],
                    hovertemplate="%{x}<br>%{y} orders<extra></extra>")
        fig.add_scatter(x=h["month"], y=h["avg_price"], name="Average price (R$)",
                        yaxis="y2", mode="lines+markers",
                        line=dict(color=COLORS["amber"], width=2.5),
                        hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                      tickfont=dict(color=COLORS["muted"])))
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)


def _portfolio_section(data: dict, out: dict) -> None:
    sig = _signature(out["parameters"], out["elasticity"])
    with st.container(border=True):
        section("Same scenario across products", basis="counterfactual")
        if st.button("Compare across products"):
            with st.spinner("Running the scenario on each product..."):
                res = portfolio_comparison(data, _candidates(data), out["parameters"],
                                           out["elasticity"])
            st.session_state["portfolio"] = {"sig": sig, "frame": res}
        cached = st.session_state.get("portfolio")
        if not cached or cached["sig"] != sig:
            return
        res = cached["frame"]
        top = res.head(12).iloc[::-1]
        labels = top["category"].str.replace("_", " ") + " | " + top["product_id"].str[:6]
        fig = go.Figure(go.Bar(
            x=top["order_value_change"], y=labels, orientation="h",
            marker_color=[COLORS["green"] if v >= 0 else COLORS["red"]
                          for v in top["order_value_change"]],
            hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>"))
        fig.update_xaxes(title="Change in customer order value (R$)")
        st.plotly_chart(style_fig(fig, 460, legend=False), use_container_width=True)
        table = pd.DataFrame({
            "Category": res["category"].str.replace("_", " "),
            "Product": res["product_id"].str[:8],
            "Orders": res["orders"], "Sellers": res["sellers"],
            "Baseline order value": res["base_order_value"].map("{:,.0f}".format),
            "Scenario order value": res["scen_order_value"].map("{:,.0f}".format),
            "Change": res["order_value_change"].map("{:+,.0f}".format),
            "Change %": res["order_value_pct"].map("{:+.1f}%".format),
            "Commission change": res["commission_change"].map("{:+,.0f}".format),
            "Commission break-even": res["commission_break_even"].map(
                lambda v: "none" if pd.isna(v) or v > 0 else f"{v:.2f}"),
        })
        st.dataframe(table, hide_index=True, use_container_width=True)


# -------------------------------------------------------------------- page
def render_scenario_page(data: dict, report_dir) -> None:
    _init_state()
    page_header("Scenario Analysis", "")

    with st.container(border=True):
        section("Product")
        sim_data, scope, focus_key = _focus_selector(data)
        if st.session_state.get("focus_key") != focus_key:
            st.session_state["focus_key"] = focus_key
            st.session_state["saved_scenarios"] = {}
            st.session_state.pop("twin_scenario", None)
            st.session_state.pop("portfolio", None)

    if scope is not None:
        _profile_section(sim_data)

    with st.container(border=True):
        section("Scenario")
        a, b = st.columns([2, 1])
        a.selectbox("Real-life scenario", list(PRESETS), key="sc_preset",
                    on_change=_apply_preset)
        b.text_input("Scenario name", key="sc_name")
        c1, c2, c3 = st.columns(3)
        c1.slider("Product price change (%)", -30.0, 30.0, step=0.5, key="sc_price")
        c2.slider("Discount on products (%)", 0.0, 30.0, step=0.5, key="sc_discount")
        c3.slider("Freight charge change (%)", -100.0, 50.0, step=1.0, key="sc_freight")
        c4, c5, c6 = st.columns(3)
        c4.slider("Platform commission (%)", 0.0, 30.0, step=0.5, key="sc_commission",
                  help="Published range 19-21% by seller plan. Charged on product "
                       "value, freight excluded.")
        c5.slider("Seller cost rate (%)", 50.0, 90.0, step=0.5, key="sc_cost",
                  help="External retail-margin proxy, not an Olist-observed cost.")
        c6.slider("Price elasticity (assumption)", -3.0, 0.0, step=0.1, key="sc_elasticity",
                  help="Not estimated from Olist. Customers react to price plus freight. "
                       "One value for the whole scope. 0 keeps volumes at their "
                       "historical values.")
        with st.expander("Assumptions and sources"):
            st.dataframe(pd.DataFrame([{
                "Parameter": a_.label, "Baseline": round(a_.baseline, 4),
                "Status": STATUS_LABEL[a_.status], "Source": a_.source,
            } for a_ in ASSUMPTIONS.values()]), hide_index=True, use_container_width=True)
        run = st.button("Run Scenario", type="primary")

    if run:
        try:
            with st.spinner("Running scenario and tracing effects..."):
                st.session_state["twin_scenario"] = _run(
                    sim_data, _scenario_parameters(), st.session_state["sc_elasticity"],
                    st.session_state["sc_name"].strip() or "Unnamed scenario")
        except Exception as error:
            st.error(f"Scenario execution failed: {error}")

    out = st.session_state.get("twin_scenario")
    if not out:
        _render_comparison()
        return

    chain = out["chain"]
    failed = [n for n, ok in chain["checks"] if not ok]
    basis = ("What-if at historical volumes" if out["multiplier"] == 1.0 else
             f"Assumed elasticity {out['elasticity']:.1f}, volume x{out['multiplier']:.3f}")
    status = (f"Reconciliation {len(chain['checks'])}/{len(chain['checks'])} passed"
              if not failed else f"Reconciliation failed: {failed}")
    page_header(f"Results: {out['name']}",
                f"Totals for {_period(sim_data['orders'])}  |  {basis}  |  {status}")
    kpi_row(_result_cards(out))

    with st.container(border=True):
        section("How the change travels")
        st.plotly_chart(_propagation_map(chain), use_container_width=True)

    left, right = st.columns(2)
    with left, st.container(border=True):
        section("Impact by seller", basis="counterfactual")
        st.plotly_chart(_seller_figure(out), use_container_width=True)
    with right, st.container(border=True):
        section("Impact over time", basis="counterfactual")
        st.plotly_chart(_month_figure(out), use_container_width=True)

    with st.container(border=True):
        section("Baseline vs scenario", basis="counterfactual")
        st.plotly_chart(_baseline_vs_scenario(chain), use_container_width=True)

    be = _break_even_table(out)
    if be is not None:
        with st.container(border=True):
            section("Break-even demand response", basis="assumption")
            l2, r2 = st.columns(2)
            with l2:
                st.dataframe(be, hide_index=True, use_container_width=True)
            with r2:
                sens = _sensitivity_frame(out)
                if sens is not None:
                    st.plotly_chart(_sensitivity_figure(sens, out["elasticity"]),
                                    use_container_width=True)

    if scope is not None:
        _portfolio_section(data, out)

    if st.button("Save to comparison"):
        _save_scenario(out)
    _render_comparison()

    with st.expander("Calculation trace"):
        for stage in chain["stages"]:
            st.markdown(f"**{stage['stage']}**")
            rows = []
            for s_ in stage["steps"]:
                if s_["baseline"] is None:
                    rows.append({"Item": s_["stage"], "Baseline": "-", "Scenario": "-",
                                 "Change": s_["formula"], "Formula": s_["formula"],
                                 "Fields": s_["fields"]})
                else:
                    rows.append({"Item": s_["stage"], "Baseline": f"{s_['baseline']:,.2f}",
                                 "Scenario": f"{s_['scenario']:,.2f}",
                                 "Change": f"{s_['change']:+,.2f}",
                                 "Formula": s_["formula"], "Fields": s_["fields"]})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.container(border=True):
        section("Reports")
        if st.button("Generate Excel and PDF report"):
            try:
                with st.spinner("Generating reports..."):
                    orch = ScenarioOrchestrator(
                        products=sim_data["products"], order_items=sim_data["items"],
                        orders=sim_data["orders"], customers=sim_data["customers"],
                        category_translation=sim_data["translation"],
                        baseline_parameters=get_baseline_parameters(),
                        scenario_parameters=out["parameters"], output_dir=report_dir)
                    res = orch.run()
                if res.get("status") == "FAILED":
                    st.error(f"Report generation failed: {res}")
                else:
                    st.session_state["scenario_result"] = res
                    st.success("Reports generated.")
            except Exception as error:
                st.error(f"Report generation failed: {error}")
        paths = (st.session_state.get("scenario_result") or {}).get("report_paths", {})
        for name, path in paths.items():
            try:
                with open(path, "rb") as fh:
                    st.download_button(f"Download {name}", fh.read(),
                                       file_name=str(path).split("\\")[-1].split("/")[-1],
                                       key=f"dl_{name}")
            except OSError:
                pass
