"""
Home page.
Landing page with app overview.
"""
import dash
from dash import html, dcc
import requests
from frontend.config import config

dash.register_page(__name__, path="/", name="Home")


def check_backend_status():
    """Check if backend is accessible"""
    try:
        response = requests.get(
            f"{config.BACKEND_API_URL}/health",
            timeout=2
        )
        return response.status_code == 200
    except:
        return False


layout = html.Div([
    html.H1("🏁 Welcome to Pitwall Analytics"),
    
    html.Div([
        html.P("Advanced F1 race analytics and telemetry visualization."),
        html.P("Explore race data, driver performance, and detailed telemetry."),
    ], className="intro"),
    
    html.Div([
        html.H3("System Status"),
        html.Div([
            html.Span("Backend API: ", style={'font-weight': 'bold'}),
            html.Span(
                "🟢 Connected" if check_backend_status() else "🔴 Disconnected",
                style={'color': 'green' if check_backend_status() else 'red'}
            ),
        ]),
        html.P(f"API Endpoint: {config.BACKEND_API_URL}", style={'font-size': '0.9em', 'color': '#666'}),
    ], className="status-box", style={
        'background': '#f5f5f5',
        'padding': '20px',
        'border-radius': '8px',
        'margin': '20px 0'
    }),
    
    html.Div([
        html.H3("Quick Links"),
        html.Ul([
            html.Li(dcc.Link("📊 Analytics Dashboard", href="/analytics")),
            html.Li(dcc.Link("🔴 Live Session", href="/live")),
        ])
    ], style={'margin': '20px 0'}),
    
    html.Div([
        html.H3("Features"),
        html.Div([
            html.Div([
                html.H4("📈 Race Analytics"),
                html.P("Analyze lap times, positions, and driver performance across seasons.")
            ], className="feature-card"),
            
            html.Div([
                html.H4("🏎️ Telemetry"),
                html.P("Deep dive into speed, throttle, brake, and gear data.")
            ], className="feature-card"),
            
            html.Div([
                html.H4("📡 Live Data"),
                html.P("Real-time session monitoring and analysis.")
            ], className="feature-card"),
        ], style={
            'display': 'grid',
            'grid-template-columns': 'repeat(auto-fit, minmax(250px, 1fr))',
            'gap': '20px',
            'margin': '20px 0'
        })
    ]),
    
], style={'padding': '20px'})
