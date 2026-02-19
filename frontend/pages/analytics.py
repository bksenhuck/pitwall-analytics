"""
Analytics page.
Main page for F1 data analysis.

This page demonstrates:
- Fetching data from backend API
- Using callbacks to update UI
- Separation of concerns (no data processing here)
"""
import dash
from dash import html, dcc, Input, Output, State, callback
import requests
from frontend.config import config
from frontend.components.charts import create_lap_time_chart

dash.register_page(__name__, path="/analytics", name="Analytics")


layout = html.Div([
    html.H2("📊 F1 Analytics"),
    
    # Filters section
    html.Div([
        html.Div([
            html.Label("Season"),
            dcc.Dropdown(
                id="season-dropdown",
                placeholder="Select season...",
                value=2023
            ),
        ], className="filter", style={'flex': '1'}),
        
        html.Div([
            html.Label("Race"),
            dcc.Dropdown(
                id="race-dropdown",
                placeholder="Select race...",
            ),
        ], className="filter", style={'flex': '1'}),
        
        html.Button("Load Data", id="load-btn", n_clicks=0, className="btn-primary"),
    ], style={
        'display': 'flex',
        'gap': '20px',
        'margin-bottom': '30px',
        'align-items': 'flex-end'
    }),
    
    # Status/Loading indicator
    html.Div(id="status-message", style={'margin': '10px 0'}),
    
    # Charts section
    html.Div([
        dcc.Graph(id="sample-chart"),
    ], id="charts-container"),
    
], style={'padding': '20px'})


# Callback to load seasons on page load
@callback(
    Output("season-dropdown", "options"),
    Input("season-dropdown", "id")  # Triggers on component mount
)
def load_seasons(_):
    """
    Fetch available seasons from backend API.
    
    This demonstrates:
    - API call to backend
    - Error handling
    - Returning data for Dash dropdown
    """
    try:
        response = requests.get(
            f"{config.BACKEND_API_URL}/data/seasons",
            timeout=config.REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                seasons = data.get('data', [])
                return [{'label': str(s), 'value': s} for s in seasons]
        
        # Fallback
        return [{'label': '2023', 'value': 2023}]
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [{'label': '2023', 'value': 2023}]


# Callback to load races when season changes
@callback(
    Output("race-dropdown", "options"),
    Input("season-dropdown", "value")
)
def load_races(season):
    """
    Fetch races for selected season from backend API.
    """
    if not season:
        return []
    
    try:
        response = requests.get(
            f"{config.BACKEND_API_URL}/data/races/{season}",
            timeout=config.REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                races = data.get('data', [])
                return [
                    {'label': f"{r.get('name', 'Unknown')} - {r.get('location', '')}", 'value': r.get('name')}
                    for r in races
                ]
        
        return []
    except Exception as e:
        print(f"Error loading races: {e}")
        return []


# Callback to load and display data
@callback(
    [Output("sample-chart", "figure"),
     Output("status-message", "children")],
    Input("load-btn", "n_clicks"),
    [State("season-dropdown", "value"),
     State("race-dropdown", "value")]
)
def load_and_display_data(n_clicks, season, race):
    """
    Load session data from backend and display charts.
    
    This demonstrates the frontend/backend separation:
    - Frontend: handles UI interaction, makes API call
    - Backend: processes data, returns clean results
    """
    if n_clicks == 0 or not season or not race:
        empty_fig = create_lap_time_chart([], "Select season and race")
        return empty_fig, html.Div("Select season and race, then click Load Data", style={'color': '#666'})
    
    try:
        # Status: loading
        status = html.Div("⏳ Loading data from backend...", style={'color': 'blue'})
        
        # Call backend API
        response = requests.get(
            f"{config.BACKEND_API_URL}/data/session",
            params={'season': season, 'event': race},
            timeout=config.REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                session_data = data.get('data', {})
                laps = session_data.get('laps', [])
                
                # Create chart from data
                fig = create_lap_time_chart(
                    [{'lap': l.get('LapNumber'), 'time': l.get('LapTimeSeconds')} 
                     for l in laps if l.get('LapTimeSeconds')],
                    f"Lap Times - {race} {season}"
                )
                
                status = html.Div(
                    f"✅ Loaded {len(laps)} laps from {race} {season}",
                    style={'color': 'green'}
                )
                
                return fig, status
            else:
                error_msg = data.get('error', 'Unknown error')
                status = html.Div(f"❌ Error: {error_msg}", style={'color': 'red'})
                return create_lap_time_chart([], "Error loading data"), status
        else:
            status = html.Div(f"❌ Backend returned {response.status_code}", style={'color': 'red'})
            return create_lap_time_chart([], "Backend error"), status
            
    except requests.Timeout:
        status = html.Div("❌ Request timeout - backend may be slow or down", style={'color': 'red'})
        return create_lap_time_chart([], "Timeout"), status
    except Exception as e:
        status = html.Div(f"❌ Error: {str(e)}", style={'color': 'red'})
        return create_lap_time_chart([], "Error"), status
