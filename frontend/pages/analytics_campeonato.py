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
    dcc.Store(id="camp-laps-store", storage_type="session"),
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
    Output("camp-laps-store", "data"),
    Input("camp-load-button", "n_clicks"),
    State("camp-season-dropdown", "value"),
    prevent_initial_call=True,
)
def load_data(n_clicks, season):
    if not n_clicks or not season:
        return dash.no_update, dash.no_update

    try:
        races = client.get_races_for_season(season)
        results_rows = []
        laps_rows = []
        for race in races:
            results = client.get_race_results(season, race)
            if not results.empty:
                results = results.copy()
                results["Race"] = race
                results_rows.append(results)

            laps, _, _ = client.load_race_session(season, race)
            if laps is not None and not laps.empty:
                laps = laps.copy()
                laps["Race"] = race
                laps_rows.append(laps)

        if not results_rows and not laps_rows:
            return None, None

        results_df = pd.concat(results_rows, ignore_index=True) if results_rows else pd.DataFrame()
        if not results_df.empty:
            results_df["points"] = pd.to_numeric(results_df["points"], errors="coerce").fillna(0)

        laps_df = pd.concat(laps_rows, ignore_index=True) if laps_rows else pd.DataFrame()

        return (
            results_df.to_json(date_format="iso", orient="split") if not results_df.empty else None,
            laps_df.to_json(date_format="iso", orient="split") if not laps_df.empty else None,
        )
    except Exception as e:
        print(f"Error loading championship data: {e}")
        return None, None


def _fmt_lap(seconds):
    try:
        m, s = divmod(float(seconds), 60)
        return f"{int(m)}:{s:05.2f}"
    except Exception:
        return "—"


def _compute_figs(results_json, laps_json, season):
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
        marker_color=color_list_for_drivers(season, driver_pts["driver_code"].tolist()),
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
    leader_driver = driver_pts.iloc[0] if not driver_pts.empty else {"driver_code": "—", "points": 0}
    leader_team = team_pts.iloc[0] if not team_pts.empty else {"team": "—"}

    def kpi(label, value):
        return html.Div([
            html.Div(label, className="kpi-label"),
            html.Div(str(value), className="kpi-value"),
        ], className="kpi")

    kpis = [
        kpi("Líder (Pilotos)", leader_driver["driver_code"]),
        kpi("Pontos", int(leader_driver["points"]) if "points" in leader_driver else 0),
        kpi("Líder (Construtores)", leader_team["team"] if "team" in leader_team else "—"),
        kpi("Corridas", df["Race"].nunique()),
    ]

    return fig_drivers, fig_teams, fig_prog, kpis


def _build_stats_panel(results_json, laps_json, season):
    if not results_json and not laps_json:
        return html.Div(
            "Carregue dados do campeonato para ver os KPIs e classificação.",
            style={"color": "#6B7280", "padding": "2rem", "fontSize": ".95rem"},
        )

    try:
        results_df = pd.read_json(io.StringIO(results_json), orient="split") if results_json else pd.DataFrame()
        laps_df = pd.read_json(io.StringIO(laps_json), orient="split") if laps_json else pd.DataFrame()

        # KPIs (reuse compute)
        _, _, _, kpis = _compute_figs(results_json, laps_json, season)

        # Build standings: aggregate by driver
        standings = []
        if not results_df.empty:
            driver_pts = (
                results_df.groupby("driver_code")["points"].sum().reset_index()
            )
            # start from points ordering
            driver_pts = driver_pts.sort_values("points", ascending=False)

            # compute total time and best lap from laps_df if available
            total_time = {}
            best_lap = {}
            fastest_indicator = {}
            if not laps_df.empty and "LapTimeSeconds" in laps_df.columns:
                # total time per driver (sum of lap times across all races)
                grp = laps_df.groupby("Driver")["LapTimeSeconds"]
                total_time = grp.sum().to_dict()
                best_lap = grp.min().to_dict()

                # fastest lap per race -> mark driver if they have the min lap in any race
                fastest_indicator = {}
                for race, sub in laps_df.groupby("Race"):
                    valid = sub[sub["LapTimeSeconds"].notna()]
                    if valid.empty:
                        continue
                    min_t = valid["LapTimeSeconds"].min()
                    drivers = valid[valid["LapTimeSeconds"] == min_t]["Driver"].unique()
                    for d in drivers:
                        fastest_indicator[d] = True

            # Build rows
            for idx, row in driver_pts.iterrows():
                drv = row["driver_code"]
                pts = int(row["points"])
                team = ""
                # try to find team from results_df
                t = results_df[results_df["driver_code"] == drv]["team"].dropna()
                if not t.empty:
                    team = str(t.iloc[0])

                total = total_time.get(drv) or total_time.get(drv.upper()) or None
                best = best_lap.get(drv) or best_lap.get(drv.upper()) or None
                fastest = bool(fastest_indicator.get(drv) or fastest_indicator.get(drv.upper()))

                standings.append(html.Div([
                    html.Span(f"{pts} pts", style={"minWidth": "56px", "fontWeight": "700"}),
                    html.Span(drv, style={"fontWeight": "700", "minWidth": "54px", "color": color_list_for_drivers(season, [drv])[0]}),
                    html.Span(team, style={"color": "#6B7280", "flex": "1"}),
                    html.Span(_fmt_lap(total) if total else "—", style={"minWidth": "86px", "textAlign": "right"}),
                    html.Span(_fmt_lap(best) if best else "—", style={"minWidth": "74px", "textAlign": "right"}),
                    html.Span("★" if fastest else "", style={"color": "#F59E0B", "minWidth": "28px", "textAlign": "center"}),
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "1rem",
                    "padding": ".42rem .75rem",
                    "borderBottom": "1px solid #DDE1E7",
                }))

        standings_block = html.Div([
            html.Div("Classificação Final", style={"fontWeight": "700", "fontSize": ".78rem", "textTransform": "uppercase", "letterSpacing": ".06em", "color": "#6B7280", "marginBottom": ".6rem"}),
            html.Div(standings or html.Div("Dados não disponíveis.", style={"color": "#6B7280", "padding": ".5rem"}), style={"border": "1px solid #DDE1E7", "borderRadius": "8px", "overflow": "hidden"}),
        ])

        return html.Div([html.Div(kpis, style={"marginBottom": "1rem"}), standings_block], style={"padding": ".25rem 0"})

    except Exception as e:
        print(f"Error building championship stats panel: {e}")
        return html.Div("Erro ao montar painel.", style={"color": "#6B7280", "padding": "1rem"})


@dash.callback(
    Output("camp-chart-area-content", "children"),
    Input("camp-data-store", "data"),
    Input("camp-laps-store", "data"),
    Input("camp-chart-selector", "value"),
    State("camp-season-dropdown", "value"),
)
def update_content(results_json, laps_json, chart_type, season):
    # Big numbers / classification
    if chart_type == "big-numbers":
        return _build_stats_panel(results_json, laps_json, season)

    # Otherwise build graphs on demand
    fig_drivers, fig_teams, fig_prog, _ = _compute_figs(results_json, laps_json, season)

    empty_fig = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if chart_type == "drivers":
        return dcc.Graph(figure=(fig_drivers or empty_fig), config={"staticPlot": True})
    if chart_type == "teams":
        return dcc.Graph(figure=(fig_teams or empty_fig), config={"staticPlot": True})
    if chart_type == "progression":
        return dcc.Graph(figure=(fig_prog or empty_fig), config={"staticPlot": True})

    return html.Div()
