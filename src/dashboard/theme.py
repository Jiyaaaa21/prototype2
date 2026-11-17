"""Visual theme for the BizTwin dashboard: CSS, Plotly style, KPI cards."""
from __future__ import annotations

import html

import streamlit as st

COLORS = {
    "bg": "#0A0F1C", "panel": "#111827", "panel2": "#0F172A", "border": "#1F2937",
    "text": "#E5E7EB", "muted": "#9CA3AF", "dim": "#6B7280",
    "blue": "#3B82F6", "cyan": "#22D3EE", "green": "#34D399",
    "amber": "#FBBF24", "red": "#F87171", "slate": "#4B5563", "violet": "#A78BFA",
}
COLORWAY = [COLORS["blue"], COLORS["cyan"], COLORS["green"],
            COLORS["amber"], COLORS["violet"], "#F472B6"]

TAGS = {
    "observed": ("Observed", "obs"),
    "external": ("External source", "ext"),
    "assumption": ("User assumption", "asm"),
    "counterfactual": ("What-if", "cf"),
}

_ICONS = {  # 24x24 stroke icons
    "dollar": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "bag": '<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    "tag": '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "store": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "truck": '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
    "percent": '<line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "pie": '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
    "trend": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {{
  font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}}
.stApp {{
  color: {COLORS['text']};
  background:
    radial-gradient(1100px 520px at 85% -8%, rgba(59,130,246,.13), transparent 60%),
    radial-gradient(900px 480px at -5% 105%, rgba(34,211,238,.07), transparent 60%),
    {COLORS['bg']};
}}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stAppDeployButton"], .stDeployButton {{ display: none; }}
.block-container {{ padding-top: 4.2rem; padding-bottom: 4rem; max-width: 1400px; }}
[data-testid="stVerticalBlock"] {{ gap: 1.4rem; }}
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-thumb {{ background: #243044; border-radius: 8px; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #0C1324 0%, #0A101E 100%);
  border-right: 1px solid {COLORS['border']};
}}
.brand {{ display: flex; align-items: center; gap: 12px; margin: 6px 0 2px 0; }}
.brand-logo {{
  width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center;
  background: linear-gradient(135deg, {COLORS['blue']}, {COLORS['cyan']});
  color: #fff; font-weight: 700; font-size: .95rem; letter-spacing: .02em;
  box-shadow: 0 6px 18px rgba(59,130,246,.35);
}}
.brand-name {{ font-size: 1.12rem; font-weight: 700; line-height: 1.1; }}
.brand-sub {{ color: {COLORS['dim']}; font-size: .74rem; margin-top: 2px; }}
.nav-label {{ color: {COLORS['dim']}; font-size: .68rem; letter-spacing: .12em;
  text-transform: uppercase; margin: 26px 0 6px 6px; }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 4px; }}
[data-testid="stSidebar"] label[data-baseweb="radio"] {{
  padding: 10px 14px; border-radius: 11px; margin: 0; width: 100%;
  border: 1px solid transparent; transition: background .15s, border-color .15s;
}}
[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {{ display: none; }}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {{ background: rgba(255,255,255,.04); }}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {{
  background: rgba(59,130,246,.14); border-color: rgba(59,130,246,.35);
}}
[data-testid="stSidebar"] label[data-baseweb="radio"] p {{ font-weight: 500; }}

/* ---------- headings ---------- */
h1, h2, h3 {{ letter-spacing: -0.015em; color: {COLORS['text']}; }}
.eyebrow {{ color: {COLORS['cyan']}; font-size: .72rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase; margin-bottom: 6px; }}
.page-title {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 .25rem 0; }}
.page-sub {{ color: {COLORS['muted']}; font-size: .92rem; margin-bottom: 1.2rem; }}
.sec-title {{ font-size: 1.06rem; font-weight: 600; margin: 0 0 4px 0; color: {COLORS['text']}; }}

/* ---------- KPI cards ---------- */
.kpi {{
  background: linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.012)), {COLORS['panel']};
  border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 22px 24px; height: 100%;
  box-shadow: 0 10px 28px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.04);
  transition: transform .18s ease, border-color .18s ease;
}}
.kpi:hover {{ transform: translateY(-2px); border-color: rgba(59,130,246,.45); }}
.kpi-top {{ display: flex; justify-content: space-between; align-items: center; }}
.kpi-label {{ color: {COLORS['muted']}; font-size: .74rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: .08em; }}
.kpi-icon {{ width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center;
  background: rgba(59,130,246,.14); color: {COLORS['cyan']}; }}
.kpi-icon svg {{ width: 18px; height: 18px; fill: none; stroke: currentColor;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
.kpi-value {{ font-size: 2.15rem; font-weight: 700; letter-spacing: -0.02em; margin: 14px 0 10px 0; }}
.kpi-foot {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}
.chip {{ font-size: .8rem; font-weight: 600; padding: 3px 10px; border-radius: 999px; }}
.chip.up {{ background: rgba(52,211,153,.14); color: {COLORS['green']}; }}
.chip.down {{ background: rgba(248,113,113,.14); color: {COLORS['red']}; }}
.chip.flat {{ background: rgba(156,163,175,.14); color: {COLORS['muted']}; }}
.kpi-sub {{ color: {COLORS['dim']}; font-size: .78rem; }}

/* ---------- basis tags ---------- */
.tag {{ display: inline-block; font-size: .66rem; font-weight: 600; padding: 3px 9px;
  border-radius: 999px; margin-left: 10px; vertical-align: middle; letter-spacing: .02em; }}
.tag.obs {{ background: rgba(52,211,153,.13); color: {COLORS['green']}; }}
.tag.ext {{ background: rgba(59,130,246,.15); color: {COLORS['blue']}; }}
.tag.asm {{ background: rgba(251,191,36,.14); color: {COLORS['amber']}; }}
.tag.cf  {{ background: rgba(156,163,175,.14); color: {COLORS['muted']}; }}

/* ---------- containers, inputs, buttons ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: linear-gradient(180deg, rgba(255,255,255,.028), rgba(255,255,255,.008)), {COLORS['panel']};
  border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 16px 20px 12px 20px;
  box-shadow: 0 10px 28px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.035);
}}
[data-testid="stExpander"] {{
  border: 1px solid {COLORS['border']}; border-radius: 12px; background: rgba(15,23,42,.55);
}}
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"] {{
  background: {COLORS['panel2']} !important; border-radius: 10px !important;
}}
[data-baseweb="select"] > div, [data-baseweb="input"] {{ border: 1px solid {COLORS['border']} !important; }}
.stButton > button, .stDownloadButton > button {{
  border-radius: 10px; border: 1px solid {COLORS['border']}; background: {COLORS['panel2']};
  color: {COLORS['text']}; font-weight: 500; padding: .5rem 1.1rem; transition: all .15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  border-color: {COLORS['blue']}; color: #fff; transform: translateY(-1px);
}}
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {COLORS['blue']}, #2563EB); border: 0; color: #fff;
  font-weight: 600; box-shadow: 0 8px 20px rgba(59,130,246,.35);
}}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.08); }}
[data-testid="stSlider"] label p {{ color: {COLORS['muted']}; font-size: .86rem; }}
[data-testid="stAlert"] {{ border-radius: 12px; }}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _safe(text: str) -> str:
    return html.escape(text).replace("$", "&#36;")


def tag(kind: str) -> str:
    label, css = TAGS[kind]
    return f'<span class="tag {css}">{label}</span>'


def brand() -> str:
    return ('<div class="brand"><div class="brand-logo">BT</div><div>'
            '<div class="brand-name">BizTwin</div>'
            '<div class="brand-sub">Commercial &amp; Sales Digital Twin</div></div></div>'
            '<div class="nav-label">Navigation</div>')


def page_header(title: str, subtitle: str, eyebrow: str = "") -> None:
    top = f'<div class="eyebrow">{_safe(eyebrow)}</div>' if eyebrow else ""
    sub = f'<div class="page-sub">{_safe(subtitle)}</div>' if subtitle else ""
    st.markdown(f'{top}<div class="page-title">{_safe(title)}</div>{sub}',
                unsafe_allow_html=True)


def section(title: str, note: str = "", basis: str | None = None) -> None:
    badge = tag(basis) if basis else ""
    st.markdown(f'<div class="sec-title">{_safe(title)}{badge}</div>',
                unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", delta: str = "",
             delta_dir: str = "flat", icon: str = "") -> str:
    ico = (f'<div class="kpi-icon"><svg viewBox="0 0 24 24">{_ICONS[icon]}</svg></div>'
           if icon in _ICONS else "")
    chip = f'<span class="chip {delta_dir}">{_safe(delta)}</span>' if delta else ""
    s = f'<span class="kpi-sub">{_safe(sub)}</span>' if sub else ""
    foot = f'<div class="kpi-foot">{chip}{s}</div>' if (chip or s) else ""
    return (f'<div class="kpi"><div class="kpi-top"><span class="kpi-label">{_safe(label)}</span>'
            f'{ico}</div><div class="kpi-value">{_safe(value)}</div>{foot}</div>')


def kpi_row(cards: list[str]) -> None:
    for col, card in zip(st.columns(len(cards)), cards):
        col.markdown(card, unsafe_allow_html=True)


def style_fig(fig, height: int = 320, legend: bool = True):
    grid = "rgba(148,163,184,0.12)"
    fig.update_layout(
        height=height, template=None, colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["text"], size=12),
        margin=dict(l=8, r=8, t=30, b=8), showlegend=legend, bargap=0.38,
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right",
                    font=dict(color=COLORS["muted"], size=11)),
        hoverlabel=dict(bgcolor="#0B1222", bordercolor=COLORS["border"],
                        font=dict(family="Inter, Segoe UI, sans-serif", size=12)),
    )
    fig.update_xaxes(gridcolor=grid, zeroline=False, showline=False,
                     tickfont=dict(color=COLORS["muted"], size=11))
    fig.update_yaxes(gridcolor=grid, zeroline=False, showline=False,
                     tickfont=dict(color=COLORS["muted"], size=11))
    try:   # rounded bars where the installed Plotly supports it
        fig.update_traces(marker_cornerradius=6, selector=dict(type="bar"))
    except Exception:
        pass
    return fig


def chart(fig) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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
