"""Analytics hub — escolha a seção de análise."""
import dash
from dash import html

dash.register_page(__name__, path="/analytics", name="Analytics")

_SECTIONS = [
    {
        "href": "/analytics/corrida",
        "title": "Corrida",
        "desc": (
            "Tempos de volta, posições, telemetria e pit stops "
            "de uma corrida específica."
        ),
    },
    {
        "href": "/analytics/telemetria",
        "title": "Telemetria",
        "desc": (
            "Desempenho individual ao longo da temporada: "
            "voltas rápidas e comparativos por piloto."
        ),
    },
    {
        "href": "/analytics/campeonato",
        "title": "Campeonato",
        "desc": (
            "Tabela de pontos e progressão do campeonato "
            "de pilotos e construtores."
        ),
    },
]

layout = html.Div([
    html.Div([
        html.H1("Analytics", className="page-title"),
        html.P("Escolha uma área de análise.", className="page-subtitle"),
    ]),

    html.Div([
        html.A([
            html.Div(s["title"], className="card-value"),
            html.Div(s["desc"], className="card-desc"),
        ], href=s["href"], className="card card-feature", style={
            "textDecoration": "none",
            "color": "inherit",
            "cursor": "pointer",
            "transition": "box-shadow .15s",
        })
        for s in _SECTIONS
    ], className="hub-grid"),
])
