"""
Backend API client for frontend application.

All data is read from the SQLite/Parquet cache via the FastAPI backend.
The full /data/available response is cached in-process for AVAILABLE_TTL
seconds so that cascading dropdowns only trigger one network round-trip
per minute instead of one per callback.
"""
import time
from typing import List, Tuple, Optional

import requests
import pandas as pd

from frontend.config import BACKEND_API_URL


# ── Backend availability (checked at most every 5 s) ──────────────────
_backend_check: dict = {"ok": False, "ts": 0.0}


def _check_backend_available() -> bool:
    now = time.time()
    if now - _backend_check["ts"] < 5:
        return _backend_check["ok"]
    try:
        r = requests.get(f"{BACKEND_API_URL}/health", timeout=1)
        _backend_check["ok"] = r.status_code == 200
    except Exception:
        _backend_check["ok"] = False
    _backend_check["ts"] = now
    if not _backend_check["ok"]:
        print(
            f"⚠️  Backend not available at {BACKEND_API_URL}. "
            "Start with: python main.py"
        )
    return _backend_check["ok"]


# ── Unified available-data cache (TTL = 60 s) ─────────────────────────
AVAILABLE_TTL = 60
_available: dict = {"data": None, "ts": 0.0}


def _get_available() -> dict:
    """Return /data/available, refreshed at most every AVAILABLE_TTL s."""
    now = time.time()
    if (
        _available["data"] is not None
        and now - _available["ts"] < AVAILABLE_TTL
    ):
        return _available["data"]
    if not _check_backend_available():
        return {}
    try:
        r = requests.get(
            f"{BACKEND_API_URL}/data/available", timeout=5
        )
        if r.status_code == 200 and r.text:
            _available["data"] = r.json()
            _available["ts"] = now
            return _available["data"]
    except Exception as e:
        print(f"❌ Error fetching available data: {e}")
    return _available["data"] or {}


# ── Public helpers ─────────────────────────────────────────────────────

def get_available_seasons() -> List[int]:
    """Return seasons that exist in the cache, sorted descending."""
    data = _get_available()
    seasons = data.get("seasons", [])
    if seasons:
        print(f"✅ Found {len(seasons)} seasons: {seasons}")
    return sorted(seasons, reverse=True)


def get_races_for_season(season: int) -> List[str]:
    """Return race event names for a given season."""
    data = _get_available()
    return data.get(str(season), {}).get("events", [])


def get_sessions_for_event(season: int, event_name: str) -> List[str]:
    """Return available session type codes for a season + event."""
    data = _get_available()
    return (
        data
        .get(str(season), {})
        .get(event_name, {})
        .get("sessions", [])
    )


def enable_cache(cache_dir: str = ".ff1cache") -> None:
    """No-op — frontend reads from backend API, not FastF1 directly."""
    pass


def get_track_layout(
    season: int, event: str, session_type: str = "R"
) -> dict:
    """Fetch circuit X/Y layout from the fastest-lap telemetry."""
    if not _check_backend_available():
        return {"x": [], "y": [], "count": 0}
    try:
        r = requests.get(
            f"{BACKEND_API_URL}/data/track-layout",
            params={
                "season": season,
                "event": event,
                "session_type": session_type,
            },
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return {"x": [], "y": [], "count": 0}
    except Exception as e:
        print(f"❌ Error loading track layout: {e}")
        return {"x": [], "y": [], "count": 0}


def get_race_results(season: int, event_name: str) -> pd.DataFrame:
    """Load race results (driver_code, team, points, position)."""
    if not _check_backend_available():
        return pd.DataFrame()
    for session_type in ("R", "Race"):
        try:
            r = requests.get(
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
            if r.status_code == 404:
                continue
            r.raise_for_status()
            results = r.json().get("results", [])
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
    Load any session type from the normalized cache.

    Returns:
        (laps_df, telemetry_df, session_meta)
    """
    if not _check_backend_available():
        return pd.DataFrame(), pd.DataFrame(), {
            "error": "Backend not available"
        }
    try:
        r = requests.get(
            f"{BACKEND_API_URL}/data/session",
            params={
                "season": season,
                "event": event_name,
                "session_type": session_type,
            },
            timeout=30,
        )
        if r.status_code == 404:
            print(f"⚠️  {season} {event_name} [{session_type}] not found")
            return pd.DataFrame(), pd.DataFrame(), {
                "error": "Session not found"
            }
        if not r.text:
            return pd.DataFrame(), pd.DataFrame(), {
                "error": "Empty response"
            }
        r.raise_for_status()
        data = r.json()
        if "laps" not in data:
            return pd.DataFrame(), pd.DataFrame(), {
                "error": "Invalid format"
            }

        laps = pd.DataFrame(data["laps"])
        col_map = {
            "lap_time_seconds": "LapTimeSeconds",
            "driver_code": "Driver",
            "lap_number": "LapNumber",
            "position": "Position",
        }
        for src, dst in col_map.items():
            if src in laps.columns:
                laps[dst] = laps[src]

        meta = {
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "drivers": data.get("drivers", []),
            "lap_count": len(laps),
        }
        print(f"✅ Loaded {len(laps)} laps for {event_name} [{session_type}]")
        return laps, pd.DataFrame(), meta

    except Exception as e:
        print(f"❌ Error loading session: {e}")
        return pd.DataFrame(), pd.DataFrame(), {"error": str(e)}


def get_predictions(season: int, event_name: str) -> pd.DataFrame:
    """Load pre-computed ML predictions for a race event."""
    if not _check_backend_available():
        return pd.DataFrame()
    try:
        r = requests.get(
            f"{BACKEND_API_URL}/data/predictions",
            params={"season": season, "event": event_name},
            timeout=10,
        )
        if r.status_code == 404:
            return pd.DataFrame()
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as e:
        print(f"❌ Error loading predictions for {event_name}: {e}")
        return pd.DataFrame()


def load_race_session(
    season: int,
    event_name: str,
    preferred_session: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load session data, trying preferred_session first then fallback."""
    priority = [preferred_session] if preferred_session else ["Q", "R"]
    for stype in priority:
        if not stype:
            continue
        laps, tel, meta = load_session(season, event_name, stype)
        if not laps.empty:
            return laps, tel, meta
    for stype in ["Q", "R"]:
        if stype == preferred_session:
            continue
        laps, tel, meta = load_session(season, event_name, stype)
        if not laps.empty:
            return laps, tel, meta
    return pd.DataFrame(), pd.DataFrame(), {}
