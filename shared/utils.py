"""Shared utilities and helpers"""


def format_lap_time(seconds):
    """
    Format lap time from seconds to MM:SS.mmm
    
    Args:
        seconds: Time in seconds (float)
    
    Returns:
        Formatted string (e.g., "1:23.456")
    """
    if not seconds or seconds <= 0:
        return "N/A"
    
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def safe_get(dictionary, key, default=None):
    """
    Safely get value from dictionary.
    
    Args:
        dictionary: Dict to query
        key: Key to retrieve
        default: Default value if key not found
    
    Returns:
        Value or default
    """
    if not isinstance(dictionary, dict):
        return default
    return dictionary.get(key, default)
