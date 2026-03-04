import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import requests

from frontend.components.navigation import create_analytics_subnav
from frontend.components.charts import _base_layout
from frontend.api import client
from frontend.f1_config import get_driver_color, get_driver_full_name
from frontend.config import BACKEND_API_URL

# Tema Pitwall (espelha frontend/components/charts.py)
_BG     = "#F4F5F7"
_BORDER = "#DDE1E7"
_TEXT   = "#1A1A1A"
_MUTED  = "#6B7280"

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
            html.Div(id="tele-header-info", style={"marginTop": "2rem", "textAlign": "center"}),
            dcc.Graph(
                id="tele-h2h-graph",
                style={"height": "1400px", "width": "100%"},
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
        return go.Figure(), "", html.Div(
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
            rows=5, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(
                "<b>Velocity</b> (km/h)",
                "<b>RPM</b>",
                "<b>Throttle</b> (%)",
                "<b>DRS Status</b>",
                "<b>Gears</b> (nGear)",
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

        for _, subplot_row, y_label in plot_configs:
            fig.update_yaxes(
                title_text=y_label, title_font=dict(color=_MUTED, size=11),
                row=subplot_row, col=1,
                showgrid=False, zeroline=False,
                linecolor=_BORDER,
                tickfont=dict(color=_MUTED, size=11),
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

        drivers_label = " vs ".join(selected_drivers)
        fig.update_layout(
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            font=dict(color=_TEXT, family="Inter, Arial, sans-serif", size=12),
            title=dict(
                text=(
                    f"<b>Telemetria F1</b>  "
                    f"<span style='font-size:13px; color:{_MUTED}'>"
                    f"{meta['event']} · {meta['session']} · {drivers_label}</span>"
                ),
                x=0, xanchor="left",
                font=dict(color="#003082", size=14),
            ),
            height=1400,
            margin=dict(t=100, b=60, l=80, r=40),
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.015, xanchor="right", x=1,
                bgcolor="rgba(0,0,0,0)", font=dict(color=_TEXT),
            ),
        )
        fig.update_xaxes(
            title_text="Distância (m)", row=5, col=1,
            showgrid=False, zeroline=False, linecolor=_BORDER,
            tickfont=dict(color=_MUTED),
        )

        # Header com tempos de volta de cada piloto
        info = html.Div([
            html.Div(
                [
                    html.Span(
                        f"{get_driver_full_name(drv)} ({drv}): {lap_times.get(drv, '—')}",
                        style={"color": colors[drv], "fontWeight": "bold", "fontSize": "1.2rem"},
                    )
                    for drv in selected_drivers
                ],
                style={
                    "display": "inline-flex", "gap": "2rem", "flexWrap": "wrap",
                    "justifyContent": "center",
                    "padding": "1rem",
                    "backgroundColor": _BG,
                    "border": f"1px solid {_BORDER}",
                    "borderRadius": "8px",
                }
            )
        ])

        return fig, info, None

    except Exception as e:
        return go.Figure(), "", html.Div(
            f"Erro na análise de telemetria: {str(e)}",
            className="alert alert-error"
        )
