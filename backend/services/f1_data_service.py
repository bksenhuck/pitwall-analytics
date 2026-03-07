"""
F1 Data Service - Reads from Per-Season Normalized Cache

This service ONLY reads from the SQLite cache.
It NEVER calls FastF1 directly - that's done by populate_cache.py

Architecture:
1. populate_cache.py -> pitwall_{year}.db (writes)
2. DataRepository -> pitwall_{year}.db (reads, season-aware)
3. F1DataService -> DataRepository (business logic)
4. API routes -> F1DataService (HTTP)
5. Frontend -> API (UI)
"""
from typing import List, Dict, Any, Optional
from backend.repositories.data_repository import DataRepository


class F1DataService:
    """Service for F1 data operations using per-season cache"""

    def __init__(self):
        self.repo = DataRepository()

    # ===== SEASON METHODS =====

    def get_available_seasons(self) -> List[int]:
        """Get all seasons that have a DB file in the data directory."""
        return self.repo.get_all_seasons()

    def get_season_info(self, season: int) -> Optional[Dict[str, Any]]:
        """Get season statistics, or None if not found."""
        seasons = self.repo.get_all_seasons()
        if season not in seasons:
            return None
        return self.repo.get_season_stats(season)

    # ===== EVENT METHODS =====

    def get_races_for_season(self, season: int) -> List[Dict[str, Any]]:
        """Get all races/events for a season."""
        events = self.repo.get_events_for_season(season)

        return [
            {
                'round': e['round'],
                'name': e['name'],
                'location': e['location'],
                'country': e['country'],
                'date': e['date'],
                'format': e['format']
            }
            for e in events
        ]

    # ===== SESSION METHODS =====

    def load_session_data(
        self,
        season: int,
        event: str,
        session_type: str = 'R',
        include_laps: bool = True,
        include_results: bool = True,
        include_weather: bool = False,
        include_messages: bool = False,
        driver_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load complete session data from the season cache.

        Raises:
            Exception: If season, event or session not found in cache.
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(
                f"Event '{event}' not found for season {season} in cache"
            )

        event_id = event_data['id']

        session_data = self.repo.get_session(season, event_id, session_type)
        if not session_data:
            raise Exception(
                f"Session '{session_type}' not found for "
                f"{event} {season} in cache"
            )

        if not session_data['has_data']:
            raise Exception(
                f"Session '{session_type}' exists but has no data loaded"
            )

        session_id = session_data['id']

        response: Dict[str, Any] = {
            'session': {
                'season': season,
                'event': event_data['name'],
                'round': event_data['round'],
                'type': session_data['type'],
                'name': session_data['name'],
                'date': session_data['date'],
                'track_length': session_data['track_length']
            }
        }

        if include_laps:
            laps = self.repo.get_laps_for_session(
                season, session_id, driver_filter
            )
            response['laps'] = laps
            response['total_laps'] = len(laps)
            response['drivers'] = self.repo.get_drivers_in_session(
                season, session_id
            )

        if include_results:
            response['results'] = self.repo.get_results_for_session(
                season, session_id
            )

        if include_weather:
            response['weather'] = self.repo.get_weather_for_session(
                season, session_id
            )

        if include_messages:
            response['race_control_messages'] = (
                self.repo.get_race_control_messages(season, session_id)
            )
            response['session_status'] = self.repo.get_session_status(
                season, session_id
            )

        return response

    def get_session_laps(
        self,
        season: int,
        event: str,
        session_type: str = 'R',
        driver: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get lap data for a session."""
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(f"Event '{event}' not found")

        session_data = self.repo.get_session(
            season, event_data['id'], session_type
        )
        if not session_data:
            raise Exception("Session not found")

        return self.repo.get_laps_for_session(
            season, session_data['id'], driver
        )

    def get_session_results(
        self,
        season: int,
        event: str,
        session_type: str = 'R'
    ) -> List[Dict[str, Any]]:
        """Get results/standings for a session."""
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(f"Event '{event}' not found")

        session_data = self.repo.get_session(
            season, event_data['id'], session_type
        )
        if not session_data:
            raise Exception("Session not found")

        return self.repo.get_results_for_session(season, session_data['id'])

    # ===== DRIVER METHODS =====

    def get_drivers_in_session(
        self,
        season: int,
        event: str,
        session_type: str = 'R'
    ) -> List[str]:
        """Get list of drivers who participated in a session."""
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            return []

        session_data = self.repo.get_session(
            season, event_data['id'], session_type
        )
        if not session_data:
            return []

        return self.repo.get_drivers_in_session(season, session_data['id'])

    # ===== TELEMETRY METHODS =====

    def get_driver_telemetry(
        self,
        season: int,
        event: str,
        session_type: str,
        driver: str,
        lap_number: int
    ) -> Dict[str, Any]:
        """
        Get telemetry samples for a specific driver lap.

        Returns X/Y/Z position + car channels (speed, throttle, brake, etc.)
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(f"Event '{event}' not found for season {season}")

        session_data = self.repo.get_session(
            season, event_data['id'], session_type
        )
        if not session_data:
            raise Exception(
                f"Session '{session_type}' not found for {event} {season}"
            )

        lap_id = self.repo.get_lap_id(
            season, session_data['id'], driver, lap_number
        )
        if lap_id is None:
            raise Exception(
                f"Lap {lap_number} not found for driver {driver}"
            )

        samples = self.repo.get_telemetry_for_lap(season, lap_id)

        return {
            'season': season,
            'event': event_data['name'],
            'session_type': session_type,
            'driver': driver,
            'lap': lap_number,
            'samples': samples,
            'sample_count': len(samples)
        }

    # ===== TRACK LAYOUT =====

    def get_track_layout(
        self,
        season: int,
        event: str,
        session_type: str = 'R'
    ) -> Dict[str, Any]:
        """
        Get X/Y circuit layout from the fastest lap's telemetry.
        Returns empty arrays if telemetry is not populated.
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            return {"x": [], "y": [], "count": 0}

        session_data = self.repo.get_session(
            season, event_data['id'], session_type
        )
        if not session_data:
            return {"x": [], "y": [], "count": 0}

        return self.repo.get_track_layout_samples(
            season, session_data['id']
        )

    # ===== AVAILABILITY METHODS =====

    def get_available_data(self) -> Dict[str, Any]:
        """Get complete map of what data is available across all season DBs."""
        return self.repo.get_available_data()

    def get_available_sessions_for_event(
        self,
        season: int,
        event: str
    ) -> List[str]:
        """Get list of available session types for an event."""
        # Try finding via common repository methods
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            return []

        # If we have an event (even a dummy from the fallback), try getting sessions
        # In a Parquet-only environment, event_data['id'] will be 0, but we can search by name
        sessions = self.repo.get_sessions_for_event(season, event_data['id'] if event_data['id'] != 0 else event_data['name'])
        return [s['type'] for s in sessions if s['has_data']]

    # ===== STATISTICS =====

    def get_database_stats(self, season: int) -> Dict[str, Any]:
        """Get cache statistics for a specific season."""
        return self.repo.get_database_stats(season)
