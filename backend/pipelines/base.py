"""
Base Pipeline

Shared SQLite insertion logic used by all F1 data pipelines.
Every _insert_* method is self-contained: receives a season + the FastF1
object it needs and writes directly to the per-season DB.
"""
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

import pandas as pd

from backend.db.session import get_db_connection, init_database
from backend.services.downloader import FastF1Downloader

logger = logging.getLogger(__name__)


class BasePipeline:
    """
    Base class for F1 data pipelines.

    Provides shared DB insertion helpers. Subclasses implement `run()` with
    their own orchestration logic and use `self.downloader` for all FastF1
    calls.
    """

    def __init__(self, downloader: FastF1Downloader):
        self.downloader = downloader

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _init_season_db(self, season: int) -> None:
        init_database(season)

    def _insert_season(self, season: int) -> None:
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO seasons (season) VALUES (?)", (season,)
            )
            cursor.execute(
                "UPDATE seasons SET last_updated = CURRENT_TIMESTAMP WHERE season = ?",
                (season,),
            )
            conn.commit()

    def _insert_event(
        self, season: int, event_info, round_number: int
    ) -> Optional[int]:
        """Insert or update an event row. Returns event_id."""
        event_name = str(
            event_info.get(
                "EventName",
                event_info.get("OfficialEventName", f"Round {round_number}"),
            )
        )
        location = str(event_info.get("Location", ""))
        country = str(event_info.get("Country", ""))
        event_format = str(event_info.get("EventFormat", "conventional"))

        event_date = event_info.get("EventDate", None)
        if pd.notna(event_date):
            event_date = pd.Timestamp(event_date).strftime("%Y-%m-%d")
        else:
            event_date = None

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM events WHERE season = ? AND event_name = ?",
                (season, event_name),
            )
            existing = cursor.fetchone()

            if existing:
                event_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE events
                    SET round_number = ?, location = ?, country = ?,
                        event_date = ?, event_format = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (round_number, location, country, event_date, event_format, event_id),
                )
            else:
                try:
                    cursor.execute(
                        """
                        INSERT INTO events
                        (season, round_number, event_name, location, country,
                         event_date, event_format)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            season,
                            round_number,
                            event_name,
                            location,
                            country,
                            event_date,
                            event_format,
                        ),
                    )
                    event_id = cursor.lastrowid
                except Exception as e:
                    print(f"⚠️  Erro ao inserir evento {season} {event_name}: {e}, usando IGNORE")
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO events
                        (season, round_number, event_name, location, country,
                         event_date, event_format)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            season,
                            round_number,
                            event_name,
                            location,
                            country,
                            event_date,
                            event_format,
                        ),
                    )
                    cursor.execute(
                        "SELECT id FROM events WHERE season = ? AND event_name = ?",
                        (season, event_name),
                    )
                    event_id = cursor.fetchone()["id"]

            conn.commit()
            return event_id

    def _insert_session(
        self, season: int, event_id: int, session_type: str, session
    ) -> Optional[int]:
        """Insert or update a session row. Returns session_id."""
        session_name = str(getattr(session, "name", session_type))
        session_date = getattr(session, "date", None)
        track_length = float(getattr(session, "track_length", 0) or 0)
        total_laps = int(getattr(session, "total_laps", 0) or 0)

        if pd.notna(session_date):
            session_date = pd.Timestamp(session_date).isoformat()
        else:
            session_date = None

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM sessions WHERE event_id = ? AND session_type = ?",
                (event_id, session_type),
            )
            existing = cursor.fetchone()

            if existing:
                session_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE sessions
                    SET session_name = ?, session_date = ?,
                        track_length = ?, total_laps = ?,
                        has_data = 1, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (session_name, session_date, track_length, total_laps, session_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO sessions
                    (event_id, session_type, session_name, session_date,
                     track_length, total_laps, has_data)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        event_id,
                        session_type,
                        session_name,
                        session_date,
                        track_length,
                        total_laps,
                    ),
                )
                session_id = cursor.lastrowid

            conn.commit()
            return session_id

    def _insert_laps(self, season: int, session_id: int, session) -> int:
        """Insert lap data. Returns count of rows inserted."""
        if (
            not hasattr(session, "laps")
            or session.laps is None
            or session.laps.empty
        ):
            return 0

        laps = session.laps

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM laps WHERE session_id = ?", (session_id,))

            count = 0
            for _, lap in laps.iterrows():
                try:
                    def _td(col):
                        v = lap.get(col)
                        return v.total_seconds() if pd.notna(v) else None

                    def _f(col):
                        v = lap.get(col)
                        return float(v) if col in lap.index and pd.notna(v) else None

                    cursor.execute(
                        """
                        INSERT INTO laps (
                            session_id, driver_number, driver_code, team,
                            lap_number, lap_time_seconds,
                            sector_1_time_seconds, sector_2_time_seconds,
                            sector_3_time_seconds,
                            speed_i1, speed_i2, speed_fl, speed_st,
                            is_personal_best, is_accurate,
                            compound, tyre_life, fresh_tyre, stint,
                            track_status, position, deleted, deleted_reason,
                            has_telemetry
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            session_id,
                            str(lap.get("DriverNumber", "")),
                            str(lap.get("Driver", "")),
                            str(lap.get("Team", "")),
                            int(lap.get("LapNumber", 0)),
                            _td("LapTime"),
                            _td("Sector1Time"),
                            _td("Sector2Time"),
                            _td("Sector3Time"),
                            _f("SpeedI1"),
                            _f("SpeedI2"),
                            _f("SpeedFL"),
                            _f("SpeedST"),
                            bool(lap.get("IsPersonalBest", False)),
                            bool(lap.get("IsAccurate", False)),
                            str(lap["Compound"])
                            if pd.notna(lap.get("Compound"))
                            else None,
                            int(lap["TyreLife"])
                            if "TyreLife" in lap.index and pd.notna(lap["TyreLife"])
                            else None,
                            bool(lap.get("FreshTyre", False)),
                            int(lap["Stint"])
                            if "Stint" in lap.index and pd.notna(lap["Stint"])
                            else None,
                            str(lap["TrackStatus"])
                            if pd.notna(lap.get("TrackStatus"))
                            else None,
                            float(lap["Position"])
                            if "Position" in lap.index and pd.notna(lap["Position"])
                            else None,
                            bool(lap.get("Deleted", False)),
                            str(lap["DeletedReason"])
                            if pd.notna(lap.get("DeletedReason"))
                            else None,
                            0,  # has_telemetry
                        ),
                    )
                    count += 1
                except Exception as exc:
                    logger.debug("Lap insert error: %s", exc)
                    continue

            # --- NOVO: Agrupar por EVENTO no Parquet (Um arquivo por Prova) ---
            try:
                laps_dir = Path("data") / "laps" / str(season)
                laps_dir.mkdir(parents=True, exist_ok=True)
                
                # Para manter a lógica por Prova, pegamos o event_id
                with get_db_connection(season) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT event_id FROM sessions WHERE id = ?", (session_id,))
                    event_id = cursor.fetchone()['event_id']

                # Lemos os laps do SQLite para garantir que temos todos do evento até agora
                # (ou anexamos ao existente). Para simplicidade e consistência, regeramos do evento:
                with get_db_connection(season) as conn:
                    df_event_laps = pd.read_sql_query("""
                        SELECT l.* FROM laps l
                        JOIN sessions s ON l.session_id = s.id
                        WHERE s.event_id = ?
                    """, conn, params=(event_id,))
                    
                    parquet_path = laps_dir / f"event_{event_id}.parquet"
                    df_event_laps.to_parquet(parquet_path, compression='snappy', index=False)
                logger.info("Laps for Event %s exported to Parquet", event_id)
            except Exception as e:
                logger.error("Error exporting laps to Parquet: %s", e)

            return count

    def _insert_telemetry(self, season: int, session_id: int, session) -> int:
        """
        Save telemetry (speed, RPM, gear, X/Y/Z…) for all laps into Parquet.
        Returns total laps with telemetry saved.
        """
        if (
            not hasattr(session, "laps")
            or session.laps is None
            or session.laps.empty
        ):
            return 0

        # Build (driver_number, lap_number) -> lap_id map
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, driver_number, lap_number FROM laps WHERE session_id = ?",
                (session_id,),
            )
            lap_map: Dict[Tuple[str, int], int] = {
                (row["driver_number"], row["lap_number"]): row["id"]
                for row in cursor.fetchall()
            }

        telemetry_dir = Path("data") / "telemetry" / str(season)
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        # 1. Coletar TODA a telemetria da sessão primeiro
        all_telemetry_data = []
        
        for driver_number in session.laps["DriverNumber"].unique():
            driver_laps = session.laps.pick_drivers(str(driver_number))

            for _, lap in driver_laps.iterrows():
                lap_number = int(lap["LapNumber"])
                lap_id = lap_map.get((str(driver_number), lap_number))
                if lap_id is None:
                    continue

                try:
                    tel = lap.get_telemetry()
                    if tel is None or tel.empty:
                        continue
                    
                    # Adicionar lap_id para poder filtrar depois
                    tel['lap_id'] = lap_id
                    all_telemetry_data.append(tel)
                    
                    # Marcar como processada no SQL
                    with get_db_connection(season) as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE laps SET has_telemetry = 1 WHERE id = ?", (lap_id,))
                        conn.commit()

                except Exception as exc:
                    logger.debug("Telemetry gathering error: %s", exc)
                    continue

        if not all_telemetry_data:
            return 0

        # 2. Unificar em um único DataFrame e salvar em UM ÚNICO POR EVENTO (Prova)
        combined_df = pd.concat(all_telemetry_data, ignore_index=True)
        
        # Otimizar tipos
        opt_df = pd.DataFrame()
        opt_df['lap_id'] = combined_df['lap_id'].astype('int32')
        opt_df['session_time_seconds'] = combined_df['SessionTime'].dt.total_seconds().astype('float32')
        opt_df['speed'] = combined_df['Speed'].astype('float32')
        opt_df['rpm'] = combined_df['RPM'].astype('int32')
        opt_df['gear'] = combined_df['nGear'].astype('int8')
        opt_df['throttle'] = combined_df['Throttle'].astype('float32')
        opt_df['brake'] = combined_df['Brake'].astype('bool')
        opt_df['drs'] = combined_df['DRS'].astype('int8')
        opt_df['x'] = combined_df['X'].astype('float32')
        opt_df['y'] = combined_df['Y'].astype('float32')
        opt_df['z'] = combined_df['Z'].astype('float32')
        opt_df['source'] = combined_df['Source'].astype('string')

        # Buscar event_id
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id FROM sessions WHERE id = ?", (session_id,))
            event_id = cursor.fetchone()['event_id']

        # Se já existir arquivo do evento (ex: FP1 já rodou e estamos no FP2), 
        # anexamos os dados das sessões anteriores para ter a PROVA COMPLETA.
        parquet_path = telemetry_dir / f"event_{event_id}.parquet"
        if parquet_path.exists():
            try:
                existing_df = pd.read_parquet(parquet_path)
                # Removendo lap_ids desta sessão se por acaso estivermos re-processando
                existing_df = existing_df[~existing_df['lap_id'].isin(opt_df['lap_id'])]
                opt_df = pd.concat([existing_df, opt_df], ignore_index=True)
            except Exception as e:
                logger.warning("Could not append to existing event Parquet: %s", e)

        opt_df.to_parquet(parquet_path, compression='snappy', index=False)

        # 3. Salvar no SQLite (Redundância opcional mas mantida conforme pedido)
        # Nota: Como o DF é grande, o SQLite pode demorar, mas manteremos pela redundância solicitada.
        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM telemetry WHERE lap_id IN (
                    SELECT id FROM laps WHERE session_id = ?
                )
            """, (session_id,))
            
            rows = opt_df.values.tolist()
            cursor.executemany("""
                INSERT INTO telemetry (
                    lap_id, session_time_seconds, speed, rpm, gear,
                    throttle, brake, drs, x, y, z, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()

        return len(all_telemetry_data)

    def _insert_results(self, season: int, session_id: int, session) -> int:
        """Insert race/session results. Returns count inserted."""
        if (
            not hasattr(session, "results")
            or session.results is None
            or session.results.empty
        ):
            return 0

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM results WHERE session_id = ?", (session_id,))

            count = 0
            for _, result in session.results.iterrows():
                try:
                    time_val = result.get("Time")
                    fl_time = result.get("FastestLapTime")
                    cursor.execute(
                        """
                        INSERT INTO results (
                            session_id, driver_number, driver_code, team,
                            grid_position, position, classification_position,
                            points, status, time_seconds,
                            fastest_lap_time_seconds, fastest_lap_number
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            session_id,
                            str(result.get("DriverNumber", "")),
                            str(result.get("Abbreviation", result.get("Driver", ""))),
                            str(result.get("TeamName", result.get("Team", ""))),
                            int(result["GridPosition"])
                            if "GridPosition" in result
                            and pd.notna(result["GridPosition"])
                            else None,
                            float(result["Position"])
                            if "Position" in result and pd.notna(result["Position"])
                            else None,
                            str(result["ClassifiedPosition"])
                            if pd.notna(result.get("ClassifiedPosition"))
                            else None,
                            float(result["Points"])
                            if "Points" in result and pd.notna(result["Points"])
                            else None,
                            str(result["Status"])
                            if pd.notna(result.get("Status"))
                            else None,
                            time_val.total_seconds()
                            if pd.notna(time_val)
                            else None,
                            fl_time.total_seconds() if pd.notna(fl_time) else None,
                            int(result["FastestLap"])
                            if "FastestLap" in result
                            and pd.notna(result["FastestLap"])
                            else None,
                        ),
                    )
                    count += 1
                except Exception as exc:
                    logger.debug("Result insert error: %s", exc)
                    continue

            # --- NOVO: Exportar Results por EVENTO (Prova) ---
            try:
                results_dir = Path("data") / "results" / str(season)
                results_dir.mkdir(parents=True, exist_ok=True)
                
                with get_db_connection(season) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT event_id FROM sessions WHERE id = ?", (session_id,))
                    event_id = cursor.fetchone()['event_id']
                    
                    # Consolidar todos os resultados do evento
                    df_event_results = pd.read_sql_query("""
                        SELECT r.* FROM results r
                        JOIN sessions s ON r.session_id = s.id
                        WHERE s.event_id = ?
                    """, conn, params=(event_id,))
                    
                    parquet_path = results_dir / f"event_{event_id}.parquet"
                    df_event_results.to_parquet(parquet_path, compression='snappy', index=False)
                logger.info("Results for Event %s exported to Parquet", event_id)
            except Exception as e:
                logger.error("Error exporting results to Parquet: %s", e)

            return count

    def _insert_weather(self, season: int, session_id: int, session) -> int:
        """Insert weather data. Returns count inserted."""
        if (
            not hasattr(session, "weather_data")
            or session.weather_data is None
            or session.weather_data.empty
        ):
            return 0

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM weather WHERE session_id = ?", (session_id,))

            count = 0
            for _, w in session.weather_data.iterrows():
                try:
                    time_s = (
                        float(w["Time"].total_seconds())
                        if "Time" in w and pd.notna(w["Time"])
                        else 0
                    )
                    cursor.execute(
                        """
                        INSERT INTO weather (
                            session_id, time_seconds, air_temp, track_temp,
                            humidity, pressure, wind_speed, wind_direction, rainfall
                        ) VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            session_id,
                            time_s,
                            float(w["AirTemp"])
                            if "AirTemp" in w and pd.notna(w["AirTemp"])
                            else None,
                            float(w["TrackTemp"])
                            if "TrackTemp" in w and pd.notna(w["TrackTemp"])
                            else None,
                            float(w["Humidity"])
                            if "Humidity" in w and pd.notna(w["Humidity"])
                            else None,
                            float(w["Pressure"])
                            if "Pressure" in w and pd.notna(w["Pressure"])
                            else None,
                            float(w["WindSpeed"])
                            if "WindSpeed" in w and pd.notna(w["WindSpeed"])
                            else None,
                            int(w["WindDirection"])
                            if "WindDirection" in w and pd.notna(w["WindDirection"])
                            else None,
                            bool(w.get("Rainfall", False)),
                        ),
                    )
                    count += 1
                except Exception:
                    continue

            # --- NOVO: Exportar Weather por EVENTO (Prova) ---
            try:
                weather_dir = Path("data") / "weather" / str(season)
                weather_dir.mkdir(parents=True, exist_ok=True)
                
                with get_db_connection(season) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT event_id FROM sessions WHERE id = ?", (session_id,))
                    event_id = cursor.fetchone()['event_id']

                    # Consolidar clima do evento
                    df_event_weather = pd.read_sql_query("""
                        SELECT w.* FROM weather w
                        JOIN sessions s ON w.session_id = s.id
                        WHERE s.event_id = ?
                    """, conn, params=(event_id,))
                    
                    parquet_path = weather_dir / f"event_{event_id}.parquet"
                    df_event_weather.to_parquet(parquet_path, compression='snappy', index=False)
                logger.info("Weather for Event %s exported to Parquet", event_id)
            except Exception as e:
                logger.error("Error exporting weather to Parquet: %s", e)

            return count

    def _insert_race_control_messages(
        self, season: int, session_id: int, session
    ) -> int:
        """Insert race control messages. Returns count inserted."""
        if (
            not hasattr(session, "race_control_messages")
            or session.race_control_messages is None
            or session.race_control_messages.empty
        ):
            return 0

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM race_control_messages WHERE session_id = ?", (session_id,)
            )

            count = 0
            for _, msg in session.race_control_messages.iterrows():
                try:
                    time_val = msg.get("Time")
                    cursor.execute(
                        """
                        INSERT INTO race_control_messages (
                            session_id, time_seconds, category, message,
                            status, flag, scope, sector, driver_number
                        ) VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            session_id,
                            time_val.total_seconds() if pd.notna(time_val) else None,
                            str(msg["Category"])
                            if pd.notna(msg.get("Category"))
                            else None,
                            str(msg.get("Message", "")),
                            str(msg["Status"])
                            if pd.notna(msg.get("Status"))
                            else None,
                            str(msg["Flag"]) if pd.notna(msg.get("Flag")) else None,
                            str(msg["Scope"]) if pd.notna(msg.get("Scope")) else None,
                            int(msg["Sector"])
                            if "Sector" in msg and pd.notna(msg["Sector"])
                            else None,
                            str(msg["RacingNumber"])
                            if pd.notna(msg.get("RacingNumber"))
                            else None,
                        ),
                    )
                    count += 1
                except Exception:
                    continue

            conn.commit()
            return count

    def _insert_session_status(self, season: int, session_id: int, session) -> int:
        """Insert session/track status changes. Returns count inserted."""
        if (
            not hasattr(session, "session_status")
            or session.session_status is None
            or session.session_status.empty
        ):
            return 0

        with get_db_connection(season) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM session_status WHERE session_id = ?", (session_id,)
            )

            count = 0
            for _, status in session.session_status.iterrows():
                try:
                    time_val = status.get("Time")
                    time_s = time_val.total_seconds() if pd.notna(time_val) else 0
                    cursor.execute(
                        "INSERT INTO session_status (session_id, time_seconds, status) "
                        "VALUES (?, ?, ?)",
                        (session_id, time_s, str(status.get("Status", ""))),
                    )
                    count += 1
                except Exception:
                    continue

            conn.commit()
            return count
