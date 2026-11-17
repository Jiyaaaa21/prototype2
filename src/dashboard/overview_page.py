"""Business Overview page."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.dashboard.component_map import build_component_map, registry_edges
from src.dashboard.overview_metrics import compute_overview
from src.dashboard.theme import (
    COLORS, compact_money, kpi_card, kpi_row, page_header, section, style_fig,
)

PCT = lambda v: f"{v * 100:.1f}%"


@st.cache_data(show_spinner="Computing business metrics...")
def _overview(_data: dict, cache_key: str) -> dict:
    return compute_overview(_data)


def render_overview(data: dict, replay_report: dict | None = None) -> None:
    m = _overview(data, f"{len(data['items'])}-{len(data['orders'])}")
    k = m["kpis"]

    page_header("Business Overview", f"{k['first_month']} to {k['last_month']}")

    kpi_row([
        kpi_card("Total revenue", compact_money(k["revenue"])),
        kpi_card("Orders", f"{k['orders']:,}"),
        kpi_card("Average order value", f"R$ {k['aov']:,.2f}"),
    ])
    kpi_row([
        kpi_card("Customers", f"{k['customers']:,}"),
        kpi_card("Sellers", f"{k['sellers']:,}"),
        kpi_card("On-time delivery", PCT(k["on_time_rate"])),
    ])

    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        section("Monthly revenue and orders", basis="observed")
        mo = m["monthly"]
        fig = go.Figure()
        fig.add_bar(x=mo["month"], y=mo["revenue"], name="Revenue (R$)",
                    marker_color=COLORS["blue"],
                    hovertemplate="%{x}<br>R$ %{y:,.0f}<extra></extra>")
        fig.add_scatter(x=mo["month"], y=mo["orders"], name="Orders", yaxis="y2",
                        mode="lines+markers", line=dict(color=COLORS["cyan"], width=2.5),
                        hovertemplate="%{x}<br>%{y:,} orders<extra></extra>")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                      tickfont=dict(color=COLORS["muted"])))
        st.plotly_chart(style_fig(fig, 440), use_container_width=True)
    with right, st.container(border=True):
        section("Payment methods", basis="observed")
        pt = m["payment_types"]
        fig = go.Figure(go.Pie(labels=pt["payment_type"].str.replace("_", " ").str.title(),
                               values=pt["payment_value"], hole=0.62, sort=False,
                               marker=dict(line=dict(color=COLORS["panel"], width=2)),
                               textinfo="percent"))
        st.plotly_chart(style_fig(fig, 440), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        section("Top product categories", basis="observed")
        cat = m["category"].iloc[::-1]
        fig = go.Figure(go.Bar(x=cat["merchandise"], y=cat["category"].str.replace("_", " "),
                               orientation="h", marker_color=COLORS["blue"],
                               hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>"))
        st.plotly_chart(style_fig(fig, 440, legend=False), use_container_width=True)
    with c2, st.container(border=True):
        section("Top sellers", basis="observed")
        ts = m["top_sellers"].iloc[::-1]
        fig = go.Figure(go.Bar(x=ts["merchandise"], y=ts["label"], orientation="h",
                               marker_color=COLORS["cyan"], customdata=ts["orders"],
                               hovertemplate="Seller %{y}<br>R$ %{x:,.0f}<br>"
                                             "%{customdata:,} orders<extra></extra>"))
        st.plotly_chart(style_fig(fig, 440, legend=False), use_container_width=True)

    d1, d2 = st.columns(2)
    with d1, st.container(border=True):
        section("On-time delivery by month", basis="observed")
        dm = m["delivery_monthly"]
        fig = go.Figure(go.Scatter(x=dm["month"], y=dm["on_time"] * 100, mode="lines+markers",
                                   line=dict(color=COLORS["green"], width=2.5),
                                   hovertemplate="%{x}<br>%{y:.1f}% on time<extra></extra>"))
        fig.update_yaxes(ticksuffix="%", range=[0, 100])
        st.plotly_chart(style_fig(fig, 420, legend=False), use_container_width=True)
    with d2, st.container(border=True):
        section("Review score by delivery time", basis="observed")
        rb = m["review_by_delivery"]
        fig = go.Figure(go.Bar(x=rb["bucket"].astype(str), y=rb["score"],
                               marker_color=COLORS["amber"], customdata=rb["orders"],
                               hovertemplate="%{x}<br>%{y:.2f} average<br>"
                                             "%{customdata:,} orders<extra></extra>"))
        fig.update_yaxes(range=[1, 5])
        st.plotly_chart(style_fig(fig, 420, legend=False), use_container_width=True)

    with st.container(border=True):
        section("Business components")
        st.plotly_chart(build_component_map(registry_edges(), height=540),
                        use_container_width=True)
