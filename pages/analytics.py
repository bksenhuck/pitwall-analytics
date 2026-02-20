import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
# removed datetime import (not needed after removing update timestamp)

from charts import lap_time_chart, position_chart, speed_telemetry_chart
import data_loader

dash.register_page(__name__, path="/analytics", name="Analytics")


layout = html.Div([
    html.H2("Analytics"),

    html.Div([
        html.Div([
            html.Label("Season"),
            dcc.Dropdown(id="season-dropdown", options=[], placeholder="Select season"),
        ], className="filter"),

        html.Div([
            html.Label("Race"),
            dcc.Dropdown(id="race-dropdown", options=[], placeholder="Select race"),
        ], className="filter"),

        html.Div([
            html.Label("Driver"),
            dcc.Dropdown(id="driver-dropdown", options=[], placeholder="Select driver"),
        ], className="filter"),

        html.Div([
            html.Button("Load Race", id="load-button", n_clicks=0)
        ], className="filter"),
        # Update button removed per user request
    ], className="filters"),

    # Stores for session and laps (persist across page refresh in browser tab)
    dcc.Store(id="laps-store", storage_type="session"),
    dcc.Store(id="session-store", storage_type="session"),  
    # Trigger to load seasons on page load
    dcc.Store(id="page-load-trigger", data={"loaded": True}),

    html.Div([
        dcc.Graph(id="lap-time-graph"),
        dcc.Graph(id="position-graph"),
        dcc.Graph(id="speed-telemetry-graph"),
    ], className="charts"),
])


@dash.callback(
    Output("season-dropdown", "options"),
    Output("season-dropdown", "value"),
    Input("page-load-trigger", "data")
)
def load_seasons(_):
    """Load available seasons from backend cache on page load."""
    try:
        seasons = data_loader.get_available_seasons()
        options = [{"label": s, "value": s} for s in seasons]
        return options, seasons[-1] if seasons else None  # Default to latest season
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [], None


@dash.callback(Output("race-dropdown", "options"), Input("season-dropdown", "value"))
def update_races(season: int):
    races = data_loader.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("laps-store", "data"),
    Output("session-store", "data"),
    Input("load-button", "n_clicks"),
    State("season-dropdown", "value"),
    State("race-dropdown", "value"),
    allow_duplicate=True,
)
def handle_load(load_n: int, season: int, race: str):
    """Load a race session and store laps + session meta."""
    if not load_n or not season or not race:
        return dash.no_update, dash.no_update

    laps, telemetry_df, session = data_loader.load_race_session(season, race)
    laps_json = laps.to_json(date_format="iso", orient="split")
    session_meta = {"season": season, "race": race}
    return laps_json, session_meta


@dash.callback(
    Output("driver-dropdown", "options"),
    Input("laps-store", "data"),
)
def update_drivers(laps_json: str):
    if not laps_json:
        return []
    laps = pd.read_json(laps_json, orient="split")
    drivers = laps["Driver"].unique().tolist() if "Driver" in laps.columns else []
    return [{"label": d, "value": d} for d in drivers]


@dash.callback(
    Output("lap-time-graph", "figure"),
    Output("position-graph", "figure"),
    Output("speed-telemetry-graph", "figure"),
    Input("driver-dropdown", "value"),
    State("laps-store", "data"),
    State("session-store", "data"),
)
def update_charts(driver: str, laps_json: str, session_meta: dict):
    # Default empty figures
    empty_fig = {"data": [], "layout": {"template": "plotly_white"}}
    if not laps_json:
        return empty_fig, empty_fig, empty_fig

    laps = pd.read_json(laps_json, orient="split")
    lap_fig = lap_time_chart(laps, driver)
    pos_fig = position_chart(laps, driver)

    speed_fig = empty_fig
    if session_meta and driver:
        # load session on demand to fetch telemetry for driver
        season = session_meta.get("season")
        race = session_meta.get("race")
        try:
            session_obj = data_loader.get_session_with_telemetry(season, race)
            telemetry = data_loader.get_driver_telemetry(session_obj, driver)
            speed_fig = speed_telemetry_chart(telemetry)
        except Exception:
            speed_fig = empty_fig

    return lap_fig, pos_fig, speed_fig


def ff1_session_loader(season: int, race: str):
    """Helper to (re)load a FastF1 session for telemetry requests."""
    # Deprecated: kept for backward compatibility; prefer get_session_with_telemetry
    return data_loader.get_session_with_telemetry(season, race)

