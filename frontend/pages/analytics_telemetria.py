import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import numpy as np
import requests

from frontend.components.navigation import create_analytics_subnav
from frontend.components.charts import _fmt_laptime_full
from frontend.api import client
from frontend.f1_config import get_driver_color, get_driver_full_name
from frontend.config import BACKEND_API_URL

# Tema Pitwall (espelha frontend/components/charts.py)
_BG     = "#F4F5F7"
_BORDER = "#DDE1E7"
_TEXT   = "#1A1A1A"
_MUTED  = "#6B7280"

dash.register_page(__name__, path="/analytics/telemetria", name="Telemetria")

# Palette de contraste para pilotos do mesmo time
_CONTRAST_PALETTE = ["#FFFFFF", "#FFD700", "#FF6B6B", "#4ECDC4", "#A29BFE", "#FD79A8"]
_LINE_STYLES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


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
    ref = min(valid, key=lambda d: valid[d]) if valid else selected_drivers[0]

    def time_arr(spds):
        s_ms = np.array([max(float(v), 1.0) for v in spds]) / 3.6
        return np.cumsum(ds / s_ms)

    ref_t = time_arr(drivers_tele.get(ref, {}).get('Speed', [0] * len(dist)))
    gaps = {}
    for drv in selected_drivers:
        spd = drivers_tele.get(drv, {}).get('Speed', [0] * len(dist))
        gaps[drv] = (time_arr(spd) - ref_t).tolist()
    return gaps, ref


def _build_track_map(drivers_tele: dict, selected_drivers: list, colors: dict) -> go.Figure:
    """Scatter map colored by which driver is faster at each point."""
    fig = go.Figure()
    ref = selected_drivers[0]
    x_data = drivers_tele.get(ref, {}).get('X', [])
    y_data = drivers_tele.get(ref, {}).get('Y', [])

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
            spd1 = drivers_tele.get(drv1, {}).get('Speed', [])
            spd2 = drivers_tele.get(drv2, {}).get('Speed', [])
            n = min(len(x_data), len(y_data), len(spd1), len(spd2))
            point_colors = [
                colors[drv1] if (spd1[i] or 0) >= (spd2[i] or 0) else colors[drv2]
                for i in range(n)
            ]
        else:
            n = min(len(x_data), len(y_data))
            point_colors = [colors[selected_drivers[0]]] * n

        fig.add_trace(go.Scatter(
            x=x_data[:n],
            y=y_data[:n],
            mode='markers',
            marker=dict(color=point_colors, size=4, symbol='circle'),
            showlegend=False,
            hoverinfo='skip',
        ))

    fig.update_layout(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        margin=dict(t=8, b=8, l=8, r=8),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor='x', scaleratio=1),
        height=220,
    )
    return fig


def _assign_colors(year, driver_codes: list) -> dict:
    """Assign distinct colors to drivers, resolving team-color clashes."""
    colors = {}
    used = []
    contrast_idx = 0
    for drv in driver_codes:
        c = get_driver_color(year, drv)
        if c in used:
            # Fallback to contrast palette
            colors[drv] = _CONTRAST_PALETTE[contrast_idx % len(_CONTRAST_PALETTE)]
            contrast_idx += 1
        else:
            colors[drv] = c
            used.append(c)
    return colors


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

    # ── Filtros ─────────────────────────────────────────────────
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
    ], className="filters", style={"display": "flex", "gap": "1rem", "flexWrap": "wrap"}),

    # ── Header estático: 30% pilotos | 70% mapa ─────────────────
    html.Div([
        # A – 30%: tempos de volta (scroll interno)
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
                "borderRight": "1px solid #DDE1E7",
            },
        ),
        # B – 70%: mapa da pista
        html.Div([
            html.Div(
                "Velocidade por setor — cor do piloto mais rápido",
                style={
                    "fontSize": "0.75rem",
                    "color": "#6B7280",
                    "textAlign": "center",
                    "paddingTop": "6px",
                },
            ),
            dcc.Graph(
                id="tele-track-map",
                config={"displayModeBar": False},
                style={"height": "220px"},
            ),
        ], style={"width": "70%"}),
    ], id="tele-header-container", style={
        "display": "none",
        "marginTop": "2rem",
        "marginBottom": "1rem",
        "border": "1px solid #DDE1E7",
        "borderRadius": "8px",
        "backgroundColor": "#FFFFFF",
    }),

    dcc.Loading(
        id="tele-loading",
        type="default",
        children=dcc.Graph(
            id="tele-h2h-graph",
            style={"height": "1600px", "width": "100%"},
            config={
                "displayModeBar": True,
                "responsive": True,
                "scrollZoom": False,
                "modeBarButtonsToRemove": [
                    "zoom2d", "zoomIn2d", "zoomOut2d",
                    "autoScale2d", "resetScale2d",
                ],
            }
        ),
    ),

    dcc.Store(id="tele-page-trigger", data={"loaded": True}),
])

# ── Callbacks ───────────────────────────────────────────────────

@dash.callback(
    Output("tele-season-dropdown", "options"),
    Output("tele-season-dropdown", "value"),
    Input("tele-page-trigger", "data"),
)
def load_seasons(_):
    seasons = [2026, 2025, 2024]
    try:
        remote = client.get_available_seasons()
        if remote: seasons = remote
    except: pass
    return [{"label": str(s), "value": s} for s in seasons], seasons[0]


_SESSION_LABELS = {
    "FP1": "Treino Livre 1 (FP1)",
    "FP2": "Treino Livre 2 (FP2)",
    "FP3": "Treino Livre 3 (FP3)",
    "Q":   "Qualificação (Q)",
    "Q1":  "Q1",
    "Q2":  "Q2",
    "Q3":  "Q3",
    "SQ":  "Sprint Quali (SQ)",
    "S":   "Sprint (S)",
    "R":   "Corrida (R)",
}


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
        default = sessions[0] if sessions else None
        return options, default
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
                {"label": f"{get_driver_full_name(d)} ({d})", "value": d}
                for d in codes
            ], None
    except Exception:
        pass
    return [], None


@dash.callback(
    Output("tele-h2h-graph", "figure"),
    Output("tele-header-info", "children"),
    Output("tele-track-map", "figure"),
    Output("tele-header-container", "style"),
    Output("tele-warning", "children"),
    Input("tele-load-button", "n_clicks"),
    State("tele-season-dropdown", "value"),
    State("tele-race-dropdown", "value"),
    State("tele-session-type-dropdown", "value"),
    State("tele-drivers-dropdown", "value"),
    prevent_initial_call=True
)
def update_telemetry(n_clicks, year, gp, session_type, selected_drivers):
    _hidden = {"display": "none"}
    _visible = {
        "display": "flex",
        "marginTop": "2rem",
        "marginBottom": "1rem",
        "border": "1px solid #DDE1E7",
        "borderRadius": "8px",
        "backgroundColor": "#FFFFFF",
    }
    if not selected_drivers:
        return go.Figure(), [], go.Figure(), _hidden, html.Div(
            "Selecione ao menos 1 piloto para analisar.",
            className="alert alert-warning"
        )

    try:
        url = f"{BACKEND_API_URL}/data/telemetry/head-to-head"
        params = {
            "year": year,
            "gp": gp,
            "session_type": session_type,
            "drivers": ",".join(selected_drivers),
        }
        res = requests.get(url, params=params, timeout=60)
        res.raise_for_status()
        data = res.json()

        tele = data["telemetry"]
        dist = tele["distance"]
        drivers_tele = tele["drivers"]
        meta = data["metadata"]
        corners = data.get("corners", [])
        lap_times = meta["lap_times"]

        colors = _assign_colors(year, selected_drivers)

        fig = make_subplots(
            rows=6, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.025,
            row_heights=[1.2, 1.0, 0.8, 0.5, 0.8, 0.7],
            subplot_titles=(
                "<b>Velocity</b> (km/h)",
                "<b>RPM</b>",
                "<b>Throttle</b> (%)",
                "<b>DRS Status</b>",
                "<b>Gears</b> (nGear)",
                "<b>GAP</b> (s)",
            )
        )

        plot_configs = [
            ("Speed",    1, "Speed"),
            ("RPM",      2, "RPM"),
            ("Throttle", 3, "%"),
            ("DRS",      4, "Status"),
            ("nGear",    5, "Gear"),
        ]

        for drv_idx, drv in enumerate(selected_drivers):
            drv_tele = drivers_tele.get(drv, {})
            color = colors[drv]
            line_style = _LINE_STYLES[drv_idx % len(_LINE_STYLES)]
            full_name = get_driver_full_name(drv)

            for col, row_idx, _ in plot_configs:
                fig.add_trace(go.Scatter(
                    x=dist,
                    y=drv_tele.get(col, []),
                    name=f"{full_name} ({drv})",
                    line=dict(color=color, width=2, dash=line_style),
                    legendgroup=drv,
                    showlegend=(row_idx == 1),
                    hovertemplate="%{y:.1f}",
                ), row=row_idx, col=1)

        # ── GAP trace (row 6) — ref = piloto mais rápido ─────────
        gaps, ref_drv = _compute_gap_all(
            dist, drivers_tele, selected_drivers, lap_times
        )
        for drv in selected_drivers:
            gap = gaps[drv]
            color = colors[drv]
            if drv == ref_drv:
                # Referência: linha plana em 0
                fig.add_trace(go.Scatter(
                    x=dist, y=gap,
                    line=dict(color=color, width=1.5, dash='dot'),
                    showlegend=False,
                    hovertemplate=f"{drv}: 0.000s",
                    name=drv,
                ), row=6, col=1)
            else:
                fig.add_trace(go.Scatter(
                    x=dist, y=gap,
                    fill='tozeroy',
                    fillcolor=_hex_to_rgba(color, 0.2),
                    line=dict(color=color, width=1.5),
                    showlegend=False,
                    hovertemplate=f"{drv}: +%{{y:.3f}}s",
                    name=drv,
                ), row=6, col=1)
        fig.add_hline(y=0, line=dict(color=_BORDER, width=1), row=6, col=1)

        # Atualiza título do GAP com o piloto de referência
        ref_name = get_driver_full_name(ref_drv)
        fig.layout.annotations[5].update(
            text=f"<b>GAP</b> vs {ref_name} ({ref_drv}) (s)"
        )

        fig.update_yaxes(
            title_text="<b>s</b>",
            title_font=dict(color=_TEXT, size=14),
            row=6, col=1,
            showgrid=False, zeroline=False,
            linecolor=_BORDER,
            tickfont=dict(color=_MUTED, size=12),
        )
        for _, subplot_row, y_label in plot_configs:
            fig.update_yaxes(
                title_text=f"<b>{y_label}</b>",
                title_font=dict(color=_TEXT, size=14),
                row=subplot_row, col=1,
                showgrid=False, zeroline=False,
                linecolor=_BORDER,
                tickfont=dict(color=_MUTED, size=12),
            )
            for corner in corners:
                fig.add_vline(
                    x=corner["Distance"],
                    line=dict(color=_BORDER, width=1, dash="dot"),
                    row=subplot_row, col=1,
                )
                if subplot_row == 1:
                    fig.add_annotation(
                        x=corner["Distance"], y=1.1, yref="paper",
                        text=f"C{corner['Number']}", showarrow=False,
                        font=dict(color=_MUTED, size=9),
                        row=1, col=1,
                    )

        fig.update_layout(
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            font=dict(color=_TEXT, family="Inter, Arial, sans-serif", size=12),
            title=dict(text=""), # Removido título nativo (linha de texto)
            height=1600,
            # Margem superior aumentada para dar mais espaço à legenda
            margin=dict(t=150, b=60, l=80, r=40),
            hovermode="x unified",
            # Legenda centralizada e mais distante do gráfico (y subiu)
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color=_TEXT),
            ),
        )
        fig.update_xaxes(
            title_text="Distância (m)", row=6, col=1,
            showgrid=False, zeroline=False, linecolor=_BORDER,
            tickfont=dict(color=_MUTED),
        )

        # ── Track map ────────────────────────────────────────────
        track_map_fig = _build_track_map(drivers_tele, selected_drivers, colors)

        # ── Pilot cards ──────────────────────────────────────────
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

        return fig, pilot_cards, track_map_fig, _visible, None

    except Exception as e:
        return go.Figure(), [], go.Figure(), _hidden, html.Div(
            f"Erro na análise de telemetria: {str(e)}",
            className="alert alert-error"
        )
