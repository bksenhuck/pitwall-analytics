"""Analytics › Telemetria — análise comparativa sincronizada."""
import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objs as go
import numpy as np
import requests

from frontend.components.navigation import create_analytics_subnav
from frontend.api import client
from frontend.f1_config import get_driver_color, get_driver_full_name
from frontend.config import BACKEND_API_URL
from frontend.utils import (
    BORDER as _BORDER,
    MUTED as _MUTED,
    fmt_laptime_full as _fmt_laptime_full,
    hex_to_rgba as _hex_to_rgba,
    alert_cache_empty,
    alert_backend_error,
    seasons_to_options,
)

_BG = "#F4F5F7"
_TEXT = "#1A1A1A"

dash.register_page(__name__, path="/analytics/telemetria", name="Telemetria")

_CONTRAST_PALETTE = [
    "#FFFFFF", "#FFD700", "#FF6B6B",
    "#4ECDC4", "#A29BFE", "#FD79A8",
]
_LINE_STYLES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]

_SESSION_LABELS = {
    "FP1": "Treino Livre 1 (FP1)",
    "FP2": "Treino Livre 2 (FP2)",
    "FP3": "Treino Livre 3 (FP3)",
    "Q": "Qualificação (Q)",
    "Q1": "Q1",
    "Q2": "Q2",
    "Q3": "Q3",
    "SQ": "Sprint Quali (SQ)",
    "S": "Sprint (S)",
    "R": "Corrida (R)",
}


# ── Helpers ──────────────────────────────────────────────────────

def _compute_gap_all(
    dist: list,
    drivers_tele: dict,
    selected_drivers: list,
    lap_times: dict,
):
    """
    Returns (gaps_dict, ref_driver).
    gaps_dict[drv] = cumulative time gap vs fastest driver (ref = 0).
    """
    empty = {drv: [0.0] * len(dist) for drv in selected_drivers}
    if len(dist) < 2 or not selected_drivers:
        return empty, selected_drivers[0] if selected_drivers else None

    ds = dist[1] - dist[0]
    valid = {d: lap_times[d] for d in selected_drivers if lap_times.get(d)}
    ref = (
        min(valid, key=lambda d: valid[d]) if valid else selected_drivers[0]
    )

    def time_arr(spds):
        s_ms = np.array([max(float(v), 1.0) for v in spds]) / 3.6
        return np.cumsum(ds / s_ms)

    ref_t = time_arr(
        drivers_tele.get(ref, {}).get("Speed", [0] * len(dist))
    )
    gaps = {}
    for drv in selected_drivers:
        spd = drivers_tele.get(drv, {}).get("Speed", [0] * len(dist))
        gaps[drv] = (time_arr(spd) - ref_t).tolist()
    return gaps, ref


def _build_track_map(
    drivers_tele: dict, selected_drivers: list, colors: dict
) -> go.Figure:
    """Scatter map colored by which driver is faster at each point."""
    fig = go.Figure()
    ref = selected_drivers[0]
    x_data = drivers_tele.get(ref, {}).get("X", [])
    y_data = drivers_tele.get(ref, {}).get("Y", [])

    has_coords = bool(x_data) and not all(v == 0 for v in x_data[:20])
    if not has_coords:
        fig.add_annotation(
            text="Dados de posição não disponíveis para este evento",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color=_MUTED, size=12),
        )
    else:
        if len(selected_drivers) >= 2:
            drv1, drv2 = selected_drivers[0], selected_drivers[1]
            spd1 = drivers_tele.get(drv1, {}).get("Speed", [])
            spd2 = drivers_tele.get(drv2, {}).get("Speed", [])
            n = min(len(x_data), len(y_data), len(spd1), len(spd2))
            point_colors = [
                colors[drv1] if (spd1[i] or 0) >= (spd2[i] or 0)
                else colors[drv2]
                for i in range(n)
            ]
        else:
            n = min(len(x_data), len(y_data))
            point_colors = [colors[selected_drivers[0]]] * n

        fig.add_trace(go.Scatter(
            x=x_data[:n],
            y=y_data[:n],
            mode="markers",
            marker=dict(color=point_colors, size=4, symbol="circle"),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Start/finish marker at lap origin
        fig.add_trace(go.Scatter(
            x=[x_data[0]],
            y=[y_data[0]],
            mode="markers+text",
            marker=dict(
                symbol="square",
                size=14,
                color="#FFFFFF",
                line=dict(color="#333333", width=2),
            ),
            text=["S/F"],
            textposition="top center",
            textfont=dict(size=9, color=_MUTED),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.update_layout(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        margin=dict(t=8, b=8, l=8, r=8),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        dragmode=False,
        height=220,
    )
    return fig


def _compute_dominance(drivers_tele: dict, selected_drivers: list) -> dict:
    """% of distance points where each driver has the highest speed."""
    if not selected_drivers:
        return {}
    if len(selected_drivers) == 1:
        return {selected_drivers[0]: 100.0}

    speeds, n = {}, None
    for drv in selected_drivers:
        arr = drivers_tele.get(drv, {}).get("Speed", [])
        speeds[drv] = np.array([float(v or 0) for v in arr])
        n = len(arr) if n is None else min(n, len(arr))

    if not n:
        return {d: 0.0 for d in selected_drivers}

    stacked = np.column_stack([speeds[d][:n] for d in selected_drivers])
    fastest_idx = np.argmax(stacked, axis=1)
    return {
        d: float(np.sum(fastest_idx == i)) / n * 100
        for i, d in enumerate(selected_drivers)
    }


def _assign_colors(year, driver_codes: list) -> dict:
    """Assign distinct colors to drivers, resolving team-color clashes."""
    colors = {}
    used = []
    contrast_idx = 0
    for drv in driver_codes:
        c = get_driver_color(year, drv)
        if c in used:
            colors[drv] = _CONTRAST_PALETTE[
                contrast_idx % len(_CONTRAST_PALETTE)
            ]
            contrast_idx += 1
        else:
            colors[drv] = c
            used.append(c)
    return colors


# ── Layout ───────────────────────────────────────────────────────

layout = html.Div([
    html.Div([
        html.H1("Analytics · Telemetria", className="page-title"),
        html.P(
            "Análise comparativa sincronizada por distância (Best Laps).",
            className="page-subtitle",
        ),
    ]),

    create_analytics_subnav("/analytics/telemetria"),

    html.Div(id="tele-warning"),

    # ── Filtros ──────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="tele-season-dropdown",
                options=[],
                placeholder="Ano",
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter", style={"flex": "0 0 100px"}),

        html.Div([
            html.Label("Grande Prêmio"),
            dcc.Dropdown(
                id="tele-race-dropdown",
                options=[],
                placeholder="GP",
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter", style={"flex": "1"}),

        html.Div([
            html.Label("Sessão"),
            dcc.Dropdown(
                id="tele-session-type-dropdown",
                options=[],
                placeholder="Sessão",
                clearable=False,
            ),
        ], className="filter", style={"flex": "0 0 150px"}),

        html.Div([
            html.Label("Pilotos"),
            dcc.Dropdown(
                id="tele-drivers-dropdown",
                options=[],
                placeholder="Selecione os pilotos…",
                multi=True,
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter", style={"flex": "2", "minWidth": "260px"}),

        html.Div([
            html.Button(
                "Analisar",
                id="tele-load-button",
                n_clicks=0,
                className="btn-primary",
            ),
        ], className="filter", style={"alignSelf": "flex-end"}),
    ], className="filters", style={
        "display": "flex", "gap": "1rem", "flexWrap": "wrap",
    }),

    # ── Header estático: 30% pilotos | 70% mapa ─────────────────
    html.Div([
        html.Div(
            html.Div(
                id="tele-header-info",
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "1.2rem",
                    "alignItems": "center",
                    "padding": "1rem",
                },
            ),
            style={
                "width": "30%",
                "height": "236px",
                "overflowY": "auto",
                "borderRight": f"1px solid {_BORDER}",
            },
        ),
        html.Div([
            html.Div(
                id="tele-dominance-row",
                style={
                    "display": "flex",
                    "justifyContent": "center",
                    "gap": "1.5rem",
                    "paddingTop": "6px",
                },
            ),
            html.Div(
                "Velocidade por setor — cor do piloto mais rápido",
                style={
                    "fontSize": "0.75rem",
                    "color": _MUTED,
                    "textAlign": "center",
                },
            ),
            dcc.Graph(
                id="tele-track-map",
                config={"displayModeBar": False, "scrollZoom": False},
                style={"height": "200px"},
            ),
        ], style={"width": "70%"}),
    ], id="tele-header-container", style={
        "display": "none",
        "marginTop": "2rem",
        "marginBottom": "1rem",
        "border": f"1px solid {_BORDER}",
        "borderRadius": "8px",
        "backgroundColor": "#FFFFFF",
    }),

    dcc.Loading(
        id="tele-loading",
        type="default",
        children=html.Div(id="tele-h2h-container"),
    ),

    dcc.Store(id="tele-page-trigger", data={"loaded": True}),
])


# ── Callbacks ────────────────────────────────────────────────────

@dash.callback(
    Output("tele-season-dropdown", "options"),
    Output("tele-season-dropdown", "value"),
    Output("tele-warning", "children"),
    Input("tele-page-trigger", "data"),
)
def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            return [], None, alert_cache_empty()
        return seasons_to_options(seasons), seasons[0], None
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [], None, alert_backend_error()


@dash.callback(
    Output("tele-race-dropdown", "options"),
    Output("tele-race-dropdown", "value"),
    Input("tele-season-dropdown", "value"),
)
def load_races(season):
    if not season:
        return [], None
    try:
        races = client.get_races_for_season(season)
        return [{"label": r, "value": r} for r in races], None
    except Exception:
        return [], None


@dash.callback(
    Output("tele-session-type-dropdown", "options"),
    Output("tele-session-type-dropdown", "value"),
    Input("tele-season-dropdown", "value"),
    Input("tele-race-dropdown", "value"),
)
def load_sessions(season, race):
    if not season or not race:
        return [], None
    try:
        sessions = client.get_sessions_for_event(season, race)
        options = [
            {"label": _SESSION_LABELS.get(s, s), "value": s}
            for s in sessions
        ]
        return options, (sessions[0] if sessions else None)
    except Exception:
        return [], None


@dash.callback(
    Output("tele-drivers-dropdown", "options"),
    Output("tele-drivers-dropdown", "value"),
    Input("tele-season-dropdown", "value"),
    Input("tele-race-dropdown", "value"),
    Input("tele-session-type-dropdown", "value"),
)
def load_drivers(season, race, session_type):
    if not season or not race or not session_type:
        return [], None
    try:
        laps, _, _ = client.load_session(season, race, session_type)
        if not laps.empty:
            codes = sorted(laps["Driver"].unique().tolist())
            return [
                {
                    "label": f"{get_driver_full_name(d)} ({d})",
                    "value": d,
                }
                for d in codes
            ], None
    except Exception:
        pass
    return [], None


@dash.callback(
    Output("tele-h2h-container", "children"),
    Output("tele-header-info", "children"),
    Output("tele-track-map", "figure"),
    Output("tele-header-container", "style"),
    Output("tele-warning", "children", allow_duplicate=True),
    Output("tele-dominance-row", "children"),
    Input("tele-load-button", "n_clicks"),
    State("tele-season-dropdown", "value"),
    State("tele-race-dropdown", "value"),
    State("tele-session-type-dropdown", "value"),
    State("tele-drivers-dropdown", "value"),
    prevent_initial_call=True,
)
def update_telemetry(n_clicks, year, gp, session_type, selected_drivers):
    _hidden = {"display": "none"}
    _visible = {
        "display": "flex",
        "marginTop": "2rem",
        "marginBottom": "1rem",
        "border": f"1px solid {_BORDER}",
        "borderRadius": "8px",
        "backgroundColor": "#FFFFFF",
    }
    if not selected_drivers:
        return html.Div(), [], go.Figure(), _hidden, html.Div(
            "Selecione ao menos 1 piloto para analisar.",
            className="alert alert-warning",
        ), []

    try:
        res = requests.get(
            f"{BACKEND_API_URL}/data/telemetry/head-to-head",
            params={
                "year": year,
                "gp": gp,
                "session_type": session_type,
                "drivers": ",".join(selected_drivers),
            },
            timeout=60,
        )
        res.raise_for_status()
        data = res.json()

        tele = data["telemetry"]
        dist = tele["distance"]
        drivers_tele = tele["drivers"]
        meta = data["metadata"]
        corners = data.get("corners", [])
        lap_times = meta["lap_times"]

        colors = _assign_colors(year, selected_drivers)

        _chart_cfg = {"displayModeBar": False, "scrollZoom": False, "staticPlot": True}
        _legend_style = dict(
            orientation="h",
            yanchor="top", y=-0.08,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_TEXT, size=12),
        )
        _xaxis_base = dict(
            showgrid=False, zeroline=False,
            linecolor=_BORDER, tickfont=dict(color=_MUTED),
        )
        _yaxis_base = dict(
            showgrid=False, zeroline=False,
            linecolor=_BORDER,
            tickfont=dict(color=_MUTED, size=12),
            title_font=dict(color=_TEXT, size=13),
        )
        _title_style = {
            "fontSize": "0.95rem",
            "fontWeight": "700",
            "color": _TEXT,
            "textAlign": "center",
            "marginBottom": "0.25rem",
        }

        channels = [
            ("Speed",    "Velocity (km/h)", "km/h"),
            ("RPM",      "RPM",             "RPM"),
            ("Throttle", "Throttle (%)",    "%"),
            ("DRS",      "DRS Status",      "Status"),
            ("nGear",    "Gears (nGear)",   "Gear"),
        ]

        graphs = []
        for ch_idx, (col, title, y_label) in enumerate(channels):
            ch_fig = go.Figure()
            for drv_idx, drv in enumerate(selected_drivers):
                drv_tele = drivers_tele.get(drv, {})
                color = colors[drv]
                line_style = _LINE_STYLES[drv_idx % len(_LINE_STYLES)]
                full_name = get_driver_full_name(drv)
                ch_fig.add_trace(go.Scatter(
                    x=dist, y=drv_tele.get(col, []),
                    name=f"{full_name} ({drv})",
                    line=dict(color=color, width=2, dash=line_style),
                    hovertemplate="%{y:.1f}",
                ))
            for corner in corners:
                ch_fig.add_vline(
                    x=corner["Distance"],
                    line=dict(color=_BORDER, width=1, dash="dot"),
                )
                if ch_idx == 0:
                    ch_fig.add_annotation(
                        x=corner["Distance"], y=0.98, yref="paper",
                        text=f"C{corner['Number']}", showarrow=False,
                        font=dict(color=_MUTED, size=9), yanchor="top",
                    )
            ch_fig.update_layout(
                paper_bgcolor=_BG, plot_bgcolor=_BG,
                showlegend=True,
                font=dict(
                    color=_TEXT,
                    family="Inter, Arial, sans-serif",
                    size=12,
                ),
                height=300,
                margin=dict(t=10, b=70, l=80, r=40),
                hovermode="x unified",
                legend=_legend_style,
                xaxis=dict(**_xaxis_base, showticklabels=False),
                yaxis=dict(**_yaxis_base, title_text=f"<b>{y_label}</b>"),
            )
            graphs.append(html.Div([
                html.Div(title, style=_title_style),
                dcc.Graph(figure=ch_fig, config=_chart_cfg),
            ], style={"marginBottom": "2rem"}))

        # ── GAP chart ──────────────────────────────────────────────
        gaps, ref_drv = _compute_gap_all(
            dist, drivers_tele, selected_drivers, lap_times
        )
        ref_name = get_driver_full_name(ref_drv)
        gap_fig = go.Figure()
        for drv_idx, drv in enumerate(selected_drivers):
            gap = gaps[drv]
            color = colors[drv]
            line_style = _LINE_STYLES[drv_idx % len(_LINE_STYLES)]
            full_name = get_driver_full_name(drv)
            if drv == ref_drv:
                gap_fig.add_trace(go.Scatter(
                    x=dist, y=gap,
                    name=f"{full_name} ({drv})",
                    line=dict(color=color, width=1.5, dash="dot"),
                    hovertemplate=f"{drv}: 0.000s",
                ))
            else:
                gap_fig.add_trace(go.Scatter(
                    x=dist, y=gap,
                    fill="tozeroy",
                    fillcolor=_hex_to_rgba(color, 0.2),
                    name=f"{full_name} ({drv})",
                    line=dict(color=color, width=1.5, dash=line_style),
                    hovertemplate=f"{drv}: +%{{y:.3f}}s",
                ))
        gap_fig.add_hline(y=0, line=dict(color=_BORDER, width=1))
        for corner in corners:
            gap_fig.add_vline(
                x=corner["Distance"],
                line=dict(color=_BORDER, width=1, dash="dot"),
            )
        gap_fig.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            showlegend=True,
            font=dict(
                color=_TEXT,
                family="Inter, Arial, sans-serif",
                size=12,
            ),
            height=300,
            margin=dict(t=10, b=100, l=80, r=40),
            hovermode="x unified",
            legend=_legend_style,
            xaxis=dict(**_xaxis_base, title_text="Distância (m)"),
            yaxis=dict(**_yaxis_base, title_text="<b>s</b>"),
        )
        gap_title = f"GAP vs {ref_name} ({ref_drv}) (s)"
        graphs.append(html.Div([
            html.Div(gap_title, style=_title_style),
            dcc.Graph(figure=gap_fig, config=_chart_cfg),
        ]))

        charts_div = html.Div(graphs, style={"marginTop": "1.5rem"})

        track_map_fig = _build_track_map(
            drivers_tele, selected_drivers, colors
        )

        dominance = _compute_dominance(drivers_tele, selected_drivers)

        # Esquerda: cards originais (piloto + tempo)
        pilot_cards = [
            html.Div([
                html.Div(
                    f"{get_driver_full_name(drv)} ({drv})",
                    style={"fontSize": "0.85rem", "color": _MUTED},
                ),
                html.Div(
                    _fmt_laptime_full(lap_times.get(drv)),
                    style={
                        "color": colors[drv],
                        "fontWeight": "bold",
                        "fontSize": "1.3rem",
                    },
                ),
            ], style={"textAlign": "center"})
            for drv in selected_drivers
        ]

        # Direita: big numbers de dominância acima do mapa
        dominance_items = [
            html.Div([
                html.Div(
                    f"{dominance.get(drv, 0):.1f}%",
                    style={
                        "color": colors[drv],
                        "fontWeight": "700",
                        "fontSize": "1.4rem",
                        "lineHeight": "1",
                    },
                ),
                html.Div(
                    drv,
                    style={"fontSize": "0.65rem", "color": _MUTED},
                ),
            ], style={"textAlign": "center"})
            for drv in selected_drivers
        ]

        return charts_div, pilot_cards, track_map_fig, _visible, None, dominance_items

    except Exception as e:
        return html.Div(), [], go.Figure(), _hidden, html.Div(
            f"Erro na análise de telemetria: {e}",
            className="alert alert-error",
        ), []
