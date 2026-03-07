import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import requests
import numpy as np

from frontend.components.navigation import create_analytics_subnav
from frontend.components.charts import _base_layout, _fmt_laptime_full
from frontend.api import client
from frontend.f1_config import get_driver_color, get_driver_full_name
from frontend.config import BACKEND_API_URL

# Tema Pitwall (espelha frontend/components/charts.py)
_BG      = "#F4F5F7"
_BORDER  = "#DDE1E7"
_TEXT    = "#1A1A1A"
_MUTED   = "#6B7280"
_PRIMARY = "#003082"  # F1 blue

dash.register_page(__name__, path="/analytics/telemetria", name="Telemetria")

_SESSION_OPTIONS = [
    {"label": "Qualificação (Q)",       "value": "Q"},
    {"label": "Q1",                     "value": "Q1"},
    {"label": "Q2",                     "value": "Q2"},
    {"label": "Q3",                     "value": "Q3"},
    {"label": "Corrida (R)",            "value": "R"},
    {"label": "Treino Livre 1 (FP1)",   "value": "FP1"},
    {"label": "Treino Livre 2 (FP2)",   "value": "FP2"},
    {"label": "Treino Livre 3 (FP3)",   "value": "FP3"},
    {"label": "Sprint (S)",             "value": "S"},
]

# Palette de contraste para pilotos do mesmo time
_CONTRAST_PALETTE = ["#FFFFFF", "#FFD700", "#FF6B6B", "#4ECDC4", "#A29BFE", "#FD79A8"]
_LINE_STYLES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]


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
                options=_SESSION_OPTIONS,
                value="Q",
                clearable=False,
                persistence=True,
                persistence_type="session",
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

    dcc.Loading(
        id="tele-loading",
        type="default",
        children=html.Div([
            # Header 30 / 70 split
            html.Div([
                # Parte A (30%) - Info do Piloto
                html.Div(id="tele-header-info", style={
                    "flex": "0 0 30%", 
                    "padding": "1rem", 
                    "borderRight": f"1px solid {_BORDER}",
                    "backgroundColor": "white",
                    "borderRadius": "8px 0 0 8px",
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "center"
                }),
                # Parte B (70%) - Mapa da Pista
                html.Div(id="tele-header-map", style={
                    "flex": "1", 
                    "padding": "0.5rem",
                    "backgroundColor": "white",
                    "borderRadius": "0 8px 8px 0"
                }, children=[
                    dcc.Graph(id="tele-track-map", style={"height": "350px"}, config={"displayModeBar": False})
                ]),
            ], style={
                "display": "flex", 
                "marginTop": "2rem", 
                "minHeight": "350px",
                "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
                "borderRadius": "8px"
            }),
            
            dcc.Graph(
                id="tele-h2h-graph",
                style={"height": "1600px", "width": "100%"},
                config={"displayModeBar": True, "responsive": True, "scrollZoom": True}
            ),
        ])
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


@dash.callback(
    Output("tele-race-dropdown", "options"),
    Input("tele-season-dropdown", "value"),
)
def load_races(season):
    if not season: return []
    try:
        races = client.get_races_for_season(season)
        return [{"label": r, "value": r} for r in races]
    except: return []


@dash.callback(
    Output("tele-drivers-dropdown", "options"),
    Input("tele-season-dropdown", "value"),
    Input("tele-race-dropdown", "value"),
    Input("tele-session-type-dropdown", "value"),
)
def load_drivers(season, race, session_type):
    if not season or not race: return []
    try:
        laps, _, _ = client.load_session(season, race, session_type or "Q")
        if not laps.empty:
            codes = sorted(laps["Driver"].unique().tolist())
            return [
                {"label": f"{get_driver_full_name(d)} ({d})", "value": d}
                for d in codes
            ]
    except: pass
    return []


@dash.callback(
    Output("tele-h2h-graph", "figure"),
    Output("tele-header-info", "children"),
    Output("tele-track-map", "figure"),
    Output("tele-warning", "children"),
    Input("tele-load-button", "n_clicks"),
    State("tele-season-dropdown", "value"),
    State("tele-race-dropdown", "value"),
    State("tele-session-type-dropdown", "value"),
    State("tele-drivers-dropdown", "value"),
    prevent_initial_call=True
)
def update_telemetry(n_clicks, year, gp, session_type, selected_drivers):
    if not selected_drivers:
        return go.Figure(), "", go.Figure(), html.Div(
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
        lap_times = meta["lap_times"]

        colors = _assign_colors(year, selected_drivers)

        # ── 1. Create Telemetry Subplots ───────────────────
        fig = make_subplots(
            rows=5, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(
                "<b>Velocity</b> (km/h) & <b>Delta</b> (s)",
                "<b>RPM</b>",
                "<b>Throttle</b> (%)",
                "<b>DRS Status</b>",
                "<b>Gears</b> (nGear)",
            )
        )

        plot_configs = [
            ("Speed",    1, "Speed"),
            ("Delta",    1, "Delta (s)"),
            ("RPM",      2, "RPM"),
            ("Throttle", 3, "%"),
            ("DRS",      4, "Status"),
            ("nGear",    5, "Gear"),
        ]

        for drv_idx, drv in enumerate(selected_drivers)z
            col = colors[drv]
            name = f"{drv} ({_fmt_laptime_full(lap_times[drv])})"
            
            for field, row, y_title in plot_configs:
                if field in drivers_tele[drv]:
                    is_delta = (field == "Delta")
                    
                    if is_delta:
                        fig.add_trace(go.Scatter(
                            x=dist,
                            y=drivers_tele[drv][field],
                            name=f"Rey{name} (Delta)",
                            legendgroup=drv,
                            line=dict(color=col, width=1.5),
                            showlegend=False,
                            yaxis="y6",
                        ), row=1, col=1)
                    else:
                        fig.add_trace(go.Scatter(
                            x=dist,
                            y=drivers_tele[drv][field],
                            name=name,
                            legendgroup=drv,
                            line=dict(color=col, width=2),
                            showlegend=(row == 1)
                        ), row=row, col=1)

        # Configurar o eixo Y secundário para o Delta
            yaxis6=dict(
                title="Delta (s)",
                anchor="x",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=True,
                zerolinecolor="rgba(0,0,0,0.2)",
                tickfont=dict(color=_MUTED)
            )
        )

        # Custom layout for telemetry (overriding base legend)
        tele_layout = _base_layout(f"Comparativo: {gp} {year} ({session_type})")
        tele_layout["height"] = 1400
        tele_layout["legend"] = dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_TEXT)
        )
        
        fig.update_layout(**tele_layout)
        
        # ── 2. Create Info Items (Vertical) ───────────────
        info_items = [
            html.H3("Resumo da Volta", style={"color": _PRIMARY, "marginBottom": "1rem"}),
        ]
        for drv in selected_drivers:
            info_items.append(html.Div([
                html.Div(style={
                    "width": "12px", "height": "12px", 
                    "backgroundColor": colors[drv], 
                    "borderRadius": "50%", "display": "inline-block",
                    "marginRight": "8px"
                }),
                html.Span(f"<b>{drv}</b>: {_fmt_laptime_full(lap_times[drv])}", style={"fontSize": "1.1rem"}),
            ], style={"padding": "0.5rem 0", "borderBottom": f"1px solid {_BORDER}"}))

        # ── 3. Create Track Map showing fastest points ───
        map_fig = go.Figure()
        
        # Draw track line (reference x/y)
        ref_x = np.array(drivers_tele[selected_drivers[0]]['x'])
        ref_y = np.array(drivers_tele[selected_drivers[0]]['y'])
        
        # Calculate dominant driver at each segment
        speeds = np.array([drivers_tele[d]['Speed'] for d in selected_drivers])
        fastest_indices = np.argmax(speeds, axis=0)
        
        # Draw track segments with colors of the fastest driver
        for i, drv in enumerate(selected_drivers):
            mask = (fastest_indices == i)
            if np.any(mask):
                # We need to draw segments. For simplicity, scattered markers or small line segments
                # Since we have 1000 points, scatter is okay
                map_fig.add_trace(go.Scatter(
                    x=ref_x[mask],
                    y=ref_y[mask],
                    mode='markers',
                    marker=dict(size=4, color=colors[drv]),
                    name=f"Fastest: {drv}",
                    showlegend=False
                ))
        
        map_fig.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
            hovermode=False
        )

        return fig, info_items, map_fig, ""

    except Exception as e:
        import traceback
        traceback.print_exc()
        return go.Figure(), "", go.Figure(), html.Div(
            f"Erro ao carregar telemetria: {str(e)}",
            className="alert alert-danger"
        )
