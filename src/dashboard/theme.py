"""Visual theme for the BizTwin dashboard: CSS, Plotly style, KPI cards."""
from __future__ import annotations

import html

import streamlit as st

COLORS = {
    "bg": "#0B1220", "panel": "#111A2E", "border": "#1E293B",
    "text": "#E2E8F0", "muted": "#94A3B8",
    "blue": "#2F81F7", "cyan": "#22D3EE", "green": "#3FB950",
    "amber": "#D29922", "red": "#F85149", "slate": "#475569",
}
COLORWAY = [COLORS["blue"], COLORS["cyan"], COLORS["green"],
            COLORS["amber"], "#A78BFA", "#F472B6"]

TAGS = {  # basis labels shown next to figures
    "observed": ("Observed", "obs"),
    "external": ("External source", "ext"),
    "assumption": ("User assumption", "asm"),
    "counterfactual": ("What-if", "cf"),
}

_CSS = f"""
<style>
html, body, [class*="css"] {{
  font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
}}
.stApp {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}
.block-container {{ padding-top: 4.6rem; padding-bottom: 4rem; max-width: 1400px; }}
[data-testid="stVerticalBlock"] {{ gap: 1.4rem; }}
[data-testid="stSidebar"] {{
  background: #0F172A; border-right: 1px solid {COLORS['border']};
}}
[data-testid="stAppDeployButton"], .stDeployButton {{ display: none; }}
h1, h2, h3 {{ letter-spacing: -0.01em; color: {COLORS['text']}; }}
.page-title {{ font-size: 1.9rem; font-weight: 700; margin: 0 0 .2rem 0; }}
.page-sub {{ color: {COLORS['muted']}; font-size: .92rem; margin-bottom: 1.1rem; }}
.brand {{ font-size: 1.15rem; font-weight: 700; color: {COLORS['text']}; }}
.brand span {{ color: {COLORS['cyan']}; }}
.brand-sub {{ color: {COLORS['muted']}; font-size: .78rem; margin-bottom: 1rem; }}
.kpi {{
  background: {COLORS['panel']}; border: 1px solid {COLORS['border']};
  border-radius: 14px; padding: 24px 26px; height: 100%;
  border-top: 2px solid {COLORS['blue']};
}}
.kpi-label {{ color: {COLORS['muted']}; font-size: .75rem; text-transform: uppercase;
  letter-spacing: .06em; }}
.kpi-value {{ font-size: 2.1rem; font-weight: 700; margin: 8px 0 6px 0;
  color: {COLORS['text']}; }}
.kpi-sub {{ color: {COLORS['muted']}; font-size: .76rem; }}
.kpi-delta {{ font-size: .95rem; font-weight: 600; margin-bottom: 2px; }}
.kpi-delta.up {{ color: {COLORS['green']}; }}
.kpi-delta.down {{ color: {COLORS['red']}; }}
.kpi-delta.flat {{ color: {COLORS['muted']}; }}
.sec-title {{ font-size: 1.08rem; font-weight: 600; margin: 0; color: {COLORS['text']}; }}
.sec-note {{ color: {COLORS['muted']}; font-size: .78rem; margin: 2px 0 6px 0; }}
.tag {{ display: inline-block; font-size: .68rem; font-weight: 600; padding: 2px 8px;
  border-radius: 999px; margin-left: 8px; vertical-align: middle; }}
.tag.obs {{ background: rgba(63,185,80,.15); color: {COLORS['green']}; }}
.tag.ext {{ background: rgba(47,129,247,.15); color: {COLORS['blue']}; }}
.tag.asm {{ background: rgba(210,153,34,.18); color: {COLORS['amber']}; }}
.tag.cf  {{ background: rgba(148,163,184,.18); color: {COLORS['muted']}; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: {COLORS['panel']}; border-radius: 14px;
  border: 1px solid {COLORS['border']}; padding: 14px 18px 10px 18px;
}}
.stButton > button[kind="primary"] {{
  background: {COLORS['blue']}; border: 0; border-radius: 10px; font-weight: 600;
}}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def tag(kind: str) -> str:
    label, css = TAGS[kind]
    return f'<span class="tag {css}">{label}</span>'


def page_header(title: str, subtitle: str) -> None:
    sub = f'<div class="page-sub">{_safe(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="page-title">{_safe(title)}</div>{sub}',
                unsafe_allow_html=True)


def section(title: str, note: str = "", basis: str | None = None) -> None:
    badge = tag(basis) if basis else ""
    st.markdown(f'<div class="sec-title">{_safe(title)}{badge}</div>',
                unsafe_allow_html=True)


def _safe(text: str) -> str:
    return html.escape(text).replace("$", "&#36;")


def kpi_card(label: str, value: str, sub: str = "", delta: str = "",
             delta_dir: str = "flat") -> str:
    d = f'<div class="kpi-delta {delta_dir}">{_safe(delta)}</div>' if delta else ""
    s = f'<div class="kpi-sub">{_safe(sub)}</div>' if sub else ""
    return (f'<div class="kpi"><div class="kpi-label">{_safe(label)}</div>'
            f'<div class="kpi-value">{_safe(value)}</div>{d}{s}</div>')


def kpi_row(cards: list[str]) -> None:
    for col, card in zip(st.columns(len(cards)), cards):
        col.markdown(card, unsafe_allow_html=True)


def style_fig(fig, height: int = 320, legend: bool = True):
    fig.update_layout(
        height=height, template=None, colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["text"], size=12),
        margin=dict(l=8, r=8, t=28, b=8), showlegend=legend,
        legend=dict(orientation="h", y=1.12, x=0, font=dict(color=COLORS["muted"])),
        hoverlabel=dict(bgcolor=COLORS["panel"], bordercolor=COLORS["border"]),
    )
    fig.update_xaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"],
                     linecolor=COLORS["border"], tickfont=dict(color=COLORS["muted"]))
    fig.update_yaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"],
                     linecolor=COLORS["border"], tickfont=dict(color=COLORS["muted"]))
    return fig


def compact_money(v: float, currency: str = "R$ ") -> str:
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e9:
        return f"{sign}{currency}{a / 1e9:.2f}B"
    if a >= 1e6:
        return f"{sign}{currency}{a / 1e6:.2f}M"
    if a >= 1e3:
        return f"{sign}{currency}{a / 1e3:.1f}K"
    return f"{sign}{currency}{a:,.2f}"
