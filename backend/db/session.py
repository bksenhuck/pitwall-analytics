"""
Database session management - Per-Season Normalized Schema.

Each season gets its own SQLite file: data/pitwall_{year}.db
This keeps individual files manageable even with telemetry (~3-5 GB/season).

Schema per DB:
- seasons: Season metadata (one row per DB)
- events: GPs/races for the season
- sessions: Session data (FP1, FP2, Q, R, etc.) for each event
- laps: Individual lap data per session
- telemetry: Car + position telemetry per lap (X, Y, Z, speed, throttle, etc.)
- results: Race/session results
- weather: Weather conditions per session
- race_control_messages: Race control messages
- session_status: Track status changes (SC, VSC, Red Flag, etc.)
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, List
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_DIR = Path(os.getenv('DB_DIR', 'data'))


def get_db_path(season: int) -> Path:
    """Return the path for a season-specific database file."""
    return DB_DIR / f"pitwall_{season}.db"


@contextmanager
def get_db_connection(season: int) -> Generator[sqlite3.Connection, None, None]:
    """Create database connection for a specific season's DB."""
    conn = sqlite3.connect(get_db_path(season))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_available_season_dbs() -> List[int]:
    """
    Scan the data directory for existing season database files.

    Returns:
        List of season years (descending) for which a pitwall_{year}.db exists.
    """
    if not DB_DIR.exists():
        return []
    seasons = []
    for f in DB_DIR.glob("pitwall_*.db"):
        try:
            year = int(f.stem.split("_")[1])
            seasons.append(year)
        except (IndexError, ValueError):
            pass
    return sorted(seasons, reverse=True)


def init_database(season: int):
    """
    Initialize the database for a given season with the normalized schema.
    Called by populate_cache.py before writing data for a season.
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with get_db_connection(season) as conn:
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
                event_format TEXT,
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
                session_type TEXT NOT NULL,
                session_name TEXT,
                session_date TIMESTAMP,
                track_length REAL,
                total_laps INTEGER,
                has_data BOOLEAN DEFAULT 0,
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
                compound TEXT,
                tyre_life INTEGER,
                fresh_tyre BOOLEAN,
                stint INTEGER,
                track_status TEXT,
                position REAL,
                deleted BOOLEAN DEFAULT 0,
                deleted_reason TEXT,
                has_telemetry BOOLEAN DEFAULT 0,

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

        # ===== TELEMETRY TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lap_id INTEGER NOT NULL,
                session_time_seconds REAL,
                speed REAL,
                rpm INTEGER,
                gear INTEGER,
                throttle REAL,
                brake BOOLEAN,
                drs INTEGER,
                x REAL,
                y REAL,
                z REAL,
                source TEXT,

                FOREIGN KEY (lap_id) REFERENCES laps(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_lap
            ON telemetry(lap_id)
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
                status TEXT,

                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, time_seconds)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_status
            ON session_status(session_id)
        """)

        # ===== METADATA TABLE =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ('schema_version', '3.0')
        """)

        conn.commit()
        print(f"✅ Database initialized: {get_db_path(season)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python session.py <season>")
        sys.exit(1)
    init_database(int(sys.argv[1]))
