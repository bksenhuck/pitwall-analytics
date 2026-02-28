"""
Plotly chart components for F1 analytics.

All charts return plotly.graph_objs.Figure objects that can be
used with dcc.Graph components in Dash.
"""
from typing import Optional
import plotly.graph_objs as go
import pandas as pd

from frontend.f1_config import (
    get_driver_color,
    get_team_color,
)


# ── Pitwall Design System — cores do CSS ────────────────────────────────────
_BG = "#F4F5F7"       # --surface  (off-white dos cards)
_BORDER = "#DDE1E7"   # --border
_PRIMARY = "#003082"  # --primary  (F1 blue)
_ACCENT = "#1565C0"   # --accent
_TEXT = "#1A1A1A"     # --text
_MUTED = "#6B7280"    # --muted

# Paleta sequencial: azuis e cinzas
PITWALL_COLORS = [
    "#003082",   # azul F1
    "#1565C0",   # azul médio
    "#42A5F5",   # azul claro
    "#90CAF9",   # azul pastel
    "#4B5563",   # cinza escuro
    "#6B7280",   # cinza médio
    "#9CA3AF",   # cinza claro
    "#0D47A1",   # azul navy
    "#1976D2",   # azul royal
    "#64B5F6",   # azul céu
]


def _base_layout(title: str, **extra) -> dict:
    """
    Base layout dict que aplica o tema Pitwall em todos os gráficos.
    Título em azul negrito com fundo azul claro, recuado à esquerda.
    Sem grid nem toolbar de interação.
    """
    # Título como annotation para suportar bgcolor
    title_annotation = dict(
        text=f"<b>{title}</b>",
        x=0,
        y=1.08,          # acima da área do plot, dentro da margem
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="bottom",
        showarrow=False,
        font=dict(
            color=_PRIMARY,
            size=14,
            family="Inter, Arial, sans-serif",
        ),
        bgcolor="#DBEAFE",   # azul pastel claro
        borderpad=6,
    )

    layout = dict(
        title=dict(text=""),   # título nativo vazio — usamos annotation
        annotations=[title_annotation],
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_TEXT, family="Inter, Arial, sans-serif", size=13),
        colorway=PITWALL_COLORS,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=_BORDER,
            tickfont=dict(color=_MUTED),
            title_font=dict(color=_MUTED),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=_BORDER,
            tickfont=dict(color=_MUTED),
            title_font=dict(color=_MUTED),
            rangemode="tozero",
            automargin=True,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_TEXT),
        ),
        margin=dict(t=90, l=50, r=20, b=50),
        hovermode="x unified",
    )
    layout.update(extra)
    return layout


def lap_time_chart(
    laps: pd.DataFrame, driver: Optional[str] = None
) -> go.Figure:
    """Lap number vs lap time seconds."""
    df = laps.copy()
    if driver:
        df = df[df["Driver"] == driver]

    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["LapNumber"],
            y=df["LapTimeSeconds"],
            mode="lines+markers",
            name=f"Tempo de volta — {driver or 'Todos'}",
            line=dict(color=_PRIMARY, width=2),
            marker=dict(color=_ACCENT, size=6),
        ))

    fig.update_layout(**_base_layout(
        "Tempo de Volta por Volta",
        xaxis_title="Volta",
        yaxis_title="Tempo (s)",
        height=400,
    ))
    return fig


def position_chart(
    laps: pd.DataFrame, driver: Optional[str] = None
) -> go.Figure:
    """Race position over laps."""
    df = laps.copy()
    if driver:
        df = df[df["Driver"] == driver]

    fig = go.Figure()
    if not df.empty and "Position" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["LapNumber"],
            y=df["Position"],
            mode="lines+markers",
            name=f"Posição — {driver or 'Todos'}",
            line=dict(color=_PRIMARY, width=2),
            marker=dict(color=_ACCENT, size=6),
        ))
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(**_base_layout(
        "Evolução de Posição por Volta",
        xaxis_title="Volta",
        yaxis_title="Posição",
        height=400,
    ))
    return fig


def speed_telemetry_chart(telemetry: pd.DataFrame) -> go.Figure:
    """Speed over distance/time from telemetry."""
    fig = go.Figure()

    if telemetry.empty:
        base = _base_layout("Telemetria de Velocidade", height=400)
        base["annotations"] = base.get("annotations", []) + [{
            "text": "Dados de telemetria não disponíveis no cache.",
            "showarrow": False,
            "xref": "paper",
            "yref": "paper",
            "x": 0.5,
            "y": 0.5,
            "font": {"size": 13, "color": _MUTED},
        }]
        fig.update_layout(**base)
        return fig

    x_col = next(
        (c for c in ("Distance", "Time") if c in telemetry.columns),
        None,
    )
    if x_col is None:
        telemetry = telemetry.reset_index()
        x_col = telemetry.columns[0]
    x_label = "Distância (m)" if x_col == "Distance" else "Tempo (s)"

    if "Speed" in telemetry.columns:
        fig.add_trace(go.Scatter(
            x=telemetry[x_col],
            y=telemetry["Speed"],
            mode="lines",
            name="Velocidade",
            line=dict(color=_PRIMARY, width=2),
        ))

    fig.update_layout(**_base_layout(
        "Telemetria de Velocidade",
        xaxis_title=x_label,
        yaxis_title="Velocidade (km/h)",
        height=400,
    ))
    return fig


def lap_time_beeswarm_chart(
    laps: pd.DataFrame, season: Optional[int] = None
) -> go.Figure:
    """
    Strip/beeswarm chart of lap times grouped by team.
    Each dot = one lap, colored and grouped by team.
    Teams ordered fastest (bottom) → slowest (top).
    X axis reversed: slow laps on left, fast on right.
    """
    fig = go.Figure()

    _title = "Tempos de Volta por Equipe"

    if laps.empty or "LapTimeSeconds" not in laps.columns:
        fig.update_layout(**_base_layout(_title, height=500))
        return fig

    df = laps.copy()

    # Determine team column
    team_col = (
        "team"
        if "team" in df.columns and df["team"].notna().any()
        else None
    )
    if team_col is None:
        fig.update_layout(**_base_layout(_title, height=500))
        return fig

    # Filter: valid lap times + accurate laps only
    df = df[df["LapTimeSeconds"].notna() & (df["LapTimeSeconds"] > 0)].copy()
    if "is_accurate" in df.columns:
        df = df[df["is_accurate"].isin([1, True])]
    if df.empty:
        fig.update_layout(**_base_layout(_title, height=500))
        return fig

    # Remove extreme outliers (> 3× median — pit stop / safety car laps)
    median = df["LapTimeSeconds"].median()
    df = df[df["LapTimeSeconds"] < median * 1.6]

    # Order: fastest median at bottom of chart
    team_medians = df.groupby(team_col)["LapTimeSeconds"].median()
    ordered_teams = team_medians.sort_values(ascending=True).index.tolist()

    # Shapes: background band + vertical median line per team
    shapes = []
    for i, team in enumerate(ordered_teams):
        hex_color = get_team_color(team)
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        # Light background band
        shapes.append(dict(
            type="rect",
            xref="paper", yref="y",
            x0=0, x1=1,
            y0=i - 0.5, y1=i + 0.5,
            fillcolor=f"rgba({r},{g},{b},0.08)",
            line=dict(width=0),
            layer="below",
        ))
        # Vertical dotted median line for this team
        shapes.append(dict(
            type="line",
            xref="x", yref="y",
            x0=team_medians[team], x1=team_medians[team],
            y0=i - 0.42, y1=i + 0.42,
            line=dict(
                color=hex_color,
                dash="dot",
                width=2.5,
            ),
            layer="above",
        ))

    # One Box trace per team (box hidden, only points shown, no tooltip)
    for team in ordered_teams:
        team_laps = df[df[team_col] == team]["LapTimeSeconds"]
        color = get_team_color(team)
        fig.add_trace(go.Box(
            x=team_laps,
            y=[team] * len(team_laps),
            name=team,
            orientation="h",
            boxpoints="all",
            jitter=0.45,
            pointpos=0,
            marker=dict(color=color, size=4, opacity=0.75),
            line=dict(color="rgba(0,0,0,0)", width=0),
            fillcolor="rgba(0,0,0,0)",
            whiskerwidth=0,
            showlegend=False,
            hoverinfo="skip",
        ))

    height = max(480, len(ordered_teams) * 62 + 130)

    layout = _base_layout(
        _title,
        xaxis_title="Tempo de Volta (s)",
        xaxis_autorange="reversed",
        yaxis=dict(
            categoryorder="array",
            categoryarray=ordered_teams,   # fastest at bottom
            showgrid=False,
            zeroline=False,
            linecolor=_BORDER,
            tickfont=dict(color=_TEXT, size=12),
            title_font=dict(color=_MUTED),
            automargin=True,
        ),
        shapes=shapes,
        height=height,
        hovermode=False,
        margin=dict(t=90, l=140, r=20, b=50),
    )
    fig.update_layout(**layout)
    return fig


def race_position_chart(
    laps: pd.DataFrame, season: Optional[int] = None
) -> go.Figure:
    """
    Race position evolution for all drivers.
    Left Y: driver codes at their final position.
    Right Y: position numbers (P1, P2, ...).
    X: lap number.
    """
    fig = go.Figure()

    if (
        laps.empty
        or "Position" not in laps.columns
        or "Driver" not in laps.columns
        or "LapNumber" not in laps.columns
    ):
        fig.update_layout(**_base_layout("Evolução de Posição", height=520))
        return fig

    df = laps[laps["Position"].notna() & laps["LapNumber"].notna()].copy()
    df["Position"] = df["Position"].astype(int)

    if df.empty:
        fig.update_layout(**_base_layout("Evolução de Posição", height=520))
        return fig

    # Final position per driver (last lap they appear)
    final_positions = {}
    for drv in df["Driver"].unique():
        drv_df = df[df["Driver"] == drv]
        last_row = drv_df.loc[drv_df["LapNumber"].idxmax()]
        pos = last_row["Position"]
        if pd.notna(pos):
            final_positions[drv] = int(pos)

    if not final_positions:
        fig.update_layout(**_base_layout("Evolução de Posição", height=520))
        return fig

    n = len(final_positions)

    def _ordinal(num):
        if 11 <= (num % 100) <= 13:
            return f"{num}th"
        return f"{num}{['th', 'st', 'nd', 'rd', 'th'][min(num % 10, 4)]}"

    # Left Y tick labels: driver code at each position slot
    left_ticks = {pos: drv for drv, pos in final_positions.items()}
    left_ticktext = [left_ticks.get(i, "") for i in range(1, n + 1)]
    right_ticktext = [_ordinal(i) for i in range(1, n + 1)]

    # One trace per driver, sorted by final position
    for drv in sorted(final_positions, key=lambda d: final_positions[d]):
        drv_laps = df[df["Driver"] == drv].sort_values("LapNumber")
        color = get_driver_color(season, drv)
        fig.add_trace(go.Scatter(
            x=drv_laps["LapNumber"],
            y=drv_laps["Position"],
            mode="lines",
            name=drv,
            line=dict(color=color, width=1.5),
            hoverinfo="skip",
        ))

    y_range = [n + 0.5, 0.5]

    # Right-side ordinal labels as annotations (more reliable than yaxis2
    # with staticPlot, which often suppresses secondary axes)
    right_annotations = [
        dict(
            text=right_ticktext[i],
            x=1.01,
            y=i + 1,
            xref="paper",
            yref="y",
            xanchor="left",
            yanchor="middle",
            showarrow=False,
            font=dict(color=_MUTED, size=11,
                      family="Inter, Arial, sans-serif"),
        )
        for i in range(n)
    ]

    layout = _base_layout(
        "Evolução de Posição",
        xaxis_title="Volta",
        yaxis=dict(
            tickvals=list(range(1, n + 1)),
            ticktext=left_ticktext,
            range=y_range,
            showgrid=False,
            zeroline=False,
            linecolor=_BORDER,
            tickfont=dict(
                color=_TEXT, size=11,
                family="monospace, Inter, Arial",
            ),
            title_font=dict(color=_MUTED),
            automargin=True,
        ),
        showlegend=False,
        hovermode=False,
        height=520,
        margin=dict(t=90, l=60, r=70, b=50),
    )
    layout["annotations"] = layout.get("annotations", []) + right_annotations
    fig.update_layout(**layout)
    return fig


def driver_comparison_chart(
    laps: pd.DataFrame, drivers: list, season: Optional[int] = None
) -> go.Figure:
    """Compare lap times for multiple drivers."""
    fig = go.Figure()
    for i, driver in enumerate(drivers):
        driver_laps = laps[laps["Driver"] == driver]
        if not driver_laps.empty:
            color = (
                get_driver_color(season, driver)
                if season
                else PITWALL_COLORS[i % len(PITWALL_COLORS)]
            )
            fig.add_trace(go.Scatter(
                x=driver_laps["LapNumber"],
                y=driver_laps["LapTimeSeconds"],
                mode="lines+markers",
                name=driver,
                line=dict(color=color, width=2),
                marker=dict(size=5),
            ))

    fig.update_layout(**_base_layout(
        "Comparativo de Tempos de Volta",
        xaxis_title="Volta",
        yaxis_title="Tempo (s)",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_TEXT),
        ),
    ))
    return fig
