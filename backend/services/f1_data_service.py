"""
F1 Data Service - Reads from Normalized Cache

This service ONLY reads from the SQLite cache.
It NEVER calls FastF1 directly - that's done by populate_cache.py

Benefits:
- Fast response (no FastF1 API calls)
- Offline operation
- Predictable performance
- Frontend only shows what's in cache

Architecture:
1. populate_cache.py -> SQLite (writes)
2. DataRepository -> SQLite (reads)
3. F1DataService -> DataRepository (business logic)
4. API routes -> F1DataService (HTTP)
5. Frontend -> API (UI)
"""
from typing import List, Dict, Any, Optional
from backend.repositories.data_repository import DataRepository


class F1DataService:
    """Service for F1 data operations using cache ONLY"""
    
    def __init__(self):
        """Initialize service with repository"""
        self.repo = DataRepository()
    
    # ===== SEASON METHODS =====
    
    def get_available_seasons(self) -> List[int]:
        """
        Get all available seasons from cache.
        
        Returns:
            List of season years
        """
        return self.repo.get_all_seasons()
    
    def get_season_info(self, season: int) -> Optional[Dict[str, Any]]:
        """
        Get season information and statistics.
        
        Returns:
            Season info dict or None if not found
        """
        seasons = self.repo.get_all_seasons()
        if season not in seasons:
            return None
        
        stats = self.repo.get_season_stats(season)
        return stats
    
    # ===== EVENT METHODS =====
    
    def get_races_for_season(self, season: int) -> List[Dict[str, Any]]:
        """
        Get all races/events for a season.
        
        Args:
            season: Year (e.g., 2024)
        
        Returns:
            List of event dictionaries
        """
        events = self.repo.get_events_for_season(season)
        
        # Format for frontend compatibility
        formatted = []
        for event in events:
            formatted.append({
                'round': event['round'],
                'name': event['name'],
                'location': event['location'],
                'country': event['country'],
                'date': event['date'],
                'format': event['format']
            })
        
        return formatted
    
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
        Load complete session data from cache.
        
        Args:
            season: Year
            event: Event name (e.g., "Bahrain")
            session_type: Session type ('R', 'Q', 'FP1', etc.)
            include_laps: Include lap data
            include_results: Include results/standings
            include_weather: Include weather data
            include_messages: Include race control messages
            driver_filter: Optional driver code filter
        
        Returns:
            Complete session data dictionary
            
        Raises:
            Exception: If session not found in cache
        """
        # Get event
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(f"Event '{event}' not found for season {season} in cache")
        
        event_id = event_data['id']
        
        # Get session
        session_data = self.repo.get_session(event_id, session_type)
        if not session_data:
            raise Exception(f"Session '{session_type}' not found for {event} {season} in cache")
        
        if not session_data['has_data']:
            raise Exception(f"Session '{session_type}' exists but has no data loaded")
        
        session_id = session_data['id']
        
        # Build response
        response = {
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
        
        # Add requested data
        if include_laps:
            laps = self.repo.get_laps_for_session(session_id, driver_filter)
            response['laps'] = laps
            response['total_laps'] = len(laps)
            
            # Get drivers list
            drivers = self.repo.get_drivers_in_session(session_id)
            response['drivers'] = drivers
        
        if include_results:
            results = self.repo.get_results_for_session(session_id)
            response['results'] = results
        
        if include_weather:
            weather = self.repo.get_weather_for_session(session_id)
            response['weather'] = weather
        
        if include_messages:
            messages = self.repo.get_race_control_messages(session_id)
            response['race_control_messages'] = messages
            
            status = self.repo.get_session_status(session_id)
            response['session_status'] = status
        
        return response
    
    def get_session_laps(
        self, 
        season: int, 
        event: str, 
        session_type: str = 'R',
        driver: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get lap data for a session.
        
        Args:
            season: Year
            event: Event name
            session_type: Session type
            driver: Optional driver filter
        
        Returns:
            List of lap dictionaries
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(f"Event '{event}' not found")
        
        session_data = self.repo.get_session(event_data['id'], session_type)
        if not session_data:
            raise Exception(f"Session not found")
        
        return self.repo.get_laps_for_session(session_data['id'], driver)
    
    def get_session_results(
        self, 
        season: int, 
        event: str, 
        session_type: str = 'R'
    ) -> List[Dict[str, Any]]:
        """
        Get results/standings for a session.
        
        Args:
            season: Year
            event: Event name
            session_type: Session type
        
        Returns:
            List of result dictionaries
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            raise Exception(f"Event '{event}' not found")
        
        session_data = self.repo.get_session(event_data['id'], session_type)
        if not session_data:
            raise Exception(f"Session not found")
        
        return self.repo.get_results_for_session(session_data['id'])
    
    # ===== DRIVER METHODS =====
    
    def get_drivers_in_session(
        self, 
        season: int, 
        event: str, 
        session_type: str = 'R'
    ) -> List[str]:
        """
        Get list of drivers who participated in a session.
        
        Args:
            season: Year
            event: Event name
            session_type: Session type
        
        Returns:
            List of driver codes
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            return []
        
        session_data = self.repo.get_session(event_data['id'], session_type)
        if not session_data:
            return []
        
        return self.repo.get_drivers_in_session(session_data['id'])
    
    # ===== AVAILABILITY METHODS =====
    
    def get_available_data(self) -> Dict[str, Any]:
        """
        Get complete map of what data is available in cache.
        
        This is CRITICAL for the frontend to only show what exists.
        
        Returns:
            Nested availability dictionary
        """
        return self.repo.get_available_data()
    
    def get_available_sessions_for_event(
        self, 
        season: int, 
        event: str
    ) -> List[str]:
        """
        Get list of available session types for an event.
        
        Args:
            season: Year
            event: Event name
        
        Returns:
            List of session types (e.g., ['FP1', 'FP2', 'Q', 'R'])
        """
        event_data = self.repo.get_event_by_name(season, event)
        if not event_data:
            return []
        
        sessions = self.repo.get_sessions_for_event(event_data['id'])
        
        # Return only sessions that have data
        return [s['type'] for s in sessions if s['has_data']]
    
    # ===== STATISTICS =====
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overall cache statistics.
        
        Returns:
            Stats dictionary
        """
        return self.repo.get_database_stats()
    
    # ===== TELEMETRY PLACEHOLDER =====
    
    def get_driver_telemetry(
        self, 
        season: int,
        event: str,
        session_type: str,
        driver: str, 
        lap_number: int
    ) -> Dict[str, Any]:
        """
        Placeholder for telemetry data.
        
        NOTE: Telemetry is not stored in cache due to size.
        This would require loading from FastF1 on-demand or
        storing in a separate telemetry table/file.
        
        For now, returns empty placeholder.
        """
        return {
            'driver': driver,
            'lap': lap_number,
            'telemetry': [],
            'note': 'Telemetry not cached - use FastF1 directly if needed'
        }
