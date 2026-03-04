"""
Backend API client for frontend application.

This module provides a clean interface to fetch data from the backend API.
All data comes from the SQLite cache via the FastAPI backend.
"""
from typing import List, Tuple, Optional
import requests
import pandas as pd
from frontend.config import BACKEND_API_URL, CACHE_DIR


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
    
    if not cache["available"]:
        print(f"⚠️  Backend not available at {BACKEND_API_URL}")
        print(f"   Start backend with: python main.py")
    
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
    
    Returns:
        List[int]: List of available F1 seasons in cache
    """
    global _seasons_cache
    
    if _seasons_cache is not None:
        return _seasons_cache
    
    if not _check_backend_available():
        _seasons_cache = []
        return _seasons_cache
    
    try:
        url = f"{BACKEND_API_URL}/data/available"
        response = requests.get(url, timeout=2)
        
        if response.status_code == 404 or not response.text:
            print(f"⚠️  Cache is empty. Populate with: python scripts/populate_cache.py --season 2024")
            _seasons_cache = []
            return _seasons_cache
        
        response.raise_for_status()
        data = response.json()
        
        if "seasons" in data and data["seasons"]:
            _seasons_cache = sorted(data["seasons"], reverse=True)
            print(f"✅ Found {len(_seasons_cache)} seasons: {_seasons_cache}")
        else:
            _seasons_cache = []
        
        return _seasons_cache
        
    except Exception as e:
        print(f"❌ Error loading seasons: {e}")
        _seasons_cache = []
        return _seasons_cache


def get_track_layout(
    season: int, event: str, session_type: str = 'R'
) -> dict:
    """
    Fetch circuit X/Y layout from fastest lap telemetry.
    Returns {"x": [...], "y": [...], "count": N}.
    Empty arrays if telemetry was not populated.
    """
    if not _check_backend_available():
        return {"x": [], "y": [], "count": 0}
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/data/track-layout",
            params={"season": season, "event": event,
                    "session_type": session_type},
            timeout=10
        )
        if response.status_code != 200:
            return {"x": [], "y": [], "count": 0}
        return response.json()
    except Exception as e:
        print(f"❌ Error loading track layout: {e}")
        return {"x": [], "y": [], "count": 0}


def get_races_for_season(season: int) -> List[str]:
    """
    Fetch available races for a season from SQLite cache.

    Returns:
        List[str]: List of race event names in cache
    """
    global _races_cache
    
    if season in _races_cache:
        return _races_cache[season]
    
    if not _check_backend_available():
        _races_cache[season] = []
        return []
    
    try:
        url = f"{BACKEND_API_URL}/data/available"
        response = requests.get(url, timeout=2)
        
        if response.status_code == 404 or not response.text:
            _races_cache[season] = []
            return []
        
        response.raise_for_status()
        data = response.json()
        
        season_str = str(season)
        if season_str in data and "events" in data[season_str]:
            events = data[season_str]["events"]
            _races_cache[season] = events
            print(f"✅ Found {len(events)} races for {season}")
            return events
        else:
            _races_cache[season] = []
            return []
        
    except Exception as e:
        print(f"❌ Error loading races for {season}: {e}")
        _races_cache[season] = []
        return []


def get_race_results(season: int, event_name: str) -> pd.DataFrame:
    """
    Load race results (position, points, team) for one event.

    Returns a DataFrame with columns: driver_code, team, points, position.
    Returns an empty DataFrame on error.
    """
    if not _check_backend_available():
        return pd.DataFrame()

    for session_type in ("R", "Race"):
        try:
            response = requests.get(
                f"{BACKEND_API_URL}/data/session",
                params={
                    "season": season,
                    "event": event_name,
                    "session_type": session_type,
                    "include_laps": False,
                    "include_results": True,
                },
                timeout=15,
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not results:
                return pd.DataFrame()
            df = pd.DataFrame(results)
            for col in ("driver_code", "team", "points", "position"):
                if col not in df.columns:
                    df[col] = None
            return df[["driver_code", "team", "points", "position"]]
        except Exception as e:
            print(f"❌ Error loading results for {event_name}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def load_session(
    season: int, event_name: str, session_type: str
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Load any session type from normalized SQLite cache.

    Args:
        season: F1 season year (e.g., 2024)
        event_name: Event name (e.g., "Bahrain Grand Prix")
        session_type: FastF1 session code (R, Q, FP1, FP2, FP3, S, SQ)

    Returns:
        tuple: (laps_df, telemetry_df, session_data)
    """
    if not _check_backend_available():
        return pd.DataFrame(), pd.DataFrame(), {"error": "Backend not available"}

    try:
        response = requests.get(
            f"{BACKEND_API_URL}/data/session",
            params={
                "season": season,
                "event": event_name,
                "session_type": session_type,
            },
            timeout=30,
        )

        if response.status_code == 404:
            print(f"⚠️  {season} {event_name} [{session_type}] not found")
            return pd.DataFrame(), pd.DataFrame(), {"error": "Session not found"}

        if not response.text:
            return pd.DataFrame(), pd.DataFrame(), {"error": "Empty response"}

        response.raise_for_status()
        data = response.json()

        if "laps" not in data:
            return pd.DataFrame(), pd.DataFrame(), {"error": "Invalid format"}

        laps = pd.DataFrame(data["laps"])

        # Normalize column names to match existing page expectations
        col_map = {
            "lap_time_seconds": "LapTimeSeconds",
            "driver_code": "Driver",
            "lap_number": "LapNumber",
            "position": "Position",
        }
        for src, dst in col_map.items():
            if src in laps.columns:
                laps[dst] = laps[src]

        session_data = {
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "drivers": data.get("drivers", []),
            "lap_count": len(laps),
        }

        print(f"✅ Loaded {len(laps)} laps for {event_name} [{session_type}]")
        return laps, pd.DataFrame(), session_data

    except Exception as e:
        print(f"❌ Error loading session: {e}")
        return pd.DataFrame(), pd.DataFrame(), {"error": str(e)}


def load_race_session(
    season: int, event_name: str, preferred_session: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Load session data based on context.
    If preferred_session is provided, try that first.
    Default: Q for Qualify rules, R for positions.
    """
    priority = [preferred_session] if preferred_session else ["Q", "R"]
    # If no preference, we might want to try both, but if we are in "Positions"
    # we definitely want "R". If we are in "Qualy", we want "Q".
    for stype in priority:
        if not stype: continue
        laps, tel, meta = load_session(season, event_name, stype)
        if not laps.empty:
            return laps, tel, meta
    
    # Second pass fallback
    for stype in ["Q", "R"]:
        if stype == preferred_session: continue
        laps, tel, meta = load_session(season, event_name, stype)
        if not laps.empty:
            return laps, tel, meta
            
    return pd.DataFrame(), pd.DataFrame(), {}
