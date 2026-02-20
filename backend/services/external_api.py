"""
External API service.

This module handles calls to external APIs and FastF1.
When you call populate_cache.py, this is what fetches the data.

Why separate this?
- Easy to mock for testing
- Easy to swap external API providers
- Clear separation: this is WHERE external data comes from
"""
import httpx
from typing import Dict, Any, Optional
import asyncio
import os
from dotenv import load_dotenv
import fastf1 as ff1
import pandas as pd

load_dotenv()

# Configuration
EXTERNAL_API_TIMEOUT = int(os.getenv('EXTERNAL_API_TIMEOUT', '30'))
FF1_CACHE_DIR = os.getenv('CACHE_DIR', '.ff1cache')

# Enable FastF1 cache
try:
    ff1.Cache.enable_cache(FF1_CACHE_DIR)
except Exception:
    pass


class ExternalAPIService:
    """
    Service for fetching data from external APIs.
    
    This is a simulation/example. Replace with real API calls.
    """
    
    def __init__(self, timeout: int = EXTERNAL_API_TIMEOUT):
        """
        Initialize external API service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    async def fetch_f1_seasons(self) -> Dict[str, Any]:
        """
        Fetch F1 seasons data.
        
        Returns:
            dict: Seasons data with list of available years
        """
        # Use a simple hardcoded list for now
        # In future, could fetch from Ergast API or FastF1
        return {
            'seasons': [2021, 2022, 2023, 2024, 2025],
            'total': 5,
            'source': 'fastf1',
            'timestamp': asyncio.get_event_loop().time()
        }
    
    async def fetch_races_for_season(self, season: int) -> Dict[str, Any]:
        """
        Fetch race schedule for a specific season using FastF1.
        
        Args:
            season: Season year (e.g., 2024)
        
        Returns:
            dict: Race schedule with event names and dates
        """
        try:
            # Run FastF1 in executor (it's synchronous)
            loop = asyncio.get_event_loop()
            schedule = await loop.run_in_executor(
                None, 
                ff1.get_event_schedule, 
                season
            )
            
            # Convert to serializable format
            races = []
            for idx, row in schedule.iterrows():
                races.append({
                    'round': int(row.get('RoundNumber', idx + 1)),
                    'event_name': str(row.get('EventName', '')),
                    'location': str(row.get('Location', '')),
                    'country': str(row.get('Country', '')),
                    'date': str(row.get('EventDate', ''))
                })
            
            return {
                'season': season,
                'races': races,
                'total': len(races),
                'source': 'fastf1'
            }
        except Exception as e:
            # Fallback to minimal list
            return {
                'season': season,
                'races': [
                    {'round': 1, 'event_name': 'Bahrain Grand Prix', 'location': 'Sakhir', 'country': 'Bahrain'},
                    {'round': 2, 'event_name': 'Australian Grand Prix', 'location': 'Melbourne', 'country': 'Australia'},
                ],
                'total': 2,
                'source': 'fallback',
                'error': str(e)
            }
    
    async def fetch_race_session_data(
        self, 
        season: int, 
        event_name: str,
        session_type: str = 'R'
    ) -> Dict[str, Any]:
        """
        Fetch complete race session data using FastF1.
        
        This is what gets cached in SQLite when you run:
        python populate_cache.py race_2024_bahrain
        
        Args:
            season: Season year (e.g., 2024)
            event_name: Event name (e.g., 'Bahrain Grand Prix')
            session_type: 'R' (Race), 'Q' (Quali), 'FP1', etc.
        
        Returns:
            dict: Complete session data including laps, drivers, results
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Load session
            def load_session():
                session = ff1.get_session(season, event_name, session_type)
                session.load(laps=True, telemetry=False, weather=True)
                return session
            
            session = await loop.run_in_executor(None, load_session)
            
            # Extract laps data
            laps = session.laps.copy()
            if 'LapTime' in laps.columns:
                # Convert timedelta to seconds
                laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
            
            # Convert to serializable format
            laps_dict = laps.to_dict(orient='records')
            
            # Clean up non-serializable types
            for lap in laps_dict:
                for key, value in lap.items():
                    if pd.isna(value):
                        lap[key] = None
                    elif isinstance(value, pd.Timestamp):
                        lap[key] = value.isoformat()
                    elif isinstance(value, pd.Timedelta):
                        lap[key] = value.total_seconds()
            
            # Get drivers list
            drivers = laps['Driver'].unique().tolist() if 'Driver' in laps.columns else []
            
            return {
                'season': season,
                'event_name': event_name,
                'session_type': session_type,
                'laps': laps_dict,
                'drivers': drivers,
                'total_laps': len(laps_dict),
                'source': 'fastf1'
            }
        
        except Exception as e:
            raise Exception(f"Error loading session data: {str(e)}")
    
    async def fetch_race_data(self, season: int, event: str) -> Dict[str, Any]:
        """
        Legacy method - calls fetch_race_session_data.
        
        Args:
            season: Season year
            event: Event name
        
        Returns:
            dict: Race data
        """
        return await self.fetch_race_session_data(season, event, 'R')
    
    async def fetch_generic_data(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generic method to fetch data from any external API.
        
        This is the real implementation you'd use for actual external APIs.
        
        Args:
            url: API endpoint URL
            params: Query parameters
        
        Returns:
            dict: API response data
        
        Raises:
            httpx.HTTPError: If request fails
        
        Example:
            data = await service.fetch_generic_data(
                'https://ergast.com/api/f1/2023/circuits.json'
            )
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()  # Raise exception for 4xx/5xx
            return response.json()
    
    async def fetch_multiple(self, urls: list[str]) -> list[Dict[str, Any]]:
        """
        Fetch data from multiple URLs concurrently.
        
        Args:
            urls: List of API endpoint URLs
        
        Returns:
            list: List of responses
        
        Example:
            urls = [
                'https://api1.com/data',
                'https://api2.com/data',
                'https://api3.com/data'
            ]
            results = await service.fetch_multiple(urls)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [client.get(url) for url in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results = []
            for response in responses:
                if isinstance(response, Exception):
                    results.append({'error': str(response)})
                else:
                    try:
                        results.append(response.json())
                    except Exception as e:
                        results.append({'error': str(e)})
            
            return results
