import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import AsyncMock, patch


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test the health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "message": "Welcome to Football Zone"}


@pytest.mark.asyncio
async def test_home_page_leagues(async_client):
    """Test the home page renders the leagues correctly."""
    mock_data = {
        "competitions": [
            {"code": "PL", "name": "Premier League", "emblem": "pl_logo.png"},
            {"code": "SA", "name": "Serie A", "emblem": "sa_logo.png"},
            {"code": "OTHER", "name": "Other League", "emblem": "other.png"}
        ]
    }
    
    with patch("main.football_service.get_data", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_data
        
        response = await async_client.get("/")
        
        assert response.status_code == 200
        assert "Premier League" in response.text
        assert "Serie A" in response.text
        assert "Other League" not in response.text


@pytest.mark.asyncio
async def test_league_standings_ui(async_client):
    """Test the competition standings UI endpoint."""
    mock_standings = {
        "competition": {"name": "Premier League", "emblem": "pl.png", "crest": "pl_crest.png"},
        "season": {"currentMatchday": 10, "startDate": "2023-08-11", "endDate": "2024-05-19"},
        "standings": [
            {
                "type": "TOTAL",
                "table": [
                    {
                        "position": 1, 
                        "team": {"name": "Chelsea", "id": 57, "crest": "che.png"},
                        "playedGames": 10,
                        "won": 8,
                        "draw": 1,
                        "lost": 1,
                        "goalsFor": 25,
                        "goalsAgainst": 10,
                        "goalDifference": 15,
                        "points": 25
                    }
                ]
            }
        ]
    }
    mock_matches = {
        "matches": [
            {
                "status": "SCHEDULED",
                "utcDate": "2023-10-21T11:30:00Z",
                "homeTeam": {"name": "Arsenal", "crest": "ars.png", "tla": "ARS"},
                "awayTeam": {"name": "Chelsea", "crest": "che.png", "tla": "CHE"}
            }
        ]
    }
    
    with patch("main.football_service.get_data", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_standings, mock_matches]
        
        response = await async_client.get("/leagues/PL")
        
        assert response.status_code == 200
        assert "Premier League" in response.text
        assert "Chelsea" in response.text
        assert "CHE" in response.text


@pytest.mark.asyncio
async def test_team_details_ui(async_client):
    """Test the team details UI endpoint."""
    mock_team = {
        "name": "Chelsea",
        "id": 57,
        "crest": "che.png",
        "venue": "Stamford Bridge",
        "website": "https://www.chelsea.com",
        "runningCompetitions": [{"code": "PL"}],
        "squad": [{"name": "Reece James", "position": "Defender"}]
    }
    mock_standings = {
        "competition": {"name": "Premier League"},
        "standings": [
            {
                "type": "TOTAL",
                "table": [
                    {
                        "team": {"id": 57, "crest": "che.png", "shortName": "Chelsea"},
                        "position": 1,
                        "playedGames": 10,
                        "goalDifference": 15,
                        "points": 25
                    }
                ]
            }
        ]
    }
    mock_matches = {
        "matches": [
            {
                "status": "FINISHED",
                "utcDate": "2023-10-08T15:30:00Z",
                "competition": {"name": "Premier League"},
                "homeTeam": {"id": 57, "name": "Chelsea", "tla": "CHE"},
                "awayTeam": {"id": 65, "name": "Man City", "tla": "MCI"},
                "score": {"fullTime": {"home": 1, "away": 0}}
            }
        ]
    }
    
    with patch("main.football_service.get_data", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_team, mock_standings, mock_matches]
        
        response = await async_client.get("/teams/57")
        
        assert response.status_code == 200
        assert "Chelsea" in response.text
        assert "Premier League" in response.text
        assert "Reece James" in response.text


@pytest.mark.asyncio
async def test_team_api_json(async_client):
    """Test the team JSON API endpoint."""
    mock_team = {"name": "Chelsea", "id": 57}
    
    with patch("main.football_service.get_data", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_team
        
        response = await async_client.get("/api/teams/57")
        
        assert response.status_code == 200
        assert response.json() == mock_team
