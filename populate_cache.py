"""
CLI tool to populate SQLite cache manually.

This script allows you to fetch data from external APIs
and populate the SQLite cache without starting the full backend server.

Usage:
    python populate_cache.py f1_seasons
    python populate_cache.py race_2024_bahrain
    python populate_cache.py --list
    python populate_cache.py --info f1_seasons
    python populate_cache.py --delete f1_seasons
"""
import asyncio
import sys
from typing import Optional
from backend.repositories.data_repository import DataRepository
from backend.services.external_api import ExternalAPIService
from backend.db.session import init_database
import json


class CachePopulator:
    """CLI tool for manual cache population."""
    
    def __init__(self):
        self.repository = DataRepository()
        self.external_api = ExternalAPIService()
    
    async def populate(self, key: str) -> bool:
        """
        Populate cache for a specific key.
        
        Args:
            key: Cache key (e.g., 'f1_seasons', 'races_2024', 'race_2024_bahrain')
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"📡 Fetching data from FastF1/External API for key: {key}")
            
            # Define fetch callback based on key
            if key == 'f1_seasons':
                data = await self.external_api.fetch_f1_seasons()
            
            elif key.startswith('races_'):
                # Format: races_2024
                parts = key.split('_')
                if len(parts) == 2:
                    season = int(parts[1])
                    data = await self.external_api.fetch_races_for_season(season)
                else:
                    print(f"❌ Invalid races key format. Use: races_YEAR")
                    return False
            
            elif key.startswith('race_'):
                # Format: race_2024_bahrain or race_2024_Bahrain_Grand_Prix
                parts = key.split('_', 2)  # Split into max 3 parts
                if len(parts) >= 3:
                    season = int(parts[1])
                    event = parts[2].replace('_', ' ')  # Convert underscores to spaces
                    print(f"   Season: {season}, Event: {event}")
                    data = await self.external_api.fetch_race_session_data(
                        season, event, 'R'
                    )
                else:
                    print(f"❌ Invalid race key format. Use: race_YEAR_EVENT")
                    print("   Examples:")
                    print("     race_2024_bahrain")
                    print("     race_2024_Bahrain_Grand_Prix")
                    return False
            
            else:
                print(f"❌ Unknown cache key: {key}")
                print("   Supported formats:")
                print("     f1_seasons                  - List of all seasons")
                print("     races_YEAR                  - Races for a season (e.g., races_2024)")
                print("     race_YEAR_EVENT             - Race data (e.g., race_2024_bahrain)")
                return False
            
            # Save to cache
            print(f"💾 Saving data to SQLite cache...")
            saved_model = self.repository.save_data(key, data)
            
            print(f"✅ Cache populated successfully!")
            print(f"   Key: {key}")
            print(f"   Last Updated: {saved_model.last_updated}")
            
            # Show size info
            if isinstance(data, dict):
                if 'races' in data:
                    print(f"   Races: {len(data['races'])}")
                elif 'laps' in data:
                    print(f"   Total Laps: {len(data['laps'])}")
                    print(f"   Drivers: {len(data.get('drivers', []))}")
                elif 'seasons' in data:
                    print(f"   Seasons: {len(data['seasons'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error populating cache: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_keys(self):
        """List all cache keys in SQLite."""
        print("📋 Cache Keys in SQLite:")
        print("-" * 50)
        
        keys = self.repository.get_all_keys()
        
        if not keys:
            print("   (empty - no cache keys found)")
            return
        
        for key in keys:
            cached = self.repository.get_cached_data(key)
            if cached:
                print(f"   ✓ {key}")
                print(f"      Last Updated: {cached.last_updated}")
        
        print("-" * 50)
        print(f"Total: {len(keys)} keys")
    
    def get_info(self, key: str):
        """Get info about a specific cache key."""
        print(f"🔍 Cache Info for: {key}")
        print("-" * 50)
        
        cached = self.repository.get_cached_data(key)
        
        if not cached:
            print(f"   ❌ Key not found in cache")
            print(f"   Run: python populate_cache.py {key}")
            return
        
        data = json.loads(cached.data)
        
        print(f"   ✓ Exists: Yes")
        print(f"   Created: {cached.created_at}")
        print(f"   Last Updated: {cached.last_updated}")
        print(f"   Data Type: {type(data).__name__}")
        
        if isinstance(data, list):
            print(f"   Records: {len(data)}")
        elif isinstance(data, dict):
            print(f"   Keys: {', '.join(list(data.keys())[:5])}")
        
        print("-" * 50)
    
    def delete_key(self, key: str):
        """Delete a cache key."""
        print(f"🗑️  Deleting cache key: {key}")
        
        deleted = self.repository.delete_cached_data(key)
        
        if deleted:
            print(f"   ✅ Cache deleted successfully")
        else:
            print(f"   ❌ Key not found in cache")


def print_help():
    """Print help message."""
    print("""
🏁 Pitwall Analytics - Cache Populator
=====================================

Usage:
    python populate_cache.py <key>          Populate cache for key
    python populate_cache.py --list         List all cache keys
    python populate_cache.py --info <key>   Show info for key
    python populate_cache.py --delete <key> Delete cache key
    python populate_cache.py --help         Show this help

Examples:
    python populate_cache.py f1_seasons
    python populate_cache.py races_2024
    python populate_cache.py race_2024_bahrain
    python populate_cache.py race_2024_Bahrain_Grand_Prix
    python populate_cache.py --list
    python populate_cache.py --info f1_seasons
    python populate_cache.py --delete f1_seasons

Supported Cache Keys:
    - f1_seasons                List of all F1 seasons
    - races_YEAR               Race schedule for a season (e.g., races_2024)
    - race_YEAR_EVENT          Full race session data (e.g., race_2024_bahrain)
    """)


async def main():
    """Main CLI entry point."""
    # Initialize database
    print("🔧 Initializing database...")
    init_database()
    
    populator = CachePopulator()
    
    # Parse arguments
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    
    if command in ['--help', '-h']:
        print_help()
    
    elif command == '--list':
        populator.list_keys()
    
    elif command == '--info':
        if len(sys.argv) < 3:
            print("❌ Missing key argument")
            print("   Usage: python populate_cache.py --info <key>")
            return
        key = sys.argv[2]
        populator.get_info(key)
    
    elif command == '--delete':
        if len(sys.argv) < 3:
            print("❌ Missing key argument")
            print("   Usage: python populate_cache.py --delete <key>")
            return
        key = sys.argv[2]
        populator.delete_key(key)
    
    else:
        # Assume it's a cache key to populate
        key = command
        success = await populator.populate(key)
        
        if not success:
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
