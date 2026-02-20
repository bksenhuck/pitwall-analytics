from typing import List, Tuple
import os

import requests
import pandas as pd


# Backend API URL - read from environment or default to localhost
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:5000")


def enable_cache(cache_dir: str = ".ff1cache") -> None:
    """
    Enable FastF1 local cache. Call this once at startup.
    
    NOTE: This is now a no-op since frontend reads from SQLite cache via backend API.
    """
    pass  # Frontend no longer uses FastF1 directly


def get_available_seasons() -> List[int]:
    """
    Fetch available seasons from SQLite cache via backend API.
    
    Returns:
        List[int]: List of available F1 seasons
    
    Raises:
        Exception: If cache is not populated or request fails
    """
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/api/cached/read",
            params={"key": "f1_seasons"},
            timeout=10
        )
        
        if response.status_code == 404:
            raise Exception(
                "Seasons cache not found. Please run: python populate_cache.py f1_seasons"
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"seasons": [2021, 2022, ...]}
        if "seasons" in data:
            return data["seasons"]
        
        # Fallback
        return [2021, 2022, 2023, 2024]
        
    except requests.RequestException as e:
        print(f"❌ Error fetching seasons from cache: {e}")
        # Return fallback list
        return [2021, 2022, 2023, 2024]


def get_races_for_season(season: int) -> List[str]:
    """
    Fetch race schedule for a season from SQLite cache via backend API.
    
    Args:
        season: F1 season year (e.g., 2024)
    
    Returns:
        List[str]: List of event names for the season
    
    Raises:
        Exception: If cache is not populated or request fails
    """
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/api/cached/read",
            params={"key": f"races_{season}"},
            timeout=10
        )
        
        if response.status_code == 404:
            raise Exception(
                f"Race schedule for {season} not found. "
                f"Please run: python populate_cache.py races_{season}"
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"season": 2024, "races": [{...}, {...}]}
        if "races" in data:
            return [race["event_name"] for race in data["races"]]
        
        # Fallback
        return ["Bahrain", "Australian", "Monaco"]
        
    except requests.RequestException as e:
        print(f"❌ Error fetching races from cache: {e}")
        # Return fallback list
        return ["Bahrain", "Australian", "Monaco"]


def load_race_session(season: int, event_name: str) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Load a race session from SQLite cache via backend API.
    
    Args:
        season: F1 season year (e.g., 2024)
        event_name: Event name (e.g., "Bahrain Grand Prix" or "Bahrain")
    
    Returns:
        laps: DataFrame of laps (with LapTimeSeconds)
        telemetry_placeholder: Empty DataFrame (telemetry not loaded)
        session_data: Dict with session metadata
    
    Raises:
        Exception: If cache is not populated or request fails
    """
    try:
        # Normalize event name: replace spaces with underscores, lowercase
        event_key = event_name.lower().replace(" ", "_")
        cache_key = f"race_{season}_{event_key}"
        
        response = requests.get(
            f"{BACKEND_API_URL}/api/cached/read",
            params={"key": cache_key},
            timeout=30  # Longer timeout for large race data
        )
        
        if response.status_code == 404:
            raise Exception(
                f"Race data for {season} {event_name} not found. "
                f"Please run: python populate_cache.py {cache_key}"
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"season": 2024, "laps": [...], "drivers": [...]}
        if "laps" not in data:
            raise Exception(f"Invalid race data format for {cache_key}")
        
        # Convert laps to DataFrame
        laps = pd.DataFrame(data["laps"])
        
        # Ensure LapTimeSeconds column exists
        if "LapTimeSeconds" not in laps.columns and "LapTime" in laps.columns:
            # LapTime might be already in seconds or needs conversion
            laps["LapTimeSeconds"] = pd.to_numeric(laps["LapTime"], errors="coerce")
        
        # Empty telemetry placeholder (not loaded from cache)
        telemetry_df = pd.DataFrame()
        
        # Session metadata
        session_data = {
            "season": data.get("season", season),
            "event_name": event_name,
            "drivers": data.get("drivers", []),
            "source": data.get("source", "sqlite_cache")
        }
        
        return laps, telemetry_df, session_data
        
    except requests.RequestException as e:
        print(f"❌ Error loading race session from cache: {e}")
        raise Exception(f"Failed to load race data: {e}")


def get_session_with_telemetry(season: int, event_name: str) -> dict:
    """
    Load session data from cache (telemetry not supported in cache mode).
    
    NOTE: Telemetry is not stored in SQLite cache. Returns the same data as load_race_session.
    """
    laps, _, session_data = load_race_session(season, event_name)
    session_data["laps"] = laps
    return session_data


def get_driver_telemetry(session: dict, driver: str) -> pd.DataFrame:
    """
    Fetch telemetry for a driver (not supported in cache mode).
    
    NOTE: Telemetry is not stored in SQLite cache. Returns empty DataFrame.
    """
    print(f"⚠️ Telemetry not available in cache mode for driver: {driver}")
    return pd.DataFrame()