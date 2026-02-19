"""
Data repository layer.

This module is responsible ONLY for database operations.
No business logic here - just CRUD operations.

Separation of concerns:
- Repository: Database operations (this file)
- Service: Business logic (cache_service.py)
- Route: HTTP handling (routes/data.py)
"""
from backend.db.session import get_db_connection
from backend.models.data_model import CachedDataModel
from datetime import datetime
from typing import Optional
import json


class DataRepository:
    """
    Repository for cached data operations.
    
    Handles all database interactions for the cached_data table.
    """
    
    @staticmethod
    def get_cached_data(key: str) -> Optional[CachedDataModel]:
        """
        Get cached data by key.
        
        Args:
            key: Unique cache key (e.g., "f1_seasons", "race_2023_monaco")
        
        Returns:
            CachedDataModel if found, None otherwise
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM cached_data WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row:
                return CachedDataModel(
                    id=row['id'],
                    key=row['key'],
                    data=row['data'],
                    last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else None,
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
            return None
    
    @staticmethod
    def save_data(key: str, data: dict) -> CachedDataModel:
        """
        Save or update cached data.
        
        Args:
            key: Unique cache key
            data: Data to cache (will be JSON serialized)
        
        Returns:
            CachedDataModel: Saved data model
        """
        data_json = json.dumps(data)
        now = datetime.utcnow()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use INSERT OR REPLACE to handle both insert and update
            cursor.execute("""
                INSERT INTO cached_data (key, data, last_updated, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    data = excluded.data,
                    last_updated = excluded.last_updated
            """, (key, data_json, now.isoformat(), now.isoformat()))
            
            conn.commit()
            
            # Return the saved model
            return CachedDataModel(
                id=cursor.lastrowid,
                key=key,
                data=data_json,
                last_updated=now,
                created_at=now
            )
    
    @staticmethod
    def get_last_updated(key: str) -> Optional[datetime]:
        """
        Get last updated timestamp for a cache key.
        
        Args:
            key: Cache key
        
        Returns:
            datetime if record exists, None otherwise
        """
        cached = DataRepository.get_cached_data(key)
        return cached.last_updated if cached else None
    
    @staticmethod
    def delete_cached_data(key: str) -> bool:
        """
        Delete cached data by key.
        
        Args:
            key: Cache key to delete
        
        Returns:
            bool: True if deleted, False if not found
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cached_data WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def get_all_keys() -> list[str]:
        """
        Get all cache keys in database.
        
        Returns:
            list: All cache keys
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key FROM cached_data ORDER BY last_updated DESC")
            return [row['key'] for row in cursor.fetchall()]
    
    @staticmethod
    def get_stats() -> dict:
        """
        Get repository statistics.
        
        Returns:
            dict: Statistics about cached data
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total records
            cursor.execute("SELECT COUNT(*) as count FROM cached_data")
            total = cursor.fetchone()['count']
            
            # Oldest and newest
            cursor.execute("""
                SELECT 
                    MIN(last_updated) as oldest,
                    MAX(last_updated) as newest
                FROM cached_data
            """)
            row = cursor.fetchone()
            
            return {
                'total_records': total,
                'oldest_update': row['oldest'],
                'newest_update': row['newest']
            }
