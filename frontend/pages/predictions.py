"""Predictions page — machine learning race outcome predictions."""
import dash
import plotly.graph_objs as go
from dash import Input, Output, State, dcc, html

from frontend.api import client
from frontend.f1_config import get_driver_color
from frontend.utils import (
    MUTED as _MUTED,
    PRIMARY as _PRIMARY,
    BORDER as _BORDER,
    alert_cache_empty,
    alert_backend_error,
    seasons_to_options,
)

dash.register_page(__name__, path="/predictions", name="Predictions")

layout = html.Div([
    html.Div([
        html.H1("Predictions", className="page-title"),
        html.P(
            "Previsões de resultado de corrida via machine learning.",
            className="page-subtitle",
        ),
    ]),

    html.Div(id="pred-cache-warning"),

    # ── Filtros ──────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="pred-season-dropdown",
                options=[],
                placeholder="Selecione a temporada",
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter"),

        html.Div([
            html.Label("Corrida"),
            dcc.Dropdown(
                id="pred-race-dropdown",
                options=[],
                placeholder="Selecione a corrida",
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter"),

        html.Div([
            html.Button(
                "Prever corrida",
                id="pred-load-button",
                n_clicks=0,
                className="btn-primary",
            ),
        ], className="filter"),
    ], className="filters"),

    dcc.Store(id="pred-page-trigger", data={"loaded": True}),

    html.Div(id="predictions-content"),
])


# ── Callbacks ────────────────────────────────────────────────────

@dash.callback(
    Output("pred-season-dropdown", "options"),
    Output("pred-season-dropdown", "value"),
    Output("pred-cache-warning", "children"),
    Input("pred-page-trigger", "data"),
)
def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            return [], None, alert_cache_empty()
        return seasons_to_options(seasons), seasons[0], None
    except Exception:
        return [], None, alert_backend_error()


@dash.callback(
    Output("pred-race-dropdown", "options"),
    Input("pred-season-dropdown", "value"),
)
def update_races(season):
    if not season:
        return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("predictions-content", "children"),
    Input("pred-load-button", "n_clicks"),
    State("pred-season-dropdown", "value"),
    State("pred-race-dropdown", "value"),
    prevent_initial_call=True,
)
def load_predictions(n_clicks, season, event_name):
    if not season or not event_name:
        return html.Div(
            "Selecione a temporada e a corrida.",
            style={"color": _MUTED, "padding": "1rem"},
        )
    try:
        from ml.predict import generate_predictions
        df = generate_predictions(season=int(season), event_name=event_name)
    except FileNotFoundError:
        return _model_not_trained_message()
    except Exception as e:
        return html.Div(
            f"Erro ao carregar predições: {e}",
            style={"color": "#EF4444", "padding": "1rem"},
        )

    if df is None or df.empty:
        return _model_not_trained_message()

    return html.Div([
        html.Div(
            f"{event_name} · {season}",
            style={
                "fontWeight": "700",
                "fontSize": "1.1rem",
                "color": _PRIMARY,
                "marginBottom": "1.25rem",
                "marginTop": "1.5rem",
            },
        ),
        _render_metrics(df),
        _render_table(df, season),
        _render_chart(df, season),
    ])


# ── UI helpers ───────────────────────────────────────────────────

def _model_not_trained_message():
    return html.Div([
        html.Div([
            html.Div("Modelo não treinado", className="card-value"),
            html.Div([
                html.P("Execute o script de treinamento para gerar predições:"),
                html.Pre(
                    "python -m ml.train",
                    style={
                        "background": "#1E293B",
                        "padding": "0.75rem 1rem",
                        "borderRadius": "6px",
                        "fontFamily": "monospace",
                        "color": "#E2E8F0",
                        "marginTop": "0.5rem",
                    },
                ),
            ], className="card-desc"),
        ], className="card", style={"maxWidth": "480px"}),
    ])


_TH = {
    "fontWeight": "700",
    "fontSize": ".7rem",
    "color": _MUTED,
    "textTransform": "uppercase",
    "letterSpacing": ".04em",
}


def _render_metrics(df):
    import math, numpy as np

    valid = [
        (float(row["predicted_finish"]), float(row["real_position"]))
        for _, row in df.iterrows()
        if row.get("real_position") is not None
        and not (isinstance(row["real_position"], float) and math.isnan(row["real_position"]))
    ]

    if not valid:
        return html.Div()

    preds, reals = zip(*valid)
    errors       = [abs(round(p) - int(r)) for p, r in valid]
    mae          = np.mean(errors)
    exact        = sum(1 for e in errors if e == 0)
    within1      = sum(1 for e in errors if e <= 1)
    n            = len(valid)
    # podium: real ≤3 AND predicted ≤3
    podium_ok    = sum(1 for p, r in valid if int(r) <= 3 and round(p) <= 3)
    podium_total = sum(1 for _, r in valid if int(r) <= 3)

    def _card(value, label, sub=None, color=_PRIMARY):
        return html.Div([
            html.Div(str(value), style={
                "fontSize": "2rem", "fontWeight": "800",
                "color": color, "lineHeight": "1",
            }),
            html.Div(label, style={
                "fontSize": ".72rem", "fontWeight": "600",
                "color": _MUTED, "textTransform": "uppercase",
                "letterSpacing": ".05em", "marginTop": ".25rem",
            }),
            html.Div(sub, style={"fontSize": ".7rem", "color": _MUTED,
                                  "marginTop": ".15rem"}) if sub else None,
        ], style={
            "background": "#FFFFFF",
            "border": f"1px solid {_BORDER}",
            "borderRadius": "10px",
            "padding": "1rem 1.25rem",
            "flex": "1",
            "minWidth": "110px",
            "boxShadow": "0 1px 3px rgba(0,0,0,.06)",
        })

    mae_color  = "#22C55E" if mae < 2 else "#F59E0B" if mae < 4 else "#EF4444"
    acc_color  = "#22C55E" if exact / n >= 0.2 else "#F59E0B" if exact / n >= 0.1 else "#EF4444"

    return html.Div([
        html.Div(
            "Métricas do Modelo",
            style={"fontWeight": "700", "fontSize": ".78rem",
                   "textTransform": "uppercase", "letterSpacing": ".06em",
                   "color": _MUTED, "marginBottom": ".6rem"},
        ),
        html.Div([
            _card(f"{mae:.1f}",      "Erro Médio (MAE)",    "posições", mae_color),
            _card(f"{exact}/{n}",    "Acertos Exatos",       f"{exact/n:.0%} dos pilotos", acc_color),
            _card(f"{within1}/{n}",  "Erro ≤ 1 posição",    f"{within1/n:.0%} dos pilotos"),
            _card(
                f"{podium_ok}/{podium_total}" if podium_total else "—",
                "Pódio Previsto",
                "P1-P3 corretos" if podium_total else "sem dados",
                "#22C55E" if podium_total and podium_ok == podium_total else _PRIMARY,
            ),
        ], style={
            "display": "flex", "gap": ".75rem",
            "flexWrap": "wrap", "marginBottom": "1.75rem",
        }),
    ])


def _render_table(df, season):
    import math

    header = html.Div([
        html.Span("Pos Real",      style={**_TH, "flex": "1", "textAlign": "center"}),
        html.Span("Piloto",        style={**_TH, "flex": "1"}),
        html.Span("Pos. Prevista", style={**_TH, "flex": "1", "textAlign": "center"}),
        html.Span("Erro",          style={**_TH, "flex": "1", "textAlign": "center"}),
        html.Span("Prob. Pódio",   style={**_TH, "flex": "1", "textAlign": "center"}),
    ], style={
        "display": "flex",
        "alignItems": "center",
        "gap": "1rem",
        "padding": ".5rem .75rem",
        "borderBottom": f"1px solid {_BORDER}",
        "background": "#F9FAFB",
    })

    rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        rank     = i + 1
        drv_code = str(row.get("driver_code", row.get("driver_number", "?"))).strip()
        drv_num  = str(row.get("driver_number", ""))
        real     = row.get("real_position")
        pred     = float(row["predicted_finish"])
        pred_int = max(1, round(pred))
        prob     = float(row["podium_probability"])
        color    = get_driver_color(season, drv_code)
        bg       = "#F4F5F7" if rank % 2 == 0 else "#FFFFFF"
        prob_color = "#22C55E" if prob >= 0.20 else "#3B82F6" if prob >= 0.05 else _MUTED

        has_real     = real is not None and not (isinstance(real, float) and math.isnan(real))
        real_pos_str = f"P{int(real)}" if has_real else "—"
        err          = (pred_int - int(real)) if has_real else None

        # Pos. Prevista color
        if has_real:
            pred_color = "#22C55E" if err == 0 else _PRIMARY
        else:
            pred_color = _PRIMARY

        # Erro badge
        if err is None:
            err_text  = "—"
            err_color = _MUTED
        elif err == 0:
            err_text  = "✓"
            err_color = "#22C55E"
        else:
            err_text  = f"+{err}" if err > 0 else str(err)
            err_color = "#F59E0B" if abs(err) <= 2 else "#EF4444"

        rows.append(html.Div([
            html.Span(
                real_pos_str,
                style={"flex": "1", "textAlign": "center", "fontWeight": "800",
                       "color": _PRIMARY, "fontSize": ".9rem"},
            ),
            html.Div([
                html.Span(
                    drv_code if drv_code else drv_num,
                    style={"fontWeight": "700", "color": color,
                           "fontFamily": "monospace, Inter, Arial", "fontSize": ".9rem"},
                ),
                html.Span(
                    f" #{drv_num}",
                    style={"fontSize": ".72rem", "color": _MUTED},
                ) if drv_code and drv_code != drv_num else None,
            ], style={"flex": "1", "display": "flex",
                      "alignItems": "baseline", "gap": "2px"}),
            html.Span(
                f"P{pred_int}",
                style={"flex": "1", "textAlign": "center",
                       "fontFamily": "monospace",
                       "fontWeight": "700", "fontSize": ".9rem", "color": pred_color},
            ),
            html.Span(
                err_text,
                style={"flex": "1", "textAlign": "center",
                       "fontWeight": "700", "fontSize": ".85rem", "color": err_color},
            ),
            html.Span(
                f"{prob:.0%}",
                style={"flex": "1", "textAlign": "center",
                       "fontWeight": "600", "fontSize": ".85rem", "color": prob_color},
            ),
        ], style={
            "display": "flex", "alignItems": "center", "gap": "1rem",
            "padding": ".5rem .75rem",
            "borderBottom": f"1px solid {_BORDER}", "background": bg,
        }))

    return html.Div([
        html.Div(
            "Classificação Prevista",
            style={"fontWeight": "700", "fontSize": ".78rem",
                   "textTransform": "uppercase", "letterSpacing": ".06em",
                   "color": _MUTED, "marginBottom": ".6rem"},
        ),
        html.Div(
            [header] + rows,
            style={"border": f"1px solid {_BORDER}", "borderRadius": "8px",
                   "overflow": "hidden", "boxShadow": "0 1px 3px rgba(0,0,0,.08)",
                   "marginBottom": "2rem"},
        ),
    ])



def _render_chart(df, season):
    df_sorted = df.sort_values("predicted_finish")
    labels = [
        str(r.get("driver_code", r.get("driver_number", "?")))
        for _, r in df_sorted.iterrows()
    ]
    colors = [get_driver_color(season, lbl) for lbl in labels]

    fig = go.Figure(go.Bar(
        x=labels,
        y=[max(1, round(v)) for v in df_sorted["predicted_finish"]],
        marker_color=colors,
        text=[f"P{max(1, round(v))}" for v in df_sorted["predicted_finish"]],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis_title="Piloto",
        yaxis_title="Posição Prevista",
        yaxis={"autorange": "reversed"},
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font={"color": "#374151", "family": "Inter, Arial, sans-serif"},
        height=360,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis={"tickangle": -30},
    )

    return html.Div([
        html.Div(
            "Posições Previstas",
            style={"fontWeight": "700", "fontSize": ".78rem",
                   "textTransform": "uppercase", "letterSpacing": ".06em",
                   "color": _MUTED, "marginBottom": ".6rem"},
        ),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])
