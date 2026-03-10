"""Navigation components for Dash application."""
from dash import html, dcc


def create_header(active_page: str = None):
    nav_links = [
        {"label": "Home", "href": "/"},
        {"label": "Analytics", "href": "/analytics"},
        {"label": "Predictions", "href": "/predictions"},
    ]
    nav_items = []
    for link in nav_links:
        cls = "nav-link active" if active_page == link["href"] else "nav-link"
        nav_items.append(
            dcc.Link(link["label"], href=link["href"], className=cls)
        )
    return html.Header([
        html.Div("🏁 Pitwall Analytics", className="brand"),
        html.Nav(nav_items, className="nav"),
    ], className="header")



def create_analytics_subnav(active_path: str = None):
    """Sub-navigation bar shown inside all /analytics/* pages."""
    links = [
        {"label": "Corrida",    "href": "/analytics/corrida"},
        {"label": "Telemetria", "href": "/analytics/telemetria"},
        {"label": "Campeonato", "href": "/analytics/campeonato"},
    ]
    items = []
    for lnk in links:
        cls = (
            "subnav-link active"
            if active_path == lnk["href"]
            else "subnav-link"
        )
        items.append(dcc.Link(lnk["label"], href=lnk["href"], className=cls))
    return html.Nav(items, className="analytics-subnav")


def create_footer():
    return html.Footer(
        "© 2026 Pitwall Analytics",
        className="footer"
    )
