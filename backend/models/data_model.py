"""
Data models for cached data.

Using Pydantic for data validation and serialization.
These models define the structure of data in the database.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any


class CachedDataModel(BaseModel):
    """
    Model for cached data.
    
    This represents a single cache entry in the database.
    """
    id: Optional[int] = None
    key: str = Field(..., description="Unique key for the cached data")
    data: str = Field(..., description="JSON string of cached data")
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class CachedDataResponse(BaseModel):
    """
    Response model for cached data API.
    
    This is what the API returns to clients.
    """
    success: bool
    data: Any
    cached: bool = Field(..., description="Whether data was served from cache")
    last_updated: Optional[datetime] = None
    message: Optional[str] = None


class RefreshResponse(BaseModel):
    """Response model for refresh endpoint"""
    success: bool
    message: str
    last_updated: datetime
    records_updated: int = 0
