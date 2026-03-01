"""Analytics › Campeonato — tabela e progressão de pontos."""
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import io

from frontend.components.navigation import create_analytics_subnav
from frontend.components.charts import _base_layout
from frontend.f1_config import color_list_for_drivers, color_list_for_teams
from frontend.api import client

dash.register_page(__name__, path="/analytics/campeonato", name="Campeonato")


layout = html.Div([
    html.Div([
        html.H1("Analytics · Campeonato", className="page-title"),
        html.P(
            "Tabela de pontos e progressão do campeonato.",
            className="page-subtitle",
        ),
    ]),

    create_analytics_subnav("/analytics/campeonato"),

    html.Div(id="camp-warning"),

    # ── Filtros ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="camp-season-dropdown",
                options=[],
                placeholder="Selecione a temporada",
            ),
        ], className="filter"),

        html.Div([
            html.Button(
                "Carregar",
                id="camp-load-button",
                n_clicks=0,
                className="btn-primary",
            ),
        ], className="filter"),
    ], className="filters"),

    dcc.Store(id="camp-data-store", storage_type="session"),
    dcc.Store(id="camp-page-trigger", data={"loaded": True}),

    html.Div(id="camp-kpi-row", className="kpi-row"),

    # Chart workspace: sidebar (visualizações) + chart area
    html.Div([
        html.Div([
            html.Div("Visualizações", className="chart-sidebar-title"),
            dcc.RadioItems(
                id="camp-chart-selector",
                options=[
                    {"label": "Pontos por Piloto", "value": "drivers"},
                    {"label": "Pontos por Equipe", "value": "teams"},
                    {"label": "Progressão", "value": "progression"},
                ],
                value="drivers",
                className="chart-nav",
                labelClassName="chart-nav-item",
                inputClassName="chart-nav-radio",
            ),
        ], className="chart-sidebar"),

        html.Div(id="camp-chart-area-content", className="chart-area"),
    ], className="chart-workspace"),
])


# ── Callbacks ───────────────────────────────────────────────────


@dash.callback(
    Output("camp-season-dropdown", "options"),
    Output("camp-season-dropdown", "value"),
    Output("camp-warning", "children"),
    Input("camp-page-trigger", "data"),
)
def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            return [], None, html.Div([
                html.Span("⚠", className="alert-icon"),
                html.Strong("Nenhum dado no cache SQLite."),
            ], className="alert alert-warning")
        return (
            [{"label": str(s), "value": s} for s in seasons],
            seasons[0],
            None,
        )
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [], None, html.Div([
            html.Span("✕", className="alert-icon"),
            html.Strong("Não foi possível conectar ao backend."),
        ], className="alert alert-error")


@dash.callback(
    Output("camp-data-store", "data"),
    Input("camp-load-button", "n_clicks"),
    State("camp-season-dropdown", "value"),
    prevent_initial_call=True,
)
def load_data(n_clicks, season):
    if not n_clicks or not season:
        return dash.no_update

    try:
        races = client.get_races_for_season(season)
        results_rows = []
        for race in races:
            results = client.get_race_results(season, race)
            if not results.empty:
                results = results.copy()
                results["Race"] = race
                results_rows.append(results)

        if not results_rows:
            return None

        results_df = pd.concat(results_rows, ignore_index=True)
        results_df["points"] = (
            pd.to_numeric(results_df["points"], errors="coerce").fillna(0)
        )
        return results_df.to_json(date_format="iso", orient="split")
    except Exception as e:
        print(f"Error loading championship data: {e}")
        return None


def _compute_figs(results_json, season):
    import plotly.graph_objs as go

    empty = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if not results_json:
        return empty, empty, empty, []

    df = pd.read_json(io.StringIO(results_json), orient="split")

    # driver points
    driver_pts = (
        df.groupby("driver_code")["points"]
        .sum()
        .reset_index()
        .sort_values("points", ascending=False)
    )
    fig_drivers = go.Figure(go.Bar(
        x=driver_pts["driver_code"],
        y=driver_pts["points"],
        marker_color=color_list_for_drivers(
            season, driver_pts["driver_code"].tolist()
        ),
    ))
    fig_drivers.update_layout(**_base_layout(
        "Campeonato de Pilotos — Pontos na Temporada",
        xaxis_title="Piloto",
        yaxis_title="Pontos",
        showlegend=False,
    ))

    # team points
    team_pts = (
        df.groupby("team")["points"]
        .sum()
        .reset_index()
        .sort_values("points", ascending=False)
    )
    fig_teams = go.Figure(go.Bar(
        x=team_pts["team"],
        y=team_pts["points"],
        marker_color=color_list_for_teams(team_pts["team"].tolist()),
    ))
    fig_teams.update_layout(**_base_layout(
        "Campeonato de Construtores — Pontos na Temporada",
        xaxis_title="Equipe",
        yaxis_title="Pontos",
        showlegend=False,
    ))

    # progression
    df = df.sort_values("Race")
    df["CumPoints"] = df.groupby("driver_code")["points"].cumsum()
    top10 = driver_pts["driver_code"].head(10).tolist()
    fig_prog = go.Figure()
    for drv in top10:
        sub = df[df["driver_code"] == drv]
        color = color_list_for_drivers(season, [drv])[0]
        fig_prog.add_trace(go.Scatter(
            x=sub["Race"],
            y=sub["CumPoints"],
            mode="lines+markers",
            name=drv,
            line=dict(color=color, width=2),
            marker=dict(size=6),
        ))
    fig_prog.update_layout(**_base_layout(
        "Progressão de Pontos — Top 10 Pilotos",
        xaxis_title="Corrida",
        yaxis_title="Pontos acumulados",
    ))

    # KPIs
    leader_driver = (
        driver_pts.iloc[0]
        if not driver_pts.empty
        else {"driver_code": "—", "points": 0}
    )
    leader_team = (
        team_pts.iloc[0] if not team_pts.empty else {"team": "—"}
    )

    def kpi(label, value):
        return html.Div([
            html.Div(label, className="kpi-label"),
            html.Div(str(value), className="kpi-value"),
        ], className="kpi")

    kpis = [
        kpi("Líder (Pilotos)", leader_driver["driver_code"]),
        kpi(
            "Pontos",
            int(leader_driver["points"]) if "points" in leader_driver else 0,
        ),
        kpi(
            "Líder (Construtores)",
            leader_team["team"] if "team" in leader_team else "—",
        ),
        kpi("Corridas", df["Race"].nunique()),
    ]

    return fig_drivers, fig_teams, fig_prog, kpis


@dash.callback(
    Output("camp-chart-area-content", "children"),
    Input("camp-data-store", "data"),
    Input("camp-chart-selector", "value"),
    State("camp-season-dropdown", "value"),
)
def update_content(results_json, chart_type, season):
    fig_drivers, fig_teams, fig_prog, _ = _compute_figs(results_json, season)

    empty_fig = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if chart_type == "drivers":
        return dcc.Graph(
            figure=(fig_drivers or empty_fig), config={"staticPlot": True}
        )
    if chart_type == "teams":
        return dcc.Graph(
            figure=(fig_teams or empty_fig), config={"staticPlot": True}
        )
    if chart_type == "progression":
        return dcc.Graph(
            figure=(fig_prog or empty_fig), config={"staticPlot": True}
        )

    return html.Div()
