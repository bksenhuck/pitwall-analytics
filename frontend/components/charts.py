"""
Plotly chart components for F1 analytics.

All charts return plotly.graph_objs.Figure objects that can be
used with dcc.Graph components in Dash.
"""
from typing import Optional
import plotly.graph_objs as go
import pandas as pd


def lap_time_chart(laps: pd.DataFrame, driver: Optional[str] = None) -> go.Figure:
    """
    Create a lap time chart (lap number vs lap time seconds).
    
    Args:
        laps: DataFrame with columns LapNumber, LapTimeSeconds, Driver
        driver: Optional driver code to filter by
    
    Returns:
        Plotly Figure object
    """
    df = laps.copy()
    
    if driver:
        df = df[df["Driver"] == driver]

    fig = go.Figure()
    
    if not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["LapNumber"],
                y=df["LapTimeSeconds"],
                mode="lines+markers",
                name=f"Lap Time {driver or 'All Drivers'}",
                line=dict(width=2),
                marker=dict(size=6)
            )
        )

    fig.update_layout(
        title="Lap Time Analysis",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        template="plotly_white",
        hovermode="x unified",
        height=400
    )
    
    return fig


def position_chart(laps: pd.DataFrame, driver: Optional[str] = None) -> go.Figure:
    """
    Create a race position over laps chart.
    
    Args:
        laps: DataFrame with columns LapNumber, Position, Driver
        driver: Optional driver code to filter by
    
    Returns:
        Plotly Figure object
    """
    df = laps.copy()
    
    if driver:
        df = df[df["Driver"] == driver]

    fig = go.Figure()
    
    if not df.empty and "Position" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["LapNumber"],
                y=df["Position"],
                mode="lines+markers",
                name=f"Position {driver or 'All Drivers'}",
                line=dict(width=2),
                marker=dict(size=6)
            )
        )
        # Reverse Y-axis so position 1 is at the top
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        title="Race Position Over Laps",
        xaxis_title="Lap Number",
        yaxis_title="Position",
        template="plotly_white",
        hovermode="x unified",
        height=400
    )
    
    return fig


def speed_telemetry_chart(telemetry: pd.DataFrame) -> go.Figure:
    """
    Plot speed over distance/time from telemetry.
    
    Args:
        telemetry: DataFrame with Speed and Distance/Time columns
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    if telemetry.empty:
        fig.update_layout(
            title="No Telemetry Available",
            template="plotly_white",
            annotations=[{
                'text': 'Telemetry data is not stored in the cache',
                'showarrow': False,
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'font': {'size': 14, 'color': 'gray'}
            }]
        )
        return fig

    # Determine X-axis column
    x_col = None
    if "Distance" in telemetry.columns:
        x_col = "Distance"
        x_label = "Distance (m)"
    elif "Time" in telemetry.columns:
        x_col = "Time"
        x_label = "Time (s)"
    else:
        # Fallback to index
        telemetry = telemetry.reset_index()
        x_col = telemetry.columns[0]
        x_label = "Index"

    if "Speed" in telemetry.columns:
        fig.add_trace(
            go.Scatter(
                x=telemetry[x_col],
                y=telemetry["Speed"],
                mode="lines",
                name="Speed",
                line=dict(width=2)
            )
        )

    fig.update_layout(
        title="Speed Telemetry",
        xaxis_title=x_label,
        yaxis_title="Speed (km/h)",
        template="plotly_white",
        hovermode="x unified",
        height=400
    )
    
    return fig


def driver_comparison_chart(laps: pd.DataFrame, drivers: list) -> go.Figure:
    """
    Compare lap times for multiple drivers.
    
    Args:
        laps: DataFrame with LapNumber, LapTimeSeconds, Driver
        drivers: List of driver codes to compare
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    for driver in drivers:
        driver_laps = laps[laps["Driver"] == driver]
        
        if not driver_laps.empty:
            fig.add_trace(
                go.Scatter(
                    x=driver_laps["LapNumber"],
                    y=driver_laps["LapTimeSeconds"],
                    mode="lines+markers",
                    name=driver,
                    line=dict(width=2),
                    marker=dict(size=5)
                )
            )
    
    fig.update_layout(
        title="Driver Comparison - Lap Times",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        template="plotly_white",
        hovermode="x unified",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig
