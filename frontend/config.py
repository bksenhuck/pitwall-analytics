"""Frontend configuration"""
import os
from pathlib import Path

# Backend API URL - read from environment or default to localhost
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:5000/api")

# Dash settings
HOST = os.getenv("DASH_HOST", "127.0.0.1")
PORT = int(os.getenv("DASH_PORT", "8050"))
DEBUG = os.getenv("DASH_DEBUG", "True").lower() == "true"

# Cache settings
CACHE_DIR = Path(".ff1cache")
CACHE_ENABLED = True

# App metadata
APP_TITLE = "Pitwall Analytics"
APP_DESCRIPTION = "F1 Race Analytics Dashboard"
