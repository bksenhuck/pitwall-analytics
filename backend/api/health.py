"""
Health check endpoints.
Used for monitoring and ensuring backend is running.

FastAPI automatically generates OpenAPI documentation for these endpoints.
"""
from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

# Create APIRouter (equivalent to Flask Blueprint)
router = APIRouter()


@router.get('/health')
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    Returns 200 if service is healthy.
    
    Returns:
        dict: Health status information
    """
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'pitwall-analytics-backend'
    }


@router.get('/status')
async def status() -> Dict[str, Any]:
    """
    Detailed status endpoint.
    Can include cache stats, service versions, etc.
    
    Returns:
        dict: Detailed service status
    """
    from backend.services.cache_service import get_cache_status
    
    return {
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'cache': get_cache_status(),
        'version': '2.0.0-fastapi'
    }
