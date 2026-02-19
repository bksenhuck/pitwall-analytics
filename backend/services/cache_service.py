"""
Cache service for FastF1 data.
Centralizes caching logic.
"""
import fastf1 as ff1
from pathlib import Path

_cache_enabled = False
_cache_dir = None


def init_cache(cache_dir: str, enabled: bool = True):
    """
    Initialize FastF1 cache.
    Should be called once at application startup.
    
    Args:
        cache_dir: Directory path for cache storage
        enabled: Whether caching is enabled
    """
    global _cache_enabled, _cache_dir
    
    _cache_dir = cache_dir
    _cache_enabled = enabled
    
    if enabled:
        try:
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            ff1.Cache.enable_cache(cache_dir)
            print(f"✅ FastF1 cache enabled: {cache_dir}")
        except Exception as e:
            print(f"⚠️  Cache initialization failed: {e}")
            _cache_enabled = False


def get_cache_status():
    """
    Get current cache status.
    
    Returns:
        dict: Cache configuration and status
    """
    return {
        'enabled': _cache_enabled,
        'directory': _cache_dir
    }


def clear_cache():
    """
    Clear the FastF1 cache.
    Use with caution in production.
    """
    if _cache_enabled and _cache_dir:
        try:
            import shutil
            cache_path = Path(_cache_dir)
            if cache_path.exists():
                shutil.rmtree(cache_path)
                cache_path.mkdir(parents=True, exist_ok=True)
                print(f"🗑️  Cache cleared: {_cache_dir}")
                return True
        except Exception as e:
            print(f"❌ Cache clear failed: {e}")
            return False
    return False
