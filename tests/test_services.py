import pytest
import httpx
from unittest.mock import AsyncMock, patch
from services import FootballDataService
from fastapi import HTTPException


@pytest.fixture
def service():
    return FootballDataService()


@pytest.mark.asyncio
async def test_get_data_success(service):
    """Test that get_data successfully returns JSON when HTTP response is 200 OK."""
    mock_request = httpx.Request("GET", "https://test.api.com/v4/test-endpoint")
    mock_response = httpx.Response(
        status_code=200,
        json={"data": "test_data"},
        request=mock_request
    )
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await service.get_data("test-endpoint")
        
        assert result == {"data": "test_data"}
        mock_get.assert_called_once_with("test-endpoint", params=None)


@pytest.mark.asyncio
async def test_get_data_http_error(service):
    """Test that get_data raises HTTPException when API returns an error status code."""
    mock_request = httpx.Request("GET", "https://test.api.com/v4/bad-endpoint")
    mock_response = httpx.Response(
        status_code=404,
        content="Not Found",
        request=mock_request
    )
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        with pytest.raises(HTTPException) as excinfo:
            await service.get_data("bad-endpoint")
        
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "Not Found"


@pytest.mark.asyncio
async def test_get_data_generic_exception(service):
    """Test that get_data handles generic network exceptions."""
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection error")):
        with pytest.raises(HTTPException) as excinfo:
            await service.get_data("any-endpoint")
        
        assert excinfo.value.status_code == 500
        assert "Connection error" in excinfo.value.detail


@pytest.mark.asyncio
async def test_close_client(service):
    """Test that close() method shuts down the HTTP client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    service.client = mock_client
    await service.close()
    
    mock_client.aclose.assert_called_once()
    assert service.client is None
