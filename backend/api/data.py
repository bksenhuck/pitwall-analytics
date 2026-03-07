"""
Data API - Normalized Cache (per-season SQLite DBs)

Reads exclusively from SQLite cache populated by populate_cache.py.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from backend.services.f1_data_service import F1DataService
from backend.services.telemetry_service import TelemetryService

router = APIRouter()
f1_service = F1DataService()
telemetry_service = TelemetryService()


@router.get('/data/telemetry/head-to-head')
async def get_telemetry_h2h(
    year: int = Query(..., description="Season year"),
    gp: str = Query(..., description="Event name/round"),
    session_type: str = Query('R', description="R, Q, FP..."),
    drivers: str = Query(..., description="Comma-separated driver codes"),
) -> Dict[str, Any]:
    """Get synchronized telemetry for N drivers on a common distance axis."""
    driver_list = [d.strip().upper() for d in drivers.split(",") if d.strip()]
    if not driver_list:
        raise HTTPException(status_code=400, detail="At least 1 driver code required")
    try:
        return telemetry_service.get_head_to_head_telemetry(
            year=year,
            gp=gp,
            session_type=session_type,
            drivers=driver_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/available')
async def get_available_data() -> Dict[str, Any]:
    """Complete availability map across all season DBs."""
    try:
        return f1_service.get_available_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/stats')
async def get_database_stats(
    season: Optional[int] = Query(
        None, description="Season year (optional)"
    )
) -> Dict[str, Any]:
    """
    Stats for a specific season, or all seasons if omitted.
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
    """Available F1 seasons from cache."""
    try:
        return f1_service.get_available_seasons()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/seasons/{season}')
async def get_season_info(season: int) -> Dict[str, Any]:
    """Season statistics."""
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
    """Races for a specific season."""
    try:
        return f1_service.get_races_for_season(season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/session')
async def get_session_data(
    season: Optional[int] = Query(None, description="Season year"),
    event: Optional[str] = Query(None, description="Event name"),
    session_type: str = Query('R', description="R, Q, FP1, FP2, FP3, S, SQ"),
    include_laps: bool = Query(True, description="Include lap data"),
    include_results: bool = Query(True, description="Include results"),
    include_weather: bool = Query(False, description="Include weather"),
    include_messages: bool = Query(
        False, description="Include race control messages"
    ),
    driver: Optional[str] = Query(None, description="Filter by driver code")
) -> Dict[str, Any]:
    """Complete session data from cache."""
    if not season or not event:
        raise HTTPException(
            status_code=400,
            detail='Missing required parameters: season and event'
        )
    try:
        return f1_service.load_session_data(
            season=season,
            event=event,
            session_type=session_type,
            include_laps=include_laps,
            include_results=include_results,
            include_weather=include_weather,
            include_messages=include_messages,
            driver_filter=driver
        )
    except Exception as e:
        error_msg = str(e)
        status_code = 404 if 'not found' in error_msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=error_msg)


@router.get('/data/session/laps')
async def get_session_laps(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type"),
    driver: Optional[str] = Query(None, description="Filter by driver")
) -> Dict[str, Any]:
    """Lap data for a session."""
    try:
        return f1_service.get_session_laps(season, event, session_type, driver)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get('/data/session/results')
async def get_session_results(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type")
) -> Dict[str, Any]:
    """Results/standings for a session."""
    try:
        return f1_service.get_session_results(season, event, session_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get('/data/session/drivers')
async def get_session_drivers(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type")
) -> Dict[str, Any]:
    """Driver list for a session."""
    try:
        return f1_service.get_drivers_in_session(season, event, session_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get('/data/track-layout')
async def get_track_layout(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type")
) -> Dict[str, Any]:
    """
    X/Y circuit outline from fastest lap telemetry.
    Returns empty arrays if telemetry was not populated.
    """
    try:
        return f1_service.get_track_layout(season, event, session_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data/telemetry')
async def get_telemetry(
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name"),
    session_type: str = Query('R', description="Session type"),
    driver: str = Query(..., description="Driver code (e.g. HAM)"),
    lap: int = Query(..., description="Lap number")
) -> Dict[str, Any]:
    """
    Telemetry samples for a specific driver lap.
    Returns X/Y/Z position + car channels (speed, RPM, gear, throttle, etc.).
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
async def get_available_sessions(
    season: int, event: str
) -> Dict[str, Any]:
    """Available session types for an event."""
    try:
        return f1_service.get_available_sessions_for_event(season, event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
