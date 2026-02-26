"""About page - Project context and motivation"""
import dash
from dash import html

dash.register_page(__name__, path="/about", name="Sobre")

_TECH = [
    ("FastF1", "Biblioteca Python oficial para dados da F1"),
    ("SQLite", "Cache normalizado de alta performance"),
    ("FastAPI", "Backend REST assíncrono"),
    ("Dash / Plotly", "UI interativa e gráficos"),
]

_DONE = [
    "Cache normalizado de dados históricos (F1 2018–2024)",
    "API REST com endpoints de temporadas, corridas e voltas",
    "Gráficos de tempo de volta e posição por piloto",
    "Multi-página com roteamento client-side",
]

_NEXT = [
    "Mapa de circuito com posição dos carros via OpenF1",
    "Comparativo entre pilotos na mesma corrida",
    "Integração com dados meteorológicos detalhados",
    "Exportação de dados para CSV/JSON",
]


def _tech_card(name, desc):
    return html.Div([
        html.Div(name, className="card-value"),
        html.Div(desc, className="card-desc"),
    ], className="card card-feature")


def _list_item(text):
    return html.Li(text, style={"marginBottom": ".4rem"})


layout = html.Div([
    html.Div([
        html.H1("Sobre o Pitwall Analytics", className="page-title"),
        html.P(
            "O contexto, a ideia e o que está por vir.",
            className="page-subtitle",
        ),
    ]),

    # ── O Projeto ──────────────────────────────────────────────
    html.Section([
        html.H2("O Projeto", className="section-heading"),
        html.P(
            "Pitwall Analytics nasceu da vontade de explorar dados reais de "
            "Formula 1 de forma interativa — sem depender de serviços pagos "
            "ou APIs instáveis. O nome vem do pitwall, a bancada de "
            "estrategistas e engenheiros que acompanham cada detalhe da "
            "corrida em tempo real.",
            style={"marginBottom": "1rem"},
        ),
        html.P(
            "A ideia é simples: baixar os dados oficiais da F1 uma vez, "
            "normalizar em um banco local e expor uma interface rápida para "
            "análise histórica e visualização de corridas."
        ),
    ], className="mt-2"),

    # ── Como funciona ──────────────────────────────────────────
    html.Section([
        html.H2("Como funciona", className="section-heading"),
        html.P(
            "A arquitetura separa ingestão de dados do servidor em tempo "
            "de execução:",
            style={"marginBottom": ".75rem"},
        ),
        html.Div([
            html.Span("FastF1", className="flow-step"),
            html.Span("→", className="flow-arrow"),
            html.Span("populate_cache.py", className="flow-step"),
            html.Span("→", className="flow-arrow"),
            html.Span("SQLite", className="flow-step"),
            html.Span("→", className="flow-arrow"),
            html.Span("FastAPI", className="flow-step"),
            html.Span("→", className="flow-arrow"),
            html.Span("Dash", className="flow-step"),
        ], className="flow-steps"),
        html.P(
            "O backend nunca chama a API da F1 em tempo de execução — "
            "apenas lê o cache SQLite, garantindo respostas rápidas e "
            "operação offline.",
            style={"marginTop": ".75rem", "color": "var(--muted)"},
        ),
    ], className="mt-3"),

    # ── Tecnologias ────────────────────────────────────────────
    html.Section([
        html.H2("Tecnologias", className="section-heading"),
        html.Div(
            [_tech_card(n, d) for n, d in _TECH],
            className="cards-grid",
        ),
    ], className="mt-3"),

    # ── Status ─────────────────────────────────────────────────
    html.Section([
        html.H2("Status do Projeto", className="section-heading"),
        html.Div([
            html.Div([
                html.Div(
                    "Implementado",
                    style={
                        "fontWeight": "700",
                        "color": "var(--primary)",
                        "marginBottom": ".6rem",
                    },
                ),
                html.Ul([_list_item(t) for t in _DONE]),
            ], className="card", style={"flex": "1", "minWidth": "240px"}),
            html.Div([
                html.Div(
                    "Planejado",
                    style={
                        "fontWeight": "700",
                        "color": "var(--muted)",
                        "marginBottom": ".6rem",
                    },
                ),
                html.Ul([_list_item(t) for t in _NEXT]),
            ], className="card", style={"flex": "1", "minWidth": "240px"}),
        ], style={"display": "flex", "gap": "1.25rem", "flexWrap": "wrap"}),
    ], className="mt-3"),
])
