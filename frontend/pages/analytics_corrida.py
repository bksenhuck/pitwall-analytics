"""Analytics › Corrida — tempos de volta, posições e telemetria."""
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import io

from frontend.components.charts import (
    lap_time_chart,
    position_chart,
    speed_telemetry_chart,
)
from frontend.components.navigation import create_analytics_subnav
from frontend.api import client

dash.register_page(__name__, path="/analytics/corrida", name="Corrida")

layout = html.Div([
    html.Div([
        html.H1("Analytics · Corrida", className="page-title"),
        html.P("Tempos de volta, posições e desempenho por piloto.", className="page-subtitle"),
    ]),

    create_analytics_subnav("/analytics/corrida"),

    html.Div(id="corrida-cache-warning"),

    # ── Filtros ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(id="corrida-season-dropdown", options=[], placeholder="Selecione a temporada"),
        ], className="filter"),

        html.Div([
            html.Label("Corrida"),
            dcc.Dropdown(id="corrida-race-dropdown", options=[], placeholder="Selecione a corrida"),
        ], className="filter"),

        html.Div([
            html.Label("Piloto"),
            dcc.Dropdown(id="corrida-driver-dropdown", options=[], placeholder="Todos os pilotos"),
        ], className="filter"),

        html.Div([
            html.Button("Carregar corrida", id="corrida-load-button", n_clicks=0, className="btn-primary"),
        ], className="filter"),
    ], className="filters"),

    dcc.Store(id="corrida-laps-store", storage_type="session"),
    dcc.Store(id="corrida-session-store", storage_type="session"),
    dcc.Store(id="corrida-page-trigger", data={"loaded": True}),

    html.Div(id="corrida-kpi-row", className="kpi-row"),

    html.Div([
        dcc.Graph(id="corrida-lap-time-graph"),
        dcc.Graph(id="corrida-position-graph"),
        dcc.Graph(id="corrida-speed-telemetry-graph"),
    ], className="charts"),
])


# ── Callbacks ───────────────────────────────────────────────────

@dash.callback(
    Output("corrida-season-dropdown", "options"),
    Output("corrida-season-dropdown", "value"),
    Output("corrida-cache-warning", "children"),
    Input("corrida-page-trigger", "data"),
)
def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            warning = html.Div([
                html.Span("⚠", className="alert-icon"),
                html.Div([
                    html.Strong("Nenhum dado no cache SQLite."),
                    html.P(["Execute: ", html.Code("python scripts/populate_cache.py --season 2024")],
                           style={"margin": ".4rem 0 0"}),
                ]),
            ], className="alert alert-warning")
            return [], None, warning
        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None, None
    except Exception as e:
        print(f"Error loading seasons: {e}")
        error = html.Div([
            html.Span("✕", className="alert-icon"),
            html.Div([
                html.Strong("Não foi possível conectar ao backend."),
                html.P(["Certifique-se de que o servidor está rodando: ", html.Code("python main.py")],
                       style={"margin": ".4rem 0 0"}),
            ]),
        ], className="alert alert-error")
        return [], None, error


@dash.callback(
    Output("corrida-race-dropdown", "options"),
    Input("corrida-season-dropdown", "value"),
)
def update_races(season):
    if not season:
        return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("corrida-laps-store", "data"),
    Output("corrida-session-store", "data"),
    Input("corrida-load-button", "n_clicks"),
    State("corrida-season-dropdown", "value"),
    State("corrida-race-dropdown", "value"),
    prevent_initial_call=True,
)
def handle_load(n_clicks, season, race):
    if not n_clicks or not season or not race:
        return dash.no_update, dash.no_update
    laps, _, session = client.load_race_session(season, race)
    if laps.empty:
        return None, None
    return laps.to_json(date_format="iso", orient="split"), {
        "season": season,
        "race": race,
        "drivers": session.get("drivers", []),
    }


@dash.callback(
    Output("corrida-driver-dropdown", "options"),
    Input("corrida-laps-store", "data"),
)
def update_drivers(laps_json):
    if not laps_json:
        return []
    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        drivers = sorted(laps["Driver"].unique().tolist()) if "Driver" in laps.columns else []
        return [{"label": d, "value": d} for d in drivers]
    except Exception:
        return []


@dash.callback(
    Output("corrida-kpi-row", "children"),
    Input("corrida-laps-store", "data"),
    State("corrida-session-store", "data"),
)
def update_kpis(laps_json, session_meta):
    if not laps_json:
        return []
    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        total_laps = int(laps["LapNumber"].max()) if "LapNumber" in laps.columns else "—"
        total_drivers = len(laps["Driver"].unique()) if "Driver" in laps.columns else "—"
        best_lap = "—"
        if "LapTimeSeconds" in laps.columns:
            val = laps["LapTimeSeconds"].min()
            m, s = divmod(val, 60)
            best_lap = f"{int(m)}:{s:05.2f}"
        race_label = session_meta.get("race", "—") if session_meta else "—"

        def kpi(label, value):
            return html.Div([
                html.Div(label, className="kpi-label"),
                html.Div(str(value), className="kpi-value"),
            ], className="kpi")

        return [
            kpi("Corrida", race_label),
            kpi("Total de Voltas", total_laps),
            kpi("Pilotos", total_drivers),
            kpi("Melhor Volta", best_lap),
        ]
    except Exception:
        return []


@dash.callback(
    Output("corrida-lap-time-graph", "figure"),
    Output("corrida-position-graph", "figure"),
    Output("corrida-speed-telemetry-graph", "figure"),
    Input("corrida-driver-dropdown", "value"),
    State("corrida-laps-store", "data"),
)
def update_charts(driver, laps_json):
    empty_fig = {"data": [], "layout": {"template": "plotly_white", "title": "Nenhum dado carregado"}}
    if not laps_json:
        return empty_fig, empty_fig, empty_fig
    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        return lap_time_chart(laps, driver), position_chart(laps, driver), speed_telemetry_chart(pd.DataFrame())
    except Exception as e:
        print(f"Error updating charts: {e}")
        return empty_fig, empty_fig, empty_fig
