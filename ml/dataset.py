"""
dataset.py — Extract historical race data from local SQLite databases.

Each season lives in data/pitwall_{year}.db.
Queries the 'results', 'sessions', and 'events' tables for all Race sessions.
"""
import pandas as pd

from backend.db.session import get_available_season_dbs
from backend.db.utils import db_fetchall


def load_race_results() -> pd.DataFrame:
    """
    Load all race results across every available season database.

    Returns a DataFrame with columns:
        season, round_number, event_name, location, country,
        driver_number, grid_position, position, points, status
    """
    seasons = get_available_season_dbs()
    frames = []

    for season in seasons:
        try:
            rows = db_fetchall(season, """
                SELECT
                    e.season,
                    e.round_number,
                    e.event_name,
                    e.location,
                    e.country,
                    r.driver_number,
                    r.driver_code,
                    r.grid_position,
                    r.position,
                    r.points,
                    r.status
                FROM results r
                JOIN sessions s ON r.session_id = s.id
                JOIN events e ON s.event_id = e.id
                WHERE s.session_type = 'R'
                  AND r.position IS NOT NULL
                ORDER BY e.season, e.round_number
            """, ())
        except Exception:
            continue

        if rows:
            frames.append(pd.DataFrame(rows))

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df["grid_position"] = pd.to_numeric(df["grid_position"], errors="coerce")
    df["round_number"] = pd.to_numeric(df["round_number"], errors="coerce")
    return df
