"""
Data Repository V2 - For Normalized SQLite Schema

This repository provides clean CRUD operations for the normalized database.
Much more efficient than the V1 JSON blob approach.

All methods return dictionaries suitable for JSON serialization.
"""
from backend.db.session import get_db_connection
from typing import Optional, List, Dict, Any


class DataRepository:
    """Repository for F1 data using normalized schema"""
    
    # ===== SEASON METHODS =====
    
    @staticmethod
    def get_all_seasons() -> List[int]:
        """
        Get all available seasons.
        
        Returns:
            List of season years (e.g., [2023, 2024])
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT season FROM seasons ORDER BY season DESC")
            return [row['season'] for row in cursor.fetchall()]
    
    @staticmethod
    def get_season_stats(season: int) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a season.
        
        Returns:
            Dict with event count, session count, etc.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Event count
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM events 
                WHERE season = ?
            """, (season,))
            event_count = cursor.fetchone()['count']
            
            # Session count
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM sessions s
                JOIN events e ON s.event_id = e.id
                WHERE e.season = ? AND s.has_data = 1
            """, (season,))
            session_count = cursor.fetchone()['count']
            
            # Lap count
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
        """
        Get all events for a season.
        
        Returns:
            List of event dictionaries
        """
        with get_db_connection() as conn:
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
    def get_event_by_name(season: int, event_name: str) -> Optional[Dict[str, Any]]:
        """
        Get event by season and name.
        
        Returns:
            Event dictionary or None
        """
        with get_db_connection() as conn:
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
    def get_sessions_for_event(event_id: int) -> List[Dict[str, Any]]:
        """
        Get all sessions for an event.
        
        Returns:
            List of session dictionaries
        """
        with get_db_connection() as conn:
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
    def get_session(event_id: int, session_type: str) -> Optional[Dict[str, Any]]:
        """
        Get specific session.
        
        Returns:
            Session dictionary or None
        """
        with get_db_connection() as conn:
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
    def get_laps_for_session(session_id: int, driver_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get laps for a session.
        
        Args:
            session_id: Session ID
            driver_filter: Optional driver code/number filter
        
        Returns:
            List of lap dictionaries
        """
        with get_db_connection() as conn:
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
            
            laps = []
            for row in cursor.fetchall():
                laps.append(dict(row))
            
            return laps
    
    @staticmethod
    def get_drivers_in_session(session_id: int) -> List[str]:
        """
        Get list of drivers in a session.
        
        Returns:
            List of driver codes
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT driver_code
                FROM laps
                WHERE session_id = ?
                ORDER BY driver_code
            """, (session_id,))
            
            return [row['driver_code'] for row in cursor.fetchall()]
    
    # ===== RESULT METHODS =====
    
    @staticmethod
    def get_results_for_session(session_id: int) -> List[Dict[str, Any]]:
        """
        Get results/standings for a session.
        
        Returns:
            List of result dictionaries
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM results
                WHERE session_id = ?
                ORDER BY position
            """, (session_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
    
    # ===== WEATHER METHODS =====
    
    @staticmethod
    def get_weather_for_session(session_id: int) -> List[Dict[str, Any]]:
        """
        Get weather data for a session.
        
        Returns:
            List of weather data points
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM weather
                WHERE session_id = ?
                ORDER BY time_seconds
            """, (session_id,))
            
            weather = []
            for row in cursor.fetchall():
                weather.append(dict(row))
            
            return weather
    
    # ===== RACE CONTROL METHODS =====
    
    @staticmethod
    def get_race_control_messages(session_id: int) -> List[Dict[str, Any]]:
        """
        Get race control messages for a session.
        
        Returns:
            List of message dictionaries
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM race_control_messages
                WHERE session_id = ?
                ORDER BY time_seconds
            """, (session_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append(dict(row))
            
            return messages
    
    # ===== SESSION STATUS METHODS =====
    
    @staticmethod
    def get_session_status(session_id: int) -> List[Dict[str, Any]]:
        """
        Get session/track status changes.
        
        Returns:
            List of status change dictionaries
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM session_status
                WHERE session_id = ?
                ORDER BY time_seconds
            """, (session_id,))
            
            status = []
            for row in cursor.fetchall():
                status.append(dict(row))
            
            return status
    
    # ===== AVAILABILITY METHODS =====
    
    @staticmethod
    def get_available_data() -> Dict[str, Any]:
        """
        Get complete availability map of all cached data.
        
        Returns:
            Nested dictionary showing what's available:
            {
                "seasons": [2023, 2024],
                "2024": {
                    "events": ["Bahrain", "Saudi Arabian", ...],
                    "Bahrain": {
                        "sessions": ["FP1", "FP2", "FP3", "Q", "R"],
                        "R": {
                            "laps": 1234,
                            "results": 20,
                            "weather": 150,
                            "messages": 45
                        }
                    }
                }
            }
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all seasons
            cursor.execute("SELECT season FROM seasons ORDER BY season DESC")
            seasons = [row['season'] for row in cursor.fetchall()]
            
            result = {
                "seasons": seasons
            }
            
            # For each season, get events and sessions
            for season in seasons:
                season_data = {"events": []}
                
                cursor.execute("""
                    SELECT DISTINCT e.id, e.event_name 
                    FROM events e
                    JOIN sessions s ON s.event_id = e.id
                    WHERE e.season = ? AND s.has_data = 1
                    ORDER BY e.round_number
                """, (season,))
                
                for event_row in cursor.fetchall():
                    event_id = event_row['id']
                    event_name = event_row['event_name']
                    
                    # Skip test/pre-season events
                    if 'testing' in event_name.lower() or 'test' in event_name.lower():
                        continue
                    
                    # Get sessions for this event
                    cursor.execute("""
                        SELECT id, session_type, has_data
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
                    
                    # Only add event if it has sessions with data
                    if not sessions:
                        continue
                    
                    season_data["events"].append(event_name)
                    
                    event_sessions = {"sessions": []}
                    
                    for session_row in sessions:
                        session_id = session_row['id']
                        session_type = session_row['session_type']
                        
                        event_sessions["sessions"].append(session_type)
                        
                        # Get counts for this session
                        cursor.execute("SELECT COUNT(*) as count FROM laps WHERE session_id = ?", (session_id,))
                        lap_count = cursor.fetchone()['count']
                        
                        cursor.execute("SELECT COUNT(*) as count FROM results WHERE session_id = ?", (session_id,))
                        result_count = cursor.fetchone()['count']
                        
                        cursor.execute("SELECT COUNT(*) as count FROM weather WHERE session_id = ?", (session_id,))
                        weather_count = cursor.fetchone()['count']
                        
                        cursor.execute("SELECT COUNT(*) as count FROM race_control_messages WHERE session_id = ?", (session_id,))
                        message_count = cursor.fetchone()['count']
                        
                        event_sessions[session_type] = {
                            "laps": lap_count,
                            "results": result_count,
                            "weather": weather_count,
                            "messages": message_count
                        }
                    
                    season_data[event_name] = event_sessions
                
                result[str(season)] = season_data
            
            return result
    
    # ===== UTILITY METHODS =====
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """
        Get overall database statistics.
        
        Returns:
            Statistics dictionary
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM seasons")
            season_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM events")
            event_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE has_data = 1")
            session_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM laps")
            lap_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM results")
            result_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM weather")
            weather_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM race_control_messages")
            message_count = cursor.fetchone()['count']
            
            return {
                'seasons': season_count,
                'events': event_count,
                'sessions': session_count,
                'laps': lap_count,
                'results': result_count,
                'weather_points': weather_count,
                'race_control_messages': message_count
            }
