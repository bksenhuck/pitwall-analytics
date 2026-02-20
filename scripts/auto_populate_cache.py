"""
DEPRECATED - Use populate_cache.py instead

This script uses the OLD caching system (JSON blobs in single table).
The system has been migrated to a normalized database schema.

Use instead:
    python scripts/populate_cache.py --season 2024
    python scripts/populate_cache.py --from 2023 --to 2024

For more info, see: docs/CACHE_V2_GUIDE.md
"""
import sys

print("=" * 80)
print("⚠️  DEPRECATED SCRIPT")
print("=" * 80)
print()
print("This script (auto_populate_cache.py) is OBSOLETE.")
print("It uses the old caching system that has been replaced.")
print()
print("Please use the updated script instead:")
print()
print("  python scripts/populate_cache.py --season 2024")
print("  python scripts/populate_cache.py --from 2023 --to 2024")
print()
print("For documentation, see: docs/CACHE_V2_GUIDE.md")
print()
print("=" * 80)
sys.exit(1)

import asyncio
import argparse
from typing import List, Dict, Any, Optional
from backend.repositories.data_repository import DataRepository
from backend.services.external_api import ExternalAPIService
from backend.db.session import init_database
import fastf1 as ff1
import json
from datetime import datetime


class AutoCachePopulator:
    """Automatically populate cache with all available F1 data."""
    
    # Session types to load
    SESSION_TYPES = {
        'FP1': 'Free Practice 1',
        'FP2': 'Free Practice 2',  
        'FP3': 'Free Practice 3',
        'Q': 'Qualifying',
        'S': 'Sprint',
        'SQ': 'Sprint Qualifying',
        'SS': 'Sprint Shootout',
        'R': 'Race'
    }
    
    def __init__(self, check_only: bool = False):
        self.repository = DataRepository()
        self.external_api = ExternalAPIService()
        self.check_only = check_only
        self.stats = {
            'seasons_processed': 0,
            'events_processed': 0,
            'sessions_loaded': 0,
            'sessions_skipped': 0,
            'errors': []
        }
    
    async def get_available_seasons(self, from_year: Optional[int] = None, to_year: Optional[int] = None) -> List[int]:
        """
        Get list of available F1 seasons.
        
        Args:
            from_year: Start from this year (inclusive)
            to_year: End at this year (inclusive)
        
        Returns:
            List of season years
        """
        # FastF1 supports data from 2018 onwards reliably
        # Some data available from earlier years but may be incomplete
        current_year = datetime.now().year
        start = from_year or 2018
        end = to_year or current_year
        
        seasons = list(range(start, end + 1))
        print(f"📅 Available seasons: {seasons[0]} - {seasons[-1]} ({len(seasons)} seasons)")
        return seasons
    
    async def get_season_events(self, season: int) -> List[Dict[str, Any]]:
        """
        Get all events (Grand Prix) for a season.
        
        Args:
            season: Season year
        
        Returns:
            List of events with metadata
        """
        try:
            loop = asyncio.get_event_loop()
            schedule = await loop.run_in_executor(None, ff1.get_event_schedule, season)
            
            events = []
            for idx, row in schedule.iterrows():
                event = {
                    'round': int(row.get('RoundNumber', idx + 1)),
                    'event_name': str(row.get('EventName', '')),
                    'location': str(row.get('Location', '')),
                    'country': str(row.get('Country', '')),
                    'date': str(row.get('EventDate', '')),
                    'format': row.get('EventFormat', 'conventional')  # conventional or sprint
                }
                events.append(event)
            
            return events
        except Exception as e:
            print(f"   ❌ Error getting events for {season}: {e}")
            self.stats['errors'].append(f"Season {season} events: {e}")
            return []
    
    def get_cache_key(self, season: int, event_name: str, session_type: str, data_type: str = 'full') -> str:
        """
        Generate cache key for a session.
        
        Args:
            season: Season year
            event_name: Event name (e.g., 'Bahrain Grand Prix')
            session_type: Session type (FP1, FP2, Q, R, etc)
            data_type: Type of data (full, laps_only, telemetry_only, etc)
        
        Returns:
            Cache key string
        """
        # Normalize event name: remove spaces, lowercase
        event_slug = event_name.lower().replace(' ', '_').replace('-', '_')
        return f"session_{season}_{event_slug}_{session_type.lower()}_{data_type}"
    
    def is_session_cached(self, season: int, event_name: str, session_type: str) -> bool:
        """Check if session data already exists in cache."""
        cache_key = self.get_cache_key(season, event_name, session_type, 'full')
        cached = self.repository.get_cached_data(cache_key)
        return cached is not None
    
    async def load_session_data(
        self, 
        season: int, 
        event_name: str, 
        session_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load complete session data from FastF1.
        
        Args:
            season: Season year
            event_name: Event name
            session_type: Session type (FP1, Q, R, etc)
        
        Returns:
            Complete session data dictionary or None if error
        """
        try:
            loop = asyncio.get_event_loop()
            
            def load_session():
                """Load session synchronously (FastF1 is not async)."""
                session = ff1.get_session(season, event_name, session_type)
                
                # Load ALL data available
                session.load(
                    laps=True,
                    telemetry=True,
                    weather=True,
                    messages=True
                )
                
                return session
            
            print(f"      ⏳ Loading {season} {event_name} - {session_type}...")
            session = await loop.run_in_executor(None, load_session)
            
            # Extract all data into serializable format
            data = {
                'season': season,
                'event_name': event_name,
                'session_type': session_type,
                'session_name': session.name,
                'date': str(session.date) if session.date else None,
                'loaded_at': datetime.utcnow().isoformat(),
            }
            
            # 1. LAP DATA
            if session.laps is not None and len(session.laps) > 0:
                laps_data = session.laps.copy()
                
                # Convert timedeltas to seconds for JSON serialization
                time_columns = ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 
                               'PitOutTime', 'PitInTime', 'LapStartTime']
                for col in time_columns:
                    if col in laps_data.columns:
                        laps_data[f'{col}Seconds'] = laps_data[col].dt.total_seconds()
                        laps_data = laps_data.drop(columns=[col])
                
                data['laps'] = json.loads(laps_data.to_json(orient='records'))
                data['total_laps'] = len(laps_data)
            
            # 2. RESULTS
            if session.results is not None and len(session.results) > 0:
                results_data = session.results.copy()
                
                # Convert timedeltas
                time_cols = ['Q1', 'Q2', 'Q3', 'Time']
                for col in time_cols:
                    if col in results_data.columns:
                        results_data[f'{col}Seconds'] = results_data[col].dt.total_seconds()
                        results_data = results_data.drop(columns=[col])
                
                data['results'] = json.loads(results_data.to_json(orient='records'))
            
            # 3. WEATHER DATA
            if session.weather_data is not None and len(session.weather_data) > 0:
                weather = session.weather_data.copy()
                if 'Time' in weather.columns:
                    weather['TimeSeconds'] = weather['Time'].dt.total_seconds()
                    weather = weather.drop(columns=['Time'])
                data['weather'] = json.loads(weather.to_json(orient='records'))
            
            # 4. RACE CONTROL MESSAGES
            if session.race_control_messages is not None and len(session.race_control_messages) > 0:
                messages = session.race_control_messages.copy()
                if 'Time' in messages.columns:
                    messages['TimeSeconds'] = messages['Time'].dt.total_seconds()
                    messages = messages.drop(columns=['Time'])
                data['race_control_messages'] = json.loads(messages.to_json(orient='records'))
            
            # 5. SESSION STATUS
            if session.session_status is not None and len(session.session_status) > 0:
                status = session.session_status.copy()
                if 'Time' in status.columns:
                    status['TimeSeconds'] = status['Time'].dt.total_seconds()
                    status = status.drop(columns=['Time'])
                data['session_status'] = json.loads(status.to_json(orient='records'))
            
            # 6. TRACK STATUS
            if session.track_status is not None and len(session.track_status) > 0:
                track = session.track_status.copy()
                if 'Time' in track.columns:
                    track['TimeSeconds'] = track['Time'].dt.total_seconds()
                    track = track.drop(columns=['Time'])
                data['track_status'] = json.loads(track.to_json(orient='records'))
            
            # 7. DRIVERS LIST
            if session.drivers:
                data['drivers'] = list(session.drivers)
            
            # 8. METADATA
            data['metadata'] = {
                'total_laps': session.total_laps if hasattr(session, 'total_laps') else None,
                'f1_api_support': session.f1_api_support,
            }
            
            # Note: Telemetry data is VERY large and should be accessed on-demand
            # We don't store it in cache, only metadata
            data['telemetry_available'] = session.f1_api_support
            
            print(f"      ✅ Loaded: {len(data.get('laps', []))} laps, "
                  f"{len(data.get('drivers', []))} drivers, "
                  f"{len(data.get('weather', []))} weather points")
            
            return data
            
        except Exception as e:
            print(f"      ❌ Error loading {season} {event_name} {session_type}: {e}")
            self.stats['errors'].append(f"{season} {event_name} {session_type}: {e}")
            return None
    
    async def process_session(
        self,
        season: int,
        event_name: str,
        session_type: str
    ) -> bool:
        """
        Process a single session: check cache and load if needed.
        
        Returns:
            True if data was loaded (or already cached), False if error
        """
        # Check if already cached
        if self.is_session_cached(season, event_name, session_type):
            print(f"   ⏭️  {session_type:3} - Already cached")
            self.stats['sessions_skipped'] += 1
            return True
        
        if self.check_only:
            print(f"   📋 {session_type:3} - Missing (would load)")
            return True
        
        # Load data
        data = await self.load_session_data(season, event_name, session_type)
        
        if data is None:
            return False
        
        # Save to cache
        cache_key = self.get_cache_key(season, event_name, session_type, 'full')
        self.repository.save_data(cache_key, data)
        self.stats['sessions_loaded'] += 1
        
        return True
    
    async def process_event(self, season: int, event: Dict[str, Any]) -> None:
        """Process all sessions for an event."""
        event_name = event['event_name']
        print(f"\n  📍 {event['round']:2d}. {event_name} ({event['location']}, {event['date']})")
        
        # Try to load each session type
        for session_code, session_name in self.SESSION_TYPES.items():
            await self.process_session(season, event_name, session_code)
        
        self.stats['events_processed'] += 1
    
    async def process_season(self, season: int) -> None:
        """Process all events in a season."""
        print(f"\n{'='*80}")
        print(f"🏁 SEASON {season}")
        print(f"{'='*80}")
        
        events = await self.get_season_events(season)
        
        if not events:
            print(f"   ⚠️  No events found for {season}")
            return
        
        print(f"   Found {len(events)} events")
        
        for event in events:
            await self.process_event(season, event)
        
        self.stats['seasons_processed'] += 1
    
    async def run(self, seasons: List[int]) -> None:
        """Run the auto-population process."""
        print("\n" + "="*80)
        print("🏎️  PITWALL ANALYTICS - AUTO CACHE POPULATION")
        print("="*80)
        
        if self.check_only:
            print("🔍 CHECK MODE: Will only show what's missing\n")
        else:
            print("💾 LOAD MODE: Will download and cache all missing data\n")
        
        for season in seasons:
            await self.process_season(season)
        
        # Print summary
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        print(f"✅ Seasons processed: {self.stats['seasons_processed']}")
        print(f"✅ Events processed: {self.stats['events_processed']}")
        print(f"✅ Sessions loaded: {self.stats['sessions_loaded']}")
        print(f"⏭️  Sessions skipped (cached): {self.stats['sessions_skipped']}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  # Show first 10
                print(f"   - {error}")
            if len(self.stats['errors']) > 10:
                print(f"   ... and {len(self.stats['errors']) - 10} more")


async def main():
    parser = argparse.ArgumentParser(
        description='Auto-populate F1 data cache from FastF1'
    )
    parser.add_argument(
        '--season',
        type=int,
        help='Load data for a specific season only'
    )
    parser.add_argument(
        '--from',
        dest='from_year',
        type=int,
        help='Load data from this season onwards'
    )
    parser.add_argument(
        '--to',
        dest='to_year',
        type=int,
        help='Load data up to this season'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Only check what data is missing, don\'t download'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    init_database()
    print("✅ Database initialized\n")
    
    # Create populator
    populator = AutoCachePopulator(check_only=args.check)
    
    # Determine seasons to process
    if args.season:
        seasons = [args.season]
    else:
        seasons = await populator.get_available_seasons(
            from_year=args.from_year,
            to_year=args.to_year
        )
    
    # Run
    await populator.run(seasons)


if __name__ == '__main__':
    asyncio.run(main())
