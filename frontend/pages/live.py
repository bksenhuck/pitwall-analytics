"""Live page - Real-time race simulation (limited without telemetry in cache)"""
import math
import json
import io
from typing import Dict, Any

import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import plotly.graph_objs as go

from frontend.api import client

dash.register_page(__name__, path="/live", name="Live")


def layout_card(label: str, component: Any):
    return html.Div([html.Label(label), component], className="filter")


layout = html.Div([
    html.H2("🏁 Live Race (Beta)"),
    
    html.Div([
        html.Strong("⚠️ Note: "),
        html.P("Telemetry data is not stored in cache. This page has limited functionality."),
    ], style={"padding": "10px", "background": "#fff3e0", "borderRadius": "5px", "margin": "10px 0"}),

    html.Div([
        layout_card(
            "Season",
            dcc.Dropdown(id="live-season", options=[], placeholder="Select season"),
        ),
        layout_card("Race", dcc.Dropdown(id="live-race", options=[], placeholder="Select race")),
        layout_card("Driver", dcc.Dropdown(id="live-driver", options=[], placeholder="Select driver")),
        html.Div([
            html.Button("Load Session", id="live-load", n_clicks=0, className="btn-primary")
        ], className="filter"),
    ], className="filters"),

    # Stores
    dcc.Store(id="live-laps-store", storage_type="session"),
    dcc.Store(id="live-page-load-trigger", data={"loaded": True}),

    html.Div([
        html.Div(id="live-info"),
        dcc.Graph(id="live-position-chart"),
    ], className="charts"),
])


@dash.callback(
    Output("live-season", "options"),
    Output("live-season", "value"),
    Input("live-page-load-trigger", "data")
)
def load_live_seasons(_):
    """Load available seasons."""
    try:
        seasons = client.get_available_seasons()
        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [], None


@dash.callback(
    Output("live-race", "options"),
    Input("live-season", "value")
)
def update_live_races(season: int):
    """Load races for selected season."""
    if not season:
        return []
    
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("live-laps-store", "data"),
    Output("live-driver", "options"),
    Input("live-load", "n_clicks"),
    State("live-season", "value"),
    State("live-race", "value"),
    prevent_initial_call=True
)
def load_live_session(n_clicks: int, season: int, race: str):
    """Load session lap data."""
    if not n_clicks or not season or not race:
        return dash.no_update, dash.no_update

    try:
        laps, _, session = client.load_race_session(season, race)
        
        if laps.empty:
            return None, []
        
        drivers = sorted(laps["Driver"].unique().tolist()) if "Driver" in laps.columns else []
        driver_options = [{"label": d, "value": d} for d in drivers]
        
        laps_json = laps.to_json(date_format="iso", orient="split")
        
        return laps_json, driver_options
        
    except Exception as e:
        print(f"Error loading live session: {e}")
        return None, []


@dash.callback(
    Output("live-info", "children"),
    Output("live-position-chart", "figure"),
    Input("live-driver", "value"),
    State("live-laps-store", "data"),
)
def update_live_view(driver: str, laps_json: str):
    """Update live view based on selected driver."""
    if not laps_json:
        return html.Div("No data loaded"), {"data": [], "layout": {"title": "No data"}}
    
    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        
        # Info display
        total_laps = len(laps)
        total_drivers = len(laps["Driver"].unique())
        
        info = html.Div([
            html.P(f"📊 Total Laps: {total_laps}"),
            html.P(f"👥 Drivers: {total_drivers}"),
        ])
        
        # Position chart
        fig = go.Figure()
        
        if driver and "Position" in laps.columns:
            driver_laps = laps[laps["Driver"] == driver]
            
            fig.add_trace(
                go.Scatter(
                    x=driver_laps["LapNumber"],
                    y=driver_laps["Position"],
                    mode="lines+markers",
                    name=driver,
                    line=dict(width=3)
                )
            )
            fig.update_yaxes(autorange="reversed")
        
        fig.update_layout(
            title=f"Race Position - {driver}" if driver else "Select a driver",
            xaxis_title="Lap Number",
            yaxis_title="Position",
            template="plotly_white",
            height=400
        )
        
        return info, fig
        
    except Exception as e:
        print(f"Error updating live view: {e}")
        return html.Div("Error loading data"), {"data": [], "layout": {"title": "Error"}}
