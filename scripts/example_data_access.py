"""
Example: How to access cached F1 data after population

This shows how to read data from the SQLite cache that was
populated by auto_populate_cache.py
"""
import sys
from pathlib import Path

# Add project root to Python path (allows imports when running from scripts/ folder)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.repositories.data_repository import DataRepository
import json


def example_access_race_data():
    """Example: Access race session data."""
    
    repo = DataRepository()
    
    # Try to get Bahrain 2024 Race data
    cache_key = "session_2024_bahrain_grand_prix_r_full"
    
    cached = repo.get_cached_data(cache_key)
    
    if not cached:
        print(f"❌ No data found for key: {cache_key}")
        print("\nRun this first to populate:")
        print(f"  python auto_populate_cache.py --season 2024")
        return
    
    # Parse JSON data
    data = json.loads(cached.data)
    
    print("="*80)
    print("🏁 Bahrain Grand Prix 2024 - Race")
    print("="*80)
    
    # Session info
    print(f"\n📅 Date: {data.get('date')}")
    print(f"🏎️  Session: {data.get('session_name')}")
    print(f"📊 Total Laps: {data.get('total_laps')}")
    
    # Drivers
    drivers = data.get('drivers', [])
    print(f"\n👥 Drivers: {len(drivers)}")
    print(f"   {', '.join(drivers)}")
    
    # Results
    results = data.get('results', [])
    if results:
        print(f"\n🏆 Top 5 Finishers:")
        for i, result in enumerate(sorted(results, key=lambda x: x.get('Position', 99))[:5], 1):
            driver = result.get('Abbreviation', 'UNK')
            team = result.get('TeamName', 'Unknown')
            position = result.get('Position', '-')
            points = result.get('Points', 0)
            print(f"   {i}. P{position} - {driver} ({team}) - {points} pts")
    
    # Lap statistics
    laps = data.get('laps', [])
    if laps:
        print(f"\n⏱️  Lap Data:")
        print(f"   Total recorded laps: {len(laps)}")
        
        # Find fastest lap
        fastest_lap = min(
            [lap for lap in laps if lap.get('LapTimeSeconds')],
            key=lambda x: x.get('LapTimeSeconds', float('inf')),
            default=None
        )
        
        if fastest_lap:
            driver = fastest_lap.get('Driver')
            time = fastest_lap.get('LapTimeSeconds')
            lap_num = fastest_lap.get('LapNumber')
            
            # Convert seconds to M:SS.mmm
            minutes = int(time // 60)
            seconds = time % 60
            
            print(f"   Fastest lap: {driver} - Lap {lap_num} - {minutes}:{seconds:06.3f}")
    
    # Weather
    weather = data.get('weather', [])
    if weather:
        print(f"\n🌤️  Weather Conditions:")
        first_weather = weather[0]
        print(f"   Air Temp: {first_weather.get('AirTemp', 'N/A')}°C")
        print(f"   Track Temp: {first_weather.get('TrackTemp', 'N/A')}°C")
        print(f"   Humidity: {first_weather.get('Humidity', 'N/A')}%")
        print(f"   Rainfall: {first_weather.get('Rainfall', False)}")
    
    # Race control messages
    messages = data.get('race_control_messages', [])
    if messages:
        print(f"\n🚩 Race Control Events: {len(messages)} messages")
        
        # Find important messages (flags, penalties)
        important = [m for m in messages if any(word in m.get('Message', '').upper() 
                     for word in ['FLAG', 'PENALTY', 'SAFETY CAR', 'VSC', 'RED FLAG'])]
        
        if important[:5]:  # Show first 5
            print(f"   Recent important events:")
            for msg in important[:5]:
                category = msg.get('Category', 'Unknown')
                message = msg.get('Message', '')
                print(f"   - [{category}] {message[:60]}...")
    
    print(f"\n💾 Cache Info:")
    print(f"   Last Updated: {cached.last_updated}")
    print(f"   Created: {cached.created_at}")
    print(f"   Cache Key: {cache_key}")


def example_list_all_cached_data():
    """Example: List all available cached sessions."""
    
    repo = DataRepository()
    all_data = repo.get_all_cached_keys()
    
    print("\n" + "="*80)
    print("📋 ALL CACHED F1 DATA")
    print("="*80)
    
    if not all_data:
        print("\n❌ No cached data found.")
        print("\nRun this to populate:")
        print("  python auto_populate_cache.py --season 2024")
        return
    
    # Group by season
    seasons = {}
    for key in all_data:
        if key.startswith('session_'):
            parts = key.split('_')
            if len(parts) >= 2:
                season = parts[1]
                if season not in seasons:
                    seasons[season] = []
                seasons[season].append(key)
    
    for season in sorted(seasons.keys(), reverse=True):
        print(f"\n🏁 Season {season}: {len(seasons[season])} sessions cached")
        
        # Count by session type
        types = {}
        for key in seasons[season]:
            parts = key.split('_')
            if len(parts) >= 4:
                session_type = parts[-2].upper()
                types[session_type] = types.get(session_type, 0) + 1
        
        for session_type, count in sorted(types.items()):
            print(f"   {session_type:3}: {count} sessions")


if __name__ == '__main__':
    print("\n🏎️  PITWALL ANALYTICS - Data Access Examples\n")
    
    # Example 1: Access specific race
    example_access_race_data()
    
    # Example 2: List all cached data
    example_list_all_cached_data()
    
    print("\n" + "="*80)
    print("\n✅ Examples completed!")
    print("\nNext steps:")
    print("  1. Run: python auto_populate_cache.py --season 2024")
    print("  2. Start backend: .\\start.ps1")
    print("  3. Access data through frontend at http://localhost:8050")
    print()
