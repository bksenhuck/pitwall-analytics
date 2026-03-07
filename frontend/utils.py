"""
Shared helpers and UI components for frontend pages.
"""
import pandas as pd
from dash import html


# ── Palette ────────────────────────────────────────────────────────────────────
MUTED   = "#6B7280"
PRIMARY = "#003082"
BORDER  = "#DDE1E7"
SURFACE = "#F4F5F7"


# ── Formatters ─────────────────────────────────────────────────────────────────

def fmt_lap(seconds) -> str:
    """Format seconds as MM:SS.mmm. Returns '-' for invalid values."""
    try:
        if seconds is None or pd.isna(seconds) or seconds <= 0:
            return "-"
    except (TypeError, ValueError):
        return "-"
    m  = int(seconds // 60)
    s  = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{m:02d}:{s:02d}.{ms:03d}"


# Alias kept for backward-compat within the session
fmt_laptime_full = fmt_lap


# ── Color helpers ──────────────────────────────────────────────────────────────

def hex_to_rgba(hex_color: str, alpha: float = 0.3) -> str:
    """Convert a hex color string to an rgba() CSS value."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Dropdown helpers ───────────────────────────────────────────────────────────

def seasons_to_options(seasons: list) -> list:
    return [{"label": str(s), "value": s} for s in seasons]


# ── Alert components ───────────────────────────────────────────────────────────

def alert_cache_empty() -> html.Div:
    """Warning shown when the SQLite cache has no data."""
    return html.Div([
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


def alert_backend_error() -> html.Div:
    """Error shown when the backend is unreachable."""
    return html.Div([
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
