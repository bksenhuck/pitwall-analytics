"""
Data routes with MANUAL caching control.

FastAPI endpoints for cache management:
- GET /read → read ONLY from SQLite (no automatic API fallback)
- POST /populate → manually fetch from API and save to SQLite
- GET /cache/info → show cache metadata
- GET /cache/keys → list all cache keys
- DELETE /cache → delete specific cache entry

Architecture:
- Frontend: calls /read (only reads SQLite)
- You (admin): calls /populate via terminal to update cache
- No automatic TTL refresh - YOU control when to fetch from API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from backend.repositories.data_repository import DataRepository
from backend.services.external_api import ExternalAPIService
from backend.models.data_model import CachedDataResponse, RefreshResponse
from datetime import datetime
import json

router = APIRouter()

# Initialize services
repository = DataRepository()
external_api = ExternalAPIService()


@router.get('/read', response_model=CachedDataResponse)
async def read_from_cache(
    key: str = Query('f1_seasons', description="Cache key to read")
) -> CachedDataResponse:
    """
    Read data ONLY from SQLite cache (read-only, no API fallback).
    
    This endpoint:
    1. Reads ONLY from SQLite database
    2. If data doesn't exist → returns 404 error
    3. NEVER calls external API automatically
    
    Use this for:
    - Frontend data consumption
    - Fast reads from pre-populated cache
    
    To populate cache, use POST /populate endpoint.
    
    Query Parameters:
        - key: Cache key (e.g., 'f1_seasons', 'race_2023_monaco')
    
    Returns:
        CachedDataResponse with data from SQLite
    
    Raises:
        404: If cache key doesn't exist (cache not populated yet)
    
    Example:
        GET /api/cached/read?key=f1_seasons
    """
    try:
        # Get from cache ONLY (no fallback)
        cached_model = repository.get_cached_data(key)
        
        if not cached_model:
            raise HTTPException(
                status_code=404,
                detail=f"Cache key '{key}' not found. Use POST /populate to fetch and cache data first."
            )
        
        # Parse data
        data = json.loads(cached_model.data)
        
        return CachedDataResponse(
            success=True,
            data=data,
            cached=True,
            last_updated=cached_model.last_updated,
            message=f"Data read from cache (last updated: {cached_model.last_updated})"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading cache: {str(e)}")


@router.post('/populate', response_model=RefreshResponse)
async def populate_cache(
    key: str = Query('f1_seasons', description="Cache key to populate")
) -> RefreshResponse:
    """
    Manually populate cache by fetching from external API.
    
    This endpoint:
    1. ALWAYS fetches fresh data from external API
    2. Saves/updates data in SQLite cache
    3. Returns the fetched data
    
    This is the ONLY way to update the cache - you control when it happens.
    
    Use when:
    - You want to update cache with fresh data
    - Initializing cache for the first time
    - You know external data has changed (e.g., new F1 season)
    
    Query Parameters:
        - key: Cache key to populate (e.g., 'f1_seasons', 'race_2024_bahrain')
    
    Returns:
        RefreshResponse with:
            - success: Operation status
            - message: What happened
            - last_updated: When data was fetched
            - records_updated: Number of records
    
    Example:
        POST /api/cached/populate?key=f1_seasons
        
    Terminal usage:
        curl -X POST "http://127.0.0.1:5000/api/cached/populate?key=f1_seasons"
    """
    try:
        # Define fetch callback based on cache key
        if key == 'f1_seasons':
            fetch_callback = external_api.fetch_f1_seasons
        
        elif key.startswith('races_'):
            # Format: races_2024
            parts = key.split('_')
            if len(parts) == 2:
                season = int(parts[1])
                fetch_callback = lambda: external_api.fetch_races_for_season(season)
            else:
                raise ValueError(
                    "Invalid races key format. Use: races_YEAR (e.g., races_2024)"
                )
        
        elif key.startswith('race_'):
            # Format: race_2024_bahrain or race_2024_Bahrain_Grand_Prix
            parts = key.split('_', 2)  # Split into max 3 parts
            if len(parts) >= 3:
                season = int(parts[1])
                event = parts[2].replace('_', ' ')  # Convert back underscores to spaces
                fetch_callback = lambda: external_api.fetch_race_session_data(
                    season, event, 'R'
                )
            else:
                raise ValueError(
                    "Invalid race key format. Use: race_YEAR_EVENT "
                    "(e.g., race_2024_bahrain or race_2024_Bahrain_Grand_Prix)"
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown cache key: {key}. Supported formats:\n"
                    "- 'f1_seasons' (list of seasons)\n"
                    "- 'races_YEAR' (races for a season, e.g., races_2024)\n"
                    "- 'race_YEAR_EVENT' (race data, e.g., race_2024_bahrain)"
                )
            )
        
        # Fetch from external API
        print(f"📡 Fetching fresh data from external API for key: {key}")
        fresh_data = await fetch_callback()
        
        # Save to cache
        saved_model = repository.save_data(key, fresh_data)
        
        return RefreshResponse(
            success=True,
            message=f"Cache populated successfully for key: {key}",
            last_updated=saved_model.last_updated,
            records_updated=1
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error populating cache: {str(e)}")


@router.get('/cache/info')
async def get_cache_info(
    key: Optional[str] = Query(None, description="Specific cache key (optional)")
) -> Dict[str, Any]:
    """
    Get cache information and metadata.
    
    Query Parameters:
        - key: Specific cache key (if omitted, returns stats for all keys)
    
    Returns:
        dict: Cache metadata including:
            - exists: Whether cache key exists
            - last_updated: When data was last fetched
            - created_at: When cache was first created
            - age_seconds: How old the data is
    
    Example:
        GET /api/cached/cache/info?key=f1_seasons
        GET /api/cached/cache/info  (all cache stats)
    """
    if key:
        # Info for specific key
        cached_model = repository.get_cached_data(key)
        
        if not cached_model:
            return {
                'exists': False,
                'key': key,
                'message': 'Cache key not found'
            }
        
        age = datetime.utcnow() - cached_model.last_updated
        
        return {
            'exists': True,
            'key': key,
            'last_updated': cached_model.last_updated.isoformat(),
            'created_at': cached_model.created_at.isoformat(),
            'age_seconds': int(age.total_seconds()),
            'age_human': str(age)
        }
    else:
        # Overall cache statistics
        stats = repository.get_stats()
        keys = repository.get_all_keys()
        
        return {
            'total_keys': len(keys),
            'keys': keys,
            'database_stats': stats
        }


@router.delete('/cache')
async def delete_cache(
    key: str = Query(..., description="Cache key to delete")
) -> Dict[str, Any]:
    """
    Delete cached data for a specific key.
    
    This removes data from SQLite cache.
    To repopulate, use POST /populate.
    
    Query Parameters:
        - key: Cache key to delete
    
    Returns:
        dict: Operation result
    
    Example:
        DELETE /api/cached/cache?key=f1_seasons
    """
    deleted = repository.delete_cached_data(key)
    
    if deleted:
        return {
            'success': True,
            'message': f"Cache deleted for key: {key}"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Cache key not found: {key}"
        )


@router.get('/cache/keys')
async def get_all_cache_keys() -> Dict[str, Any]:
    """
    Get all cache keys in SQLite database.
    
    Returns:
        dict: List of all cache keys with metadata
    
    Example:
        GET /api/cached/cache/keys
    """
    keys = repository.get_all_keys()
    
    return {
        'success': True,
        'total': len(keys),
        'keys': keys
    }
