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
    dcc.Store(id="camp-selected-driver"),

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

        html.Div([
            html.Div(id="camp-chart-area-content"),
            dcc.Graph(
                id="camp-progression-graph",
                figure={},
                style={"display": "none"},
                config={"displayModeBar": False, "scrollZoom": False},
            ),
        ], className="chart-area"),
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
        text=driver_pts["points"].astype(int),
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=11, family="Inter, Arial, sans-serif"),
        marker_color=color_list_for_drivers(
            season, driver_pts["driver_code"].tolist()
        ),
    ))
    fig_drivers.update_layout(**_base_layout(
        "Campeonato de Pilotos — Pontos na Temporada",
        xaxis_title="Piloto",
        yaxis_title="Pontos",
        showlegend=False,
        yaxis=dict(autorange=True),
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
        text=team_pts["points"].astype(int),
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=11, family="Inter, Arial, sans-serif"),
        marker_color=color_list_for_teams(team_pts["team"].tolist()),
    ))
    fig_teams.update_layout(**_base_layout(
        "Campeonato de Construtores — Pontos na Temporada",
        xaxis_title="Equipe",
        yaxis_title="Pontos",
        showlegend=False,
        yaxis=dict(autorange=True),
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

    return fig_drivers, fig_teams, kpis


def _build_progression_fig(results_json, season, selected_driver=None):
    import plotly.graph_objs as go

    empty = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if not results_json:
        return empty

    df = pd.read_json(io.StringIO(results_json), orient="split")

    driver_pts = (
        df.groupby("driver_code")["points"]
        .sum()
        .reset_index()
        .sort_values("points", ascending=False)
    )
    top10 = driver_pts["driver_code"].head(10).tolist()

    df = df.sort_values("Race")
    df["CumPoints"] = df.groupby("driver_code")["points"].cumsum()

    fig = go.Figure()
    for drv in top10:
        sub = df[df["driver_code"] == drv]
        color = color_list_for_drivers(season, [drv])[0]
        is_active = selected_driver is None or drv == selected_driver
        fig.add_trace(go.Scatter(
            x=sub["Race"],
            y=sub["CumPoints"],
            mode="lines+markers",
            name=drv,
            customdata=[[drv]] * len(sub),
            line=dict(color=color, width=2.5 if is_active else 1.0),
            marker=dict(size=7 if is_active else 4, color=color),
            opacity=1.0 if is_active else 0.1,
            hovertemplate="<b>%{customdata[0]}</b><br>Corrida: %{x}<br>Pontos: %{y}<extra></extra>",
        ))

    layout = _base_layout(
        "Progressão de Pontos — Top 10 Pilotos",
        xaxis_title="Corrida",
        yaxis_title="Pontos acumulados",
        hovermode="closest",
    )
    if selected_driver:
        layout["annotations"][0]["text"] = (
            f"<b>Progressão de Pontos</b>"
            f"  <span style='font-size:11px;color:#6B7280'>"
            f"— {selected_driver} em destaque · clique novamente para resetar"
            f"</span>"
        )
    else:
        layout["annotations"][0]["text"] = (
            "<b>Progressão de Pontos — Top 10 Pilotos</b>"
            "  <span style='font-size:11px;color:#6B7280'>clique em uma linha para destacar</span>"
        )
    fig.update_layout(**layout)
    return fig


@dash.callback(
    Output("camp-data-store", "data", allow_duplicate=True),
    Output("camp-selected-driver", "data", allow_duplicate=True),
    Input("camp-load-button", "n_clicks"),
    State("camp-season-dropdown", "value"),
    prevent_initial_call=True,
)
def reset_selected_on_load(n_clicks, season):
    # Delega o carregamento ao callback original; aqui só reseta o driver
    return dash.no_update, None


@dash.callback(
    Output("camp-chart-area-content", "children"),
    Output("camp-chart-area-content", "style"),
    Output("camp-progression-graph", "style"),
    Input("camp-data-store", "data"),
    Input("camp-chart-selector", "value"),
    State("camp-season-dropdown", "value"),
)
def update_content(results_json, chart_type, season):
    SHOW = {"display": "block"}
    HIDE = {"display": "none"}
    empty_fig = {"data": [], "layout": _base_layout("Nenhum dado carregado")}

    if chart_type == "progression":
        return None, HIDE, SHOW

    fig_drivers, fig_teams, _ = _compute_figs(results_json, season)

    if chart_type == "drivers":
        return dcc.Graph(figure=(fig_drivers or empty_fig), config={"staticPlot": True}), SHOW, HIDE
    if chart_type == "teams":
        return dcc.Graph(figure=(fig_teams or empty_fig), config={"staticPlot": True}), SHOW, HIDE

    return html.Div(), SHOW, HIDE


@dash.callback(
    Output("camp-progression-graph", "figure"),
    Input("camp-data-store", "data"),
    Input("camp-selected-driver", "data"),
    State("camp-season-dropdown", "value"),
    State("camp-chart-selector", "value"),
)
def update_progression_figure(results_json, selected_driver, season, chart_type):
    if chart_type != "progression":
        return dash.no_update
    return _build_progression_fig(results_json, season, selected_driver)


@dash.callback(
    Output("camp-selected-driver", "data"),
    Input("camp-progression-graph", "clickData"),
    State("camp-selected-driver", "data"),
    prevent_initial_call=True,
)
def handle_camp_driver_click(click_data, current_driver):
    if not click_data or not click_data.get("points"):
        return None
    try:
        driver = click_data["points"][0]["customdata"][0]
        return None if driver == current_driver else driver
    except (KeyError, IndexError, TypeError):
        return None
