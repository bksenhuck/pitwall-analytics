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
    
    Returns:
        List[int]: List of available F1 seasons
    """
    global _seasons_cache
    
    # Return cached value if available
    if _seasons_cache is not None:
        return _seasons_cache
    
    # Check if backend is available first
    if not _check_backend_available():
        _seasons_cache = [2021, 2022, 2023, 2024]
        return _seasons_cache
    
    try:
        url = f"{BACKEND_API_URL}/cached/read"
        response = requests.get(
            url,
            params={"key": "f1_seasons"},
            timeout=2
        )
        
        if response.status_code == 404:
            print(f"⚠️  Seasons cache not populated. Please run: python populate_cache.py f1_seasons")
            _seasons_cache = [2021, 2022, 2023, 2024]
            return _seasons_cache
        
        # Check if response is empty
        if not response.text:
            _seasons_cache = [2021, 2022, 2023, 2024]
            return _seasons_cache
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"data": {"seasons": [2021, 2022, ...]}, ...}
        if "data" in data and "seasons" in data["data"]:
            _seasons_cache = data["data"]["seasons"]
        elif "seasons" in data:
            _seasons_cache = data["seasons"]
        else:
            _seasons_cache = [2021, 2022, 2023, 2024]
        
        return _seasons_cache
        
    except Exception:
        # Silent fallback - error already logged by _check_backend_available
        _seasons_cache = [2021, 2022, 2023, 2024]
        return _seasons_cache


def get_races_for_season(season: int) -> List[str]:
    """
    """
    global _races_cache
    
    # Return cached value if available
    if season in _races_cache:
        return _races_cache[season]
    
    # Check if backend is available first
    if not _check_backend_available():
        fallback = ["Bahrain", "Australian", "Monaco"]
        _races_cache[season] = fallback
        return fallback
    
    try:
        url = f"{BACKEND_API_URL}/cached/read"
        response = requests.get(
            url,
            params={"key": f"races_{season}"},
            timeout=2
        )
        
        if response.status_code == 404:
            print(f"⚠️  Race schedule for {season} not populated. Please run: python populate_cache.py races_{season}")
            fallback = ["Bahrain", "Australian", "Monaco"]
            _races_cache[season] = fallback
            return fallback
        
        # Check if response is empty
        if not response.text:
            fallback = ["Bahrain", "Australian", "Monaco"]
            _races_cache[season] = fallback
            return fallback
        
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"data": {"season": 2024, "races": [{...}, {...}]}, ...}
        if "data" in data and "races" in data["data"]:
            races = [race["event_name"] for race in data["data"]["races"]]
            _races_cache[season] = races
            return races
        elif "races" in data:
            races = [race["event_name"] for race in data["races"]]
            _races_cache[season] = races
            return races
        
        # Fallback
        fallback = ["Bahrain", "Australian", "Monaco"]
        _races_cache[season] = fallback
        return fallback
        
    except Exception:
        # Silent fallback - error already logged by _check_backend_available
        fallback = ["Bahrain", "Australian", "Monaco"]
        _races_cache[season] = fallback
        return fallback


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
    """
    # Check if backend is available first
    if not _check_backend_available():
        print(f"⚠️  Cannot load race data: backend not available")
        return pd.DataFrame(), pd.DataFrame(), {"error": "Backend not available"}
    
    try:
        # Normalize event name: replace spaces with underscores, lowercase
        event_key = event_name.lower().replace(" ", "_")
        cache_key = f"race_{season}_{event_key}"
        
        url = f"{BACKEND_API_URL}/cached/read"
        print(f"🔍 Requesting: {url}?key={cache_key}")
        
        response = requests.get(
            url,
            params={"key": cache_key},
            timeout=30  # Longer timeout for large race data
        )
        
        print(f"📡 Response status: {response.status_code}")
        print(f"📦 Response length: {len(response.text)} chars")
        
        if response.status_code == 404:
            print(f"⚠️  Race data for {season} {event_name} not found.")
            print(f"   Please run: python populate_cache.py {cache_key}")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Cache not populated"}
        
        # Check if response is empty
        if not response.text or len(response.text.strip()) == 0:
            print(f"⚠️  Backend returned empty response for {cache_key}")
            print(f"   Response text: '{response.text[:100]}'")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Empty response"}
        
        response.raise_for_status()
        
        # Try to parse JSON
        try:
            data = response.json()
        except ValueError as json_err:
            print(f"❌ JSON decode error for {cache_key}")
            print(f"   Response preview: '{response.text[:200]}'")
            print(f"   Error: {json_err}")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Invalid JSON"}
        
        # Extract nested data if present
        if "data" in data:
            data = data["data"]
        
        # Response format: {"season": 2024, "laps": [...], "drivers": [...]}
        if "laps" not in data:
            print(f"⚠️  Invalid race data format for {cache_key}")
            print(f"   Available keys: {list(data.keys())}")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Invalid format"}
        
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
        
        print(f"✅ Loaded {len(laps)} laps for {event_name}")
        
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