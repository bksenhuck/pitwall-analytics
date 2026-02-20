"""Analytics page - Main F1 data analysis interface"""
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import io

from frontend.components.charts import lap_time_chart, position_chart, speed_telemetry_chart
from frontend.api import client

dash.register_page(__name__, path="/analytics", name="Analytics")


layout = html.Div([
    html.H2("📊 Analytics"),
    
    # Warning message when cache is empty
    html.Div(id="cache-warning", style={"margin": "20px 0"}),

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
            dcc.Dropdown(id="driver-dropdown", options=[], placeholder="Select driver (optional)"),
        ], className="filter"),

        html.Div([
            html.Button("Load Race", id="load-button", n_clicks=0, className="btn-primary")
        ], className="filter"),
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
    Output("cache-warning", "children"),
    Input("page-load-trigger", "data")
)
def load_seasons(_):
    """Load available seasons from backend cache on page load."""
    try:
        seasons = client.get_available_seasons()
        
        if not seasons:
            warning = html.Div([
                html.Strong("⚠️ No data in SQLite cache", style={"color": "#ff9800"}),
                html.P([
                    "Run this command to populate the cache:",
                    html.Br(),
                    html.Code("python scripts/populate_cache.py --season 2024", 
                             style={"background": "#f5f5f5", "padding": "8px", "display": "block", "margin": "10px 0"}),
                ]),
            ], style={
                "border": "2px solid #ff9800",
                "padding": "15px",
                "borderRadius": "5px",
                "backgroundColor": "#fff3e0"
            })
            return [], None, warning
        
        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None, None
        
    except Exception as e:
        print(f"Error loading seasons: {e}")
        error_msg = html.Div([
            html.Strong("❌ Cannot connect to backend", style={"color": "#f44336"}),
            html.P([
                "Make sure the backend is running:",
                html.Br(),
                html.Code("python main.py", 
                         style={"background": "#f5f5f5", "padding": "8px", "display": "block", "margin": "10px 0"}),
            ]),
        ], style={
            "border": "2px solid #f44336",
            "padding": "15px",
            "borderRadius": "5px",
            "backgroundColor": "#ffebee"
        })
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
    
    if not races:
        return []
    
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
    session_meta = {"season": season, "race": race, "drivers": session.get("drivers", [])}
    
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
        drivers = sorted(laps["Driver"].unique().tolist()) if "Driver" in laps.columns else []
        return [{"label": d, "value": d} for d in drivers]
    except:
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
    # Default empty figures
    empty_fig = {"data": [], "layout": {"template": "plotly_white", "title": "No data loaded"}}
    
    if not laps_json:
        return empty_fig, empty_fig, empty_fig

    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        
        lap_fig = lap_time_chart(laps, driver)
        pos_fig = position_chart(laps, driver)
        
        # Telemetry not available from cache
        speed_fig = speed_telemetry_chart(pd.DataFrame())
        
        return lap_fig, pos_fig, speed_fig
        
    except Exception as e:
        print(f"Error updating charts: {e}")
        return empty_fig, empty_fig, empty_fig
