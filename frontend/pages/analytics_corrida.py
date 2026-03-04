"""Analytics › Corrida — tempos de volta, posições e telemetria."""
import io
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
from frontend.components.charts import (
    lap_time_beeswarm_chart,
    race_position_chart,
    rule_107_chart,
    qualifying_elimination_chart,
    _base_layout,
)
from frontend.components.navigation import create_analytics_subnav
from frontend.f1_config import get_driver_color, get_team_color
from frontend.api import client

dash.register_page(__name__, path="/analytics/corrida", name="Corrida")

_MUTED = "#6B7280"
_PRIMARY = "#003082"
_BORDER = "#DDE1E7"
_SURFACE = "#F4F5F7"

layout = html.Div([
    html.Div([
        html.H1("Analytics · Corrida", className="page-title"),
        html.P(
            "Tempos de volta e evolução de posições da corrida.",
            className="page-subtitle",
        ),
    ]),

    create_analytics_subnav("/analytics/corrida"),

    html.Div(id="corrida-cache-warning"),

    # ── Filtros ─────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Temporada"),
            dcc.Dropdown(
                id="corrida-season-dropdown",
                options=[],
                placeholder="Selecione a temporada",
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter"),

        html.Div([
            html.Label("Corrida"),
            dcc.Dropdown(
                id="corrida-race-dropdown",
                options=[],
                placeholder="Selecione a corrida",
                persistence=True,
                persistence_type="session",
            ),
        ], className="filter"),

        html.Div([
            html.Button(
                "Carregar corrida",
                id="corrida-load-button",
                n_clicks=0,
                className="btn-primary",
            ),
        ], className="filter"),
    ], className="filters"),

    dcc.Store(id="corrida-laps-store", storage_type="session"),
    dcc.Store(id="corrida-session-store", storage_type="session"),
    dcc.Store(id="corrida-page-trigger", data={"loaded": True}),
    dcc.Store(id="corrida-selected-driver"),

    # ── Chart workspace ──────────────────────────────────────────
    html.Div([
        # Sidebar
        html.Div([
            html.Div("Visualizações", className="chart-sidebar-title"),
            
            html.Div("Corrida", style={"fontWeight": "bold", "fontSize": "0.85rem", "color": _MUTED, "marginTop": "1rem", "padding": "0 1rem"}),
            dcc.RadioItems(
                id="corrida-chart-selector",
                options=[
                    {"label": "Resultados", "value": "big-numbers"},
                    {"label": "Tempos por Equipe", "value": "beeswarm"},
                    {"label": "Evolução de Posições", "value": "positions"},
                ],
                value="big-numbers",
                className="chart-nav",
                labelClassName="chart-nav-item",
                inputClassName="chart-nav-radio",
            ),

            html.Div("Qualificação", style={"fontWeight": "bold", "fontSize": "0.85rem", "color": _MUTED, "marginTop": "1.5rem", "padding": "0 1rem"}),
            dcc.RadioItems(
                id="qualificacao-chart-selector",
                options=[
                    {"label": "Resultados", "value": "qualy-results"},
                    {"label": "Qualify", "value": "qualy-elimination"},
                    {"label": "Regra dos 107%", "value": "rule-107"},
                ],
                value=None,
                className="chart-nav",
                labelClassName="chart-nav-item",
                inputClassName="chart-nav-radio",
            ),
        ], className="chart-sidebar"),

        # Chart area — conteúdo dinâmico + gráfico de posições com ID estável
        html.Div([
            html.Div(id="corrida-chart-area-content"),
            dcc.Graph(
                id="corrida-positions-graph",
                figure={},
                style={"display": "none"},
                config={"displayModeBar": False, "scrollZoom": False},
            ),
        ], className="chart-area"),
    ], className="chart-workspace"),
])


# ── Helpers ─────────────────────────────────────────────────────

def _fmt_lap(seconds):
    """Formata segundos em MM:SS.mmm para tabelas"""
    if not seconds or pd.isna(seconds):
        return "-"
    m = int(seconds // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{m:02d}:{s:02d}.{ms:03d}"


def _fmt_laptime_full(seconds):
    """Formata segundos em MM:SS.mmm (Mesma lógica do gráfico)"""
    return _fmt_lap(seconds)
    ms = round((s % 1) * 1000)
    return f"{h}:{m:02d}:{int(s):02d}.{ms:03d}"


def _build_qualy_results_table(laps: pd.DataFrame, session_meta: dict):
    if laps.empty:
        return html.Div("Nenhum dado disponível.", style={"padding": "2rem", "color": _MUTED})

    # Obter o melhor tempo de cada piloto
    best_laps = laps[laps["LapTimeSeconds"] > 0].sort_values("LapTimeSeconds").groupby("Driver").first().reset_index()
    best_laps = best_laps.sort_values("LapTimeSeconds")
    
    if best_laps.empty:
        return html.Div("Nenhum tempo registrado.", style={"padding": "2rem", "color": _MUTED})

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


def _build_team_avg_panel(laps: pd.DataFrame) -> html.Div:
    """Painel lateral: equipe → barra → média, alinhado ao gráfico beeswarm."""
    team_col = (
        "team" if "team" in laps.columns and laps["team"].notna().any() else None
    )
    if team_col is None or "LapTimeSeconds" not in laps.columns:
        return html.Div()

    df = laps[laps["LapTimeSeconds"].notna() & (laps["LapTimeSeconds"] > 0)].copy()
    if "is_accurate" in df.columns:
        df = df[df["is_accurate"].isin([1, True])]
    if df.empty:
        return html.Div()

    median = df["LapTimeSeconds"].median()
    df = df[df["LapTimeSeconds"] < median * 1.6]

    team_means = df.groupby(team_col)["LapTimeSeconds"].mean().sort_values()
    if team_means.empty:
        return html.Div()

    min_avg = team_means.min()
    max_avg = team_means.max()
    span = max_avg - min_avg if max_avg != min_avg else 1.0

    rows = []
    for team, avg in team_means.items():
        color = get_team_color(team)
        bar_pct = int((1 - (avg - min_avg) / span) * 100)
        rows.append(html.Div([
            html.Span(team, style={
                "flex": "0 0 110px",
                "fontSize": ".8rem",
                "fontWeight": "700",
                "color": color,
                "whiteSpace": "nowrap",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            }),
            html.Div(
                html.Div(style={
                    "width": f"{bar_pct}%",
                    "height": "7px",
                    "backgroundColor": color,
                    "borderRadius": "4px",
                }),
                style={
                    "flex": "1",
                    "backgroundColor": "#E5E7EB",
                    "borderRadius": "4px",
                    "overflow": "hidden",
                    "alignSelf": "center",
                },
            ),
            html.Span(_fmt_laptime_full(avg), style={
                "flex": "0 0 88px",
                "fontFamily": "monospace, Inter, Arial",
                "fontSize": ".8rem",
                "color": color,
                "fontWeight": "600",
                "textAlign": "right",
            }),
        ], style={
            "display": "flex",
            "alignItems": "center",
            "gap": ".5rem",
            "padding": ".38rem .6rem",
            "borderBottom": f"1px solid {_BORDER}",
        }))

    header = html.Div([
        html.Span("Equipe", style={"flex": "0 0 110px", "fontWeight": "700", "color": _MUTED, "fontSize": ".72rem"}),
        html.Span("", style={"flex": "1"}),
        html.Span("Média", style={"flex": "0 0 88px", "textAlign": "right", "fontWeight": "700", "color": _MUTED, "fontSize": ".72rem"}),
    ], style={
        "display": "flex",
        "alignItems": "center",
        "gap": ".5rem",
        "padding": ".38rem .6rem",
        "background": "#F9FAFB",
        "borderBottom": f"1px solid {_BORDER}",
    })

    return html.Div(
        [header] + rows,
        style={
            "border": f"1px solid {_BORDER}",
            "borderRadius": "8px",
            "overflow": "hidden",
            "flex": "0 0 310px",
            "alignSelf": "flex-start",
            "marginTop": "52px",  # alinha com a área do plot (abaixo da annotation de título)
        },
    )


def _build_stats_panel(laps_json, session_meta):
    """Big Numbers panel: KPIs + final standings."""
    if not laps_json:
        return html.Div(
            "Carregue uma corrida para ver os dados.",
            style={"color": _MUTED, "padding": "2rem", "fontSize": ".95rem"},
        )

    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        season = session_meta.get("season") if session_meta else None
        race_label = session_meta.get("race", "—") if session_meta else "—"

        # ── KPIs ────────────────────────────────────────────────
        total_laps = (
            int(laps["LapNumber"].max())
            if "LapNumber" in laps.columns else "—"
        )
        total_drivers = (
            len(laps["Driver"].unique())
            if "Driver" in laps.columns else "—"
        )
        # ── Contagem de DNF ─────────────────────────────────────
        dnf_count = 0
        if "Position" in laps.columns and "LapNumber" in laps.columns:
            # Um piloto é considerado DNF se sua última volta registrada
            # for significativamente menor que a volta máxima da corrida
            max_race_lap = laps["LapNumber"].max()
            for drv in laps["Driver"].unique():
                last_lap = laps[laps["Driver"] == drv]["LapNumber"].max()
                if last_lap < max_race_lap:
                    dnf_count += 1

        best_lap = "—"
        best_lap_driver = ""
        best_lap_seconds = None
        if "LapTimeSeconds" in laps.columns and "Driver" in laps.columns:
            valid = laps[laps["LapTimeSeconds"].notna()]
            if not valid.empty:
                idx = valid["LapTimeSeconds"].idxmin()
                best_lap = _fmt_lap(valid.at[idx, "LapTimeSeconds"])
                best_lap_driver = valid.at[idx, "Driver"]
                best_lap_seconds = valid.at[idx, "LapTimeSeconds"]

        def kpi(label, value, sub=None):
            children = [
                html.Div(label, className="kpi-label"),
                html.Div(str(value), className="kpi-value"),
            ]
            if sub:
                children.append(html.Div(
                    sub,
                    style={
                        "fontSize": ".75rem",
                        "color": _MUTED,
                        "marginTop": ".1rem",
                    },
                ))
            return html.Div(children, className="kpi")

        kpi_row = html.Div([
            kpi("Corrida", race_label),
            kpi("Total de Voltas", total_laps),
            kpi("Pilotos", total_drivers),
            kpi("DNF", dnf_count) if dnf_count > 0 else kpi("Status", "Grid Completo"),
            kpi("Melhor Volta", best_lap, best_lap_driver),
        ], className="kpi-row", style={
            "marginBottom": "1.5rem",
            "display": "flex",
            "flexDirection": "row",
            "flexWrap": "nowrap",
            "gap": "1rem",
            "width": "100%",
            "overflowX": "auto"
        })

        # ── Classificação Final ──────────────────────────────────
        standings_rows = []
        if (
            "Position" in laps.columns
            and "Driver" in laps.columns
            and "LapNumber" in laps.columns
        ):
            final_pos = {}
            for drv in laps["Driver"].unique():
                drv_df = laps[laps["Driver"] == drv]
                if drv_df.empty:
                    continue
                last_row = drv_df.loc[drv_df["LapNumber"].idxmax()]
                pos = last_row["Position"]
                if pd.notna(pos):
                    final_pos[drv] = int(pos)
            # build pos -> driver map and precompute total times so we can show gaps to leader
            pos_to_drv = {p: d for d, p in final_pos.items()}

            # helper to format gap as HH:MM:SS
            def _fmt_gap(seconds):
                if seconds is None or pd.isna(seconds):
                    return "—"
                secs = int(round(seconds))
                h, rem = divmod(secs, 3600)
                m, s = divmod(rem, 60)
                return f"{h:02d}:{m:02d}:{s:02d}"

            # format lap gap as MM:SS.ss (used for best-lap gaps)
            def _fmt_lap_gap(seconds):
                if seconds is None or pd.isna(seconds) or seconds == 0:
                    return "—"
                return f"+{seconds:.3f}"

            total_times = {}
            if "LapTimeSeconds" in laps.columns:
                for drv in final_pos.keys():
                    drv_laps = laps[laps["Driver"] == drv]
                    valid = drv_laps[drv_laps["LapTimeSeconds"].notna()]
                    if not valid.empty:
                        total_times[drv] = valid["LapTimeSeconds"].sum()
                    else:
                        total_times[drv] = None

            leader_time = None
            if 1 in pos_to_drv:
                leader = pos_to_drv[1]
                leader_time = total_times.get(leader)

            for pos in sorted(final_pos.values()):
                drv = next((d for d, p in final_pos.items() if p == pos), None)
                if not drv:
                    continue

                team_name = ""
                if "team" in laps.columns:
                    t = laps[laps["Driver"] == drv]["team"].dropna()
                    if not t.empty:
                        team_name = str(t.iloc[0])

                drv_color = get_driver_color(season, drv)
                bg = _SURFACE if pos % 2 == 0 else "#FFFFFF"

                # best lap and fastest flag (total_time retrieved from precomputed table)
                total_time = total_times.get(drv) if isinstance(total_times, dict) else None
                best_lap_drv = None
                fastest_flag = False
                if "LapTimeSeconds" in laps.columns:
                    drv_laps = laps[laps["Driver"] == drv]
                    valid = drv_laps[drv_laps["LapTimeSeconds"].notna()]
                    if not valid.empty:
                        best_lap_drv = valid["LapTimeSeconds"].min()
                        fastest_flag = (best_lap_driver == drv)

                # format totals: original total and gap to leader
                display_total_original = _fmt_lap(total_time) if total_time is not None else "—"
                if total_time is None:
                    display_total = "—"
                elif leader_time is None:
                    display_total = _fmt_lap(total_time)
                else:
                    if pos == 1:
                        display_total = "—"
                    else:
                        gap = total_time - leader_time
                        display_total = f"+{gap:.3f}"

                # compute gap to best lap: leader = 00:00.00, others +MM:SS.ss
                if best_lap_drv is None:
                    display_best_lap_gap = "—"
                elif best_lap_seconds is None:
                    display_best_lap_gap = _fmt_lap(best_lap_drv)
                else:
                    if best_lap_driver and drv == best_lap_driver:
                        display_best_lap_gap = "—"
                    else:
                        lap_gap = best_lap_drv - best_lap_seconds
                        display_best_lap_gap = _fmt_lap_gap(lap_gap)

                    standings_rows.append(html.Div([
                            html.Span(f"P{pos}", style={"fontWeight": "800", "color": _PRIMARY, "flex": "0 0 36px", "fontSize": ".85rem"}),
                            html.Span(drv, style={"fontWeight": "700", "color": drv_color, "flex": "0 0 64px", "fontFamily": "monospace, Inter, Arial", "fontSize": ".9rem"}),
                            html.Span(team_name, style={"color": _MUTED, "fontSize": ".85rem", "flex": "1"}),
                            html.Span(display_total_original, style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".85rem"}),
                            html.Span(display_total, style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".85rem"}),
                            html.Span(_fmt_lap(best_lap_drv) if best_lap_drv else "—", style={"flex": "0 0 74px", "textAlign": "center", "fontSize": ".85rem"}),
                            html.Span(display_best_lap_gap, style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".85rem"}),
                            html.Span("★" if fastest_flag else "", style={"color": "#F59E0B", "flex": "0 0 28px", "textAlign": "center"}),
                    ], style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "1rem",
                        "padding": ".42rem .75rem",
                        "borderBottom": f"1px solid {_BORDER}",
                        "background": bg,
                    }))

            # fallback: if we couldn't build standings from Position, try from total_times
            if not standings_rows and total_times:
                # order drivers by total time (None goes last)
                ordered = sorted(total_times.items(), key=lambda kv: (kv[1] is None, kv[1]))
                leader_time_fb = None
                if ordered and ordered[0][1] is not None:
                    leader_time_fb = ordered[0][1]

                for idx, (drv, ttime) in enumerate(ordered, start=1):
                    pos = idx
                    team_name = ""
                    if "team" in laps.columns:
                        tt = laps[laps["Driver"] == drv]["team"].dropna()
                        if not tt.empty:
                            team_name = str(tt.iloc[0])

                    drv_color = get_driver_color(season, drv)
                    bg = _SURFACE if pos % 2 == 0 else "#FFFFFF"

                    best_lap_drv = None
                    fastest_flag = False
                    if "LapTimeSeconds" in laps.columns:
                        drv_laps = laps[laps["Driver"] == drv]
                        valid = drv_laps[drv_laps["LapTimeSeconds"].notna()]
                        if not valid.empty:
                            best_lap_drv = valid["LapTimeSeconds"].min()
                            fastest_flag = (best_lap_driver == drv)

                    display_total_original = _fmt_lap(ttime) if ttime is not None else "—"
                    if ttime is None:
                        display_total = "—"
                    elif leader_time_fb is None:
                        display_total = _fmt_lap(ttime)
                    else:
                        if pos == 1:
                            display_total = "—"
                        else:
                            gap = ttime - leader_time_fb
                            display_total = f"+{gap:.3f}"

                    standings_rows.append(html.Div([
                        html.Span(f"P{pos}", style={"fontWeight": "800", "color": _PRIMARY, "flex": "0 0 36px", "fontSize": ".85rem"}),
                        html.Span(drv, style={"fontWeight": "700", "color": drv_color, "flex": "0 0 64px", "fontFamily": "monospace, Inter, Arial", "fontSize": ".9rem"}),
                        html.Span(team_name, style={"color": _MUTED, "fontSize": ".85rem", "flex": "1"}),
                        html.Span(display_total_original, style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".85rem"}),
                        html.Span(display_total, style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".85rem"}),
                        html.Span(_fmt_lap(best_lap_drv) if best_lap_drv else "—", style={"flex": "0 0 74px", "textAlign": "center", "fontSize": ".85rem"}),
                        html.Span(display_best_lap_gap, style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".85rem"}),
                        html.Span("★" if fastest_flag else "", style={"color": "#F59E0B", "flex": "0 0 28px", "textAlign": "center"}),
                    ], style={"display": "flex", "alignItems": "center", "gap": "1rem", "padding": ".42rem .75rem", "borderBottom": f"1px solid {_BORDER}", "background": bg}))

        # header for standings table
        header_row = html.Div([
            html.Span("Pos", style={"flex": "0 0 36px", "fontWeight": "700", "fontSize": ".7rem", "color": _MUTED, "textAlign": "center"}),
            html.Span("Piloto", style={"flex": "0 0 64px", "fontWeight": "700", "fontSize": ".7rem", "color": _MUTED, "textAlign": "center"}),
            html.Span("Equipe", style={"flex": "1", "fontWeight": "700", "fontSize": ".7rem", "color": _MUTED, "textAlign": "center"}),
            html.Span("T. Total", style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".7rem", "fontWeight": "700", "color": _MUTED}),
            html.Span("Gap Total", style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".7rem", "fontWeight": "700", "color": _MUTED}),
            html.Span("M. Volta", style={"flex": "0 0 74px", "textAlign": "center", "fontSize": ".7rem", "fontWeight": "700", "color": _MUTED}),
            html.Span("Gap Volta", style={"flex": "0 0 86px", "textAlign": "center", "fontSize": ".7rem", "fontWeight": "700", "color": _MUTED}),
            html.Span("", style={"flex": "0 0 28px", "textAlign": "center", "fontWeight": "700", "color": _MUTED}),
        ], style={"display": "flex", "alignItems": "center", "gap": "1rem", "padding": ".5rem .75rem", "borderBottom": f"1px solid {_BORDER}", "background": "#F9FAFB"})

        standings = html.Div([
            html.Div(
                "Classificação Final",
                style={
                    "fontWeight": "700",
                    "fontSize": ".78rem",
                    "textTransform": "uppercase",
                    "letterSpacing": ".06em",
                    "color": _MUTED,
                    "marginBottom": ".6rem",
                },
            ),
            html.Div(
                [header_row] + (standings_rows or [html.Div(
                    "Dados de posição não disponíveis.",
                    style={"color": _MUTED, "fontSize": ".9rem", "padding": ".5rem"},
                )]),
                style={
                    "border": f"1px solid {_BORDER}",
                    "borderRadius": "8px",
                    "overflow": "hidden",
                },
            ),
        ])

        return html.Div([kpi_row, standings], style={"padding": ".25rem 0"})

    except Exception as e:
        print(f"Error building stats panel: {e}")
        return html.Div(
            "Erro ao carregar dados.",
            style={"color": _MUTED, "padding": "1rem"},
        )


# ── Callbacks ───────────────────────────────────────────────────

@dash.callback(
    Output("corrida-season-dropdown", "options"),
    Output("corrida-season-dropdown", "value"),
    Output("corrida-cache-warning", "children"),
    Input("corrida-page-trigger", "data"),
)

def load_seasons(_):
    try:
        seasons = client.get_available_seasons()
        if not seasons:
            warning = html.Div([
                html.Span("⚠", className="alert-icon"),
                html.Div([
                    html.Strong("Nenhum dado no cache SQLite."),
                    html.P(
                        ["Execute: ", html.Code(
                            "python scripts/populate_cache.py --season 2024"
                        )],
                        style={"margin": ".4rem 0 0"},
                    ),
                ]),
            ], className="alert alert-warning")
            return [], None, warning
        options = [{"label": str(s), "value": s} for s in seasons]
        return options, seasons[0] if seasons else None, None
    except Exception as e:
        print(f"Error loading seasons: {e}")
        error = html.Div([
            html.Span("✕", className="alert-icon"),
            html.Div([
                html.Strong("Não foi possível conectar ao backend."),
                html.P(
                    ["Certifique-se de que o servidor está rodando: ",
                     html.Code("python main.py")],
                    style={"margin": ".4rem 0 0"},
                ),
            ]),
        ], className="alert alert-error")
        return [], None, error

@dash.callback(
    Output("corrida-race-dropdown", "options"),
    Input("corrida-season-dropdown", "value"),
)
def update_races(season):
    if not season:
        return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("corrida-laps-store", "data"),
    Output("corrida-session-store", "data"),
    Input("corrida-load-button", "n_clicks"),
    Input("corrida-race-dropdown", "value"),
    State("corrida-season-dropdown", "value"),
    State("corrida-chart-selector", "value"),
    State("qualificacao-chart-selector", "value"),
)
def handle_load(n_clicks, race, season, corrida_sel, qualy_sel):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Se mudar a corrida no dropdown e for para vazio, resetar stores
    if triggered_id == "corrida-race-dropdown" and not race:
        return None, None

    # Se for o botão ou mudança no dropdown para uma corrida válida
    if not season or not race:
        return dash.no_update, dash.no_update
    
    # Decide qual sessão tentar primeiro com base no que o usuário está vendo
    preferred = "Q" if qualy_sel else "R"
    
    laps, _, session = client.load_race_session(season, race, preferred_session=preferred)
    if laps.empty:
        return None, None
    
    return laps.to_json(date_format="iso", orient="split"), {
        "season": season,
        "race": race,
        "drivers": session.get("drivers", []),
        "session_type": session.get("session_type"),
    }


@dash.callback(
    Output("corrida-chart-selector", "value"),
    Output("qualificacao-chart-selector", "value"),
    Input("corrida-chart-selector", "value"),
    Input("qualificacao-chart-selector", "value"),
    prevent_initial_call=True
)
def sync_chart_selectors(corrida_val, qualy_val):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if triggered_id == "corrida-chart-selector":
        return corrida_val, None
    elif triggered_id == "qualificacao-chart-selector":
        return None, qualy_val
    
    return dash.no_update, dash.no_update


@dash.callback(
    Output("corrida-chart-area-content", "children"),
    Output("corrida-chart-area-content", "style"),
    Output("corrida-positions-graph", "style"),
    Input("corrida-laps-store", "data"),
    Input("corrida-chart-selector", "value"),
    Input("qualificacao-chart-selector", "value"),
    State("corrida-session-store", "data"),
)
def update_content(laps_json, corrida_chart, qualy_chart, session_meta):
    chart_type = corrida_chart or qualy_chart
    
    SHOW = {"display": "block"}
    HIDE = {"display": "none"}

    # Gráfico de posições tem ID estável e é gerenciado por callback separado
    if chart_type == "positions":
        return None, HIDE, SHOW

    if chart_type == "big-numbers":
        return _build_stats_panel(laps_json, session_meta), SHOW, HIDE

    # beeswarm / qualy
    empty_fig = {"data": [], "layout": _base_layout("Nenhum dado carregado")}
    if not laps_json:
        return dcc.Graph(figure=empty_fig, config={"staticPlot": True}), SHOW, HIDE

    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        season = session_meta.get("season") if session_meta else None
        
        if chart_type == "rule-107":
            fig = rule_107_chart(laps)
        elif chart_type == "qualy-elimination":
            fig = qualifying_elimination_chart(laps, season)
            return dcc.Graph(
                figure=fig,
                config={"displayModeBar": False, "staticPlot": True},
            ), SHOW, HIDE
        elif chart_type == "qualy-results":
            return _build_qualy_results_table(laps, session_meta), SHOW, HIDE
        else: # beeswarm
            fig = lap_time_beeswarm_chart(laps, season)
        
        return dcc.Graph(
            figure=fig,
            config={"displayModeBar": False, "staticPlot": False, "scrollZoom": False},
        ), SHOW, HIDE

    except Exception as e:
        print(f"Error updating corrida content: {e}")
        return dcc.Graph(figure=empty_fig, config={"staticPlot": True}), SHOW, HIDE


@dash.callback(
    Output("corrida-positions-graph", "figure"),
    Input("corrida-laps-store", "data"),
    Input("corrida-chart-selector", "value"),
    State("corrida-session-store", "data"),
)
def update_positions_graph(laps_json, chart_type, session_meta):
    if chart_type != "positions" or not laps_json:
        return {}
    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")
        season = session_meta.get("season") if session_meta else None
        return race_position_chart(laps, season=season)
    except Exception as e:
        print(f"Error updating positions graph: {e}")
        return {}
