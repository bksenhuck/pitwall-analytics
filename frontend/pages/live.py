"""Live page - Race map visualization with circuit tracking"""
import io
import json

import dash
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Input, Output, State, dcc, html, no_update

from frontend.api import client

dash.register_page(__name__, path="/live", name="Live")

# ── Team colours (2024/2025) ───────────────────────────────────
TEAM_COLORS = {
    'Red Bull Racing': '#3671C6',
    'Ferrari': '#E8002D',
    'Mercedes': '#27F4D2',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#FF87BC',
    'Williams': '#64C4FF',
    'RB': '#6692FF',
    'Haas F1 Team': '#B6BABD',
    'Kick Sauber': '#52E252',
    # Legacy names
    'Red Bull': '#3671C6',
    'Haas': '#B6BABD',
    'Sauber': '#52E252',
    'AlphaTauri': '#5E8FAA',
    'Alfa Romeo': '#900000',
    'Racing Point': '#F596C8',
    'Renault': '#FFF500',
    'Force India': '#F596C8',
    'Toro Rosso': '#469BFF',
}


def _filter_card(label, component):
    return html.Div([html.Label(label), component], className="filter")


def _fmt_laptime(seconds):
    """Format seconds → M:SS.mmm"""
    if seconds is None:
        return '—'
    try:
        if pd.isna(seconds):
            return '—'
    except Exception:
        pass
    m = int(float(seconds) // 60)
    s = float(seconds) % 60
    return f'{m}:{s:06.3f}'


# ── Layout ─────────────────────────────────────────────────────
layout = html.Div([
    html.Div([
        html.H1("Live", className="page-title"),
        html.P(
            "Mapa da corrida volta a volta com posições em tempo real.",
            className="page-subtitle",
        ),
    ]),

    # Filters
    html.Div([
        _filter_card("Temporada", dcc.Dropdown(
            id="live-season", options=[], placeholder="Selecione a temporada"
        )),
        _filter_card("Corrida", dcc.Dropdown(
            id="live-race", options=[], placeholder="Selecione a corrida"
        )),
        html.Div([
            html.Button(
                "Carregar sessão",
                id="live-load", n_clicks=0, className="btn-primary"
            ),
        ], className="filter"),
    ], className="filters"),

    # Stores
    dcc.Store(id="live-laps-store", storage_type="session"),
    dcc.Store(id="live-track-layout-store", storage_type="session"),
    dcc.Store(id="live-session-meta-store", storage_type="session"),
    dcc.Store(id="live-page-load-trigger", data={"loaded": True}),

    # Auto-play interval (disabled by default)
    dcc.Interval(
        id="live-interval", interval=1000, disabled=True, n_intervals=0
    ),

    # Status message
    html.Div(id="live-status"),

    # Body: standings + track map
    html.Div([

        # Left: driver standings
        html.Div([
            html.Div(
                "POSIÇÕES",
                className="section-heading",
                style={"fontSize": ".7rem", "marginBottom": "8px"}
            ),
            html.Div(id="live-standings-panel"),
        ], className="live-standings"),

        # Right: track map
        html.Div([
            dcc.Graph(
                id="live-track-map",
                config={"displayModeBar": False},
                style={"height": "100%"},
            ),
        ], className="live-map"),

    ], className="live-body"),

    # Bottom: lap controls
    html.Div([
        html.Div(id="live-lap-label", className="live-lap-label"),
        html.Button(
            "‹", id="live-prev", n_clicks=0,
            className="btn-primary",
            style={"padding": ".5rem .85rem", "fontSize": "1.1rem"},
        ),
        dcc.Slider(
            id="live-lap-slider",
            min=1, max=70, step=1, value=1,
            marks=None,
            tooltip={"placement": "bottom", "always_visible": False},
            className="live-slider-input",
        ),
        html.Button(
            "›", id="live-next", n_clicks=0,
            className="btn-primary",
            style={"padding": ".5rem .85rem", "fontSize": "1.1rem"},
        ),
        html.Button(
            "▶ Play", id="live-play", n_clicks=0,
            className="btn-primary",
        ),
    ], className="live-slider-panel"),
])


# ── Callbacks ──────────────────────────────────────────────────

@dash.callback(
    Output("live-season", "options"),
    Output("live-season", "value"),
    Input("live-page-load-trigger", "data")
)
def load_live_seasons(_):
    seasons = client.get_available_seasons()
    opts = [{"label": str(s), "value": s} for s in seasons]
    return opts, seasons[0] if seasons else None


@dash.callback(
    Output("live-race", "options"),
    Input("live-season", "value")
)
def update_live_races(season):
    if not season:
        return []
    races = client.get_races_for_season(season)
    return [{"label": r, "value": r} for r in races]


@dash.callback(
    Output("live-laps-store", "data"),
    Output("live-track-layout-store", "data"),
    Output("live-session-meta-store", "data"),
    Output("live-lap-slider", "max"),
    Output("live-lap-slider", "value"),
    Output("live-status", "children"),
    Input("live-load", "n_clicks"),
    State("live-season", "value"),
    State("live-race", "value"),
    prevent_initial_call=True
)
def load_live_session(n_clicks, season, race):
    if not n_clicks or not season or not race:
        return (no_update,) * 6

    try:
        laps, _, _session = client.load_race_session(season, race)

        if laps.empty:
            msg = html.Div(
                "Nenhum dado encontrado.", className="alert alert-warning"
            )
            return None, None, None, 70, 1, msg

        total_laps = (
            int(laps["LapNumber"].max())
            if "LapNumber" in laps.columns else 70
        )

        laps_json = laps.to_json(date_format="iso", orient="split")

        layout_data = client.get_track_layout(season, race)

        meta = {"season": season, "event": race, "total_laps": total_laps}

        if layout_data.get("count", 0) > 0:
            status_txt = (
                f"✅ {race} {season} — {total_laps} voltas | "
                f"{layout_data['count']} pontos de circuito"
            )
            status = html.Div(
                status_txt, className="alert alert-info",
                style={"marginBottom": "8px"}
            )
        else:
            status = html.Div(
                "✅ Laps carregados. Circuito indisponível "
                "(rode populate_cache.py com telemetry=True).",
                className="alert alert-warning",
                style={"marginBottom": "8px"}
            )

        return (
            laps_json,
            json.dumps(layout_data),
            meta,
            total_laps,
            1,
            status,
        )

    except Exception as e:
        msg = html.Div(f"Erro: {e}", className="alert alert-error")
        return None, None, None, 70, 1, msg


@dash.callback(
    Output("live-lap-slider", "value", allow_duplicate=True),
    Input("live-prev", "n_clicks"),
    Input("live-next", "n_clicks"),
    Input("live-interval", "n_intervals"),
    State("live-lap-slider", "value"),
    State("live-lap-slider", "max"),
    prevent_initial_call=True
)
def navigate_laps(prev_clicks, next_clicks, n_intervals, current_val, max_val):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    current = current_val or 1
    max_lap = max_val or 70

    if triggered_id == "live-prev":
        return max(1, current - 1)
    if triggered_id == "live-next":
        return min(max_lap, current + 1)
    if triggered_id == "live-interval":
        new_val = current + 1
        return new_val if new_val <= max_lap else no_update
    return no_update


@dash.callback(
    Output("live-interval", "disabled"),
    Output("live-play", "children"),
    Input("live-play", "n_clicks"),
    State("live-interval", "disabled"),
    prevent_initial_call=True
)
def toggle_play(n_clicks, is_disabled):
    if is_disabled:
        return False, "⏸ Pausar"
    return True, "▶ Play"


@dash.callback(
    Output("live-standings-panel", "children"),
    Output("live-track-map", "figure"),
    Output("live-lap-label", "children"),
    Input("live-lap-slider", "value"),
    State("live-laps-store", "data"),
    State("live-track-layout-store", "data"),
    State("live-session-meta-store", "data"),
)
def update_race_view(lap_value, laps_json, layout_json, meta):
    empty_fig = _empty_map()

    if not laps_json:
        return [], empty_fig, "Volta —"

    try:
        laps = pd.read_json(io.StringIO(laps_json), orient="split")

        # Ensure snake_case columns exist
        if 'driver_code' not in laps.columns and 'Driver' in laps.columns:
            laps['driver_code'] = laps['Driver']
        if 'lap_number' not in laps.columns and 'LapNumber' in laps.columns:
            laps['lap_number'] = laps['LapNumber']
        if (
            'lap_time_seconds' not in laps.columns
            and 'LapTimeSeconds' in laps.columns
        ):
            laps['lap_time_seconds'] = laps['LapTimeSeconds']

        track_x, track_y = [], []
        if layout_json:
            ld = json.loads(layout_json)
            track_x = ld.get('x', [])
            track_y = ld.get('y', [])

        total_laps = meta.get('total_laps', 70) if meta else 70
        lap_label = f"Volta {lap_value} / {total_laps}"

        drivers = _compute_race_positions(laps, lap_value, track_x, track_y)

        return _build_standings(drivers), _build_track_map(
            drivers, track_x, track_y
        ), lap_label

    except Exception as e:
        print(f"Error updating race view: {e}")
        return [], _empty_map(), f"Volta {lap_value}"


# ── Helpers ────────────────────────────────────────────────────

def _empty_map():
    fig = go.Figure()
    fig.update_layout(
        plot_bgcolor='#0A0A14',
        paper_bgcolor='#0A0A14',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
        uirevision='race',
    )
    return fig


def _compute_race_positions(laps_df, lap_number, track_x, track_y):
    """
    Compute each driver's approximate position on circuit at end of lap N.

    Algorithm:
    1. Sum lap times up to lap N per driver → cumulative race time
    2. Compute gap to leader in seconds
    3. Convert gap to distance behind on circuit (arc-length)
    4. Interpolate X/Y along the circuit curve
    """
    valid = laps_df[
        (laps_df['lap_number'] <= lap_number)
        & (laps_df['lap_time_seconds'].notna())
    ].copy()

    if valid.empty:
        return []

    cum = valid.groupby('driver_code')['lap_time_seconds'].sum()
    leader_time = cum.min()
    leader_code = cum.idxmin()
    leader_laps = valid[valid['driver_code'] == leader_code].shape[0]
    leader_avg = leader_time / max(leader_laps, 1)

    has_track = bool(track_x and track_y and len(track_x) > 2)
    if has_track:
        x = np.array(track_x, dtype=float)
        y = np.array(track_y, dtype=float)
        dx, dy = np.diff(x), np.diff(y)
        arc = np.concatenate([[0], np.cumsum(np.sqrt(dx**2 + dy**2))])
        total_arc = arc[-1]
        speed = total_arc / leader_avg

    lap_N = laps_df[laps_df['lap_number'] == lap_number].set_index(
        'driver_code'
    )

    result = []
    for driver_code, driver_time in cum.items():
        gap_s = float(driver_time - leader_time)

        if has_track:
            dist_behind = gap_s * speed
            arc_pos = (total_arc - (dist_behind % total_arc)) % total_arc
            px = float(np.interp(arc_pos, arc, x))
            py = float(np.interp(arc_pos, arc, y))
        else:
            px, py = 0.0, 0.0

        if driver_code in lap_N.index:
            row = lap_N.loc[driver_code]
            pos_val = row.get('position')
            race_pos = int(pos_val) if pd.notna(pos_val) else 99
            lap_time = row.get('lap_time_seconds')
            team = str(row.get('team', ''))
        else:
            race_pos, lap_time, team = 99, None, ''

        result.append({
            'driver': driver_code,
            'x': px,
            'y': py,
            'position': race_pos,
            'gap': gap_s,
            'lap_time': lap_time,
            'team': team,
        })

    return sorted(result, key=lambda d: d['position'])


def _build_standings(drivers):
    """Left panel: ordered driver list with lap time and gap."""
    if not drivers:
        return [html.P(
            "Nenhum dado",
            style={"color": "var(--muted)", "padding": "8px"}
        )]

    rows = []
    for d in drivers:
        color = TEAM_COLORS.get(d['team'], '#888888')
        gap_str = 'Líder' if d['gap'] < 0.001 else f'+{d["gap"]:.3f}s'
        lap_str = _fmt_laptime(d['lap_time'])

        rows.append(html.Div([
            html.Span(f"{d['position']}", className="srow-pos"),
            html.Span(style={
                "width": "3px",
                "background": color,
                "display": "inline-block",
                "height": "28px",
                "verticalAlign": "middle",
                "marginRight": "8px",
                "borderRadius": "2px",
                "flexShrink": "0",
            }),
            html.Div([
                html.Span(d['driver'], className="srow-code"),
                html.Span(lap_str, className="srow-time"),
                html.Span(gap_str, className="srow-gap"),
            ], className="srow-info"),
        ], className="standing-row"))

    return rows


def _build_track_map(drivers, track_x, track_y):
    """Plotly circuit map with driver dots. Fixed ranges prevent dancing."""
    fig = go.Figure()

    x_range, y_range = None, None

    if track_x and track_y:
        # Close the loop
        xl = list(track_x) + [track_x[0]]
        yl = list(track_y) + [track_y[0]]

        # Thick dark road
        fig.add_trace(go.Scatter(
            x=xl, y=yl, mode='lines',
            line=dict(color='#2A2A4A', width=14),
            hoverinfo='none', showlegend=False,
        ))
        # Thin centre line
        fig.add_trace(go.Scatter(
            x=xl, y=yl, mode='lines',
            line=dict(color='#5A5A7A', width=3),
            hoverinfo='none', showlegend=False,
        ))

        # Compute fixed axis ranges with 5% padding
        x_arr = np.array(track_x, dtype=float)
        y_arr = np.array(track_y, dtype=float)
        x_pad = (x_arr.max() - x_arr.min()) * 0.05
        y_pad = (y_arr.max() - y_arr.min()) * 0.05
        x_range = [
            float(x_arr.min() - x_pad), float(x_arr.max() + x_pad)
        ]
        y_range = [
            float(y_arr.min() - y_pad), float(y_arr.max() + y_pad)
        ]

    for d in drivers:
        if not track_x and d['x'] == 0.0 and d['y'] == 0.0:
            continue

        color = TEAM_COLORS.get(d['team'], '#888888')
        gap_str = 'Líder' if d['gap'] < 0.001 else f'+{d["gap"]:.3f}s'

        fig.add_trace(go.Scatter(
            x=[d['x']], y=[d['y']],
            mode='markers+text',
            marker=dict(
                size=18, color=color,
                line=dict(color='white', width=1.5)
            ),
            text=[d['driver']],
            textposition='top center',
            textfont=dict(color='white', size=9, family='monospace'),
            name=d['driver'],
            hovertemplate=(
                f"<b>P{d['position']} {d['driver']}</b><br>"
                f"{gap_str}<br>"
                f"Volta: {_fmt_laptime(d['lap_time'])}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    xaxis_cfg = dict(
        visible=False, scaleanchor='y', scaleratio=1, fixedrange=True
    )
    yaxis_cfg = dict(visible=False, fixedrange=True)
    if x_range:
        xaxis_cfg['range'] = x_range
    if y_range:
        yaxis_cfg['range'] = y_range

    fig.update_layout(
        xaxis=xaxis_cfg,
        yaxis=yaxis_cfg,
        plot_bgcolor='#0A0A14',
        paper_bgcolor='#0A0A14',
        margin=dict(l=8, r=8, t=8, b=8),
        height=520,
        uirevision='race',  # preserves zoom/pan state between updates
    )
    return fig
