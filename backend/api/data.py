"""
Data API - Normalized Cache (per-season SQLite DBs)

Reads exclusively from SQLite cache populated by populate_cache.py.
"""
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Any, Dict, List, Optional, Union

from backend.services.f1_data_service import F1DataService
from backend.services.telemetry_service import TelemetryService
from backend.security import limiter, RATE_LIMIT_HEAVY, RATE_LIMIT_LIGHT

logger = logging.getLogger(__name__)

router = APIRouter()
f1_service = F1DataService()
telemetry_service = TelemetryService()


@router.get('/data/telemetry/head-to-head')
@limiter.limit(RATE_LIMIT_HEAVY)
async def get_telemetry_h2h(
    request: Request,
    year: int = Query(..., description="Season year"),
    gp: str = Query(..., description="Event name/round", max_length=100),
    session_type: str = Query('R', description="R, Q, FP...", max_length=5),
    drivers: str = Query(
        ..., description="Comma-separated driver codes", max_length=200
    ),
) -> Dict[str, Any]:
    """Get synchronized telemetry for N drivers on a common distance axis."""
    driver_list = [d.strip().upper() for d in drivers.split(",") if d.strip()]
    if not driver_list:
        raise HTTPException(
            status_code=400, detail="At least 1 driver code required"
        )
    try:
        return telemetry_service.get_head_to_head_telemetry(
            year=year,
            gp=gp,
            session_type=session_type,
            drivers=driver_list,
        )
    except Exception as e:
        logger.error("get_telemetry_h2h failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/available')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_available_data(request: Request) -> Dict[str, Any]:
    """Complete availability map across all season DBs."""
    try:
        return f1_service.get_available_data()
    except Exception as e:
        logger.error("get_available_data failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/stats')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_database_stats(
    request: Request,
    season: Optional[int] = Query(None, description="Season year (optional)"),
) -> Dict[str, Any]:
    """Stats for a specific season, or all seasons if omitted."""
    try:
        if season:
            return f1_service.get_database_stats(season)
        seasons = f1_service.get_available_seasons()
        return {'seasons': [f1_service.get_database_stats(s) for s in seasons]}
    except Exception as e:
        logger.error("get_database_stats failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/seasons')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_seasons(request: Request) -> Union[List[int], Dict[str, Any]]:
    """Available F1 seasons from cache."""
    try:
        return f1_service.get_available_seasons()
    except Exception as e:
        logger.error("get_seasons failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/seasons/{season}')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_season_info(request: Request, season: int) -> Dict[str, Any]:
    """Season statistics."""
    try:
        info = f1_service.get_season_info(season)
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f'Season {season} not found in cache',
            )
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_season_info failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/races/{season}')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_races(request: Request, season: int) -> Any:
    """Races for a specific season."""
    try:
        return f1_service.get_races_for_season(season)
    except Exception as e:
        logger.error("get_races failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/session')
@limiter.limit(RATE_LIMIT_HEAVY)
async def get_session_data(
    request: Request,
    season: Optional[int] = Query(None, description="Season year"),
    event: Optional[str] = Query(
        None, description="Event name", max_length=100
    ),
    session_type: str = Query(
        'R', description="R, Q, FP1, FP2, FP3, S, SQ", max_length=5
    ),
    include_laps: bool = Query(True, description="Include lap data"),
    include_results: bool = Query(True, description="Include results"),
    include_weather: bool = Query(False, description="Include weather"),
    include_messages: bool = Query(
        False, description="Include race control messages"
    ),
    driver: Optional[str] = Query(
        None, description="Filter by driver code", max_length=10
    ),
) -> Dict[str, Any]:
    """Complete session data from cache."""
    if not season or not event:
        raise HTTPException(
            status_code=400,
            detail='Missing required parameters: season and event',
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
            driver_filter=driver,
        )
    except Exception as e:
        logger.error("get_session_data failed: %s", e)
        error_msg = str(e)
        status_code = 404 if 'not found' in error_msg.lower() else 500
        detail = (
            error_msg
            if status_code == 404
            else "An error occurred. Please try again."
        )
        raise HTTPException(status_code=status_code, detail=detail)


@router.get('/data/session/laps')
@limiter.limit(RATE_LIMIT_HEAVY)
async def get_session_laps(
    request: Request,
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name", max_length=100),
    session_type: str = Query(
        'R', description="Session type", max_length=5
    ),
    driver: Optional[str] = Query(
        None, description="Filter by driver", max_length=10
    ),
) -> Dict[str, Any]:
    """Lap data for a session."""
    try:
        return f1_service.get_session_laps(season, event, session_type, driver)
    except Exception as e:
        logger.error("get_session_laps failed: %s", e)
        raise HTTPException(status_code=404, detail="Session not found.")


@router.get('/data/session/results')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_session_results(
    request: Request,
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name", max_length=100),
    session_type: str = Query(
        'R', description="Session type", max_length=5
    ),
) -> Dict[str, Any]:
    """Results/standings for a session."""
    try:
        return f1_service.get_session_results(season, event, session_type)
    except Exception as e:
        logger.error("get_session_results failed: %s", e)
        raise HTTPException(status_code=404, detail="Session not found.")


@router.get('/data/session/drivers')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_session_drivers(
    request: Request,
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name", max_length=100),
    session_type: str = Query(
        'R', description="Session type", max_length=5
    ),
) -> Dict[str, Any]:
    """Driver list for a session."""
    try:
        return f1_service.get_drivers_in_session(season, event, session_type)
    except Exception as e:
        logger.error("get_session_drivers failed: %s", e)
        raise HTTPException(status_code=404, detail="Session not found.")


@router.get('/data/track-layout')
@limiter.limit(RATE_LIMIT_HEAVY)
async def get_track_layout(
    request: Request,
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name", max_length=100),
    session_type: str = Query(
        'R', description="Session type", max_length=5
    ),
) -> Dict[str, Any]:
    """X/Y circuit outline from fastest lap telemetry."""
    try:
        return f1_service.get_track_layout(season, event, session_type)
    except Exception as e:
        logger.error("get_track_layout failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )


@router.get('/data/telemetry')
@limiter.limit(RATE_LIMIT_HEAVY)
async def get_telemetry(
    request: Request,
    season: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name", max_length=100),
    session_type: str = Query(
        'R', description="Session type", max_length=5
    ),
    driver: str = Query(
        ..., description="Driver code (e.g. HAM)", max_length=10
    ),
    lap: int = Query(..., description="Lap number"),
) -> Dict[str, Any]:
    """Telemetry samples for a specific driver lap."""
    try:
        return f1_service.get_driver_telemetry(
            season, event, session_type, driver, lap
        )
    except Exception as e:
        logger.error("get_telemetry failed: %s", e)
        error_msg = str(e)
        status_code = 404 if 'not found' in error_msg.lower() else 500
        detail = (
            error_msg
            if status_code == 404
            else "An error occurred. Please try again."
        )
        raise HTTPException(status_code=status_code, detail=detail)


@router.get('/data/sessions/{season}/{event}')
@limiter.limit(RATE_LIMIT_LIGHT)
async def get_available_sessions(
    request: Request,
    season: int,
    event: str,
) -> Dict[str, Any]:
    """Available session types for an event."""
    try:
        return f1_service.get_available_sessions_for_event(season, event)
    except Exception as e:
        logger.error("get_available_sessions failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An error occurred. Please try again."
        )
