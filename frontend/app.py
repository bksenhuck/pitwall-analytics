"""
Frontend Dash application.

This is the UI layer that:
- Renders layout and components
- Handles user interactions via callbacks
- Fetches data from backend API (does NOT process data directly)
"""
import dash
from dash import html, dcc
from frontend.config import config


def create_dash_app():
    """Create and configure Dash application"""
    
    app = dash.Dash(
        __name__,
        use_pages=True,
        suppress_callback_exceptions=True,
        title=config.APP_TITLE
    )
    
    # Main layout with navigation
    app.layout = html.Div([
        # Top navigation bar
        html.Header([
            html.Div("🏁 Pitwall Analytics", className="brand"),
            html.Nav([
                dcc.Link("Home", href="/", className="nav-link"),
                dcc.Link("Analytics", href="/analytics", className="nav-link"),
                dcc.Link("Live", href="/live", className="nav-link"),
            ], className="nav"),
        ], className="header"),
        
        # Page content container
        dash.page_container,
        
        # Footer
        html.Footer("© 2026 Pitwall Analytics", className="footer"),
    ], className="container")
    
    return app


if __name__ == '__main__':
    app = create_dash_app()
    print(f"🎨 Frontend starting on http://{config.HOST}:{config.PORT}")
    print(f"📡 Backend API: {config.BACKEND_API_URL}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
