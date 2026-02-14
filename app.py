import dash
from dash import html, dcc, Input, Output
import shutil
import os

import data_loader

# Initialize FastF1 local cache on startup
data_loader.enable_cache(".ff1cache")

app = dash.Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    # Top navigation
    html.Header([
        html.Div("Pitwall Analytics", className="brand"),
        html.Nav([
            dcc.Link("Home", href="/", className="nav-link"),
            dcc.Link("Analytics", href="/analytics", className="nav-link"),
            dcc.Link("Live", href="/live", className="nav-link"),
        ], className="nav"),
    ], className="header"),

    # page content
    dash.page_container,

    # small footer
    html.Footer("© Pitwall Analytics", className="footer"),
], className="container")



# Navigation-clear callback removed to avoid duplicate-output conflicts.
# If desired, per-page clearing callbacks can be added inside page modules.


if __name__ == "__main__":
    app.run(debug=True)
