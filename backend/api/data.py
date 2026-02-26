"""
Data API V2 - Uses Normalized Cache Only

Key difference from V1:
- V1: Called FastF1 directly, slow, unpredictable
- V2: Reads from SQLite cache, fast, only shows what's available

New endpoints:
- GET /api/v2/data/available - Lists all cached data
- GET /api/v2/data/stats - Database statistics
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from backend.services.f1_data_service import F1DataService

# Create APIRouter
router = APIRouter()

# Initialize service
f1_service = F1DataService()


@router.get('/data/available')
async def get_available_data() -> Dict[str, Any]:
    """
    Get complete map of ALL cached data.
    
    Returns availability tree:
    {
        "seasons": [2023, 2024],
        "2024": {
            "events": ["Bahrain", "Saudi Arabian", ...],
            "Bahrain": {
                "sessions": ["FP1", "FP2", "Q", "R"],
                "R": {
                    "laps": 1234,
                    "results": 20,
                    "weather": 150
                }
            }
        }
    }
    
    Frontend should use this to populate dropdowns!
    """
    try:
        available = f1_service.get_available_data()
        # Return directly without wrapper for easier frontend consumption
        return available
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/stats')
async def get_database_stats(
    season: Optional[int] = Query(None, description="Season year (optional)")
) -> Dict[str, Any]:
    """
    Get database statistics.

    If season is provided, returns stats for that season.
    Otherwise returns stats for all available seasons.
    """
    try:
        if season:
            return f1_service.get_database_stats(season)
        seasons = f1_service.get_available_seasons()
        return {
            'seasons': [f1_service.get_database_stats(s) for s in seasons]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/seasons')
async def get_seasons() -> Dict[str, Any]:
    """
    Get available F1 seasons from cache.
    
    Returns:
        List of season years
    """
    try:
        seasons = f1_service.get_available_seasons()
        return seasons
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/seasons/{season}')
async def get_season_info(season: int) -> Dict[str, Any]:
    """
    Get season information and statistics.
    
    Args:
        season: Year (e.g., 2024)
    
    Returns:
        Season info with event count, session count, etc.
    """
    try:
        info = f1_service.get_season_info(season)
        
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f'Season {season} not found in cache'
            )
        
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/races/{season}')
async def get_races(season: int) -> Dict[str, Any]:
    """
    Get races for a specific season from cache.
    
    Args:
        season: Year (e.g., 2024)
    
    Returns:
        List of race events
    """
    try:
        races = f1_service.get_races_for_season(season)
        return races
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/session')
async def get_session_data(
    season: Optional[int] = Query(None, description="Season year (e.g., 2024)"),
    event: Optional[str] = Query(None, description="Event name (e.g., 'Bahrain')"),
    session_type: str = Query('R', description="Session type: R, Q, FP1, FP2, FP3, S, SQ"),
    include_laps: bool = Query(True, description="Include lap data"),
    include_results: bool = Query(True, description="Include results"),
    include_weather: bool = Query(False, description="Include weather data"),
    include_messages: bool = Query(False, description="Include race control messages"),
    driver: Optional[str] = Query(None, description="Filter by driver code")
) -> Dict[str, Any]:
    """
    Get complete session data from cache.
    
    Query parameters:
        - season: Year (required)
        - event: Event name (required)
        - session_type: Session type (default: 'R')
        - include_laps: Include lap data (default: true)
        - include_results: Include results (default: true)
        - include_weather: Include weather (default: false)
        - include_messages: Include race control messages (default: false)
        - driver: Filter laps by driver code (optional)
    
    Returns:
        Complete session data
        
    Raises:
        400: Missing required parameters
        404: Session not found in cache
        500: Server error
    """
    # Validate required parameters
    if not season or not event:
        raise HTTPException(
            status_code=400,
            detail='Missing required parameters: season and event are required'
        )
    
    try:
        session_data = f1_service.load_session_data(
            season=season,
            event=event,
            session_type=session_type,
            include_laps=include_laps,
            include_results=include_results,
            include_weather=include_weather,
            include_messages=include_messages,
            driver_filter=driver
        )
        
        return session_data
    except Exception as e:
        error_msg = str(e)
        
        # Determine appropriate status code
        if 'not found' in error_msg.lower():
            status_code = 404
        else:
            status_code = 500
        
        raise HTTPException(status_code=status_code, detail=error_msg)


@router.get('/data/session/laps')
async def get_session_laps(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type"),
    driver: Optional[str] = Query(None, description="Filter by driver")
) -> Dict[str, Any]:
    """
    Get lap data for a session.
    
    Returns:
        List of laps
    """
    try:
        laps = f1_service.get_session_laps(season, event, session_type, driver)
        return laps
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get('/data/session/results')
async def get_session_results(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type")
) -> Dict[str, Any]:
    """
    Get results/standings for a session.
    
    Returns:
        List of results
    """
    try:
        results = f1_service.get_session_results(season, event, session_type)
        return results
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get('/data/session/drivers')
async def get_session_drivers(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type")
) -> Dict[str, Any]:
    """
    Get list of drivers in a session.
    
    Returns:
        List of driver codes
    """
    try:
        drivers = f1_service.get_drivers_in_session(season, event, session_type)
        return drivers
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get('/data/telemetry')
async def get_telemetry(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type"),
    driver: str = Query(..., description="Driver code (e.g. HAM)"),
    lap: int = Query(..., description="Lap number")
) -> Dict[str, Any]:
    """
    Get telemetry samples for a specific driver lap.

    Returns X/Y/Z track position plus car channels
    (speed, RPM, gear, throttle, brake, DRS).
    """
    try:
        return f1_service.get_driver_telemetry(
            season, event, session_type, driver, lap
        )
    except Exception as e:
        error_msg = str(e)
        status_code = 404 if 'not found' in error_msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=error_msg)


@router.get('/data/sessions/{season}/{event}')
async def get_available_sessions(season: int, event: str) -> Dict[str, Any]:
    """
    Get available session types for an event.
    
    Returns:
        List of session types that have data
    """
    try:
        sessions = f1_service.get_available_sessions_for_event(season, event)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
