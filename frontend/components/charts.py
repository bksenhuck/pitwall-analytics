"""
Chart components.
Reusable chart functions using Plotly.
"""
import plotly.graph_objects as go
import plotly.express as px


def create_lap_time_chart(data, title="Lap Times"):
    """
    Create lap time line chart.
    
    Args:
        data: List of dicts with 'lap' and 'time' keys
        title: Chart title
    
    Returns:
        Plotly figure
    """
    if not data:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d.get('lap', i) for i, d in enumerate(data)],
        y=[d.get('time', 0) for d in data],
        mode='lines+markers',
        name='Lap Time'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Lap Number",
        yaxis_title="Time (seconds)",
        template="plotly_dark"
    )
    
    return fig


def create_position_chart(data, title="Position Changes"):
    """
    Create position line chart.
    
    Args:
        data: List of dicts with 'lap' and 'position' keys
        title: Chart title
    
    Returns:
        Plotly figure
    """
    if not data:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d.get('lap', i) for i, d in enumerate(data)],
        y=[d.get('position', 0) for d in data],
        mode='lines+markers',
        name='Position'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Lap Number",
        yaxis_title="Position",
        yaxis_autorange="reversed",  # Lower position = better
        template="plotly_dark"
    )
    
    return fig


def create_telemetry_chart(data, title="Speed Telemetry"):
    """
    Create telemetry chart (speed vs distance).
    
    Args:
        data: List of dicts with 'distance' and 'speed' keys
        title: Chart title
    
    Returns:
        Plotly figure
    """
    if not data:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d.get('distance', i) for i, d in enumerate(data)],
        y=[d.get('speed', 0) for d in data],
        mode='lines',
        name='Speed',
        line=dict(color='#FF1E00', width=2)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Distance (m)",
        yaxis_title="Speed (km/h)",
        template="plotly_dark"
    )
    
    return fig
