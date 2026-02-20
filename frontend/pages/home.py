"""Home page - Landing page for Pitwall Analytics"""
import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")


def overview_card(title: str, value: str):
    """Create a simple info card"""
    return html.Div([
        html.Div(title, className="card-title"),
        html.Div(value, className="card-value"),
    ], className="card")


layout = html.Div([
    html.Section([
        html.H1("🏁 Pitwall Analytics"),
        html.P("F1 Race Analytics Dashboard - Your gateway to Formula 1 data insights"),
    ], className="hero"),

    html.Section([
        html.Div([
            overview_card("Data Source", "FastF1 + SQLite Cache"),
            overview_card("Architecture", "FastAPI + Dash"),
            overview_card("Latest Season", "2024 (+ historical data)"),
        ], className="cards"),
    ], className="overview"),

    html.Section([
        html.H3("📊 Get Started"),
        html.Ul([
            html.Li([
                html.Strong("Analytics Page: "),
                "Explore race data, lap times, and driver performance"
            ]),
            html.Li([
                html.Strong("Live Page: "),
                "Visualize race telemetry and track positions"
            ]),
            html.Li([
                html.Strong("Populate Data: "),
                html.Code("python scripts/populate_cache.py --season 2024")
            ]),
        ]),
    ], className="notes"),
    
    html.Section([
        html.H3("🔧 Quick Start"),
        html.Ol([
            html.Li("Ensure backend is running (python main.py)"),
            html.Li("Populate cache with F1 data using scripts"),
            html.Li("Navigate to Analytics to explore race sessions"),
        ]),
    ], className="notes"),
], className="page")
