import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")


def overview_card(title: str, value: str):
    return html.Div([
        html.Div(title, className="card-title"),
        html.Div(value, className="card-value"),
    ], className="card")


layout = html.Div([
    html.Section([
        html.H1("Pitwall Analytics"),
        html.P("A minimal motorsport analytics dashboard built with Dash and FastF1."),
    ], className="hero"),

    html.Section([
        html.Div([
            overview_card("Seasons", "2021, 2022, 2023, 2024"),
            overview_card("Default Race", "2023 Bahrain GP Race"),
            overview_card("Built With", "Dash · FastF1 · Pandas"),
        ], className="cards"),
    ], className="overview"),

    html.Section([
        html.H3("Get started"),
        html.Ul([
            html.Li("Go to Analytics to load race sessions and explore telemetry."),
        ]),
    ], className="notes"),
], className="page")
