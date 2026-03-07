"""
Data Repository - Parquet-only implementation.

All data is read exclusively from Parquet files:
  data/metadata/{season}/events.parquet    - event catalog
  data/metadata/{season}/sessions.parquet  - session catalog
  data/laps/{season}/event_{id}.parquet    - lap data
  data/results/{season}/event_{id}.parquet - race results
  data/telemetry/{season}/event_{id}.parquet - telemetry
  data/weather/{season}/event_{id}.parquet   - weather
"""
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any

DATA_DIR = Path("data")


class DataRepository:

    # ------------------------------------------------------------------ paths

    @staticmethod
    def _meta_events(season: int) -> Path:
        return DATA_DIR / "metadata" / str(season) / "events.parquet"

    @staticmethod
    def _meta_sessions(season: int) -> Path:
        return DATA_DIR / "metadata" / str(season) / "sessions.parquet"

    @staticmethod
    def _laps_path(season: int, event_id: int) -> Path:
        return DATA_DIR / "laps" / str(season) / f"event_{event_id}.parquet"

    @staticmethod
    def _results_path(season: int, event_id: int) -> Path:
        return DATA_DIR / "results" / str(season) / f"event_{event_id}.parquet"

    @staticmethod
    def _weather_path(season: int, event_id: int) -> Path:
        return DATA_DIR / "weather" / str(season) / f"event_{event_id}.parquet"

    @staticmethod
    def _telemetry_path(season: int, event_id: int) -> Path:
        return DATA_DIR / "telemetry" / str(season) / f"event_{event_id}.parquet"

    # --------------------------------------------------------------- loaders

    @staticmethod
    def _load_events(season: int) -> pd.DataFrame:
        p = DataRepository._meta_events(season)
        if p.exists():
            return pd.read_parquet(p)
        return pd.DataFrame()

    @staticmethod
    def _load_sessions(season: int) -> pd.DataFrame:
        p = DataRepository._meta_sessions(season)
        if p.exists():
            return pd.read_parquet(p)
        return pd.DataFrame()

    @staticmethod
    def _event_id_for_session(season: int, session_id: int) -> Optional[int]:
        df = DataRepository._load_sessions(season)
        if df.empty:
            return None
        rows = df[df["id"] == session_id]
        if rows.empty:
            return None
        return int(rows.iloc[0]["event_id"])

    # ------------------------------------------------------------ seasons

    @staticmethod
    def get_all_seasons() -> List[int]:
        meta_dir = DATA_DIR / "metadata"
        if not meta_dir.exists():
            return []
        seasons = [
            int(d.name)
            for d in meta_dir.iterdir()
            if d.is_dir() and d.name.isdigit()
        ]
        return sorted(seasons, reverse=True)

    @staticmethod
    def get_season_stats(season: int) -> Dict[str, Any]:
        events = DataRepository.get_events_for_season(season)
        return {"season": season, "events": len(events), "sessions": 0, "laps": 0}

    # ------------------------------------------------------------ events

    @staticmethod
    def get_events_for_season(season: int) -> List[Dict[str, Any]]:
        df = DataRepository._load_events(season)
        if df.empty:
            return []
        result = []
        for _, row in df.iterrows():
            result.append({
                "id": int(row["id"]),
                "round": int(row["round_number"]),
                "name": str(row["event_name"]),
                "location": str(row.get("location", "") or ""),
                "country": str(row.get("country", "") or ""),
                "date": str(row.get("event_date", "") or ""),
                "format": str(row.get("event_format", "conventional") or "conventional"),
            })
        return sorted(result, key=lambda x: x["round"])

    @staticmethod
    def get_event_by_name(season: int, event_name: str) -> Optional[Dict[str, Any]]:
        df = DataRepository._load_events(season)
        if df.empty:
            return None
        mask = df["event_name"].str.contains(event_name, case=False, na=False)
        rows = df[mask]
        if rows.empty:
            return None
        row = rows.iloc[0]
        return {
            "id": int(row["id"]),
            "round": int(row["round_number"]),
            "name": str(row["event_name"]),
            "location": str(row.get("location", "") or ""),
            "country": str(row.get("country", "") or ""),
            "date": str(row.get("event_date", "") or ""),
            "format": str(row.get("event_format", "conventional") or "conventional"),
        }

    # ------------------------------------------------------------ sessions

    @staticmethod
    def get_sessions_for_event(
        season: int, event_id_or_name: Any
    ) -> List[Dict[str, Any]]:
        df = DataRepository._load_sessions(season)
        if df.empty:
            return []

        if isinstance(event_id_or_name, str):
            events = DataRepository._load_events(season)
            mask = events["event_name"].str.contains(
                event_id_or_name, case=False, na=False
            )
            if not mask.any():
                return []
            event_id = int(events[mask].iloc[0]["id"])
        else:
            event_id = int(event_id_or_name)

        sess_df = df[df["event_id"] == event_id]
        order = {"FP1": 1, "FP2": 2, "FP3": 3, "SQ": 4, "S": 5, "Q": 6, "R": 7}
        result = []
        for _, row in sess_df.iterrows():
            result.append({
                "id": int(row["id"]),
                "type": str(row["session_type"]),
                "name": str(row.get("session_name", row["session_type"]) or row["session_type"]),
                "date": str(row.get("session_date", "") or ""),
                "track_length": float(row.get("track_length", 0) or 0),
                "total_laps": int(row.get("total_laps", 0) or 0),
                "has_data": bool(row.get("has_data", True)),
            })
        return sorted(result, key=lambda s: order.get(s["type"], 99))

    @staticmethod
    def get_session(
        season: int, event_id: int, session_type: str
    ) -> Optional[Dict[str, Any]]:
        df = DataRepository._load_sessions(season)
        if df.empty:
            return None
        mask = (df["event_id"] == event_id) & (df["session_type"] == session_type)
        rows = df[mask]
        if rows.empty:
            return None
        row = rows.iloc[0]
        return {
            "id": int(row["id"]),
            "type": str(row["session_type"]),
            "name": str(row.get("session_name", row["session_type"]) or row["session_type"]),
            "date": str(row.get("session_date", "") or ""),
            "track_length": float(row.get("track_length", 0) or 0),
            "total_laps": int(row.get("total_laps", 0) or 0),
            "has_data": bool(row.get("has_data", True)),
        }

    # ------------------------------------------------------------ laps

    @staticmethod
    def get_laps_for_session(
        season: int,
        session_id: int,
        driver_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        event_id = DataRepository._event_id_for_session(season, session_id)
        if event_id is None:
            return []
        path = DataRepository._laps_path(season, event_id)
        if not path.exists():
            return []
        try:
            df = pd.read_parquet(path)
            df = df[df["session_id"] == session_id]
            if driver_filter:
                mask = (df["driver_code"] == driver_filter) | (
                    df["driver_number"] == str(driver_filter)
                )
                df = df[mask]
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error reading laps parquet (event {event_id}): {e}")
            return []

    @staticmethod
    def get_drivers_in_session(season: int, session_id: int) -> List[str]:
        event_id = DataRepository._event_id_for_session(season, session_id)
        if event_id is None:
            return []
        path = DataRepository._laps_path(season, event_id)
        if not path.exists():
            return []
        try:
            df = pd.read_parquet(path, columns=["session_id", "driver_code"])
            df = df[df["session_id"] == session_id]
            return sorted(df["driver_code"].dropna().unique().tolist())
        except Exception as e:
            print(f"Error reading drivers (event {event_id}): {e}")
            return []

    @staticmethod
    def get_lap_id(
        season: int, session_id: int, driver_number: str, lap_number: int
    ) -> Optional[int]:
        event_id = DataRepository._event_id_for_session(season, session_id)
        if event_id is None:
            return None
        path = DataRepository._laps_path(season, event_id)
        if not path.exists():
            return None
        try:
            df = pd.read_parquet(path)
            mask = (
                (df["session_id"] == session_id)
                & (
                    (df["driver_number"] == str(driver_number))
                    | (df["driver_code"] == str(driver_number))
                )
                & (df["lap_number"] == lap_number)
            )
            rows = df[mask]
            return int(rows.iloc[0]["id"]) if not rows.empty else None
        except Exception as e:
            print(f"Error resolving lap_id: {e}")
            return None

    # ------------------------------------------------------------ telemetry

    @staticmethod
    def _read_telemetry_parquet(season: int, event_id: int) -> pd.DataFrame:
        """Read telemetry parquet from local disk or GCS fallback."""
        local = DataRepository._telemetry_path(season, event_id)
        if local.exists():
            return pd.read_parquet(local)
        # Fallback: read directly from GCS (telemetry not downloaded at startup)
        import os
        bucket = os.getenv("GCS_BUCKET_NAME", "")
        if bucket:
            try:
                gcs_path = f"gs://{bucket}/telemetry/{season}/event_{event_id}.parquet"
                return pd.read_parquet(gcs_path)
            except Exception:
                pass
        return pd.DataFrame()

    @staticmethod
    def get_telemetry_for_lap(
        season: int, lap_id: int, session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        # If session_id provided, resolve event directly (fast path)
        if session_id is not None:
            event_id = DataRepository._event_id_for_session(season, session_id)
            if event_id is not None:
                try:
                    df = DataRepository._read_telemetry_parquet(season, event_id)
                    if not df.empty and "lap_id" in df.columns:
                        return df[df["lap_id"] == lap_id].to_dict(orient="records")
                except Exception as e:
                    print(f"Error reading telemetry (event {event_id}): {e}")
                return []

        # Slow path: scan all events (fallback when session_id unknown)
        sessions_df = DataRepository._load_sessions(season)
        if sessions_df.empty:
            return []
        for event_id in sessions_df["event_id"].unique():
            try:
                df = DataRepository._read_telemetry_parquet(season, int(event_id))
                if not df.empty and "lap_id" in df.columns and lap_id in df["lap_id"].values:
                    return df[df["lap_id"] == lap_id].to_dict(orient="records")
            except Exception as e:
                print(f"Error reading telemetry (event {event_id}): {e}")
        return []

    def get_track_layout_samples(
        self, season: int, session_id: int
    ) -> Dict[str, Any]:
        return {"x": [], "y": [], "count": 0}

    # ------------------------------------------------------------ results

    @staticmethod
    def get_results_for_session(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        event_id = DataRepository._event_id_for_session(season, session_id)
        if event_id is None:
            return []
        path = DataRepository._results_path(season, event_id)
        if not path.exists():
            return []
        try:
            df = pd.read_parquet(path)
            df = df[df["session_id"] == session_id]
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error reading results parquet (event {event_id}): {e}")
            return []

    # ------------------------------------------------------------ weather

    @staticmethod
    def get_weather_for_session(
        season: int, session_id: int
    ) -> List[Dict[str, Any]]:
        event_id = DataRepository._event_id_for_session(season, session_id)
        if event_id is None:
            return []
        path = DataRepository._weather_path(season, event_id)
        if not path.exists():
            return []
        try:
            df = pd.read_parquet(path)
            df = df[df["session_id"] == session_id]
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error reading weather parquet (event {event_id}): {e}")
            return []

    # ------------------------------------------------------------ availability

    @staticmethod
    def get_available_data() -> Dict[str, Any]:
        seasons = DataRepository.get_all_seasons()
        result: Dict[str, Any] = {"seasons": seasons}

        for season in seasons:
            events_df = DataRepository._load_events(season)
            sessions_df = DataRepository._load_sessions(season)
            if events_df.empty:
                continue

            season_data: Dict[str, Any] = {"events": []}

            for _, event_row in events_df.iterrows():
                event_id = int(event_row["id"])
                event_name = str(event_row["event_name"])
                season_data["events"].append(event_name)

                event_sessions = sessions_df[sessions_df["event_id"] == event_id]
                sessions_list = []
                for _, s_row in event_sessions.iterrows():
                    if bool(s_row.get("has_data", True)):
                        sessions_list.append(str(s_row["session_type"]))

                season_data[event_name] = {"sessions": sessions_list}
                for stype in sessions_list:
                    season_data[event_name][stype] = {"has_data": True}

            result[str(season)] = season_data

        return result

    # ------------------------------------------------------------ stubs (unused in prod)

    @staticmethod
    def get_race_control_messages(season: int, session_id: int) -> List:
        return []

    @staticmethod
    def get_session_status(season: int, session_id: int) -> List:
        return []

    @staticmethod
    def get_database_stats(season: int) -> Dict[str, Any]:
        return {"season": season}
