from typing import Optional

import plotly.graph_objs as go
import pandas as pd


def lap_time_chart(laps: pd.DataFrame, driver: Optional[str] = None) -> go.Figure:
    """Return a lap time chart (lap number vs lap time seconds).

    If `driver` is provided, filter laps to that driver.
    """
    df = laps
    if driver:
        df = df[df["Driver"] == driver]

    fig = go.Figure()
    if not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["LapNumber"],
                y=df["LapTimeSeconds"],
                mode="lines+markers",
                name=f"Lap Time {driver or 'all'}",
            )
        )

    fig.update_layout(
        title="Lap Time (seconds)",
        xaxis_title="Lap",
        yaxis_title="Time (s)",
        template="plotly_white",
    )
    return fig


def position_chart(laps: pd.DataFrame, driver: Optional[str] = None) -> go.Figure:
    """Return a race position over laps chart."""
    df = laps
    if driver:
        df = df[df["Driver"] == driver]

    fig = go.Figure()
    if not df.empty and "Position" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["LapNumber"],
                y=df["Position"],
                mode="lines+markers",
                name=f"Position {driver or 'all'}",
            )
        )
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        title="Race Position Over Laps",
        xaxis_title="Lap",
        yaxis_title="Position",
        template="plotly_white",
    )
    return fig


def speed_telemetry_chart(telemetry: pd.DataFrame) -> go.Figure:
    """Plot speed over distance/time from telemetry.

    Assumes telemetry contains 'Speed' and 'Distance' or index time.
    """
    fig = go.Figure()
    if telemetry.empty:
        fig.update_layout(title="No telemetry available", template="plotly_white")
        return fig

    x_col = None
    if "Distance" in telemetry.columns:
        x_col = "Distance"
    elif "Time" in telemetry.columns:
        x_col = "Time"
    else:
        # fallback to index
        telemetry = telemetry.reset_index()
        x_col = telemetry.columns[0]

    fig.add_trace(
        go.Scatter(x=telemetry[x_col], y=telemetry["Speed"], mode="lines", name="Speed")
    )

    fig.update_layout(
        title="Telemetry: Speed",
        xaxis_title=x_col,
        yaxis_title="Speed (km/h)",
        template="plotly_white",
    )
    return fig
