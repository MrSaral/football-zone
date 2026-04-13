import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from services import FootballDataService
import httpx

@pytest.fixture
def service():
    return FootballDataService()

@pytest.mark.asyncio
async def test_rate_limiter_burst(service):
    """Test that 9 calls go through without sleeping."""
    service.client = AsyncMock(spec=httpx.AsyncClient)
    # Mock response
    mock_response = httpx.Response(200, json={"status": "ok"})
    mock_response._request = httpx.Request("GET", "http://test")
    service.client.get.return_value = mock_response

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        for i in range(9):
            await service.get_data(f"endpoint-{i}")
        
        # Should have made 9 calls and 0 sleeps
        assert len(service.call_times) == 9
        assert mock_sleep.call_count == 0

@pytest.mark.asyncio
async def test_rate_limiter_throttles_tenth_call(service):
    """Test that the 10th call triggers a sleep."""
    service.client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = httpx.Response(200, json={"status": "ok"})
    mock_response._request = httpx.Request("GET", "http://test")
    service.client.get.return_value = mock_response

    # Reduce the window for testing purposes
    service.window_seconds = 10
    
    # Pre-fill 9 calls at t=100.0 (manually to avoid many time.time() calls)
    from collections import deque
    service.call_times = deque([100.0] * 9)

    # The 10th call happens at t=107.0 (within 10s window)
    # It should calculate wait_time = 10 - (107 - 100) = 3s
    with patch("services.time.time") as mock_time, \
         patch("services.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        # 1st call: _wait_for_slot start -> 107.0
        # 2nd call: _wait_for_slot (recursive) start -> 115.0 (clears the window)
        # 3rd call: _wait_for_slot end (append) -> 115.0
        # We provide extra values just in case.
        mock_time.side_effect = [107.0, 115.0, 115.0, 115.0, 115.0]

        await service.get_data("endpoint-10")

        # Verify sleep was called with 3 seconds
        mock_sleep.assert_called_once_with(3.0)
        # Verify we now have 9 calls in the window (8 old ones popped, 1 new added)
        # Actually, in this scenario:
        # 9 calls at 100.0.
        # now = 107.0 -> wait_time = 3.0.
        # now = 115.0 -> while 115 - 100 > 10: popleft.
        # All 9 calls at 100.0 are popped because 115 - 100 = 15 > 10.
        # So call_times becomes empty, then appends 115.0.
        assert len(service.call_times) == 1
        assert service.call_times[0] == 115.0

@pytest.mark.asyncio
async def test_cache_does_not_consume_rate_limit(service):
    """Test that hits to the cache don't count towards the 9-call limit."""
    service.client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = httpx.Response(200, json={"data": "cached"})
    mock_response._request = httpx.Request("GET", "http://test")
    service.client.get.return_value = mock_response

    # 1. First call (Cache Miss)
    await service.get_data("same-endpoint")
    assert len(service.call_times) == 1
    
    # 2. Subsequent 20 calls to same endpoint (Cache Hits)
    for _ in range(20):
        await service.get_data("same-endpoint")
    
    # Rate limit counter should still be at 1
    assert len(service.call_times) == 1
    # API client should have only been called once
    assert service.client.get.call_count == 1
