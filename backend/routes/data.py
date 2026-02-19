"""
Data routes with caching.

FastAPI endpoints that demonstrate the caching layer:
- GET /data → returns cached data (uses TTL logic)
- POST /refresh → forces cache refresh
- GET /cache/info → shows cache metadata
- DELETE /cache → clears cache

These routes are thin controllers - business logic is in service layer.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from backend.services.cache_service_v2 import CacheService
from backend.services.external_api import ExternalAPIService
from backend.models.data_model import CachedDataResponse, RefreshResponse
from datetime import datetime

router = APIRouter()

# Initialize services
cache_service = CacheService()
external_api = ExternalAPIService()


@router.get('/data', response_model=CachedDataResponse)
async def get_data(
    key: str = Query('f1_seasons', description="Cache key for the data")
) -> CachedDataResponse:
    """
    Get data with intelligent caching.
    
    This endpoint demonstrates the cache-first strategy:
    1. Checks cache (database)
    2. If cache valid (within TTL) → returns cached data ⚡
    3. If cache expired/missing → fetches from external API → updates cache
    
    Query Parameters:
        - key: Cache key (default: 'f1_seasons')
    
    Returns:
        CachedDataResponse with:
            - success: Operation status
            - data: The actual data
            - cached: True if from cache, False if fresh
            - last_updated: When data was last refreshed
    
    Example:
        GET /api/cached/data?key=f1_seasons
    """
    try:
        # Define fetch callback based on cache key
        # This is where you map cache keys to external API calls
        if key == 'f1_seasons':
            fetch_callback = external_api.fetch_f1_seasons
        elif key.startswith('race_'):
            # Example: race_2023_monaco
            parts = key.split('_')
            if len(parts) >= 3:
                season = int(parts[1])
                event = '_'.join(parts[2:])
                fetch_callback = lambda: external_api.fetch_race_data(season, event)
            else:
                raise ValueError("Invalid race cache key format")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown cache key: {key}. Supported: 'f1_seasons', 'race_YEAR_EVENT'"
            )
        
        # Get data with cache logic
        data, is_cached = await cache_service.get_data_with_cache(
            cache_key=key,
            fetch_callback=fetch_callback
        )
        
        # Get cache info for metadata
        cache_info = cache_service.get_cache_info(key)
        
        return CachedDataResponse(
            success=True,
            data=data,
            cached=is_cached,
            last_updated=datetime.fromisoformat(cache_info.get('last_updated')) if cache_info.get('last_updated') else None,
            message=f"Data served from {'cache' if is_cached else 'external API'}"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


@router.post('/refresh', response_model=RefreshResponse)
async def refresh_data(
    key: str = Query('f1_seasons', description="Cache key to refresh")
) -> RefreshResponse:
    """
    Force refresh data (bypass cache).
    
    This endpoint:
    1. ALWAYS fetches fresh data from external API
    2. Updates the cache
    3. Returns fresh data
    
    Use when:
    - User explicitly requests fresh data
    - You know external data has changed
    - Cache is corrupted
    
    Query Parameters:
        - key: Cache key to refresh
    
    Returns:
        RefreshResponse with:
            - success: Operation status
            - message: Description of what happened
            - last_updated: New timestamp
            - records_updated: Number of records updated
    
    Example:
        POST /api/cached/refresh?key=f1_seasons
    """
    try:
        # Define fetch callback
        if key == 'f1_seasons':
            fetch_callback = external_api.fetch_f1_seasons
        elif key.startswith('race_'):
            parts = key.split('_')
            if len(parts) >= 3:
                season = int(parts[1])
                event = '_'.join(parts[2:])
                fetch_callback = lambda: external_api.fetch_race_data(season, event)
            else:
                raise ValueError("Invalid race cache key format")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown cache key: {key}"
            )
        
        # Force refresh
        fresh_data = await cache_service.refresh_data(
            cache_key=key,
            fetch_callback=fetch_callback
        )
        
        return RefreshResponse(
            success=True,
            message=f"Cache refreshed for key: {key}",
            last_updated=datetime.utcnow(),
            records_updated=1
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")


@router.get('/cache/info')
async def get_cache_info(
    key: Optional[str] = Query(None, description="Specific cache key (optional)")
) -> Dict[str, Any]:
    """
    Get cache information.
    
    Query Parameters:
        - key: Specific cache key (if omitted, returns all cache info)
    
    Returns:
        dict: Cache metadata including:
            - age: How old the cache is
            - ttl: Time to live configuration
            - expired: Whether cache is expired
            - exists: Whether cache exists
    
    Example:
        GET /api/cached/cache/info?key=f1_seasons
        GET /api/cached/cache/info  (all cache stats)
    """
    if key:
        # Info for specific key
        return cache_service.get_cache_info(key)
    else:
        # Overall cache statistics
        return {
            'cache_stats': cache_service.get_cache_stats(),
            'all_keys': cache_service.get_all_cache_keys()
        }


@router.delete('/cache')
async def invalidate_cache(
    key: str = Query(..., description="Cache key to invalidate")
) -> Dict[str, Any]:
    """
    Invalidate (delete) cached data.
    
    This removes data from the cache database.
    Next request will fetch fresh data from external API.
    
    Query Parameters:
        - key: Cache key to delete
    
    Returns:
        dict: Operation result
    
    Example:
        DELETE /api/cached/cache?key=f1_seasons
    """
    deleted = cache_service.invalidate_cache(key)
    
    if deleted:
        return {
            'success': True,
            'message': f"Cache invalidated for key: {key}"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Cache key not found: {key}"
        )


@router.get('/cache/keys')
async def get_all_cache_keys() -> Dict[str, Any]:
    """
    Get all cache keys in the database.
    
    Returns:
        dict: List of all cache keys
    
    Example:
        GET /api/cached/cache/keys
    """
    keys = cache_service.get_all_cache_keys()
    return {
        'success': True,
        'total': len(keys),
        'keys': keys
    }
