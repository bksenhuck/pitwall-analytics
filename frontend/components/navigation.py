"""
Navigation components for Dash application.
"""
from dash import html, dcc


def create_header(active_page: str = None):
    """
    Create the main navigation header.
    
    Args:
        active_page: Current active page path (e.g., '/', '/analytics')
    
    Returns:
        Dash HTML component
    """
    nav_links = [
        {"label": "Home", "href": "/"},
        {"label": "Analytics", "href": "/analytics"},
        {"label": "Live", "href": "/live"},
    ]
    
    nav_items = []
    for link in nav_links:
        class_name = "nav-link active" if active_page == link["href"] else "nav-link"
        nav_items.append(
            dcc.Link(link["label"], href=link["href"], className=class_name)
        )
    
    return html.Header([
        html.Div("🏁 Pitwall Analytics", className="brand"),
        html.Nav(nav_items, className="nav"),
    ], className="header")


def create_footer():
    """
    Create the footer component.
    
    Returns:
        Dash HTML component
    """
    return html.Footer(
        "© 2026 Pitwall Analytics",
        className="footer"
    )
