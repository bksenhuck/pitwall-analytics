from typing import List, Tuple

import fastf1 as ff1
import pandas as pd


def enable_cache(cache_dir: str = ".ff1cache") -> None:
    """Enable FastF1 local cache. Call this once at startup."""
    try:
        ff1.Cache.enable_cache(cache_dir)
    except Exception:
        # best-effort: some environments may not need explicit cache
        pass


def get_available_seasons() -> List[int]:
    """Return a small range of recent seasons. Replace with dynamic query if needed."""
    return [2021, 2022, 2023, 2024]


def get_races_for_season(season: int) -> List[str]:
    """Return a list of event names for a season using FastF1 schedule when available."""
    try:
        schedule = ff1.get_event_schedule(season)
        if hasattr(schedule, "EventName"):
            return schedule["EventName"].tolist()
        # fallback: convert dataframe first column
        return schedule.iloc[:, 0].tolist()
    except Exception:
        # Fallback minimal list
        return ["Bahrain", "Australian", "Monaco"]


def load_race_session(season: int, event_name: str) -> Tuple[pd.DataFrame, pd.DataFrame, object]:
    """Load a race session and return laps and an (optional) telemetry placeholder.

    Returns:
        laps: DataFrame of laps (with LapTimeSeconds)
        telemetry_placeholder: Empty DataFrame (telemetry loaded per-driver)
        session: raw FastF1 session object
    """
    session = ff1.get_session(season, event_name, "R")
    session.load(laps=True, telemetry=False, weather=True)

    laps = session.laps.copy()
    if "LapTime" in laps.columns:
        # convert to seconds for plotting
        laps = laps.assign(LapTimeSeconds=laps["LapTime"].dt.total_seconds())

    telemetry_df = pd.DataFrame()
    return laps, telemetry_df, session


def get_session_with_telemetry(season: int, event_name: str) -> object:
    """Load session with telemetry enabled (can be slower)."""
    session = ff1.get_session(season, event_name, "R")
    session.load(laps=True, telemetry=True, weather=True)
    return session


def get_driver_telemetry(session: object, driver: str) -> pd.DataFrame:
    """Fetch telemetry for the driver's fastest lap in the loaded session."""
    try:
        # use pick_drivers when available (pick_driver is deprecated)
        if hasattr(session.laps, "pick_drivers"):
            driver_laps = session.laps.pick_drivers([driver])
        else:
            # fallback to boolean filtering
            driver_laps = session.laps[session.laps["Driver"] == driver]
        # find fastest lap row
        if driver_laps.empty:
            return pd.DataFrame()
        fastest = driver_laps.loc[driver_laps["LapTime"].idxmin()]
        telemetry = fastest.get_telemetry()
        return telemetry
    except Exception:
        return pd.DataFrame()
