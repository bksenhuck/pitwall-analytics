"""
Live session page.
Placeholder for live session monitoring.
"""
import dash
from dash import html, dcc

dash.register_page(__name__, path="/live", name="Live")


layout = html.Div([
    html.H2("🔴 Live Session"),
    
    html.Div([
        html.P("Live session monitoring coming soon!"),
        html.P("This will show:"),
        html.Ul([
            html.Li("Real-time lap times"),
            html.Li("Live position tracking"),
            html.Li("Current weather conditions"),
            html.Li("Session timing"),
        ])
    ], style={'padding': '20px'}),
    
    html.Div([
        html.H3("Backend Integration"),
        html.P("When implemented, this page will:"),
        html.Ol([
            html.Li("Poll backend API every few seconds"),
            html.Li("Backend fetches live timing data"),
            html.Li("Frontend updates charts automatically"),
        ]),
    ], style={
        'background': '#f5f5f5',
        'padding': '20px',
        'border-radius': '8px',
        'margin-top': '20px'
    }),
    
], style={'padding': '20px'})
