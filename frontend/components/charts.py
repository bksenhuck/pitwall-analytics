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

def _fmt_laptime_full(seconds):
    """Formata segundos em MM:SS.mmm"""
    if not seconds or pd.isna(seconds):
        return "-"
    m = int(seconds // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{m:02d}:{s:02d}.{ms:03d}"

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
    team_means = df.groupby(team_col)["LapTimeSeconds"].mean()
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

    # Anotações de média à direita de cada linha
    def _fmt_mean(secs):
        h = int(secs // 3600)
        rem = secs % 3600
        m = int(rem // 60)
        s = rem % 60
        ms = round((s % 1) * 1000)
        return f"{h}:{m:02d}:{int(s):02d}.{ms:03d}"

    avg_annotations = [
        dict(
            text=_fmt_mean(team_means[team]),
            x=1.01,
            y=team,
            xref="paper",
            yref="y",
            xanchor="left",
            yanchor="middle",
            showarrow=False,
            font=dict(
                color=get_team_color(team),
                size=11,
                family="monospace, Inter, Arial",
            ),
        )
        for team in ordered_teams
        if team in team_means
    ]

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
        margin=dict(t=90, l=140, r=110, b=50),
    )
    layout["annotations"] = layout.get("annotations", []) + avg_annotations
    fig.update_layout(**layout)
    return fig


def race_position_chart(
    laps: pd.DataFrame, season: Optional[int] = None, selected_driver: Optional[str] = None
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

    # Filtrar apenas voltas com posição válida e garantir que seja numérico
    df = laps.copy()
    df = df[pd.to_numeric(df["Position"], errors="coerce").notna()].copy()
    df["Position"] = df["Position"].astype(int)
    df = df[df["LapNumber"].notna()].copy()

    if df.empty:
        fig.update_layout(**_base_layout("Evolução de Posição", height=520))
        return fig

    # Final position per driver (last lap they appear)
    final_positions = {}
    for drv in df["Driver"].unique():
        drv_df = df[df["Driver"] == drv]
        if not drv_df.empty:
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
        # título sobrescrito abaixo
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

    # Atualiza o texto do título para refletir o estado de seleção
    if selected_driver:
        title_html = (
            f"<b>Evolução de Posição</b>"
            f"  <span style='font-size:11px;color:#6B7280'>"
            f"— {selected_driver} em destaque · clique novamente para resetar"
            f"</span>"
        )
    else:
        title_html = (
            "<b>Evolução de Posição</b>"
            "  <span style='font-size:11px;color:#6B7280'>clique em uma linha para destacar</span>"
        )
    layout["annotations"][0]["text"] = title_html

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


def rule_107_chart(laps: pd.DataFrame) -> go.Figure:
    """
    Gráfico demonstrando a regra dos 107% na Fórmula 1.
    Recebe um conjunto de tempos de volta, calcula o limite de 107%
    com base no melhor tempo e destaca quem está dentro/fora.
    """
    if laps.empty or "LapTimeSeconds" not in laps.columns:
        fig = go.Figure()
        fig.update_layout(**_base_layout("Regra dos 107%"))
        return fig

    # Filtrar voltas válidas (maiores que 0)
    laps_valid = laps[laps["LapTimeSeconds"] > 0].copy()
    
    if laps_valid.empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout("Regra dos 107%"))
        return fig

    # Considerar o melhor tempo de cada piloto na sessão
    best_laps = (
        laps_valid.groupby("Driver")["LapTimeSeconds"]
        .min()
        .reset_index()
        .sort_values(by="LapTimeSeconds")
    )

    # Identificar pilotos que participaram mas não têm tempo válido
    all_drivers = laps["Driver"].unique()
    missing_drivers = [d for d in all_drivers if d not in best_laps["Driver"].values]
    
    if missing_drivers:
        missing_df = pd.DataFrame({
            "Driver": missing_drivers,
            "LapTimeSeconds": [None] * len(missing_drivers),
            "Percent": [115.0] * len(missing_drivers),
            "WithinLimit": [False] * len(missing_drivers)
        })
        
    best_session_time = best_laps["LapTimeSeconds"].min()
    limit_107 = best_session_time * 1.07

    # Converter para percentual
    best_laps["Percent"] = (best_laps["LapTimeSeconds"] / best_session_time) * 100
    best_laps["WithinLimit"] = best_laps["LapTimeSeconds"] <= limit_107
    
    if missing_drivers:
        best_laps = pd.concat([best_laps, missing_df], ignore_index=True)

    # Cores: Verde para dentro (107%), Vermelho para fora, Cinza para sem tempo
    colors = []
    for _, row in best_laps.iterrows():
        if pd.isna(row["LapTimeSeconds"]):
            colors.append("#9CA3AF")
        elif row["WithinLimit"]:
            colors.append("#10B981")
        else:
            colors.append("#EF4444")

    fig = go.Figure()

    # Adicionar as barras
    fig.add_trace(go.Bar(
        x=best_laps["Driver"],
        y=best_laps["Percent"],
        marker_color=colors,
        text=best_laps["LapTimeSeconds"].apply(lambda x: _fmt_laptime_full(x) if pd.notna(x) else "Sem Tempo"),
        textposition="auto",
        name="Percentual do Melhor Tempo",
        hovertemplate="Piloto: %{x}<br>Tempo: %{text}<br>Percentual: %{y:.2f}%<extra></extra>"
    ))

    # Linha horizontal de 107%
    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=len(best_laps) - 0.5,
        y0=107,
        y1=107,
        line=dict(color="#EF4444", width=3, dash="dash"),
    )

    # Anotação para a linha de 107%
    fig.add_annotation(
        x=len(best_laps) - 1,
        y=107.5,
        text="Limite 107%",
        showarrow=False,
        font=dict(color="#EF4444", weight="bold"),
        bgcolor="white",
        opacity=0.8
    )

    fig.update_layout(**_base_layout(
        "Regra dos 107% - Classificação",
        xaxis_title="Piloto",
        yaxis_title="Percentual (%)",
        height=500,
        yaxis=dict(range=[95, max(110, best_laps["Percent"].max() or 110) + 2])
    ))

    return fig


def qualifying_elimination_chart(laps: pd.DataFrame, season: int) -> go.Figure:
    """
    Gráfico estilo 'F1 Visualized' para sessões de Qualificação.
    Mostra as etapas (Q1, Q2, Q3) e o posicionamento dos carros.
    """
    if laps.empty or "LapTimeSeconds" not in laps.columns:
        fig = go.Figure()
        fig.update_layout(**_base_layout("Eliminação da Qualificação"))
        return fig

    # Mapeamento de nomes de arquivo de imagem (ajustado para redbull.png, etc)
    team_to_img = {
        "Red Bull Racing": "redbull",
        "Red Bull": "redbull",
        "Ferrari": "ferrari",
        "Mercedes": "mercedes",
        "McLaren": "mclaren",
        "Aston Martin": "aston_martin",
        "Alpine": "alpine",
        "Williams": "williams",
        "Haas F1 Team": "haas",
        "Haas": "haas",
        "RB": "racing_bulls",
        "Racing Bulls": "racing_bulls",
        "Kick Sauber": "audi",
        "Sauber": "audi",
        "Alfa Romeo": "audi",
        "Audi": "audi",
        "Cadillac": "cadillac"
    }

    df = laps[laps["LapTimeSeconds"] > 0].copy()
    best_results = df.sort_values("LapTimeSeconds").groupby("Driver").first().reset_index()
    best_results = best_results.sort_values("LapTimeSeconds")

    total_drivers = len(best_results)
    
    best_results["Phase"] = "Q1"
    # Identificar quem participou de cada fase REALMENTE
    # Q1: Todos (best_results já contém o melhor tempo de cada um)
    # Q2: Top 15 (pelo tempo)
    # Q3: Top 10 (pelo tempo)
    # Mas no gráfico original "F1 Visualized", os carros do Q1 mostram o tempo do Q1, Q2 mostra Q2, etc.
    # Como o seu dataframe já é o "best" por piloto, vamos apenas atribuir as zonas:
    total_count = len(best_results)
    if total_count > 0:
        best_results.loc[best_results.index[0:min(10, total_count)], "Phase"] = "Q3"
        if total_count > 10:
            best_results.loc[best_results.index[10:min(15, total_count)], "Phase"] = "Q2"
        if total_count > 15:
            best_results.loc[best_results.index[15:], "Phase"] = "Q1"

    fig = go.Figure()

    phases = ["Q3", "Q2", "Q1"]
    y_coords = {"Q3": 3, "Q2": 2, "Q1": 1}
    
    # Lógica de Distribuição Proporcional no Eixo Y
    best_results["Y_Offset"] = 0.0
    for phase in phases:
        mask = best_results["Phase"] == phase
        phase_subset = best_results[mask]
        if not phase_subset.empty:
            count = len(phase_subset)
            if count > 1:
                # Distribuir uniformemente por índice dentro do Q para evitar concentração
                # (Mesmo que o tempo seja próximo, eles ocupam o espaço vertical do Q)
                y_step = 0.7 / (count - 1) if count > 1 else 0
                for idx_in_phase, (idx, row) in enumerate(phase_subset.iterrows()):
                    # Primeiro do Q no topo (0.35), último na base (-0.35)
                    offset = 0.35 - (idx_in_phase * y_step)
                    best_results.at[idx, "Y_Offset"] = offset
            else:
                best_results.loc[mask, "Y_Offset"] = 0.0

    best_overall = best_results["LapTimeSeconds"].min()

    for phase in phases:
        fig.add_shape(
            type="rect",
            x0=-1, x1=max(best_results["LapTimeSeconds"]) * 1.2,
            y0=y_coords[phase] - 0.5, y1=y_coords[phase] + 0.5,
            fillcolor="#E5E7EB" if phase == "Q2" else "#F3F4F6",
            opacity=0.3,
            line_width=0,
            layer="below"
        )
        # Adicionar linhas tracejadas limitando o Q2 (superior e inferior)
        if phase == "Q2":
            # Linha superior do Q2 (limite com Q3)
            fig.add_shape(
                type="line",
                x0=-1, x1=max(best_results["LapTimeSeconds"]) * 1.2,
                y0=y_coords[phase] + 0.5, y1=y_coords[phase] + 0.5,
                line=dict(color="#000000", width=1, dash="dash"),
                layer="below"
            )
            # Linha inferior do Q2 (limite com Q1)
            fig.add_shape(
                type="line",
                x0=-1, x1=max(best_results["LapTimeSeconds"]) * 1.2,
                y0=y_coords[phase] - 0.5, y1=y_coords[phase] - 0.5,
                line=dict(color="#000000", width=1, dash="dash"),
                layer="below"
            )

    # Calcular gaps para os ticks do eixo X
    max_time = best_results["LapTimeSeconds"].max()
    x_range_min = best_overall - 0.2
    x_range_max = max_time + 0.5

    # Adicionar as imagens dos carros (cada um mostrando seu tempo)
    for i, row in best_results.iterrows():
        driver = row["Driver"]
        team = row["team"] if "team" in row else ""
        time = row["LapTimeSeconds"]
        phase = row["Phase"]
        y_final = y_coords[phase] + row["Y_Offset"]

        img_name = team_to_img.get(team, "general")
        _img_season = season if season in (2025, 2026) else 2025
        img_path = f"/assets/static/images/{_img_season}/cars_drawing/{img_name}.png"
        
        # Cálculo da posição X no modo "paper" (0 a 1) para manter tamanho FIXO da imagem
        x_paper = (time - x_range_min) / (x_range_max - x_range_min) if (x_range_max - x_range_min) > 0 else 0

        fig.add_layout_image(
            dict(
                source=img_path,
                xref="paper", yref="y",
                x=x_paper, y=y_final,
                # sizex=0.07 significa 7% da largura TOTAL do gráfico, ignorando o zoom do eixo X
                sizex=0.07, sizey=0.25, 
                xanchor="center", yanchor="middle",
                layer="above",
                sizing="contain"
            )
        )

        fig.add_annotation(
            x=time, y=y_final + 0.12,
            text=f"<b>{driver}</b>", # Removido tempo do topo para não poluir, já está no eixo e no hover
            showarrow=False,
            font=dict(size=9, color=_TEXT),
            align="center"
        )
    
    # Criar ticks: o primeiro é o tempo absoluto, os outros são +Gap
    tick_vals = [best_overall]
    tick_text = [_fmt_laptime_full(best_overall)]
    
    # Adiciona ticks a cada 2s para não poluir se a diferença for pequena, ou 5s se for grande
    import numpy as np
    diff = x_range_max - best_overall
    step = 2.0 if diff < 20 else 5.0
    
    current_tick = best_overall + step
    while current_tick <= x_range_max:
        tick_vals.append(current_tick)
        tick_text.append(f"+{int(current_tick - best_overall)}s")
        current_tick += step

    fig.update_layout(**_base_layout(
        "Eliminação da Qualificação",
        xaxis_title="Tempo / Gap para Pole",
        yaxis=dict(
            tickvals=[1, 2, 3],
            ticktext=["Q1", "Q2", "Q3"],
            range=[0.5, 3.5],
            fixedrange=True
        ),
        xaxis=dict(
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[x_range_min, x_range_max],
            fixedrange=True,
            showgrid=True,
            gridcolor="#E5E7EB",
            gridwidth=1,
            griddash="dot"
        ),
        height=600,
        showlegend=False,
        dragmode=False,
        hovermode=False
    ))

    return fig
