from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, Path, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from services import football_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown logic for the application."""
    # Initialize resources
    await football_service.start()
    yield
    # Cleanup resources
    await football_service.close()


app = FastAPI(
    title="Football Zone",
    description="Simple App to explore football leagues and teams.",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")


@app.get("/", tags=["UI"])
async def home(request: Request) -> HTMLResponse:
    """Redirects to the leagues UI page."""
    data = await football_service.get_data("competitions")
    simplified_leagues = [
        {
            "id": league.get("id"),
            "name": league.get("name"),
            "emblem": league.get("emblem")
        }
        for league in data.get("competitions", [])
    ]
    return templates.TemplateResponse(
        request=request,
        name="leagues.html",
        context={"request": request, "leagues": simplified_leagues}
    )


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Simple endpoint to verify the API is running."""
    return {"status": "online", "message": "Welcome to Football Zone"}


@app.get("/api/competitions", tags=["Football"])
@app.get("/api/leagues", tags=["Football"])
async def list_competitions_api() -> Dict[str, Any]:
    """Returns all available football leagues/competitions as JSON."""
    data = await football_service.get_data("competitions")
    simplified_leagues = [
        {
            "id": league.get("id"),
            "name": league.get("name"),
            "emblem": league.get("emblem")
        }
        for league in data.get("competitions", [])
    ]
    return {
        "count": len(simplified_leagues),
        "leagues": simplified_leagues
    }


@app.get("/leagues", tags=["UI"], response_class=HTMLResponse)
async def list_competitions_ui(request: Request) -> HTMLResponse:
    """Returns all available football leagues/competitions in a beautiful UI."""
    data = await football_service.get_data("competitions")
    simplified_leagues = [
        {
            "id": league.get("id"),
            "name": league.get("name"),
            "emblem": league.get("emblem")
        }
        for league in data.get("competitions", [])
    ]
    return templates.TemplateResponse(
        request=request,
        name="leagues.html",
        context={"request": request, "leagues": simplified_leagues}
    )


@app.get("/competitions/{competition_id}", tags=["Football"])
@app.get("/leagues/{competition_id}", tags=["Football"])
async def get_competition(
    competition_id: str = Path(
        ..., description="The unique code for the league (e.g., 'PL', 'BL1')"
    )
) -> Dict[str, Any]:
    """
    Fetch details for a single competition (like 'PL' for Premier League).
    This works with both /competitions and /leagues paths.
    """
    return await football_service.get_data(f"competitions/{competition_id}")


@app.get("/teams/{team_id}", tags=["Football"])
async def get_team(
    team_id: int = Path(..., gt=0)  # Validating that ID is a positive integer
) -> Dict[str, Any]:
    """Fetch details for a specific football team."""
    return await football_service.get_data(f"teams/{team_id}")


@app.get("/teams/{team_id}/matches", tags=["Football"])
async def get_team_matches(
    team_id: int = Path(..., gt=0),
    status: Optional[str] = Query(
        None, description="Filter by: SCHEDULED, LIVE, FINISHED"
    ),
) -> Dict[str, Any]:
    """Fetch recent or upcoming matches for a specific team."""
    params = {"status": status} if status else None
    return await football_service.get_data(f"teams/{team_id}/matches", params=params)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
