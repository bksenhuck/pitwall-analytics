"""
Data API endpoints.
Thin controllers that delegate to service layer.

FastAPI advantages:
- Automatic request/response validation
- Type hints for better IDE support
- Async support for better performance
- Automatic OpenAPI documentation
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from backend.services.f1_data_service import F1DataService

# Create APIRouter (equivalent to Flask Blueprint)
router = APIRouter()

# Initialize service (singleton pattern)
f1_service = F1DataService()


@router.get('/data/seasons')
async def get_seasons() -> Dict[str, Any]:
    """
    Get available F1 seasons.
    
    Returns:
        dict: Response with list of available seasons
    
    Raises:
        HTTPException: If data retrieval fails
    """
    try:
        seasons = f1_service.get_available_seasons()
        return {
            'success': True,
            'data': seasons
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/races/{season}')
async def get_races(season: int) -> Dict[str, Any]:
    """
    Get races for a specific season.
    
    Args:
        season: Year (e.g., 2023)
    
    Returns:
        dict: Response with list of race events
    
    Raises:
        HTTPException: If data retrieval fails
    """
    try:
        races = f1_service.get_races_for_season(season)
        return {
            'success': True,
            'data': races
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/session')
async def get_session_data(
    season: Optional[int] = Query(None, description="Season year (e.g., 2023)"),
    event: Optional[str] = Query(None, description="Event name (e.g., 'Monaco')"),
    session_type: str = Query('R', description="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3")
) -> Dict[str, Any]:
    """
    Get session data (laps, telemetry, etc.).
    
    Query parameters:
        - season: int (e.g., 2023) - Required
        - event: str (e.g., "Monaco") - Required
        - session_type: str (default: "R" for Race)
    
    Returns:
        dict: Session data with laps and metadata
    
    Raises:
        HTTPException: If parameters are missing or data retrieval fails
    """
    # Validate required parameters
    if not season or not event:
        raise HTTPException(
            status_code=400,
            detail='Missing required parameters: season and event are required'
        )
    
    try:
        session_data = f1_service.load_session_data(season, event, session_type)
        return {
            'success': True,
            'data': session_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data')
async def get_sample_data() -> Dict[str, Any]:
    """
    Sample endpoint returning mock data.
    Demonstrates async backend API pattern.
    
    This endpoint can be used to test async external API calls.
    
    Returns:
        dict: Sample data response
    """
    # Future: Add async external API call here using httpx
    # Example:
    # async with httpx.AsyncClient() as client:
    #     response = await client.get('https://external-api.com/data')
    #     external_data = response.json()
    
    return {
        'success': True,
        'message': 'Backend API is working with FastAPI!',
        'data': {
            'sample': 'This is sample data from the FastAPI backend',
            'timestamp': '2026-02-19',
            'async_ready': True
        }
    }
