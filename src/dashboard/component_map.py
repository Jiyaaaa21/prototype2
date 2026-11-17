"""Interconnected-component map (Plotly) for the overview and scenario pages."""
from __future__ import annotations

import math

import plotly.graph_objects as go

from src.dashboard.theme import COLORS, style_fig
from src.relationships.relationship_manager import RelationshipManager

NODES = {
    "customer_management": "Customer",
    "product_management": "Product",
    "seller_management": "Seller",
    "order_sales_management": "Order & Sales",
    "payment_revenue_management": "Payment & Revenue",
    "delivery_customer_experience": "Delivery & Experience",
}
CENTER = "order_sales_management"

# hub-and-spoke: Order & Sales in the centre
_R, _SX = 2.2, 1.55
POS = {CENTER: (0.0, 0.0)}
for _name, _deg in [("seller_management", 90), ("payment_revenue_management", 18),
                    ("delivery_customer_experience", -54),
                    ("customer_management", -126), ("product_management", 162)]:
    POS[_name] = (_SX * _R * math.cos(math.radians(_deg)),
                  _R * math.sin(math.radians(_deg)))

# approximate pixels per data unit (figure ~1250 px wide), used to trim edges
_XR, _YR, _W = 4.7, 3.2, 1250.0
NODE_PX = {CENTER: 46.0}          # edge trim radius in px; others use the default
DEFAULT_PX = 24.0

EDGE_STYLE = {   # colour, width, dash
    "direct": (COLORS["blue"], 2.4, "solid"),
    "indirect": (COLORS["cyan"], 1.8, "dash"),
    "hypothesis": (COLORS["slate"], 1.4, "dot"),
    "active": (COLORS["cyan"], 3.4, "solid"),
    "inactive": (COLORS["slate"], 1.6, "dot"),
}
_TYPE_STYLE = {"DIRECT_OBSERVED": "direct", "INDIRECT_DERIVED": "indirect",
               "BEHAVIOURAL_HYPOTHESIS": "hypothesis"}


def registry_edges() -> list[tuple[str, str, str]]:
    """Relationships from the registry; a hypothesis duplicating a drawn pair is skipped."""
    edges, seen = [], set()
    for r in RelationshipManager().get_all_relationships():
        style = _TYPE_STYLE[r.relationship_type]
        if style == "hypothesis" and (r.source, r.target) in seen:
            continue
        seen.add((r.source, r.target))
        edges.append((r.source, r.target, style))
    return edges


def build_component_map(edges, node_notes: dict | None = None,
                        active_nodes: set | None = None, height: int = 430):
    node_notes = node_notes or {}
    pairs = {(a, b) for a, b, _ in edges}
    kx, ky = _W / (2 * _XR), (height - 50) / (2 * _YR)
    fig = go.Figure()

    for a, b, style in edges:
        (x0, y0), (x1, y1) = POS[a], POS[b]
        dxp, dyp = (x1 - x0) * kx, (y1 - y0) * ky          # pixel space
        length = math.hypot(dxp, dyp)
        ux, uy = dxp / length, dyp / length
        off = 7.0 if (b, a) in pairs else 0.0              # separate reverse pairs
        px, py = -uy * off, ux * off
        ra, rb = NODE_PX.get(a, DEFAULT_PX), NODE_PX.get(b, DEFAULT_PX)
        sx, sy = x0 + (ux * ra + px) / kx, y0 + (uy * ra + py) / ky
        ex, ey = x1 - (ux * rb - px) / kx, y1 - (uy * rb - py) / ky
        color, width, dash = EDGE_STYLE[style]
        fig.add_trace(go.Scatter(x=[sx, ex], y=[sy, ey], mode="lines",
                                 line=dict(color=color, width=width, dash=dash),
                                 hoverinfo="skip", showlegend=False))
        fig.add_annotation(x=ex, y=ey, ax=ex - ux * 16 / kx, ay=ey - uy * 16 / ky,
                           xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=2, arrowsize=1.1,
                           arrowwidth=max(width - 0.4, 1.4), arrowcolor=color)

    for name, label in NODES.items():
        x, y = POS[name]
        on = active_nodes is None or name in active_nodes
        fill = COLORS["blue"] if on else COLORS["panel"]
        line = COLORS["cyan"] if on else COLORS["slate"]
        note = node_notes.get(name)
        c = COLORS["cyan"] if on else COLORS["muted"]
        if name == CENTER:                       # label inside the larger hub node
            inner = "<b>Order<br>& Sales</b>"
            if note:
                inner += f'<br><span style="font-size:10px;color:#E2E8F0">{note}</span>'
            fig.add_trace(go.Scatter(
                x=[x], y=[y], mode="markers+text", text=[inner],
                textposition="middle center",
                textfont=dict(color="#FFFFFF", size=11),
                marker=dict(size=92, color=fill, line=dict(color=line, width=3)),
                hovertext=[note or label], hoverinfo="text", showlegend=False))
            continue
        top = y > 0.3
        text = f"<b>{label}</b>"
        if note:
            span = f'<span style="font-size:11px;color:{c}">{note}</span>'
            text = (span + "<br>" + text) if top else (text + "<br>" + span)
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[text],
            textposition="top center" if top else "bottom center",
            textfont=dict(color=COLORS["text"], size=12),
            marker=dict(size=34, color=fill, line=dict(color=line, width=2.5)),
            hovertext=[(note or label).replace("<br>", ", ")], hoverinfo="text",
            showlegend=False))
    fig.update_xaxes(visible=False, range=[-_XR, _XR])
    fig.update_yaxes(visible=False, range=[-_YR, _YR])
    return style_fig(fig, height=height, legend=False)
