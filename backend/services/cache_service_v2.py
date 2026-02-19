"""
Cache service with TTL (Time To Live) logic.

This is the business logic layer that:
1. Checks if data exists in database
2. Validates TTL (time-to-live)
3. Fetches fresh data if expired
4. Returns cached data if valid

Flow:
    Request → Cache Service → Repository (DB) → External API
                    ↓
              Return to user
"""
from backend.repositories.data_repository import DataRepository
from backend.services.external_api import ExternalAPIService
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
# TTL (Time To Live) in seconds - how long cache is valid
DEFAULT_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '3600'))  # 1 hour default


class CacheService:
    """
    Cache service with TTL-based expiration.
    
    This service implements intelligent caching:
    - Checks database first (fast)
    - Only calls external API if cache expired (slow but fresh)
    - Automatically updates cache
    """
    
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Initialize cache service.
        
        Args:
            ttl_seconds: Time to live in seconds (default from env)
        """
        self.ttl_seconds = ttl_seconds
        self.repository = DataRepository()
        self.external_api = ExternalAPIService()
    
    async def get_data_with_cache(
        self, 
        cache_key: str,
        fetch_callback
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get data with intelligent caching.
        
        Cache Strategy (TTL-based):
        1. Check if data exists in DB
        2. If not → fetch from external API → save → return
        3. If exists:
            a. If TTL expired → fetch new data → update DB → return
            b. If not expired → return cached data
        
        Args:
            cache_key: Unique cache identifier (e.g., "f1_seasons")
            fetch_callback: Async function to call if cache miss/expired
        
        Returns:
            Tuple[dict, bool]: (data, is_from_cache)
                - data: The actual data
                - is_from_cache: True if served from cache, False if fresh
        
        Example:
            data, cached = await cache_service.get_data_with_cache(
                cache_key="f1_seasons",
                fetch_callback=external_api.fetch_f1_seasons
            )
        """
        # Step 1: Check if data exists in cache
        cached_model = self.repository.get_cached_data(cache_key)
        
        # Step 2: If no cache, fetch fresh data
        if not cached_model:
            print(f"📭 Cache MISS for key: {cache_key}")
            fresh_data = await fetch_callback()
            self.repository.save_data(cache_key, fresh_data)
            return fresh_data, False
        
        # Step 3: Check if cache is expired (TTL logic)
        time_since_update = datetime.utcnow() - cached_model.last_updated
        ttl_delta = timedelta(seconds=self.ttl_seconds)
        
        if time_since_update > ttl_delta:
            # Cache expired - fetch fresh data
            print(f"⏰ Cache EXPIRED for key: {cache_key} (age: {time_since_update.total_seconds()}s > TTL: {self.ttl_seconds}s)")
            fresh_data = await fetch_callback()
            self.repository.save_data(cache_key, fresh_data)
            return fresh_data, False
        
        # Step 4: Cache is valid - return cached data
        print(f"✅ Cache HIT for key: {cache_key} (age: {time_since_update.total_seconds()}s)")
        cached_data = json.loads(cached_model.data)
        return cached_data, True
    
    async def refresh_data(
        self, 
        cache_key: str,
        fetch_callback
    ) -> Dict[str, Any]:
        """
        Force refresh data (bypass cache).
        
        This function:
        1. Fetches new data from external API (always)
        2. Overwrites database
        3. Updates timestamp
        4. Returns fresh data
        
        Use this when user explicitly requests fresh data.
        
        Args:
            cache_key: Cache identifier
            fetch_callback: Async function to fetch fresh data
        
        Returns:
            dict: Fresh data from external API
        
        Example:
            fresh_data = await cache_service.refresh_data(
                cache_key="f1_seasons",
                fetch_callback=external_api.fetch_f1_seasons
            )
        """
        print(f"🔄 Force REFRESH for key: {cache_key}")
        
        # Fetch fresh data from external API
        fresh_data = await fetch_callback()
        
        # Save/update in database
        self.repository.save_data(cache_key, fresh_data)
        
        return fresh_data
    
    def get_cache_info(self, cache_key: str) -> Dict[str, Any]:
        """
        Get information about cached data.
        
        Args:
            cache_key: Cache identifier
        
        Returns:
            dict: Cache metadata (age, TTL, status, etc.)
        """
        cached_model = self.repository.get_cached_data(cache_key)
        
        if not cached_model:
            return {
                'exists': False,
                'key': cache_key,
                'message': 'No cached data found'
            }
        
        time_since_update = datetime.utcnow() - cached_model.last_updated
        ttl_delta = timedelta(seconds=self.ttl_seconds)
        is_expired = time_since_update > ttl_delta
        
        return {
            'exists': True,
            'key': cache_key,
            'last_updated': cached_model.last_updated.isoformat(),
            'age_seconds': time_since_update.total_seconds(),
            'ttl_seconds': self.ttl_seconds,
            'is_expired': is_expired,
            'expires_in_seconds': max(0, (ttl_delta - time_since_update).total_seconds())
        }
    
    def invalidate_cache(self, cache_key: str) -> bool:
        """
        Invalidate (delete) cached data.
        
        Args:
            cache_key: Cache identifier
        
        Returns:
            bool: True if deleted, False if not found
        """
        print(f"🗑️  Invalidating cache for key: {cache_key}")
        return self.repository.delete_cached_data(cache_key)
    
    def get_all_cache_keys(self) -> list[str]:
        """
        Get all cache keys.
        
        Returns:
            list: All cache keys in database
        """
        return self.repository.get_all_keys()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get overall cache statistics.
        
        Returns:
            dict: Cache statistics
        """
        repo_stats = self.repository.get_stats()
        return {
            'ttl_seconds': self.ttl_seconds,
            'ttl_human': f"{self.ttl_seconds // 60} minutes" if self.ttl_seconds >= 60 else f"{self.ttl_seconds} seconds",
            **repo_stats
        }
