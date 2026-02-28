"""Analytics › Telemetria — desempenho individual ao longo da temporada."""
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import io

from frontend.components.navigation import create_analytics_subnav
from frontend.components.charts import _base_layout, PITWALL_COLORS
from frontend.f1_config import color_list_for_drivers
from frontend.api import client

dash.register_page(__name__, path="/analytics/telemetria", name="Telemetria")

layout = html.Div([
    html.Div([
        html.H1("Analytics · Telemetria", className="page-title"),
        html.P("Desempenho individual ao longo da temporada.", className="page-subtitle"),
    ]),

    create_analytics_subnav("/analytics/telemetria"),

    html.Div(id="tele-warning"),

    # ── Filtros ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(id="tele-season-dropdown", options=[], placeholder="Selecione a temporada"),
        ], className="filter"),

        html.Div([
            html.Label("Piloto"),
            dcc.Dropdown(id="tele-driver-dropdown", options=[], placeholder="Selecione o piloto",
                         multi=True),
        ], className="filter"),

        html.Div([
            html.Button("Carregar", id="tele-load-button", n_clicks=0, className="btn-primary"),
        ], className="filter"),
    ], className="filters"),

    dcc.Store(id="tele-results-store", storage_type="session"),
    dcc.Store(id="tele-page-trigger", data={"loaded": True}),

    html.Div(id="tele-kpi-row", className="kpi-row"),

    html.Div([
        dcc.Graph(id="tele-points-graph"),
        dcc.Graph(id="tele-positions-graph"),
    ], className="charts"),
])


# ── Callbacks ───────────────────────────────────────────────────

@dash.callback(
    Output("tele-season-dropdown", "options"),
    Output("tele-season-dropdown", "value"),
    Output("tele-warning", "children"),
    Input("tele-page-trigger", "data"),
)
def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            return [], None, html.Div([
                html.Span("⚠", className="alert-icon"),
                html.Strong("Nenhum dado no cache SQLite."),
            ], className="alert alert-warning")
        return [{"label": str(s), "value": s} for s in seasons], seasons[0], None
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [], None, html.Div([
            html.Span("✕", className="alert-icon"),
            html.Strong("Não foi possível conectar ao backend."),
        ], className="alert alert-error")


@dash.callback(
    Output("tele-driver-dropdown", "options"),
    Input("tele-season-dropdown", "value"),
)
def load_drivers(season):
    if not season:
        return []
    try:
        races = client.get_races_for_season(season)
        if not races:
            return []
        laps, _, _ = client.load_race_session(season, races[0])
        if laps.empty or "Driver" not in laps.columns:
            return []
        drivers = sorted(laps["Driver"].unique().tolist())
        return [{"label": d, "value": d} for d in drivers]
    except Exception:
        return []


@dash.callback(
    Output("tele-results-store", "data"),
    Input("tele-load-button", "n_clicks"),
    State("tele-season-dropdown", "value"),
    State("tele-driver-dropdown", "value"),
    prevent_initial_call=True,
)
def load_data(n_clicks, season, drivers):
    if not n_clicks or not season:
        return dash.no_update

    try:
        races = client.get_races_for_season(season)
        rows = []
        for race in races:
            laps, _, _ = client.load_race_session(season, race)
            if laps.empty:
                continue
            sel = laps[laps["Driver"].isin(drivers)] if drivers else laps
            if "LapTimeSeconds" in sel.columns and "Driver" in sel.columns:
                best = sel.groupby("Driver")["LapTimeSeconds"].min().reset_index()
                best["Race"] = race
                rows.append(best)

        if not rows:
            return None

        df = pd.concat(rows, ignore_index=True)
        return df.to_json(date_format="iso", orient="split")
    except Exception as e:
        print(f"Error loading telemetry data: {e}")
        return None


@dash.callback(
    Output("tele-points-graph", "figure"),
    Output("tele-positions-graph", "figure"),
    Input("tele-results-store", "data"),
    State("tele-driver-dropdown", "value"),
    State("tele-season-dropdown", "value"),
)
def update_charts(data_json, drivers, season):
    import plotly.graph_objs as go
    empty_fig = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if not data_json:
        return empty_fig, empty_fig

    try:
        df = pd.read_json(io.StringIO(data_json), orient="split")
        all_drivers = df["Driver"].unique().tolist()

        fig_best = go.Figure()
        for drv in all_drivers:
            sub = df[df["Driver"] == drv]
            color = color_list_for_drivers(season, [drv])[0]
            fig_best.add_trace(go.Scatter(
                x=sub["Race"],
                y=sub["LapTimeSeconds"],
                mode="lines+markers",
                name=drv,
                line=dict(color=color, width=2),
                marker=dict(size=6),
            ))
        fig_best.update_layout(**_base_layout(
            "Melhor Volta por Corrida (s)",
            xaxis_title="Corrida",
            yaxis_title="Tempo (s)",
        ))

        avg = (
            df.groupby("Driver")["LapTimeSeconds"]
            .mean()
            .reset_index()
            .sort_values("LapTimeSeconds")
        )
        fig_avg = go.Figure(go.Bar(
            x=avg["Driver"],
            y=avg["LapTimeSeconds"],
            marker_color=color_list_for_drivers(
                season, avg["Driver"].tolist()
            ),
        ))
        fig_avg.update_layout(**_base_layout(
            "Média de Melhor Volta na Temporada (s)",
            xaxis_title="Piloto",
            yaxis_title="Tempo médio (s)",
            showlegend=False,
        ))

        return fig_best, fig_avg
    except Exception as e:
        print(f"Error updating telemetry charts: {e}")
        return empty_fig, empty_fig
