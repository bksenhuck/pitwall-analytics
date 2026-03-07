"""
Data Repository - Per-Season Normalized SQLite Schema

All methods take a `season` parameter to open the correct DB file.
Season discovery is done by scanning the data/ directory for
pitwall_{year}.db files.
"""
import os
import pandas as pd
from typing import Optional, List, Dict, Any

from backend.db.session import get_db_connection, get_available_season_dbs
from backend.db.utils import db_fetchone, db_fetchall


class DataRepository:
    """Repository for F1 data using per-season normalized schema"""

    # Local storage for optimized files
    TELEMETRY_DATA_DIR = os.path.join("data", "telemetry")
    LAPS_DATA_DIR = os.path.join("data", "laps")
    WEATHER_DATA_DIR = os.path.join("data", "weather")
    RESULTS_DATA_DIR = os.path.join("data", "results")

    # ===== SEASON METHODS =====

    @staticmethod
    def get_all_seasons() -> List[int]:
        """
        Discover available seasons by scanning the data directory.

        Returns:
            List of season years (descending) with an existing DB file.
        """
        return get_available_season_dbs()

    @staticmethod
    def get_season_stats(season: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a season."""
        event_count = (db_fetchone(
            season,
            "SELECT COUNT(*) as count FROM events WHERE season = ?",
            (season,),
        ) or {}).get("count", 0)

        session_count = (db_fetchone(season, """
            SELECT COUNT(*) as count
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            WHERE e.season = ? AND s.has_data = 1
        """, (season,)) or {}).get("count", 0)

        lap_count = (db_fetchone(season, """
            SELECT COUNT(*) as count
            FROM laps l
            JOIN sessions s ON l.session_id = s.id
            JOIN events e ON s.event_id = e.id
            WHERE e.season = ?
        """, (season,)) or {}).get("count", 0)

        return {
            "season": season,
            "events": event_count,
            "sessions": session_count,
            "laps": lap_count,
        }

    # ===== EVENT METHODS =====

    @staticmethod
    def get_events_for_season(season: int) -> List[Dict[str, Any]]:
        """Get all events for a season."""
        rows = db_fetchall(season, """
            SELECT id, round_number, event_name, location, country,
                   event_date, event_format
            FROM events
            WHERE season = ?
            ORDER BY round_number
        """, (season,))
        return [
            {
                "id": r["id"],
                "round": r["round_number"],
                "name": r["event_name"],
                "location": r["location"],
                "country": r["country"],
                "date": r["event_date"],
                "format": r["event_format"],
            }
            for r in rows
        ]

    @staticmethod
    def get_event_by_name(
        season: int, event_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get event by season and name (partial match)."""
        row = db_fetchone(season, """
            SELECT id, round_number, event_name, location, country,
                   event_date, event_format
            FROM events
            WHERE season = ? AND event_name LIKE ?
        """, (season, f"%{event_name}%"))
        if not row:
            return None
        return {
            "id": row["id"],
            "round": row["round_number"],
            "name": row["event_name"],
            "location": row["location"],
            "country": row["country"],
            "date": row["event_date"],
            "format": row["event_format"],
        }

    # ===== SESSION METHODS =====

    @staticmethod
    def get_sessions_for_event(
        season: int, event_id: int
    ) -> List[Dict[str, Any]]:
        """Get all sessions for an event."""
        rows = db_fetchall(season, """
            SELECT id, session_type, session_name, session_date,
                   track_length, total_laps, has_data
            FROM sessions
            WHERE event_id = ?
            ORDER BY
                CASE session_type
                    WHEN 'FP1' THEN 1
                    WHEN 'FP2' THEN 2
                    WHEN 'FP3' THEN 3
                    WHEN 'SQ'  THEN 4
                    WHEN 'S'   THEN 5
                    WHEN 'Q'   THEN 6
                    WHEN 'R'   THEN 7
                    ELSE 99
                END
        """, (event_id,))
        return [
            {
                "id": r["id"],
                "type": r["session_type"],
                "name": r["session_name"],
                "date": r["session_date"],
                "track_length": r["track_length"],
                "total_laps": r["total_laps"],
                "has_data": bool(r["has_data"]),
            }
            for r in rows
        ]

    @staticmethod
    def get_session(
        season: int, event_id: int, session_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific session."""
        row = db_fetchone(season, """
            SELECT id, session_type, session_name, session_date,
                   track_length, total_laps, has_data
            FROM sessions
            WHERE event_id = ? AND session_type = ?
        """, (event_id, session_type))
        if not row:
            return None
        return {
            "id": row["id"],
            "type": row["session_type"],
            "name": row["session_name"],
            "date": row["session_date"],
            "track_length": row["track_length"],
            "total_laps": row["total_laps"],
            "has_data": bool(row["has_data"]),
        }

    # ===== LAP METHODS =====

    @staticmethod
    def get_laps_for_session(
        season: int,
        session_id: int,
        driver_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get laps for a session, optionally filtered by driver.
        Tries Event-based Parquet first, falls back to SQLite.
        """
        row = db_fetchone(
            season,
            "SELECT event_id FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not row:
            return []
        event_id = row["event_id"]

        parquet_path = os.path.join(
            DataRepository.LAPS_DATA_DIR,
            str(season),
            f"event_{event_id}.parquet",
        )
        if os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path)
                df = df[df["session_id"] == session_id]
                if driver_filter:
                    mask = (
                        (df["driver_code"] == driver_filter)
                        | (df["driver_number"] == str(driver_filter))
                    )
                    df = df[mask]
                return df.to_dict(orient="records")
            except Exception as e:
                print(f"Error reading Laps Parquet for event {event_id}: {e}")

        # SQLite fallback
        if driver_filter:
            return db_fetchall(season, """
                SELECT * FROM laps
                WHERE session_id = ?
                  AND (driver_code = ? OR driver_number = ?)
                ORDER BY lap_number
            """, (session_id, driver_filter, driver_filter))

        return db_fetchall(season, """
            SELECT * FROM laps
            WHERE session_id = ?
            ORDER BY lap_number, driver_number
        """, (session_id,))

    @staticmethod
    def get_drivers_in_session(
        season: int, session_id: int
    ) -> List[str]:
        """Get list of driver codes in a session."""
        rows = db_fetchall(season, """
            SELECT DISTINCT driver_code
            FROM laps
            WHERE session_id = ?
            ORDER BY driver_code
        """, (session_id,))
        return [r["driver_code"] for r in rows]

    # ===== TELEMETRY METHODS =====

    @staticmethod
    def get_telemetry_for_lap(
        season: int, lap_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get telemetry samples for a specific lap.
        Tries Event-based Parquet first, falls back to SQLite.
        """
        row = db_fetchone(season, """
            SELECT s.event_id FROM laps l
            JOIN sessions s ON l.session_id = s.id
            WHERE l.id = ?
        """, (lap_id,))
        if not row:
            return []
        event_id = row["event_id"]

        parquet_path = os.path.join(
            DataRepository.TELEMETRY_DATA_DIR,
            str(season),
            f"event_{event_id}.parquet",
        )
        if os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path)
                if "lap_id" in df.columns:
                    return df[df["lap_id"] == lap_id].to_dict(orient="records")
            except Exception as e:
                print(f"Error reading Telemetry Parquet for lap {lap_id}: {e}")

        return db_fetchall(season, """
            SELECT * FROM telemetry
            WHERE lap_id = ?
            ORDER BY session_time_seconds
        """, (lap_id,))

    @staticmethod
    def get_lap_id(
        season: int, session_id: int, driver_number: str, lap_number: int
    ) -> Optional[int]:
        """Resolve internal lap id by (session, driver, lap_number)."""
        row = db_fetchone(season, """
            SELECT id FROM laps
            WHERE session_id = ?
              AND (driver_number = ? OR driver_code = ?)
              AND lap_number = ?
        """, (session_id, driver_number, driver_number, lap_number))
        return row["id"] if row else None

    # ===== RESULT METHODS =====

    @staticmethod
    def get_results_for_session(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get results for a session.
        Tries Event-based Parquet first, falls back to SQLite.
        """
        row = db_fetchone(
            season,
            "SELECT event_id FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not row:
            return []
        event_id = row["event_id"]

        parquet_path = os.path.join(
            DataRepository.RESULTS_DATA_DIR,
            str(season),
            f"event_{event_id}.parquet",
        )
        if os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path)
                df = df[df["session_id"] == session_id]
                return df.to_dict(orient="records")
            except Exception as e:
                print(
                    f"Error reading Results Parquet for event {event_id}: {e}"
                )

        return db_fetchall(season, """
            SELECT * FROM results
            WHERE session_id = ?
            ORDER BY position
        """, (session_id,))

    # ===== WEATHER METHODS =====

    @staticmethod
    def get_weather_for_session(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get weather for a session.
        Tries Event-based Parquet first, falls back to SQLite.
        """
        row = db_fetchone(
            season,
            "SELECT event_id FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not row:
            return []
        event_id = row["event_id"]

        parquet_path = os.path.join(
            DataRepository.WEATHER_DATA_DIR,
            str(season),
            f"event_{event_id}.parquet",
        )
        if os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path)
                df = df[df["session_id"] == session_id]
                return df.to_dict(orient="records")
            except Exception as e:
                print(
                    f"Error reading Weather Parquet for event {event_id}: {e}"
                )

        return db_fetchall(season, """
            SELECT * FROM weather
            WHERE session_id = ?
            ORDER BY time_seconds
        """, (session_id,))

    # ===== RACE CONTROL METHODS =====

    @staticmethod
    def get_race_control_messages(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get race control messages for a session."""
        return db_fetchall(season, """
            SELECT * FROM race_control_messages
            WHERE session_id = ?
            ORDER BY time_seconds
        """, (session_id,))

    # ===== SESSION STATUS METHODS =====

    @staticmethod
    def get_session_status(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get track status changes for a session."""
        return db_fetchall(season, """
            SELECT * FROM session_status
            WHERE session_id = ?
            ORDER BY time_seconds
        """, (session_id,))

    # ===== AVAILABILITY METHODS =====

    @staticmethod
    def get_available_data() -> Dict[str, Any]:
        """
        Get complete availability map across all season DBs.

        Returns:
            {
                "seasons": [2024, 2023],
                "2024": {
                    "events": ["Bahrain Grand Prix", ...],
                    "Bahrain Grand Prix": {
                        "sessions": ["FP1", "Q", "R"],
                    }
                }
            }
        """
        seasons = get_available_season_dbs()
        result: Dict[str, Any] = {"seasons": seasons}

        for season in seasons:
            try:
                with get_db_connection(season) as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT DISTINCT e.id, e.event_name
                        FROM events e
                        JOIN sessions s ON s.event_id = e.id
                        WHERE e.season = ? AND s.has_data = 1
                        ORDER BY e.round_number
                    """, (season,))
                    events_rows = cursor.fetchall()

                    season_data: Dict[str, Any] = {"events": []}

                    for event_row in events_rows:
                        event_id = event_row["id"]
                        event_name = event_row["event_name"]

                        cursor.execute("""
                            SELECT id, session_type
                            FROM sessions
                            WHERE event_id = ? AND has_data = 1
                            ORDER BY
                                CASE session_type
                                    WHEN 'FP1' THEN 1
                                    WHEN 'FP2' THEN 2
                                    WHEN 'FP3' THEN 3
                                    WHEN 'SQ'  THEN 4
                                    WHEN 'S'   THEN 5
                                    WHEN 'Q'   THEN 6
                                    WHEN 'R'   THEN 7
                                    ELSE 99
                                END
                        """, (event_id,))
                        sessions = cursor.fetchall()

                        if not sessions:
                            continue

                        season_data["events"].append(event_name)
                        season_data[event_name] = {
                            "sessions": [
                                s["session_type"] for s in sessions
                            ]
                        }

                    result[str(season)] = season_data

            except Exception as e:
                print(f"Could not read season {season} DB: {e}")
                continue

        return result

    # ===== TRACK LAYOUT METHODS =====

    @staticmethod
    def get_track_layout_samples(
        season: int, session_id: int
    ) -> Dict[str, Any]:
        """
        Get X/Y telemetry from the fastest accurate lap in a session.
        Used to draw the circuit outline.
        """
        lap = db_fetchone(season, """
            SELECT id FROM laps
            WHERE session_id = ?
              AND lap_time_seconds IS NOT NULL
              AND is_accurate = 1
              AND lap_number > 1
            ORDER BY lap_time_seconds ASC
            LIMIT 1
        """, (session_id,))

        if not lap:
            return {"x": [], "y": [], "count": 0}

        rows = db_fetchall(season, """
            SELECT x, y FROM telemetry
            WHERE lap_id = ?
            ORDER BY session_time_seconds
        """, (lap["id"],))

        return {
            "x": [r["x"] for r in rows],
            "y": [r["y"] for r in rows],
            "count": len(rows),
        }

    # ===== UTILITY METHODS =====

    @staticmethod
    def get_database_stats(season: int) -> Dict[str, Any]:
        """Get statistics for a specific season DB."""
        # Table names are hardcoded constants — not user input.
        _ALLOWED = {
            "events", "sessions", "laps",
            "telemetry", "results", "weather", "race_control_messages",
        }

        with get_db_connection(season) as conn:
            cursor = conn.cursor()

            def count(table: str, where: str = "") -> int:
                if table not in _ALLOWED:
                    raise ValueError(f"Unknown table: {table}")
                q = f"SELECT COUNT(*) as c FROM {table}"  # noqa: S608
                if where:
                    q += f" WHERE {where}"
                cursor.execute(q)
                return cursor.fetchone()["c"]

            return {
                "season": season,
                "events": count("events"),
                "sessions": count("sessions", "has_data = 1"),
                "laps": count("laps"),
                "telemetry_samples": count("telemetry"),
                "results": count("results"),
                "weather_points": count("weather"),
                "race_control_messages": count("race_control_messages"),
            }
