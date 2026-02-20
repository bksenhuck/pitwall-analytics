"""
Frontend Dash Application.

This is the main entry point for the frontend UI.
Can be run standalone (development) or mounted in main.py (production).
"""
import dash
from dash import html
from pathlib import Path
from frontend.config import APP_TITLE, HOST, PORT, DEBUG, CACHE_DIR
from frontend.api import client


def create_app():
    """
    Create and configure the Dash application.
    
    Returns:
        Dash app instance
    """
    # Initialize cache
    client.enable_cache(str(CACHE_DIR))
    
    # Get project root and assets folder
    project_root = Path(__file__).parent.parent
    assets_folder = project_root / "assets"
    
    # Create Dash app with multi-page support
    app = dash.Dash(
        __name__,
        use_pages=True,
        pages_folder="pages",  # Relative to frontend/ directory
        assets_folder=str(assets_folder),  # Point to project root assets/
        suppress_callback_exceptions=True,
        title=APP_TITLE
    )
    
    # Main layout with navigation
    app.layout = html.Div([
        # Top navigation bar
        html.Header([
            html.Div("🏁 Pitwall Analytics", className="brand"),
            html.Nav([
                dash.dcc.Link("Home", href="/", className="nav-link"),
                dash.dcc.Link("Analytics", href="/analytics", className="nav-link"),
                dash.dcc.Link("Live", href="/live", className="nav-link"),
            ], className="nav"),
        ], className="header"),
        
        # Page content (populated by dash.page_container)
        dash.page_container,
        
        # Footer
        html.Footer(
            "© 2026 Pitwall Analytics",
            className="footer"
        ),
    ], className="container")
    
    return app


def run_app(app=None):
    """Run the application server."""
    if app is None:
        app = create_app()
    
    print(f"🎨 Frontend starting on http://{HOST}:{PORT}")
    print(f"📡 Backend API: {client.BACKEND_API_URL}")
    
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG
    )


if __name__ == "__main__":
    app = create_app()
    run_app(app)
