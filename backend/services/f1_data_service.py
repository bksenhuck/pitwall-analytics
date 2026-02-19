"""
F1 Data Service.
Business logic layer for F1 data processing using FastF1.

This service:
- Fetches data from FastF1 API
- Processes and transforms data
- Applies business logic
- Returns clean data to API layer
"""
from typing import List, Dict, Any
import fastf1 as ff1
import pandas as pd


class F1DataService:
    """Service for F1 data operations"""
    
    def get_available_seasons(self) -> List[int]:
        """
        Get list of available F1 seasons.
        
        Returns:
            List of season years
        """
        # Can be extended to query from database or external API
        return [2021, 2022, 2023, 2024]
    
    def get_races_for_season(self, season: int) -> List[Dict[str, Any]]:
        """
        Get all races for a given season.
        
        Args:
            season: Year (e.g., 2023)
        
        Returns:
            List of race events with metadata
        """
        try:
            schedule = ff1.get_event_schedule(season)
            
            races = []
            for idx, row in schedule.iterrows():
                races.append({
                    'round': int(row.get('RoundNumber', idx + 1)),
                    'name': str(row.get('EventName', row.get('OfficialEventName', 'Unknown'))),
                    'location': str(row.get('Location', row.get('Country', 'Unknown'))),
                    'date': str(row.get('EventDate', ''))
                })
            
            return races
        except Exception as e:
            # Fallback to minimal list
            print(f"⚠️  Error fetching schedule: {e}")
            return [
                {'round': 1, 'name': 'Bahrain', 'location': 'Bahrain', 'date': ''},
                {'round': 2, 'name': 'Saudi Arabian', 'location': 'Saudi Arabia', 'date': ''},
                {'round': 3, 'name': 'Australian', 'location': 'Australia', 'date': ''}
            ]
    
    def load_session_data(self, season: int, event: str, session_type: str = 'R') -> Dict[str, Any]:
        """
        Load session data including laps and basic statistics.
        
        Args:
            season: Year
            event: Race name
            session_type: 'R' for Race, 'Q' for Qualifying, 'FP1', 'FP2', 'FP3'
        
        Returns:
            Dictionary with session data, laps, and metadata
        """
        try:
            # Load session
            session = ff1.get_session(season, event, session_type)
            session.load(laps=True, telemetry=False, weather=False)
            
            # Process laps
            laps = session.laps.copy()
            
            # Convert lap times to seconds for easier processing
            if 'LapTime' in laps.columns:
                laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
            
            # Get drivers
            drivers = laps['Driver'].unique().tolist() if 'Driver' in laps.columns else []
            
            # Convert to dict for JSON serialization
            laps_dict = laps.to_dict('records')
            
            # Clean up non-serializable objects
            laps_dict = self._clean_for_json(laps_dict)
            
            return {
                'session': {
                    'season': season,
                    'event': event,
                    'type': session_type,
                    'name': str(session.event.get('EventName', event))
                },
                'drivers': drivers,
                'laps': laps_dict[:100],  # Limit for demo, implement pagination in production
                'total_laps': len(laps_dict)
            }
        except Exception as e:
            raise Exception(f"Failed to load session data: {str(e)}")
    
    def get_driver_telemetry(self, session_obj, driver: str, lap_number: int) -> Dict[str, Any]:
        """
        Get telemetry data for a specific driver and lap.
        
        Args:
            session_obj: FastF1 session object
            driver: Driver code (e.g., 'VER', 'HAM')
            lap_number: Lap number
        
        Returns:
            Telemetry data dictionary
        """
        try:
            lap = session_obj.laps.pick_driver(driver).pick_lap(lap_number)
            telemetry = lap.get_telemetry()
            
            return {
                'driver': driver,
                'lap': lap_number,
                'telemetry': telemetry.to_dict('records')[:1000]  # Limit points
            }
        except Exception as e:
            raise Exception(f"Failed to load telemetry: {str(e)}")
    
    def _clean_for_json(self, data: List[Dict]) -> List[Dict]:
        """
        Clean data for JSON serialization.
        Converts Timedelta, NaT, etc. to serializable types.
        """
        import numpy as np
        
        cleaned = []
        for record in data:
            clean_record = {}
            for key, value in record.items():
                # Handle pandas/numpy types
                if pd.isna(value):
                    clean_record[key] = None
                elif isinstance(value, (pd.Timedelta, pd.Timestamp)):
                    clean_record[key] = str(value)
                elif isinstance(value, (np.integer, np.floating)):
                    clean_record[key] = value.item()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    clean_record[key] = value
                else:
                    clean_record[key] = str(value)
            cleaned.append(clean_record)
        
        return cleaned
