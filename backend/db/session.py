"""
Database session management - Normalized Schema.

SQLite database with normalized tables for F1 data:
- Better query performance (10-100x faster than JSON blobs)
- Data integrity with foreign keys
- Easier to query and join
- Reduced storage (no JSON redundancy)

Schema:
- seasons: Available F1 seasons
- events: GPs/races for each season
- sessions: Session data (FP1, FP2, Q, R, etc.) for each event
- laps: Individual lap data per session
- results: Race/session results
- weather: Weather conditions per session
- race_control_messages: Race control messages
- session_status: Track status changes (SC, VSC, Red Flag, etc.)
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_DIR = Path(os.getenv('DB_DIR', 'data'))
DB_NAME = os.getenv('DB_NAME', 'pitwall_cache.db')
DB_PATH = DB_DIR / DB_NAME


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Create database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """
    Initialize database with normalized schema.
    Called on application startup.
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # ===== SEASONS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seasons (
                season INTEGER PRIMARY KEY,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ===== EVENTS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                location TEXT,
                country TEXT,
                event_date DATE,
                event_format TEXT,  -- 'conventional', 'sprint'
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (season) REFERENCES seasons(season),
                UNIQUE(season, round_number),
                UNIQUE(season, event_name)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_season 
            ON events(season)
        """)
        
        # ===== SESSIONS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                session_type TEXT NOT NULL,  -- 'FP1', 'FP2', 'FP3', 'Q', 'S', 'SQ', 'R'
                session_name TEXT,
                session_date TIMESTAMP,
                track_length REAL,
                total_laps INTEGER,
                has_data BOOLEAN DEFAULT 0,  -- Flag if data was successfully loaded
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (event_id) REFERENCES events(id),
                UNIQUE(event_id, session_type)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_event 
            ON sessions(event_id)
        """)
        
        # ===== LAPS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                driver_number TEXT NOT NULL,
                driver_code TEXT,
                team TEXT,
                lap_number INTEGER NOT NULL,
                lap_time_seconds REAL,
                sector_1_time_seconds REAL,
                sector_2_time_seconds REAL,
                sector_3_time_seconds REAL,
                speed_i1 REAL,
                speed_i2 REAL,
                speed_fl REAL,
                speed_st REAL,
                is_personal_best BOOLEAN,
                is_accurate BOOLEAN,
                pit_out_time TIMESTAMP,
                pit_in_time TIMESTAMP,
                compound TEXT,  -- Tyre compound
                tyre_life INTEGER,
                fresh_tyre BOOLEAN,
                stint INTEGER,
                track_status TEXT,
                position REAL,
                deleted BOOLEAN DEFAULT 0,
                deleted_reason TEXT,
                
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, driver_number, lap_number)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_laps_session 
            ON laps(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_laps_driver 
            ON laps(session_id, driver_number)
        """)
        
        # ===== RESULTS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                driver_number TEXT NOT NULL,
                driver_code TEXT,
                team TEXT,
                grid_position INTEGER,
                position REAL,
                classification_position TEXT,
                points REAL,
                status TEXT,
                time_seconds REAL,
                fastest_lap_time_seconds REAL,
                fastest_lap_number INTEGER,
                
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, driver_number)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_session 
            ON results(session_id)
        """)
        
        # ===== WEATHER TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                time_seconds REAL NOT NULL,
                air_temp REAL,
                track_temp REAL,
                humidity REAL,
                pressure REAL,
                wind_speed REAL,
                wind_direction INTEGER,
                rainfall BOOLEAN,
                
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, time_seconds)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_session 
            ON weather(session_id)
        """)
        
        # ===== RACE CONTROL MESSAGES TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_control_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                time_seconds REAL,
                category TEXT,
                message TEXT,
                status TEXT,
                flag TEXT,
                scope TEXT,
                sector INTEGER,
                driver_number TEXT,
                
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_race_control_session 
            ON race_control_messages(session_id)
        """)
        
        # ===== SESSION STATUS TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                time_seconds REAL NOT NULL,
                status TEXT,  -- 'AllClear', 'Yellow', 'SCDeployed', 'VSCDeployed', 'Red', etc.
                
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, time_seconds)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_status 
            ON session_status(session_id)
        """)
        
        # ===== METADATA TABLE (for migration tracking, version, etc.) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Set schema version
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ('schema_version', '2.0')
        """)
        
        conn.commit()
        print(f"✅ Normalized database initialized: {DB_PATH}")


if __name__ == "__main__":
    init_database()
    print("\n📊 Schema version 2.0 - Normalized tables:")
    print("  - seasons")
    print("  - events")
    print("  - sessions")
    print("  - laps")
    print("  - results")
    print("  - weather")
    print("  - race_control_messages")
    print("  - session_status")
    print("  - metadata")
