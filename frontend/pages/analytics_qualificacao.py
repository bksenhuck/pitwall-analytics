"""Página de Resultados da Classificação."""
import io
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
from frontend.components.navigation import create_analytics_subnav
from frontend.f1_config import get_driver_color, get_team_color
from frontend.api import client

dash.register_page(__name__, path="/analytics/qualificacao", name="Resultado Classificação")

_MUTED = "#6B7280"
_PRIMARY = "#003082"
_BORDER = "#DDE1E7"
_SURFACE = "#F4F5F7"

layout = html.Div([
    html.Div([
        html.H1("Resultado da Classificação", className="page-title"),
        html.P(
            "Tabela de tempos e posições finais da qualificação.",
            className="page-subtitle",
        ),
    ]),

    create_analytics_subnav("/analytics/qualificacao"),

    html.Div(id="qualy-res-cache-warning"),

    # ── Filtros ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="qualy-res-season-dropdown",
                options=[],
                placeholder="Selecione a temporada",
            ),
        ], className="filter"),

        html.Div([
            html.Label("Corrida"),
            dcc.Dropdown(
                id="qualy-res-race-dropdown",
                placeholder="Selecione a corrida",
            ),
        ], className="filter"),

        html.Button(
            "Carregar Resultados",
            id="qualy-res-load-button",
            className="button-primary",
        ),
    ], className="filters-container"),

    dcc.Loading(
        id="qualy-res-loading",
        type="default",
        children=html.Div(id="qualy-res-content")
    ),

    dcc.Store(id="qualy-res-store"),
    dcc.Store(id="qualy-res-session-store"),
    dcc.Interval(id="qualy-res-page-trigger", interval=100, max_intervals=1),
], className="analytics-container")


def _fmt_lap(seconds):
    if seconds is None or pd.isna(seconds) or seconds == 0:
        return "—"
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:06.3f}"


def _build_qualy_results_table(laps_json, session_meta):
    if not laps_json:
        return html.Div("Nenhum dado carregado.", style={"padding": "2rem", "color": _MUTED})

    laps = pd.read_json(io.StringIO(laps_json), orient="split")
    if laps.empty:
        return html.Div("Nenhum dado disponível para esta sessão.", style={"padding": "2rem", "color": _MUTED})

    # Obter o melhor tempo de cada piloto
    best_laps = laps[laps["LapTimeSeconds"] > 0].sort_values("LapTimeSeconds").groupby("Driver").first().reset_index()
    best_laps = best_laps.sort_values("LapTimeSeconds")
    
    # Calcular Gaps
    best_overall = best_laps["LapTimeSeconds"].min()
    best_laps["Gap"] = best_laps["LapTimeSeconds"] - best_overall
    
    # Header
    header = html.Div([
        html.Span("Pos", style={"flex": "0 0 45px", "fontWeight": "bold", "fontSize": ".75rem"}),
        html.Span("Piloto", style={"flex": "0 0 80px", "fontWeight": "bold", "fontSize": ".75rem"}),
        html.Span("Equipe", style={"flex": "1", "fontWeight": "bold", "fontSize": ".75rem"}),
        html.Span("Tempo", style={"flex": "0 0 100px", "textAlign": "right", "fontWeight": "bold", "fontSize": ".75rem"}),
        html.Span("Gap", style={"flex": "0 0 80px", "textAlign": "right", "fontWeight": "bold", "fontSize": ".75rem"}),
    ], style={
        "display": "flex",
        "padding": "0.75rem 1rem",
        "borderBottom": f"1px solid {_BORDER}",
        "backgroundColor": "#F9FAFB",
        "color": _MUTED,
        "textTransform": "uppercase",
        "letterSpacing": "0.025em"
    })

    rows = []
    season = session_meta.get("season")
    for i, (_, row) in enumerate(best_laps.iterrows()):
        drv = row["Driver"]
        team = row.get("team", "—")
        drv_color = get_driver_color(season, drv)
        
        row_div = html.Div([
            html.Span(f"{i+1}º", style={"flex": "0 0 45px", "fontWeight": "800", "color": _PRIMARY}),
            html.Span(drv, style={"flex": "0 0 80px", "fontWeight": "700", "color": drv_color, "fontFamily": "monospace"}),
            html.Span(team, style={"flex": "1", "color": _MUTED, "fontSize": "0.9rem"}),
            html.Span(_fmt_lap(row["LapTimeSeconds"]), style={"flex": "0 0 100px", "textAlign": "right", "fontWeight": "600"}),
            html.Span(f"+{row['Gap']:.3f}" if row['Gap'] > 0 else "—", style={"flex": "0 0 80px", "textAlign": "right", "color": _MUTED, "fontSize": "0.85rem"}),
        ], style={
            "display": "flex",
            "padding": "0.85rem 1rem",
            "borderBottom": f"1px solid {_BORDER}",
            "alignItems": "center",
            "backgroundColor": "white"
        })
        rows.append(row_div)

    return html.Div([
        header,
        html.Div(rows)
    ], style={
        "border": f"1px solid {_BORDER}",
        "borderRadius": "8px",
        "overflow": "hidden",
        "marginTop": "1.5rem",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
    })


# ── Callbacks ───────────────────────────────────────────────────

@dash.callback(
    Output("qualy-res-season-dropdown", "options"),
    Output("qualy-res-season-dropdown", "value"),
    Output("qualy-res-cache-warning", "children"),
    Input("qualy-res-page-trigger", "data"),
)
def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            return [], None, html.Div("Nenhum dado no cache.", className="alert alert-warning")
        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None, None
    except Exception as e:
        return [], None, html.Div(f"Erro: {e}", className="alert alert-error")


@dash.callback(
    Output("qualy-res-race-dropdown", "options"),
    Input("qualy-res-season-dropdown", "value"),
)
def update_races(season):
    if not season: return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("qualy-res-store", "data"),
    Output("qualy-res-session-store", "data"),
    Input("qualy-res-load-button", "n_clicks"),
    State("qualy-res-season-dropdown", "value"),
    State("qualy-res-race-dropdown", "value"),
    prevent_initial_call=True,
)
def handle_load(n_clicks, season, race):
    if not n_clicks or not season or not race:
        return dash.no_update, dash.no_update
    laps, _, session = client.load_race_session(season, race, preferred_session="Q")
    if laps.empty:
        return None, None
    return laps.to_json(date_format="iso", orient="split"), {
        "season": season,
        "race": race,
        "session_type": session.get("session_type")
    }


@dash.callback(
    Output("qualy-res-content", "children"),
    Input("qualy-res-store", "data"),
    State("qualy-res-session-store", "data"),
)
def update_table(laps_json, session_meta):
    return _build_qualy_results_table(laps_json, session_meta)
