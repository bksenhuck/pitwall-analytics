"""Analytics page - Main F1 data analysis interface"""
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import io

from frontend.components.charts import (
    lap_time_chart,
    position_chart,
    speed_telemetry_chart,
)
from frontend.api import client

dash.register_page(__name__, path="/analytics", name="Analytics")


layout = html.Div([
    html.Div([
        html.H1("Analytics", className="page-title"),
        html.P(
            "Tempos de volta, posições e desempenho por piloto.",
            className="page-subtitle",
        ),
    ]),

    # Warning / status messages
    html.Div(id="cache-warning"),

    # ── Filters ────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="season-dropdown",
                options=[],
                placeholder="Selecione a temporada",
            ),
        ], className="filter"),

        html.Div([
            html.Label("Corrida"),
            dcc.Dropdown(
                id="race-dropdown",
                options=[],
                placeholder="Selecione a corrida",
            ),
        ], className="filter"),

        html.Div([
            html.Label("Piloto"),
            dcc.Dropdown(
                id="driver-dropdown",
                options=[],
                placeholder="Todos os pilotos",
            ),
        ], className="filter"),

        html.Div([
            html.Button(
                "Carregar corrida",
                id="load-button",
                n_clicks=0,
                className="btn-primary",
            ),
        ], className="filter"),
    ], className="filters"),

    # Stores
    dcc.Store(id="laps-store", storage_type="session"),
    dcc.Store(id="session-store", storage_type="session"),
    dcc.Store(id="page-load-trigger", data={"loaded": True}),

    # ── KPI row (populated after load) ─────────────────────────
    html.Div(id="kpi-row", className="kpi-row"),

    # ── Charts ──────────────────────────────────────────────────
    html.Div([
        dcc.Graph(id="lap-time-graph"),
        dcc.Graph(id="position-graph"),
        dcc.Graph(id="speed-telemetry-graph"),
    ], className="charts"),
])


# ── Callbacks ──────────────────────────────────────────────────

@dash.callback(
    Output("season-dropdown", "options"),
    Output("season-dropdown", "value"),
    Output("cache-warning", "children"),
    Input("page-load-trigger", "data")
)
def load_seasons(_):
    """Load available seasons from backend cache on page load."""
    try:
        seasons = client.get_available_seasons()

        if not seasons:
            warning = html.Div([
                html.Span("⚠", className="alert-icon"),
                html.Div([
                    html.Strong("Nenhum dado no cache SQLite."),
                    html.P([
                        "Execute: ",
                        html.Code(
                            "python scripts/populate_cache.py --season 2024"
                        ),
                    ], style={"margin": ".4rem 0 0"}),
                ]),
            ], className="alert alert-warning")
            return [], None, warning

        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None, None

    except Exception as e:
        print(f"Error loading seasons: {e}")
        error_msg = html.Div([
            html.Span("✕", className="alert-icon"),
            html.Div([
                html.Strong("Não foi possível conectar ao backend."),
                html.P([
                    "Certifique-se de que o servidor está rodando: ",
                    html.Code("python main.py"),
                ], style={"margin": ".4rem 0 0"}),
            ]),
        ], className="alert alert-error")
        return [], None, error_msg


@dash.callback(
    Output("race-dropdown", "options"),
    Input("season-dropdown", "value")
)
def update_races(season: int):
    """Load races for selected season."""
    if not season:
        return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("laps-store", "data"),
    Output("session-store", "data"),
    Input("load-button", "n_clicks"),
    State("season-dropdown", "value"),
    State("race-dropdown", "value"),
    allow_duplicate=True,
    prevent_initial_call=True
)
def handle_load(load_n: int, season: int, race: str):
    """Load a race session and store laps + session meta."""
    if not load_n or not season or not race:
        return dash.no_update, dash.no_update

    laps, _, session = client.load_race_session(season, race)

    if laps.empty:
        return None, None

    laps_json = laps.to_json(date_format="iso", orient="split")
    session_meta = {
        "season": season,
        "race": race,
        "drivers": session.get("drivers", []),
    }
    return laps_json, session_meta


@dash.callback(
    Output("driver-dropdown", "options"),
    Input("laps-store", "data"),
)
def update_drivers(laps_json: str):
    """Extract driver list from loaded laps."""
    if not laps_json:
        return []
    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        drivers = (
            sorted(laps["Driver"].unique().tolist())
            if "Driver" in laps.columns else []
        )
        return [{"label": d, "value": d} for d in drivers]
    except Exception:
        return []


@dash.callback(
    Output("kpi-row", "children"),
    Input("laps-store", "data"),
    State("session-store", "data"),
)
def update_kpis(laps_json: str, session_meta: dict):
    """Render KPI cards after a session is loaded."""
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
    Output("lap-time-graph", "figure"),
    Output("position-graph", "figure"),
    Output("speed-telemetry-graph", "figure"),
    Input("driver-dropdown", "value"),
    State("laps-store", "data"),
)
def update_charts(driver: str, laps_json: str):
    """Update all charts based on selected driver."""
    empty_fig = {
        "data": [],
        "layout": {"template": "plotly_white", "title": "Nenhum dado carregado"},
    }

    if not laps_json:
        return empty_fig, empty_fig, empty_fig

    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        lap_fig = lap_time_chart(laps, driver)
        pos_fig = position_chart(laps, driver)
        speed_fig = speed_telemetry_chart(pd.DataFrame())
        return lap_fig, pos_fig, speed_fig
    except Exception as e:
        print(f"Error updating charts: {e}")
        return empty_fig, empty_fig, empty_fig
