"""
Navigation component.
Reusable navigation bar.
"""
from dash import html, dcc


def create_navbar():
    """
    Create navigation bar component.
    
    Returns:
        Dash component
    """
    return html.Header([
        html.Div("🏁 Pitwall Analytics", className="brand"),
        html.Nav([
            dcc.Link("Home", href="/", className="nav-link"),
            dcc.Link("Analytics", href="/analytics", className="nav-link"),
            dcc.Link("Live", href="/live", className="nav-link"),
        ], className="nav"),
    ], className="header")
