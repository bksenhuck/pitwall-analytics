"""Analytics › Telemetria — desempenho individual por sessão."""
import io

import dash
from dash import html, dcc, Input, Output, State
import pandas as pd

from frontend.components.navigation import create_analytics_subnav
from frontend.components.charts import _base_layout
from frontend.f1_config import color_list_for_drivers
from frontend.api import client

dash.register_page(__name__, path="/analytics/telemetria", name="Telemetria")

_SESSION_OPTIONS = [
    {"label": "Corrida (R)",            "value": "R"},
    {"label": "Qualificação (Q)",       "value": "Q"},
    {"label": "Treino Livre 1 (FP1)",   "value": "FP1"},
    {"label": "Treino Livre 2 (FP2)",   "value": "FP2"},
    {"label": "Treino Livre 3 (FP3)",   "value": "FP3"},
    {"label": "Sprint (S)",             "value": "S"},
    {"label": "Sprint Qualifying (SQ)", "value": "SQ"},
]

layout = html.Div([
    html.Div([
        html.H1("Analytics · Telemetria", className="page-title"),
        html.P(
            "Desempenho individual por sessão ao longo da temporada.",
            className="page-subtitle",
        ),
    ]),

    create_analytics_subnav("/analytics/telemetria"),

    html.Div(id="tele-warning"),

    # ── Filtros ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="tele-season-dropdown",
                options=[],
                placeholder="Selecione a temporada",
            ),
        ], className="filter"),

        html.Div([
            html.Label("Corrida"),
            dcc.Dropdown(
                id="tele-race-dropdown",
                options=[],
                placeholder="Todas as corridas",
                clearable=True,
            ),
        ], className="filter"),

        html.Div([
            html.Label("Tipo de Sessão"),
            dcc.Dropdown(
                id="tele-session-type-dropdown",
                options=_SESSION_OPTIONS,
                value="R",
                clearable=False,
            ),
        ], className="filter"),

        html.Div([
            html.Label("Piloto(s)"),
            dcc.Dropdown(
                id="tele-driver-dropdown",
                options=[],
                placeholder="Todos os pilotos",
                multi=True,
            ),
        ], className="filter"),

        html.Div([
            html.Button(
                "Carregar",
                id="tele-load-button",
                n_clicks=0,
                className="btn-primary",
            ),
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
    Output("tele-race-dropdown", "options"),
    Output("tele-race-dropdown", "value"),
    Input("tele-season-dropdown", "value"),
)
def load_races(season):
    if not season:
        return [], None
    try:
        races = client.get_races_for_season(season)
        return [{"label": r, "value": r} for r in races], None
    except Exception:
        return [], None


@dash.callback(
    Output("tele-driver-dropdown", "options"),
    Output("tele-driver-dropdown", "value"),
    Input("tele-season-dropdown", "value"),
    Input("tele-race-dropdown", "value"),
    Input("tele-session-type-dropdown", "value"),
)
def load_drivers(season, race, session_type):
    """Populate driver list from the selected event (or first available)."""
    if not season or not session_type:
        return [], None
    try:
        races = [race] if race else (client.get_races_for_season(season) or [])
        for r in races:
            laps, _, _ = client.load_session(season, r, session_type)
            if not laps.empty and "Driver" in laps.columns:
                drivers = sorted(laps["Driver"].dropna().unique().tolist())
                return [{"label": d, "value": d} for d in drivers], None
        return [], None
    except Exception:
        return [], None


@dash.callback(
    Output("tele-results-store", "data"),
    Input("tele-load-button", "n_clicks"),
    State("tele-season-dropdown", "value"),
    State("tele-race-dropdown", "value"),
    State("tele-session-type-dropdown", "value"),
    State("tele-driver-dropdown", "value"),
    prevent_initial_call=True,
)
def load_data(n_clicks, season, race, session_type, drivers):
    if not n_clicks or not season or not session_type:
        return dash.no_update

    try:
        # If a specific race is selected, load only that one;
        # otherwise load all races for the season.
        races = [race] if race else (client.get_races_for_season(season) or [])
        rows = []
        for r in races:
            laps, _, _ = client.load_session(season, r, session_type)
            if laps.empty or "Driver" not in laps.columns:
                continue
            sel = laps[laps["Driver"].isin(drivers)] if drivers else laps
            if "LapTimeSeconds" not in sel.columns:
                continue
            best = (
                sel.groupby("Driver")["LapTimeSeconds"]
                .min()
                .reset_index()
            )
            best["Race"] = r
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
    State("tele-session-type-dropdown", "value"),
)
def update_charts(data_json, drivers, season, session_type):
    import plotly.graph_objs as go

    empty_fig = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if not data_json:
        return empty_fig, empty_fig

    try:
        df = pd.read_json(io.StringIO(data_json), orient="split")
        all_drivers = df["Driver"].unique().tolist()
        session_label = next(
            (o["label"] for o in _SESSION_OPTIONS if o["value"] == session_type),
            session_type,
        )

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
            f"Melhor Volta por Evento — {session_label} (s)",
            xaxis_title="Evento",
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
            f"Média de Melhor Volta — {session_label} (s)",
            xaxis_title="Piloto",
            yaxis_title="Tempo médio (s)",
            showlegend=False,
        ))

        return fig_best, fig_avg

    except Exception as e:
        print(f"Error updating telemetry charts: {e}")
        return empty_fig, empty_fig
