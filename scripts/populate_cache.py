"""
Populate Cache - Load FastF1 data into normalized SQLite schema

This script loads F1 data from FastF1 and stores it in the normalized database.

Usage:
    python scripts/populate_cache.py --season 2024
    python scripts/populate_cache.py --season 2024 --event "Bahrain"
    python scripts/populate_cache.py --from 2023 --to 2024
"""
import argparse
import asyncio
from pathlib import Path
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import fastf1 as ff1
import pandas as pd

from backend.db.session import get_db_connection, init_database


class CachePopulator:
    """Populate normalized SQLite cache with F1 data"""
    
    def __init__(self):
        """Initialize cache populator"""
        # Enable FastF1 cache
        cache_dir = project_root / '.ff1cache'
        cache_dir.mkdir(exist_ok=True)
        ff1.Cache.enable_cache(str(cache_dir))
        
        # Initialize database
        init_database()
        
    def populate_season(self, season: int, event_filter: Optional[str] = None):
        """
        Populate all data for a season.
        
        Args:
            season: Year (e.g., 2024)
            event_filter: Optional event name filter (e.g., "Bahrain")
        """
        print(f"\n{'='*60}")
        print(f"📅 Processing Season {season}")
        print(f"{'='*60}\n")
        
        # Insert season
        self._insert_season(season)
        
        # Get schedule
        try:
            schedule = ff1.get_event_schedule(season)
        except Exception as e:
            print(f"❌ Failed to get schedule for {season}: {e}")
            return
        
        total_events = len(schedule)
        
        for idx, (_, event_info) in enumerate(schedule.iterrows(), 1):
            event_name = str(event_info.get('EventName', event_info.get('OfficialEventName', f'Round {idx}')))
            
            # Skip if filtering by event
            if event_filter and event_filter.lower() not in event_name.lower():
                continue
            
            print(f"\n[{idx}/{total_events}] 🏁 {event_name}")
            print("-" * 60)
            
            # Insert event
            event_id = self._insert_event(season, event_info, idx)
            
            if not event_id:
                print(f"  ⚠️  Skipped (failed to insert event)")
                continue
            
            # Load sessions for this event
            self._populate_event_sessions(season, event_name, event_id)
    
    def _insert_season(self, season: int):
        """Insert season into database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO seasons (season)
                VALUES (?)
            """, (season,))
            
            cursor.execute("""
                UPDATE seasons 
                SET last_updated = CURRENT_TIMESTAMP 
                WHERE season = ?
            """, (season,))
            
            conn.commit()
    
    def _insert_event(self, season: int, event_info, round_number: int) -> Optional[int]:
        """
        Insert event into database.
        
        Returns:
            event_id if successful, None otherwise
        """
        event_name = str(event_info.get('EventName', event_info.get('OfficialEventName', f'Round {round_number}')))
        location = str(event_info.get('Location', ''))
        country = str(event_info.get('Country', ''))
        event_date = event_info.get('EventDate', None)
        event_format = str(event_info.get('EventFormat', 'conventional'))
        
        # Convert date to string if it's a Timestamp
        if pd.notna(event_date):
            event_date = pd.Timestamp(event_date).strftime('%Y-%m-%d')
        else:
            event_date = None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute("""
                SELECT id FROM events 
                WHERE season = ? AND round_number = ?
            """, (season, round_number))
            
            existing = cursor.fetchone()
            
            if existing:
                event_id = existing['id']
                # Update
                cursor.execute("""
                    UPDATE events 
                    SET event_name = ?, location = ?, country = ?, 
                        event_date = ?, event_format = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (event_name, location, country, event_date, event_format, event_id))
            else:
                # Insert
                cursor.execute("""
                    INSERT INTO events 
                    (season, round_number, event_name, location, country, event_date, event_format)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (season, round_number, event_name, location, country, event_date, event_format))
                event_id = cursor.lastrowid
            
            conn.commit()
            return event_id
    
    def _populate_event_sessions(self, season: int, event_name: str, event_id: int):
        """Populate all sessions for an event"""
        
        # Determine session types based on event format
        try:
            event = ff1.get_event(season, event_name)
            
            # Check if sprint format
            is_sprint = hasattr(event, 'is_testing') and not event.is_testing()
            
            # Standard sessions
            session_types = ['FP1', 'FP2', 'FP3', 'Q', 'R']
            
            # Add sprint sessions if applicable
            if is_sprint:
                try:
                    # Try to get sprint sessions
                    _ = ff1.get_session(season, event_name, 'S')
                    session_types = ['FP1', 'SQ', 'S', 'Q', 'R']
                except:
                    pass  # Not a sprint weekend
        except:
            # Fallback to standard
            session_types = ['FP1', 'FP2', 'FP3', 'Q', 'R']
        
        for session_type in session_types:
            try:
                print(f"  📊 {session_type}...", end=" ", flush=True)
                
                # Try to load session
                session = ff1.get_session(season, event_name, session_type)
                
                # Load data
                session.load(
                    laps=True,
                    telemetry=False,  # Skip telemetry for now (too large)
                    weather=True,
                    messages=True
                )
                
                # Insert session
                session_id = self._insert_session(event_id, session_type, session)
                
                if not session_id:
                    print("❌ Failed to insert session")
                    continue
                
                # Insert laps
                laps_count = self._insert_laps(session_id, session)
                
                # Insert results
                results_count = self._insert_results(session_id, session)
                
                # Insert weather
                weather_count = self._insert_weather(session_id, session)
                
                # Insert race control messages
                messages_count = self._insert_race_control_messages(session_id, session)
                
                # Insert session status
                status_count = self._insert_session_status(session_id, session)
                
                print(f"✅ L:{laps_count} R:{results_count} W:{weather_count} M:{messages_count} S:{status_count}")
                
            except Exception as e:
                print(f"⚠️  {str(e)[:50]}")
                continue
    
    def _insert_session(self, event_id: int, session_type: str, session) -> Optional[int]:
        """Insert session metadata"""
        
        session_name = str(getattr(session, 'name', session_type))
        session_date = getattr(session, 'date', None)
        track_length = float(getattr(session, 'track_length', 0) or 0)
        total_laps = int(getattr(session, 'total_laps', 0) or 0)
        
        if pd.notna(session_date):
            session_date = pd.Timestamp(session_date).isoformat()
        else:
            session_date = None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM sessions 
                WHERE event_id = ? AND session_type = ?
            """, (event_id, session_type))
            
            existing = cursor.fetchone()
            
            if existing:
                session_id = existing['id']
                cursor.execute("""
                    UPDATE sessions 
                    SET session_name = ?, session_date = ?, 
                        track_length = ?, total_laps = ?,
                        has_data = 1, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (session_name, session_date, track_length, total_laps, session_id))
            else:
                cursor.execute("""
                    INSERT INTO sessions 
                    (event_id, session_type, session_name, session_date, track_length, total_laps, has_data)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (event_id, session_type, session_name, session_date, track_length, total_laps))
                session_id = cursor.lastrowid
            
            conn.commit()
            return session_id
    
    def _insert_laps(self, session_id: int, session) -> int:
        """Insert lap data"""
        if not hasattr(session, 'laps') or session.laps is None or session.laps.empty:
            return 0
        
        laps = session.laps
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing laps for this session
            cursor.execute("DELETE FROM laps WHERE session_id = ?", (session_id,))
            
            count = 0
            for _, lap in laps.iterrows():
                try:
                    # Extract fields with safe defaults
                    driver_number = str(lap.get('DriverNumber', ''))
                    driver_code = str(lap.get('Driver', ''))
                    team = str(lap.get('Team', ''))
                    lap_number = int(lap.get('LapNumber', 0))
                    
                    # Convert timedeltas to seconds
                    lap_time = lap.get('LapTime')
                    lap_time_seconds = lap_time.total_seconds() if pd.notna(lap_time) else None
                    
                    s1 = lap.get('Sector1Time')
                    s1_seconds = s1.total_seconds() if pd.notna(s1) else None
                    
                    s2 = lap.get('Sector2Time')
                    s2_seconds = s2.total_seconds() if pd.notna(s2) else None
                    
                    s3 = lap.get('Sector3Time')
                    s3_seconds = s3.total_seconds() if pd.notna(s3) else None
                    
                    # Speed traps
                    speed_i1 = float(lap['SpeedI1']) if 'SpeedI1' in lap and pd.notna(lap['SpeedI1']) else None
                    speed_i2 = float(lap['SpeedI2']) if 'SpeedI2' in lap and pd.notna(lap['SpeedI2']) else None
                    speed_fl = float(lap['SpeedFL']) if 'SpeedFL' in lap and pd.notna(lap['SpeedFL']) else None
                    speed_st = float(lap['SpeedST']) if 'SpeedST' in lap and pd.notna(lap['SpeedST']) else None
                    
                    # Booleans
                    is_personal_best = bool(lap.get('IsPersonalBest', False))
                    is_accurate = bool(lap.get('IsAccurate', False))
                    fresh_tyre = bool(lap.get('FreshTyre', False))
                    deleted = bool(lap.get('Deleted', False))
                    
                    # Other fields
                    compound = str(lap.get('Compound', '')) if pd.notna(lap.get('Compound')) else None
                    tyre_life = int(lap['TyreLife']) if 'TyreLife' in lap and pd.notna(lap['TyreLife']) else None
                    stint = int(lap['Stint']) if 'Stint' in lap and pd.notna(lap['Stint']) else None
                    track_status = str(lap.get('TrackStatus', '')) if pd.notna(lap.get('TrackStatus')) else None
                    position = float(lap['Position']) if 'Position' in lap and pd.notna(lap['Position']) else None
                    deleted_reason = str(lap.get('DeletedReason', '')) if pd.notna(lap.get('DeletedReason')) else None
                    
                    cursor.execute("""
                        INSERT INTO laps (
                            session_id, driver_number, driver_code, team, lap_number,
                            lap_time_seconds, sector_1_time_seconds, sector_2_time_seconds, sector_3_time_seconds,
                            speed_i1, speed_i2, speed_fl, speed_st,
                            is_personal_best, is_accurate, compound, tyre_life,
                            fresh_tyre, stint, track_status, position, deleted, deleted_reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, driver_number, driver_code, team, lap_number,
                        lap_time_seconds, s1_seconds, s2_seconds, s3_seconds,
                        speed_i1, speed_i2, speed_fl, speed_st,
                        is_personal_best, is_accurate, compound, tyre_life,
                        fresh_tyre, stint, track_status, position, deleted, deleted_reason
                    ))
                    
                    count += 1
                    
                except Exception as e:
                    print(f"\n    ⚠️  Error inserting lap {lap_number}: {e}")
                    continue
            
            conn.commit()
            return count
    
    def _insert_results(self, session_id: int, session) -> int:
        """Insert race/session results"""
        if not hasattr(session, 'results') or session.results is None or session.results.empty:
            return 0
        
        results = session.results
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing results
            cursor.execute("DELETE FROM results WHERE session_id = ?", (session_id,))
            
            count = 0
            for _, result in results.iterrows():
                try:
                    driver_number = str(result.get('DriverNumber', ''))
                    driver_code = str(result.get('Abbreviation', result.get('Driver', '')))
                    team = str(result.get('TeamName', result.get('Team', '')))
                    grid_position = int(result['GridPosition']) if 'GridPosition' in result and pd.notna(result['GridPosition']) else None
                    position = float(result['Position']) if 'Position' in result and pd.notna(result['Position']) else None
                    classification_position = str(result.get('ClassifiedPosition', '')) if pd.notna(result.get('ClassifiedPosition')) else None
                    points = float(result['Points']) if 'Points' in result and pd.notna(result['Points']) else None
                    status = str(result.get('Status', '')) if pd.notna(result.get('Status')) else None
                    
                    # Time
                    time_val = result.get('Time')
                    time_seconds = time_val.total_seconds() if pd.notna(time_val) else None
                    
                    # Fastest lap
                    fl_time = result.get('FastestLapTime')
                    fl_time_seconds = fl_time.total_seconds() if pd.notna(fl_time) else None
                    fl_number = int(result['FastestLap']) if 'FastestLap' in result and pd.notna(result['FastestLap']) else None
                    
                    cursor.execute("""
                        INSERT INTO results (
                            session_id, driver_number, driver_code, team,
                            grid_position, position, classification_position,
                            points, status, time_seconds, 
                            fastest_lap_time_seconds, fastest_lap_number
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, driver_number, driver_code, team,
                        grid_position, position, classification_position,
                        points, status, time_seconds,
                        fl_time_seconds, fl_number
                    ))
                    
                    count += 1
                    
                except Exception as e:
                    print(f"\n    ⚠️  Error inserting result: {e}")
                    continue
            
            conn.commit()
            return count
    
    def _insert_weather(self, session_id: int, session) -> int:
        """Insert weather data"""
        if not hasattr(session, 'weather_data') or session.weather_data is None or session.weather_data.empty:
            return 0
        
        weather = session.weather_data
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing weather
            cursor.execute("DELETE FROM weather WHERE session_id = ?", (session_id,))
            
            count = 0
            for _, w in weather.iterrows():
                try:
                    time_seconds = float(w['Time'].total_seconds()) if 'Time' in w and pd.notna(w['Time']) else 0
                    air_temp = float(w['AirTemp']) if 'AirTemp' in w and pd.notna(w['AirTemp']) else None
                    track_temp = float(w['TrackTemp']) if 'TrackTemp' in w and pd.notna(w['TrackTemp']) else None
                    humidity = float(w['Humidity']) if 'Humidity' in w and pd.notna(w['Humidity']) else None
                    pressure = float(w['Pressure']) if 'Pressure' in w and pd.notna(w['Pressure']) else None
                    wind_speed = float(w['WindSpeed']) if 'WindSpeed' in w and pd.notna(w['WindSpeed']) else None
                    wind_direction = int(w['WindDirection']) if 'WindDirection' in w and pd.notna(w['WindDirection']) else None
                    rainfall = bool(w.get('Rainfall', False))
                    
                    cursor.execute("""
                        INSERT INTO weather (
                            session_id, time_seconds, air_temp, track_temp,
                            humidity, pressure, wind_speed, wind_direction, rainfall
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, time_seconds, air_temp, track_temp,
                        humidity, pressure, wind_speed, wind_direction, rainfall
                    ))
                    
                    count += 1
                    
                except Exception as e:
                    continue
            
            conn.commit()
            return count
    
    def _insert_race_control_messages(self, session_id: int, session) -> int:
        """Insert race control messages"""
        if not hasattr(session, 'race_control_messages') or session.race_control_messages is None or session.race_control_messages.empty:
            return 0
        
        messages = session.race_control_messages
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing messages
            cursor.execute("DELETE FROM race_control_messages WHERE session_id = ?", (session_id,))
            
            count = 0
            for _, msg in messages.iterrows():
                try:
                    time_val = msg.get('Time')
                    time_seconds = time_val.total_seconds() if pd.notna(time_val) else None
                    category = str(msg.get('Category', '')) if pd.notna(msg.get('Category')) else None
                    message = str(msg.get('Message', ''))
                    status = str(msg.get('Status', '')) if pd.notna(msg.get('Status')) else None
                    flag = str(msg.get('Flag', '')) if pd.notna(msg.get('Flag')) else None
                    scope = str(msg.get('Scope', '')) if pd.notna(msg.get('Scope')) else None
                    sector = int(msg['Sector']) if 'Sector' in msg and pd.notna(msg['Sector']) else None
                    driver_number = str(msg.get('RacingNumber', '')) if pd.notna(msg.get('RacingNumber')) else None
                    
                    cursor.execute("""
                        INSERT INTO race_control_messages (
                            session_id, time_seconds, category, message,
                            status, flag, scope, sector, driver_number
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, time_seconds, category, message,
                        status, flag, scope, sector, driver_number
                    ))
                    
                    count += 1
                    
                except Exception as e:
                    continue
            
            conn.commit()
            return count
    
    def _insert_session_status(self, session_id: int, session) -> int:
        """Insert session/track status changes"""
        if not hasattr(session, 'session_status') or session.session_status is None or session.session_status.empty:
            return 0
        
        status_data = session.session_status
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing status
            cursor.execute("DELETE FROM session_status WHERE session_id = ?", (session_id,))
            
            count = 0
            for _, status in status_data.iterrows():
                try:
                    time_val = status.get('Time')
                    time_seconds = time_val.total_seconds() if pd.notna(time_val) else 0
                    status_text = str(status.get('Status', ''))
                    
                    cursor.execute("""
                        INSERT INTO session_status (session_id, time_seconds, status)
                        VALUES (?, ?, ?)
                    """, (session_id, time_seconds, status_text))
                    
                    count += 1
                    
                except Exception as e:
                    continue
            
            conn.commit()
            return count


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description='Populate F1 data cache with normalized schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load single season
  python scripts/populate_cache.py --season 2024

  # Load specific event
  python scripts/populate_cache.py --season 2024 --event "Bahrain"

  # Load range of seasons
  python scripts/populate_cache.py --from 2023 --to 2024
        """
    )
    
    parser.add_argument('--season', type=int, help='Season year (e.g., 2024)')
    parser.add_argument('--event', type=str, help='Event name filter (e.g., "Bahrain")')
    parser.add_argument('--from', type=int, dest='from_season', help='Start season (inclusive)')
    parser.add_argument('--to', type=int, dest='to_season', help='End season (inclusive)')
    
    args = parser.parse_args()
    
    populator = CachePopulator()
    
    if args.from_season and args.to_season:
        # Range mode
        for season in range(args.from_season, args.to_season + 1):
            populator.populate_season(season)
    elif args.season:
        # Single season
        populator.populate_season(args.season, args.event)
    else:
        parser.print_help()
        print("\n❌ Error: Must specify --season or --from/--to")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("✅ Population complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
