"""Live page - Race session visualization"""
import io

import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import plotly.graph_objs as go

from frontend.api import client

dash.register_page(__name__, path="/live", name="Live")


def _filter_card(label, component):
    return html.Div([html.Label(label), component], className="filter")


layout = html.Div([
    html.Div([
        html.H1("Live", className="page-title"),
        html.P(
            "Carregue uma corrida e acompanhe a evolução de posições "
            "volta a volta.",
            className="page-subtitle",
        ),
    ]),

    # Info banner (subtle, no inline styles)
    html.Div([
        html.Span("ℹ", className="alert-icon"),
        html.Span(
            "Dados de telemetria GPS não estão no cache atual. "
            "A visualização de mapa de circuito está planejada para "
            "versões futuras."
        ),
    ], className="alert alert-info"),

    # ── Filters ────────────────────────────────────────────────
    html.Div([
        _filter_card(
            "Temporada",
            dcc.Dropdown(
                id="live-season",
                options=[],
                placeholder="Selecione a temporada",
            ),
        ),
        _filter_card(
            "Corrida",
            dcc.Dropdown(
                id="live-race",
                options=[],
                placeholder="Selecione a corrida",
            ),
        ),
        _filter_card(
            "Piloto",
            dcc.Dropdown(
                id="live-driver",
                options=[],
                placeholder="Selecione o piloto",
            ),
        ),
        html.Div([
            html.Button(
                "Carregar sessão",
                id="live-load",
                n_clicks=0,
                className="btn-primary",
            ),
        ], className="filter"),
    ], className="filters"),

    # Stores
    dcc.Store(id="live-laps-store", storage_type="session"),
    dcc.Store(id="live-page-load-trigger", data={"loaded": True}),

    # KPI row
    html.Div(id="live-info", className="kpi-row"),

    # Charts
    html.Div([
        dcc.Graph(id="live-position-chart"),
    ], className="charts"),
])


# ── Callbacks ──────────────────────────────────────────────────

@dash.callback(
    Output("live-season", "options"),
    Output("live-season", "value"),
    Input("live-page-load-trigger", "data")
)
def load_live_seasons(_):
    """Load available seasons."""
    try:
        seasons = client.get_available_seasons()
        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None
    except Exception as e:
        print(f"Error loading seasons: {e}")
        return [], None


@dash.callback(
    Output("live-race", "options"),
    Input("live-season", "value")
)
def update_live_races(season: int):
    """Load races for selected season."""
    if not season:
        return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("live-laps-store", "data"),
    Output("live-driver", "options"),
    Input("live-load", "n_clicks"),
    State("live-season", "value"),
    State("live-race", "value"),
    prevent_initial_call=True
)
def load_live_session(n_clicks: int, season: int, race: str):
    """Load session lap data."""
    if not n_clicks or not season or not race:
        return dash.no_update, dash.no_update

    try:
        laps, _, session = client.load_race_session(season, race)

        if laps.empty:
            return None, []

        drivers = (
            sorted(laps["Driver"].unique().tolist())
            if "Driver" in laps.columns else []
        )
        driver_options = [{"label": d, "value": d} for d in drivers]
        laps_json = laps.to_json(date_format="iso", orient="split")
        return laps_json, driver_options

    except Exception as e:
        print(f"Error loading live session: {e}")
        return None, []


@dash.callback(
    Output("live-info", "children"),
    Output("live-position-chart", "figure"),
    Input("live-driver", "value"),
    State("live-laps-store", "data"),
)
def update_live_view(driver: str, laps_json: str):
    """Update live view based on selected driver."""
    empty_fig = {
        "data": [],
        "layout": {
            "title": "Nenhum dado carregado",
            "template": "plotly_white",
        },
    }

    if not laps_json:
        return [], empty_fig

    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")

        total_laps = (
            int(laps["LapNumber"].max())
            if "LapNumber" in laps.columns else "—"
        )
        total_drivers = (
            len(laps["Driver"].unique()) if "Driver" in laps.columns else "—"
        )

        def kpi(label, value):
            return html.Div([
                html.Div(label, className="kpi-label"),
                html.Div(str(value), className="kpi-value"),
            ], className="kpi")

        kpis = [
            kpi("Total de Voltas", total_laps),
            kpi("Pilotos", total_drivers),
        ]

        fig = go.Figure()

        if driver and "Position" in laps.columns:
            driver_laps = laps[laps["Driver"] == driver]
            fig.add_trace(go.Scatter(
                x=driver_laps["LapNumber"],
                y=driver_laps["Position"],
                mode="lines+markers",
                name=driver,
                line=dict(width=3, color="#003082"),
                marker=dict(size=5),
            ))
            fig.update_yaxes(autorange="reversed")

        fig.update_layout(
            title=(
                f"Posição na corrida — {driver}"
                if driver else "Selecione um piloto"
            ),
            xaxis_title="Volta",
            yaxis_title="Posição",
            template="plotly_white",
            height=420,
        )

        return kpis, fig

    except Exception as e:
        print(f"Error updating live view: {e}")
        return [], empty_fig
