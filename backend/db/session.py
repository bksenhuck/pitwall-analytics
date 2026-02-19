"""
Database session management.

SQLite database connection and session handling.
Simple file-based database for caching external API data.

Why SQLite?
- No separate database server needed
- File-based, perfect for development
- Easy to migrate to PostgreSQL later (same SQL syntax)
- Good performance for read-heavy workloads
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


def init_database():
    """
    Initialize database and create tables if they don't exist.
    Called on application startup.
    """
    # Create data directory if it doesn't exist
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create connection and tables
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create cached_data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cached_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on key for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cached_data_key 
            ON cached_data(key)
        """)
        
        # Create index on last_updated for TTL checks
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cached_data_last_updated 
            ON cached_data(last_updated)
        """)
        
        conn.commit()
        print(f"✅ Database initialized: {DB_PATH}")


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cached_data")
    
    Yields:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(str(DB_PATH))
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Return rows as dictionaries instead of tuples
    conn.row_factory = sqlite3.Row
    
    try:
        yield conn
    finally:
        conn.close()


def get_db_stats() -> dict:
    """
    Get database statistics.
    
    Returns:
        dict: Database statistics (size, row count, etc.)
    """
    stats = {
        'db_path': str(DB_PATH),
        'db_exists': DB_PATH.exists(),
        'db_size_bytes': DB_PATH.stat().st_size if DB_PATH.exists() else 0,
    }
    
    if DB_PATH.exists():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM cached_data")
            stats['total_records'] = cursor.fetchone()['count']
    else:
        stats['total_records'] = 0
    
    return stats


def clear_database():
    """
    Clear all data from database.
    Use with caution - this deletes all cached data!
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cached_data")
        conn.commit()
        print("🗑️  Database cleared")
