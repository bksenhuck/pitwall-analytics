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
    color_list_for_drivers,
    _FALLBACK_COLOR,
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
