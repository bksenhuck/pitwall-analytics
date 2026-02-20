from typing import List, Tuple
import os
import io

import requests
import pandas as pd


# Backend API URL - read from environment or default to localhost
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:5000/api")

# Cache to avoid repeated error messages and redundant calls
_backend_available_cache = {"checked": False, "available": False, "last_check": 0}
_seasons_cache = None
_races_cache = {}


def _check_backend_available() -> bool:
    """Check if backend is available, with caching to reduce spam."""
    import time
    
    cache = _backend_available_cache
    current_time = time.time()
    
    # Only check every 5 seconds
    if cache["checked"] and (current_time - cache["last_check"]) < 5:
        return cache["available"]
    
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=1)
        cache["available"] = response.status_code == 200
    except:
        cache["available"] = False
    
    cache["checked"] = True
    cache["last_check"] = current_time
    
    if not cache["available"] and current_time - cache["last_check"] < 1:
        print(f"⚠️  Backend not available at {BACKEND_API_URL}. Using fallback data.")
        print(f"   To use cached data, start the backend with: python main.py")
    
    return cache["available"]


def enable_cache(cache_dir: str = ".ff1cache") -> None:
    """
    Enable FastF1 local cache. Call this once at startup.
    
    NOTE: This is now a no-op since frontend reads from SQLite cache via backend API.
    """
    pass  # Frontend no longer uses FastF1 directly


def get_available_seasons() -> List[int]:
    """
    Fetch available seasons from SQLite cache via backend API.
    
    Returns ONLY seasons that actually exist in the cache.
    If cache is empty, returns empty list (not fallback data).
    
    Returns:
        List[int]: List of available F1 seasons actually in cache
    """
    global _seasons_cache
    
    # Return cached value if available
    if _seasons_cache is not None:
        return _seasons_cache
    
    # Check if backend is available first
    if not _check_backend_available():
        print(f"⚠️  Backend not available. Cannot load seasons.")
        print(f"   Start backend with: python main.py")
        _seasons_cache = []
        return _seasons_cache
    
    try:
        # Use new normalized cache endpoint
        url = f"{BACKEND_API_URL}/data/available"
        response = requests.get(url, timeout=2)
        
        if response.status_code == 404:
            print(f"⚠️  No cached data found. Cache is empty.")
            print(f"   Populate cache with: python scripts/populate_cache.py --season 2024")
            _seasons_cache = []
            return _seasons_cache
        
        # Check if response is empty
        if not response.text:
            print(f"⚠️  Cache is empty.")
            _seasons_cache = []
            return _seasons_cache
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"seasons": [2024, 2023], "2024": {...}, ...}
        if "seasons" in data and data["seasons"]:
            _seasons_cache = sorted(data["seasons"], reverse=True)  # Most recent first
            print(f"✅ Found {len(_seasons_cache)} seasons in cache: {_seasons_cache}")
        else:
            print(f"⚠️  No seasons found in cache. Please populate data first.")
            _seasons_cache = []
        
        return _seasons_cache
        
    except Exception as e:
        print(f"❌ Error loading seasons: {e}")
        _seasons_cache = []
        return _seasons_cache


def get_races_for_season(season: int) -> List[str]:
    """
    Fetch available races for a season from SQLite cache via backend API.
    
    Returns ONLY races that actually exist in the cache for this season.
    If no data exists, returns empty list (not fallback data).
    
    Returns:
        List[str]: List of race event names actually in cache for the season
    """
    global _races_cache
    
    # Return cached value if available
    if season in _races_cache:
        return _races_cache[season]
    
    # Check if backend is available first
    if not _check_backend_available():
        print(f"⚠️  Backend not available. Cannot load races.")
        _races_cache[season] = []
        return []
    
    try:
        # Use new normalized cache endpoint
        url = f"{BACKEND_API_URL}/data/available"
        response = requests.get(url, timeout=2)
        
        if response.status_code == 404:
            print(f"⚠️  No data for season {season}. Cache is empty.")
            print(f"   Populate cache with: python scripts/populate_cache.py --season {season}")
            _races_cache[season] = []
            return []
        
        # Check if response is empty
        if not response.text:
            _races_cache[season] = []
            return []
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"seasons": [2024], "2024": {"events": ["Bahrain Grand Prix", ...]}, ...}
        season_str = str(season)
        if season_str in data and "events" in data[season_str]:
            events = data[season_str]["events"]
            _races_cache[season] = events
            print(f"✅ Found {len(events)} races for {season}: {events}")
            return events
        else:
            print(f"⚠️  No races found for season {season} in cache.")
            print(f"   Populate with: python scripts/populate_cache.py --season {season}")
            _races_cache[season] = []
            return []
        
    except Exception as e:
        print(f"❌ Error loading races for {season}: {e}")
        _races_cache[season] = []
        return []


def load_race_session(season: int, event_name: str) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Load a race session from normalized SQLite cache via backend API.
    
    Args:
        season: F1 season year (e.g., 2024)
        event_name: Event name (e.g., "Bahrain Grand Prix" or "Bahrain")
    
    Returns:
        laps: DataFrame of laps (with LapTimeSeconds)
        telemetry_placeholder: Empty DataFrame (telemetry not loaded)
        session_data: Dict with session metadata
    """
    # Check if backend is available first
    if not _check_backend_available():
        print(f"⚠️  Cannot load race data: backend not available")
        return pd.DataFrame(), pd.DataFrame(), {"error": "Backend not available"}
    
    try:
        # Use new normalized cache endpoint
        # Try "R" first (FastF1 code), then "Race" as fallback
        url = f"{BACKEND_API_URL}/data/session"
        
        # Try with "R" first
        print(f"🔍 Requesting: {url}?season={season}&event={event_name}&session_type=R")
        
        response = requests.get(
            url,
            params={
                "season": season,
                "event": event_name,
                "session_type": "R"  # FastF1 uses "R" for Race
            },
            timeout=30  # Longer timeout for large race data
        )
        
        # If not found with "R", try "Race"
        if response.status_code == 404:
            print(f"   ⏭️  Trying with session_type=Race...")
            response = requests.get(
                url,
                params={
                    "season": season,
                    "event": event_name,
                    "session_type": "Race"
                },
                timeout=30
            )
        
        print(f"📡 Response status: {response.status_code}")
        print(f"📦 Response length: {len(response.text)} chars")
        
        if response.status_code == 404:
            print(f"⚠️  Race data for {season} {event_name} not found in cache.")
            print(f"   This event may not have a race session (e.g., testing event)")
            return pd.DataFrame(), pd.DataFrame(), {"error": "No race session"}
        
        # Check if response is empty
        if not response.text or len(response.text.strip()) == 0:
            print(f"⚠️  Backend returned empty response")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Empty response"}
        
        response.raise_for_status()
        
        # Try to parse JSON
        try:
            data = response.json()
        except ValueError as json_err:
            print(f"❌ JSON decode error")
            print(f"   Response preview: '{response.text[:200]}'")
            print(f"   Error: {json_err}")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Invalid JSON"}
        
        # Response format: {"laps": [...], "results": [...], "weather": [...], "drivers": [...]}
        if "laps" not in data:
            print(f"⚠️  Invalid session data format")
            print(f"   Available keys: {list(data.keys())}")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Invalid format"}
        
        # Convert laps to DataFrame
        laps = pd.DataFrame(data["laps"])
        
        # Ensure required columns exist
        if "lap_time_seconds" in laps.columns and "LapTimeSeconds" not in laps.columns:
            laps["LapTimeSeconds"] = laps["lap_time_seconds"]
        elif "LapTime" in laps.columns and "LapTimeSeconds" not in laps.columns:
            laps["LapTimeSeconds"] = pd.to_numeric(laps["LapTime"], errors="coerce")
        
        # Map driver_code to Driver if needed
        if "driver_code" in laps.columns and "Driver" not in laps.columns:
            laps["Driver"] = laps["driver_code"]
        
        # Map lap_number to LapNumber if needed
        if "lap_number" in laps.columns and "LapNumber" not in laps.columns:
            laps["LapNumber"] = laps["lap_number"]
        
        # Empty telemetry placeholder (not loaded from cache)
        telemetry_df = pd.DataFrame()
        
        # Extract drivers list
        drivers = data.get("drivers", [])
        if not drivers and "laps" in data and len(data["laps"]) > 0:
            # Extract from laps if not provided
            drivers = list(set([lap.get("driver_code", lap.get("Driver", "")) for lap in data["laps"]]))
        
        # Session metadata
        session_data = {
            "season": season,
            "event_name": event_name,
            "drivers": drivers,
            "source": "normalized_cache",
            "lap_count": len(laps)
        }
        
        print(f"✅ Loaded {len(laps)} laps from {len(drivers)} drivers for {event_name}")
        
        return laps, telemetry_df, session_data
        
    except Exception as e:
        print(f"❌ Error loading race session from cache: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame(), {"error": str(e)}


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