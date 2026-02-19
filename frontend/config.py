"""
Frontend configuration.
Manages settings for Dash application.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
basedir = Path(__file__).parent.parent
load_dotenv(basedir / '.env')


class FrontendConfig:
    """Frontend Dash configuration"""
    
    # Dash settings
    DEBUG = os.getenv('DASH_DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('DASH_HOST', '127.0.0.1')
    PORT = int(os.getenv('DASH_PORT', '8050'))
    
    # Backend API settings
    BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://127.0.0.1:5000/api')
    
    # App metadata
    APP_TITLE = os.getenv('APP_TITLE', 'Pitwall Analytics')
    
    # Timeout for backend requests (seconds)
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))


config = FrontendConfig()
