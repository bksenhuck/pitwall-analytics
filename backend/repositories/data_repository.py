"""
Data Repository - Per-Season Normalized SQLite Schema

All methods take a `season` parameter to open the correct DB file.
Season discovery is done by scanning the data/ directory for
pitwall_{year}.db files.
"""
from backend.db.session import get_db_connection, get_available_season_dbs
from typing import Optional, List, Dict, Any


class DataRepository:
    """Repository for F1 data using per-season normalized schema"""

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
        with get_db_connection(season) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) as count FROM events WHERE season = ?",
                (season,)
            )
            event_count = cursor.fetchone()['count']

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM sessions s
                JOIN events e ON s.event_id = e.id
                WHERE e.season = ? AND s.has_data = 1
            """, (season,))
            session_count = cursor.fetchone()['count']

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM laps l
                JOIN sessions s ON l.session_id = s.id
                JOIN events e ON s.event_id = e.id
                WHERE e.season = ?
            """, (season,))
            lap_count = cursor.fetchone()['count']

            return {
                'season': season,
                'events': event_count,
                'sessions': session_count,
                'laps': lap_count
            }

    # ===== EVENT METHODS =====

    @staticmethod
    def get_events_for_season(season: int) -> List[Dict[str, Any]]:
        """Get all events for a season."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, round_number, event_name, location, country,
                       event_date, event_format
                FROM events
                WHERE season = ?
                ORDER BY round_number
            """, (season,))

            events = []
            for row in cursor.fetchall():
                events.append({
                    'id': row['id'],
                    'round': row['round_number'],
                    'name': row['event_name'],
                    'location': row['location'],
                    'country': row['country'],
                    'date': row['event_date'],
                    'format': row['event_format']
                })

            return events

    @staticmethod
    def get_event_by_name(
        season: int, event_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get event by season and name (partial match)."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, round_number, event_name, location, country,
                       event_date, event_format
                FROM events
                WHERE season = ? AND event_name LIKE ?
            """, (season, f'%{event_name}%'))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row['id'],
                'round': row['round_number'],
                'name': row['event_name'],
                'location': row['location'],
                'country': row['country'],
                'date': row['event_date'],
                'format': row['event_format']
            }

    # ===== SESSION METHODS =====

    @staticmethod
    def get_sessions_for_event(
        season: int, event_id: int
    ) -> List[Dict[str, Any]]:
        """Get all sessions for an event."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_type, session_name, session_date,
                       track_length, total_laps, has_data
                FROM sessions
                WHERE event_id = ?
                ORDER BY
                    CASE session_type
                        WHEN 'FP1' THEN 1
                        WHEN 'FP2' THEN 2
                        WHEN 'FP3' THEN 3
                        WHEN 'SQ' THEN 4
                        WHEN 'S' THEN 5
                        WHEN 'Q' THEN 6
                        WHEN 'R' THEN 7
                        ELSE 99
                    END
            """, (event_id,))

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row['id'],
                    'type': row['session_type'],
                    'name': row['session_name'],
                    'date': row['session_date'],
                    'track_length': row['track_length'],
                    'total_laps': row['total_laps'],
                    'has_data': bool(row['has_data'])
                })

            return sessions

    @staticmethod
    def get_session(
        season: int, event_id: int, session_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific session."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_type, session_name, session_date,
                       track_length, total_laps, has_data
                FROM sessions
                WHERE event_id = ? AND session_type = ?
            """, (event_id, session_type))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row['id'],
                'type': row['session_type'],
                'name': row['session_name'],
                'date': row['session_date'],
                'track_length': row['track_length'],
                'total_laps': row['total_laps'],
                'has_data': bool(row['has_data'])
            }

    # ===== LAP METHODS =====

    @staticmethod
    def get_laps_for_session(
        season: int,
        session_id: int,
        driver_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get laps for a session, optionally filtered by driver."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()

            if driver_filter:
                cursor.execute("""
                    SELECT * FROM laps
                    WHERE session_id = ?
                      AND (driver_code = ? OR driver_number = ?)
                    ORDER BY lap_number
                """, (session_id, driver_filter, driver_filter))
            else:
                cursor.execute("""
                    SELECT * FROM laps
                    WHERE session_id = ?
                    ORDER BY lap_number, driver_number
                """, (session_id,))

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_drivers_in_session(
        season: int, session_id: int
    ) -> List[str]:
        """Get list of driver codes in a session."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT driver_code
                FROM laps
                WHERE session_id = ?
                ORDER BY driver_code
            """, (session_id,))

            return [row['driver_code'] for row in cursor.fetchall()]

    # ===== TELEMETRY METHODS =====

    @staticmethod
    def get_telemetry_for_lap(
        season: int, lap_id: int
    ) -> List[Dict[str, Any]]:
        """Get telemetry samples for a specific lap."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM telemetry
                WHERE lap_id = ?
                ORDER BY session_time_seconds
            """, (lap_id,))

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_lap_id(
        season: int, session_id: int, driver_number: str, lap_number: int
    ) -> Optional[int]:
        """Resolve internal lap id by (session, driver, lap_number)."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM laps
                WHERE session_id = ?
                  AND (driver_number = ? OR driver_code = ?)
                  AND lap_number = ?
            """, (session_id, driver_number, driver_number, lap_number))

            row = cursor.fetchone()
            return row['id'] if row else None

    # ===== RESULT METHODS =====

    @staticmethod
    def get_results_for_session(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get results/standings for a session."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM results
                WHERE session_id = ?
                ORDER BY position
            """, (session_id,))

            return [dict(row) for row in cursor.fetchall()]

    # ===== WEATHER METHODS =====

    @staticmethod
    def get_weather_for_session(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get weather data points for a session."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM weather
                WHERE session_id = ?
                ORDER BY time_seconds
            """, (session_id,))

            return [dict(row) for row in cursor.fetchall()]

    # ===== RACE CONTROL METHODS =====

    @staticmethod
    def get_race_control_messages(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get race control messages for a session."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM race_control_messages
                WHERE session_id = ?
                ORDER BY time_seconds
            """, (session_id,))

            return [dict(row) for row in cursor.fetchall()]

    # ===== SESSION STATUS METHODS =====

    @staticmethod
    def get_session_status(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get track status changes for a session."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM session_status
                WHERE session_id = ?
                ORDER BY time_seconds
            """, (session_id,))

            return [dict(row) for row in cursor.fetchall()]

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
                        "R": {"laps": 1234, "results": 20, ...}
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
                        event_id = event_row['id']
                        event_name = event_row['event_name']

                        cursor.execute("""
                            SELECT id, session_type
                            FROM sessions
                            WHERE event_id = ? AND has_data = 1
                            ORDER BY
                                CASE session_type
                                    WHEN 'FP1' THEN 1
                                    WHEN 'FP2' THEN 2
                                    WHEN 'FP3' THEN 3
                                    WHEN 'SQ' THEN 4
                                    WHEN 'S' THEN 5
                                    WHEN 'Q' THEN 6
                                    WHEN 'R' THEN 7
                                    ELSE 99
                                END
                        """, (event_id,))
                        sessions = cursor.fetchall()

                        if not sessions:
                            continue

                        season_data["events"].append(event_name)
                        event_sessions: Dict[str, Any] = {"sessions": []}

                        for session_row in sessions:
                            stype = session_row['session_type']
                            event_sessions["sessions"].append(stype)

                        season_data[event_name] = event_sessions

                    result[str(season)] = season_data

            except Exception as e:
                print(f"⚠️  Could not read season {season} DB: {e}")
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
        with get_db_connection(season) as conn:
            cursor = conn.cursor()

            # Fastest accurate non-formation lap
            cursor.execute("""
                SELECT id FROM laps
                WHERE session_id = ?
                  AND lap_time_seconds IS NOT NULL
                  AND is_accurate = 1
                  AND lap_number > 1
                ORDER BY lap_time_seconds ASC
                LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()

            if not row:
                return {"x": [], "y": [], "count": 0}

            lap_id = row['id']

            cursor.execute("""
                SELECT x, y FROM telemetry
                WHERE lap_id = ?
                ORDER BY session_time_seconds
            """, (lap_id,))
            rows = cursor.fetchall()

            return {
                "x": [r['x'] for r in rows],
                "y": [r['y'] for r in rows],
                "count": len(rows)
            }

    # ===== UTILITY METHODS =====

    @staticmethod
    def get_database_stats(season: int) -> Dict[str, Any]:
        """Get statistics for a specific season DB."""
        with get_db_connection(season) as conn:
            cursor = conn.cursor()

            def count(table, where=""):
                q = f"SELECT COUNT(*) as c FROM {table}"
                if where:
                    q += f" WHERE {where}"
                cursor.execute(q)
                return cursor.fetchone()['c']

            return {
                'season': season,
                'events': count('events'),
                'sessions': count('sessions', 'has_data = 1'),
                'laps': count('laps'),
                'telemetry_samples': count('telemetry'),
                'results': count('results'),
                'weather_points': count('weather'),
                'race_control_messages': count('race_control_messages')
            }
