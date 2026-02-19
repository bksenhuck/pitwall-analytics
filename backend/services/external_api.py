"""
External API service.

This module handles calls to external APIs.
Easily replaceable - just change the implementation here.

Why separate this?
- Easy to mock for testing
- Easy to swap external API providers
- Clear separation: this is WHERE external data comes from
"""
import httpx
from typing import Dict, Any, Optional
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
EXTERNAL_API_TIMEOUT = int(os.getenv('EXTERNAL_API_TIMEOUT', '30'))


class ExternalAPIService:
    """
    Service for fetching data from external APIs.
    
    This is a simulation/example. Replace with real API calls.
    """
    
    def __init__(self, timeout: int = EXTERNAL_API_TIMEOUT):
        """
        Initialize external API service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    async def fetch_f1_seasons(self) -> Dict[str, Any]:
        """
        Fetch F1 seasons data from external API.
        
        This is a SIMULATION - replace with real API call.
        Example: https://ergast.com/api/f1/seasons.json
        
        Returns:
            dict: Seasons data
        """
        # Simulate API call delay
        await asyncio.sleep(0.5)
        
        # Simulated response - replace with real API call:
        # async with httpx.AsyncClient(timeout=self.timeout) as client:
        #     response = await client.get('https://ergast.com/api/f1/seasons.json')
        #     return response.json()
        
        return {
            'seasons': [2021, 2022, 2023, 2024, 2025],
            'total': 5,
            'source': 'external_api',
            'timestamp': 'simulated'
        }
    
    async def fetch_race_data(self, season: int, event: str) -> Dict[str, Any]:
        """
        Fetch race data from external API.
        
        Args:
            season: Season year
            event: Event name
        
        Returns:
            dict: Race data
        """
        # Simulate API call delay
        await asyncio.sleep(1.0)
        
        # Simulated response
        return {
            'season': season,
            'event': event,
            'data': {
                'laps': 50,
                'winner': 'Simulation Driver',
                'fastest_lap': '1:23.456'
            },
            'source': 'external_api'
        }
    
    async def fetch_generic_data(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generic method to fetch data from any external API.
        
        This is the real implementation you'd use for actual external APIs.
        
        Args:
            url: API endpoint URL
            params: Query parameters
        
        Returns:
            dict: API response data
        
        Raises:
            httpx.HTTPError: If request fails
        
        Example:
            data = await service.fetch_generic_data(
                'https://ergast.com/api/f1/2023/circuits.json'
            )
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()  # Raise exception for 4xx/5xx
            return response.json()
    
    async def fetch_multiple(self, urls: list[str]) -> list[Dict[str, Any]]:
        """
        Fetch data from multiple URLs concurrently.
        
        Args:
            urls: List of API endpoint URLs
        
        Returns:
            list: List of responses
        
        Example:
            urls = [
                'https://api1.com/data',
                'https://api2.com/data',
                'https://api3.com/data'
            ]
            results = await service.fetch_multiple(urls)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [client.get(url) for url in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results = []
            for response in responses:
                if isinstance(response, Exception):
                    results.append({'error': str(response)})
                else:
                    try:
                        results.append(response.json())
                    except Exception as e:
                        results.append({'error': str(e)})
            
            return results
