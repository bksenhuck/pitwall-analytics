"""
Frontend Integration Example - Using Normalized Cache

This module shows how the frontend should integrate with the cache API
to ONLY show data that's actually available.

Key principle: 
    Frontend asks "what do you have?" BEFORE trying to load anything.
"""
import requests
from typing import List, Dict, Any, Optional


class CachedDataClient:
    """Client for accessing cached F1 data via API"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:5000"):
        """
        Initialize client.
        
        Args:
            api_url: Backend API base URL
        """
        self.api_url = api_url
        self.api_data_url = f"{api_url}/api"
        self._available_cache = None
    
    # ===== AVAILABILITY METHODS =====
    
    def get_available_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get complete availability map.
        
        This should be called ONCE at app startup and cached.
        
        Args:
            force_refresh: Force fetch from API (ignore cache)
        
        Returns:
            Availability tree
        """
        if self._available_cache is not None and not force_refresh:
            return self._available_cache
        
        response = requests.get(f"{self.api_data_url}/data/available")
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            self._available_cache = data['data']
            return self._available_cache
        else:
            raise Exception("Failed to fetch available data")
    
    def get_available_seasons(self) -> List[int]:
        """
        Get list of available seasons.
        
        Use this to populate season dropdown!
        
        Returns:
            List of season years
        """
        available = self.get_available_data()
        return available.get('seasons', [])
    
    def get_available_events(self, season: int) -> List[str]:
        """
        Get available events for a season.
        
        Use this to populate race dropdown!
        
        Args:
            season: Year
        
        Returns:
            List of event names
        """
        available = self.get_available_data()
        season_data = available.get(str(season), {})
        return season_data.get('events', [])
    
    def get_available_sessions(self, season: int, event: str) -> List[str]:
        """
        Get available sessions for an event.
        
        Use this to enable/disable session buttons!
        
        Args:
            season: Year
            event: Event name
        
        Returns:
            List of session types (e.g., ['FP1', 'Q', 'R'])
        """
        available = self.get_available_data()
        season_data = available.get(str(season), {})
        event_data = season_data.get(event, {})
        return event_data.get('sessions', [])
    
    def has_session_data(self, season: int, event: str, session_type: str) -> bool:
        """
        Check if specific session data exists.
        
        Use this before trying to load!
        
        Args:
            season: Year
            event: Event name
            session_type: Session type
        
        Returns:
            True if data exists, False otherwise
        """
        sessions = self.get_available_sessions(season, event)
        return session_type in sessions
    
    # ===== DATA LOADING METHODS =====
    
    def load_session_data(
        self,
        season: int,
        event: str,
        session_type: str = 'R',
        include_weather: bool = False,
        include_messages: bool = False,
        driver_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load complete session data.
        
        Args:
            season: Year
            event: Event name
            session_type: Session type
            include_weather: Include weather data
            include_messages: Include race control messages
            driver_filter: Filter by driver code
        
        Returns:
            Session data dictionary
            
        Raises:
            Exception: If session not in cache
        """
        # Validate first
        if not self.has_session_data(season, event, session_type):
            raise Exception(
                f"Session '{session_type}' for {event} {season} not in cache. "
                f"Available sessions: {self.get_available_sessions(season, event)}"
            )
        
        # Build query params
        params = {
            'season': season,
            'event': event,
            'session_type': session_type,
            'include_weather': include_weather,
            'include_messages': include_messages
        }
        
        if driver_filter:
            params['driver'] = driver_filter
        
        response = requests.get(f"{self.api_data_url}/data/session", params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            return data['data']
        else:
            raise Exception(data.get('detail', 'Unknown error'))
    
    def get_drivers_in_session(
        self,
        season: int,
        event: str,
        session_type: str = 'R'
    ) -> List[str]:
        """
        Get list of drivers in a session.
        
        Use this to populate driver dropdown!
        
        Args:
            season: Year
            event: Event name
            session_type: Session type
        
        Returns:
            List of driver codes
        """
        params = {
            'season': season,
            'event': event,
            'session_type': session_type
        }
        
        response = requests.get(f"{self.api_data_url}/data/session/drivers", params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            return data['data']
        else:
            return []


# ===== USAGE EXAMPLES =====

def example_dash_callback_pattern():
    """
    Example of how to use this in Dash callbacks.
    
    This replaces hardcoded dropdown values with dynamic ones from cache.
    """
    client = CachedDataClient()
    
    # ===== PATTERN 1: Populate season dropdown =====
    def get_season_dropdown_options():
        """Callback to populate season dropdown"""
        seasons = client.get_available_seasons()
        return [{'label': str(s), 'value': s} for s in seasons]
    
    # ===== PATTERN 2: Update race dropdown based on season =====
    def update_race_dropdown(selected_season: int):
        """Callback when season changes"""
        if not selected_season:
            return []
        
        events = client.get_available_events(selected_season)
        return [{'label': event, 'value': event} for event in events]
    
    # ===== PATTERN 3: Enable/disable session buttons =====
    def get_session_button_states(season: int, event: str):
        """Determine which session buttons should be enabled"""
        if not season or not event:
            return {
                'fp1_disabled': True,
                'fp2_disabled': True,
                'fp3_disabled': True,
                'q_disabled': True,
                'r_disabled': True
            }
        
        available_sessions = client.get_available_sessions(season, event)
        
        return {
            'fp1_disabled': 'FP1' not in available_sessions,
            'fp2_disabled': 'FP2' not in available_sessions,
            'fp3_disabled': 'FP3' not in available_sessions,
            'q_disabled': 'Q' not in available_sessions,
            'r_disabled': 'R' not in available_sessions
        }
    
    # ===== PATTERN 4: Load data only if available =====
    def load_race_data(season: int, event: str):
        """Load race data with validation"""
        try:
            # Check first
            if not client.has_session_data(season, event, 'R'):
                return {
                    'error': f"Race data for {event} {season} not in cache",
                    'available': client.get_available_sessions(season, event)
                }
            
            # Load
            data = client.load_session_data(season, event, 'R')
            
            return {
                'success': True,
                'session': data['session'],
                'laps': data['laps'],
                'drivers': data['drivers']
            }
            
        except Exception as e:
            return {
                'error': str(e)
            }
    
    # ===== PATTERN 5: Populate driver dropdown dynamically =====
    def update_driver_dropdown(season: int, event: str, session_type: str):
        """Get drivers who participated in session"""
        try:
            drivers = client.get_drivers_in_session(season, event, session_type)
            return [{'label': d, 'value': d} for d in drivers]
        except:
            return []


def example_initial_data_load():
    """
    Example: Load availability data at app startup.
    
    This should run ONCE when the app starts.
    """
    client = CachedDataClient()
    
    # Fetch available data
    print("🔍 Fetching available data from cache...")
    available = client.get_available_data()
    
    print(f"\n📅 Available seasons: {available['seasons']}")
    
    for season in available['seasons']:
        season_data = available[str(season)]
        print(f"\n{season}:")
        print(f"  Events: {len(season_data['events'])}")
        
        for event in season_data['events']:
            event_data = season_data[event]
            sessions = event_data['sessions']
            print(f"  - {event}: {', '.join(sessions)}")


def example_complete_workflow():
    """
    Example: Complete workflow from selecting race to viewing data.
    
    This shows the recommended pattern for the frontend.
    """
    client = CachedDataClient()
    
    # Step 1: Get available data
    print("\n" + "="*60)
    print("STEP 1: Fetch Available Data")
    print("="*60)
    
    seasons = client.get_available_seasons()
    print(f"Available seasons: {seasons}")
    
    # Step 2: User selects season
    selected_season = seasons[0] if seasons else None
    print(f"\nUser selects season: {selected_season}")
    
    # Step 3: Get events for that season
    print("\n" + "="*60)
    print("STEP 2: Get Events for Season")
    print("="*60)
    
    events = client.get_available_events(selected_season)
    print(f"Available events: {events}")
    
    # Step 4: User selects event
    selected_event = events[0] if events else None
    print(f"\nUser selects event: {selected_event}")
    
    # Step 5: Get available sessions
    print("\n" + "="*60)
    print("STEP 3: Get Available Sessions")
    print("="*60)
    
    sessions = client.get_available_sessions(selected_season, selected_event)
    print(f"Available sessions: {sessions}")
    
    # Step 6: User selects session and loads data
    print("\n" + "="*60)
    print("STEP 4: Load Session Data")
    print("="*60)
    
    if 'R' in sessions:
        print("Loading Race data...")
        
        data = client.load_session_data(
            season=selected_season,
            event=selected_event,
            session_type='R'
        )
        
        print(f"\n✅ Loaded successfully!")
        print(f"   Session: {data['session']['name']}")
        print(f"   Total laps: {data['total_laps']}")
        print(f"   Drivers: {len(data['drivers'])}")
        print(f"   Driver list: {', '.join(data['drivers'][:5])}...")
        
        # Get a specific driver's laps
        if data['drivers']:
            print("\n" + "="*60)
            print("STEP 5: Filter by Driver")
            print("="*60)
            
            driver = data['drivers'][0]
            print(f"Getting laps for {driver}...")
            
            driver_data = client.load_session_data(
                season=selected_season,
                event=selected_event,
                session_type='R',
                driver_filter=driver
            )
            
            print(f"   {driver} completed {len(driver_data['laps'])} laps")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FRONTEND INTEGRATION EXAMPLE - Normalized Cache")
    print("="*60)
    
    print("\n⚠️  Note: This requires the backend to be running!")
    print("   Start with: python main.py")
    
    try:
        # Run examples
        example_initial_data_load()
        print("\n")
        example_complete_workflow()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Backend not running!")
        print("   Start backend first: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
