"""Home page - Landing / welcome page for Pitwall Analytics"""
import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")

_PAGES = [
    {
        "title": "Analytics",
        "href": "/analytics",
        "desc": (
            "Mergulhe nos dados de corrida. Compare tempos de volta, "
            "evolução de posições e desempenho por piloto ao longo de "
            "toda a temporada."
        ),
    },
    {
        "title": "Live",
        "href": "/live",
        "desc": (
            "Carregue uma corrida e acompanhe a evolução da prova volta "
            "a volta — posições, gaps e contexto de cada stint."
        ),
    },
    {
        "title": "Sobre",
        "href": "/about",
        "desc": (
            "A motivação por trás do projeto, a arquitetura de dados e "
            "o roadmap do que vem por aí."
        ),
    },
]


def _page_card(page):
    return html.A([
        html.Div(page["title"], className="card-value"),
        html.Div(page["desc"], className="card-desc"),
    ], href=page["href"], className="card card-feature", style={
        "textDecoration": "none",
        "color": "inherit",
        "cursor": "pointer",
        "transition": "box-shadow .15s",
    })


layout = html.Div([
    # ── Hero ───────────────────────────────────────────────────
    html.Section([
        html.H1([
            html.Span("Pitwall", style={"color": "#90CAF9"}),
            " Analytics",
        ]),
        html.P(
            "Dados reais de Formula 1 — histórico completo de corridas, "
            "tempos de volta e posições em uma interface interativa e rápida."
        ),
        html.Div([
            html.Span("FastF1", className="badge"),
            html.Span("SQLite", className="badge"),
            html.Span("FastAPI", className="badge"),
            html.Span("Dash", className="badge"),
        ], className="badge-row"),
    ], className="hero"),

    # ── O que tem aqui ─────────────────────────────────────────
    html.Section([
        html.H2("Explore o dashboard", className="section-heading"),
        html.Div(
            [_page_card(p) for p in _PAGES],
            className="cards-grid",
        ),
    ], className="mt-2"),

])
