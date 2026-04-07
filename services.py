from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from config import settings


class FootballDataService:
    """
    This is our helper class for all things related to the Football Data API.
    Instead of writing the same request logic everywhere, we wrap it all here
    using an asynchronous HTTP client (httpx) to keep things fast and non-blocking.
    """

    def __init__(self) -> None:
        # We initialize the client as None and set it up during app startup (lifespan).
        # This ensures the client is bound to the correct running event loop.
        self.headers = {"X-Auth-Token": settings.FOOTBALL_API_KEY}
        self.base_url = settings.FOOTBALL_BASE_URL
        self.client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Initialize the HTTP client if it doesn't already exist."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url, headers=self.headers, timeout=10.0
            )

    async def get_data(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        A generic fetcher function:
        1. Makes the request to the specified endpoint.
        2. Raises an error if the API returns something other than a 200 OK.
        3. Returns the clean JSON data we need.
        """
        if self.client is None:
            # Fallback in case start() wasn't called in lifespan
            await self.start()

        # The check above ensures self.client is not None here, but for type-safety:
        assert self.client is not None
        try:
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Let the user know exactly why the external API failed
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.text
            ) from e

        except Exception as e:
            # Catch-all for other issues like timeouts or network problems
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def close(self) -> None:
        """Cleanly shut down the HTTP client when the app stops."""
        if self.client:
            await self.client.aclose()
            self.client = None


# Global instance for the app
football_service = FootballDataService()
