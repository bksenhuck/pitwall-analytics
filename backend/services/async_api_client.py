"""
Example: Async HTTP client service using httpx.

This demonstrates how to make async external API calls in FastAPI.
Use this pattern when calling external APIs like weather services,
third-party F1 APIs, or any HTTP-based service.

Why httpx?
- Async/await support (unlike requests)
- Similar API to requests library
- Better performance in async contexts
- Connection pooling out of the box
"""
import httpx
from typing import Dict, Any, Optional
import asyncio


class AsyncAPIClient:
    """
    Async HTTP client for external API calls.
    
    Example usage in FastAPI endpoint:
        api_client = AsyncAPIClient()
        data = await api_client.fetch_external_data("https://api.example.com/data")
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize async HTTP client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    async def fetch_external_data(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Fetch data from external API asynchronously.
        
        Args:
            url: API endpoint URL
            params: Query parameters
        
        Returns:
            JSON response data
        
        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()  # Raise exception for 4xx/5xx
            return response.json()
    
    async def post_external_data(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post data to external API asynchronously.
        
        Args:
            url: API endpoint URL
            data: JSON data to post
        
        Returns:
            JSON response data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
    
    async def fetch_multiple(self, urls: list[str]) -> list[Dict[str, Any]]:
        """
        Fetch data from multiple URLs concurrently.
        
        Args:
            urls: List of API endpoint URLs
        
        Returns:
            List of JSON responses
        
        Example:
            urls = ["https://api1.com/data", "https://api2.com/data"]
            results = await client.fetch_multiple(urls)
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


# Example usage in FastAPI endpoint:
"""
from backend.services.async_api_client import AsyncAPIClient

@router.get('/external-data')
async def get_external_data():
    client = AsyncAPIClient()
    
    # Single request
    data = await client.fetch_external_data(
        "https://api.weather.com/current",
        params={"location": "monaco"}
    )
    
    # Multiple concurrent requests
    urls = [
        "https://api1.com/data",
        "https://api2.com/data",
        "https://api3.com/data"
    ]
    results = await client.fetch_multiple(urls)
    
    return {
        'success': True,
        'data': data,
        'multi_results': results
    }
"""
