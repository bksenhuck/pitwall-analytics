"""
Backend configuration management.
Handles environment variables and app settings.

Works with both Flask and FastAPI - using environment variables
makes it framework-agnostic.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = Path(__file__).parent.parent
load_dotenv(basedir / '.env')


class Config:
    """Base configuration"""
    # API settings (framework-agnostic)
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('API_DEBUG', os.getenv('FLASK_DEBUG', 'False')).lower() == 'true'
    
    # Server settings
    API_HOST = os.getenv('API_HOST', '127.0.0.1')
    API_PORT = int(os.getenv('API_PORT', '5000'))
    
    # FastF1 cache settings
    CACHE_DIR = os.getenv('CACHE_DIR', '.ff1cache')
    CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'True').lower() == 'true'
    
    # CORS settings (for frontend communication)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8050').split(',')
    
    # API Documentation (FastAPI specific)
    API_TITLE = os.getenv('API_TITLE', 'Pitwall Analytics API')
    API_VERSION = os.getenv('API_VERSION', '2.0.0')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


# Configuration selector
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('API_ENV', os.getenv('FLASK_ENV', 'development'))
    return config_by_name.get(env, DevelopmentConfig)
