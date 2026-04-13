import asyncio
import time
from collections import deque
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException
from cachetools import TTLCache

from config import settings


class FootballDataService:
    """
    Service for interacting with the Football-Data.org API.
    
    This service includes:
    1. Caching layer to minimize API calls.
    2. Rate limiting layer to ensure we stay within the 9 calls/min limit.
    """

    def __init__(self) -> None:
        self.headers = {"X-Auth-Token": settings.FOOTBALL_API_KEY}
        self.base_url = settings.FOOTBALL_BASE_URL
        self.client: Optional[httpx.AsyncClient] = None
        
        # Caching: We'll store up to 100 responses.
        # Default TTL is 10 minutes (600 seconds), but this can be adjusted per call.
        self.cache = TTLCache(maxsize=100, ttl=600)
        
        # Rate Limiting: Max 9 calls per 60 seconds (9/min)
        self.max_calls = 9
        self.window_seconds = 60
        self.call_times = deque()
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """Initialize the HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url, headers=self.headers, timeout=15.0
            )

    async def _wait_for_slot(self) -> None:
        """
        Implements a sliding window rate limiter.
        Pauses execution if we've reached the 9 calls/min limit.
        """
        while True:
            async with self.lock:
                now = time.time()
                
                # Remove timestamps outside the current 60s window
                while self.call_times and now - self.call_times[0] > self.window_seconds:
                    self.call_times.popleft()
                
                if len(self.call_times) < self.max_calls:
                    # Slot is available
                    self.call_times.append(time.time())
                    return
                
                # Calculate how long we must wait for the oldest slot to free up
                wait_time = self.window_seconds - (now - self.call_times[0])
            
            # Wait outside the lock so others can check/clear the window
            if wait_time > 0:
                await asyncio.sleep(wait_time)

    async def get_data(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, cache_ttl: int = 600
    ) -> Dict[str, Any]:
        """
        Fetches data from the API with caching and rate-limiting.
        """
        if self.client is None:
            await self.start()
        
        # Create a unique cache key based on endpoint and params
        cache_key = f"{endpoint}:{sorted(params.items()) if params else ''}"
        
        # 1. Check Cache
        cached_response = self.cache.get(cache_key)
        if cached_response:
            return cached_response

        # 2. Respect Rate Limit (9/min)
        await self._wait_for_slot()

        # 3. Execute Request
        assert self.client is not None
        try:
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 4. Save to Cache
            # (Note: TTLCache uses its own global TTL unless we provide a specific one, 
            # but for simplicity, we use the constructor TTL for now or custom logic if needed)
            self.cache[cache_key] = data
            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Should not happen with our rate limiter, but as a safety:
                raise HTTPException(status_code=429, detail="API Rate Limit reached. Please wait.")
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.text
            ) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}") from e

    async def close(self) -> None:
        """Cleanly shut down the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None


# Global instance
football_service = FootballDataService()
