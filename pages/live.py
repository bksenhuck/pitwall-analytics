import math
import json
import io
from typing import Dict, Any

import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import plotly.graph_objs as go

import data_loader

dash.register_page(__name__, path="/live", name="Live")


def layout_card(label: str, component: Any):
    return html.Div([html.Label(label), component], className="filter")


layout = html.Div([
    html.H2("Live Race Simulation"),

    html.Div([
        layout_card(
            "Season",
            dcc.Dropdown(id="live-season", options=[], placeholder="Select season"),
        ),
        layout_card("Race", dcc.Dropdown(id="live-race", options=[], placeholder="Select race")),
        layout_card("Driver (highlight)", dcc.Dropdown(id="live-highlight", options=[], placeholder="Optional")),
        html.Div([html.Button("Load Session", id="live-load", n_clicks=0), html.Button("Start", id="live-start", n_clicks=0)], className="filter"),
    ], className="filters"),

    # Stores: telemetry per driver
    dcc.Store(id="live-telemetry-store", storage_type="session"),
    dcc.Store(id="live-drivers-store", storage_type="session"),
    # Trigger to load seasons on page load
    dcc.Store(id="live-page-load-trigger", data={"loaded": True}),

    # Interval to animate
    dcc.Interval(id="live-interval", interval=1000, n_intervals=0, disabled=True),

    html.Div([
        dcc.Graph(id="live-map", config={"displayModeBar": False}),
    ], className="charts"),
])


@dash.callback(
    Output("live-season", "options"),
    Output("live-season", "value"),
    Input("live-page-load-trigger", "data")
)
def load_live_seasons(_):
    """Load available seasons from backend cache on page load."""
    try:
        seasons = data_loader.get_available_seasons()
        options = [{"label": s, "value": s} for s in seasons]
        return options, seasons[-1] if seasons else None
    except Exception as e:
        print(f"Error loading seasons in live page: {e}")
        return [], None


@dash.callback(Output("live-race", "options"), Input("live-season", "value"))
def update_live_races(season: int):
    races = data_loader.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("live-telemetry-store", "data"),
    Output("live-drivers-store", "data"),
    Output("live-highlight", "options"),
    Input("live-load", "n_clicks"),
    State("live-season", "value"),
    State("live-race", "value"),
    allow_duplicate=True,
)
def load_live_session(n_clicks: int, season: int, race: str):
    """Load session with telemetry and store per-driver fastest-lap telemetry serialized as JSON."""
    if not n_clicks or not season or not race:
        return dash.no_update, dash.no_update, dash.no_update

    try:
        session = data_loader.get_session_with_telemetry(season, race)
    except Exception:
        return dash.no_update, dash.no_update, dash.no_update

    # collect drivers
    laps = session.laps
    drivers = laps["Driver"].unique().tolist() if "Driver" in laps.columns else []

    telemetry_map: Dict[str, Any] = {}
    for drv in drivers:
        try:
            tel = data_loader.get_driver_telemetry(session, drv)
            if tel is None or tel.empty:
                continue
            # keep only Distance and Speed (and index/time) to reduce size
            keep = [c for c in ["Distance", "Speed"] if c in tel.columns]
            small = tel[keep].reset_index()
            telemetry_map[drv] = small.to_json(date_format="iso", orient="split")
        except Exception:
            continue

    highlight_options = [{"label": d, "value": d} for d in telemetry_map.keys()]
    return json.dumps(telemetry_map), json.dumps(list(telemetry_map.keys())), highlight_options


def _pos_from_distance(dist: float, max_dist: float, radius: float = 1.0):
    """Map a distance along lap to a point on a circle for simple 2D visualization."""
    if max_dist <= 0:
        return 0.0, 0.0
    frac = (dist % max_dist) / max_dist
    theta = frac * 2 * math.pi
    x = radius * math.cos(theta)
    y = radius * math.sin(theta)
    return x, y


@dash.callback(
    Output("live-map", "figure"),
    Input("live-interval", "n_intervals"),
    State("live-telemetry-store", "data"),
    State("live-drivers-store", "data"),
    State("live-highlight", "value"),
)
def update_live_map(n: int, telemetry_json: str, drivers_json: str, highlight: str):
    fig = go.Figure()
    if not telemetry_json or not drivers_json:
        fig.update_layout(title="No live data loaded", template="plotly_white")
        return fig

    telemetry_map = json.loads(telemetry_json)
    drivers = json.loads(drivers_json)

    # for each driver, pick a point index based on n modulo their length
    for drv in drivers:
        tel_json = telemetry_map.get(drv)
        if not tel_json:
            continue
        # pd.read_json with a literal JSON string requires a StringIO wrapper
        tel = pd.read_json(io.StringIO(tel_json), orient="split")
        if tel.empty:
            continue
        # prefer Distance column
        if "Distance" in tel.columns:
            maxd = tel["Distance"].max()
            idx = n % len(tel)
            dist = tel.iloc[idx]["Distance"]
            speed = tel.iloc[idx]["Speed"] if "Speed" in tel.columns else None
        else:
            # fallback to index progression
            maxd = len(tel)
            idx = n % len(tel)
            dist = float(idx)
            speed = tel.iloc[idx]["Speed"] if "Speed" in tel.columns else None

        x, y = _pos_from_distance(dist, maxd, radius=1.0)
        marker = dict(size=10, opacity=0.9)
        name = drv
        marker_color = "red" if highlight == drv else "blue"
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", name=name, text=[drv], marker={**marker, "color": marker_color}))

    fig.update_layout(title="Live Track (simulated 2D)", xaxis=dict(visible=False), yaxis=dict(visible=False), template="plotly_white")
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig



@dash.callback(
    Output("live-interval", "disabled"),
    Output("live-start", "children"),
    Input("live-start", "n_clicks"),
    State("live-interval", "disabled"),
)
def toggle_live(n_clicks: int, currently_disabled: bool):
    """Toggle the live interval on/off and update button label."""
    if not n_clicks:
        # initial state: interval disabled
        return True, "Start"

    # flip current disabled state
    new_disabled = not bool(currently_disabled)
    label = "Stop" if not new_disabled else "Start"
    return new_disabled, label
