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
    try:
        data = await football_service.get_data("competitions")
        all_leagues = data.get("competitions", [])
        
        # Filter for top leagues typically available in free tier
        top_codes = {"PL", "PD", "BL1", "SA", "FL1", "CL", "DED", "PPL", "ELC", "BSA"}
        
        simplified_leagues = [
            {
                "id": league.get("code") or league.get("id"),
                "name": league.get("name"),
                "emblem": league.get("emblem") or league.get("crest")
            }
            for league in all_leagues
            if league.get("code") in top_codes
        ]
        
        # If filtering made it empty (or no matches), just show the first few to avoid an empty page
        if not simplified_leagues and all_leagues:
            simplified_leagues = [
                {
                    "id": l.get("code") or l.get("id"),
                    "name": l.get("name"),
                    "emblem": l.get("emblem") or l.get("crest")
                }
                for l in all_leagues[:12]
            ]

        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": simplified_leagues, "timezone": "UTC"}
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": [], "error": str(e), "timezone": "UTC"}
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
            "id": league.get("code") or league.get("id"),
            "name": league.get("name"),
            "emblem": league.get("emblem") or league.get("crest")
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
    try:
        data = await football_service.get_data("competitions")
        all_leagues = data.get("competitions", [])
        
        top_codes = {"PL", "PD", "BL1", "SA", "FL1", "CL", "DED", "PPL", "ELC", "BSA"}
        
        simplified_leagues = [
            {
                "id": league.get("code") or league.get("id"),
                "name": league.get("name"),
                "emblem": league.get("emblem") or league.get("crest")
            }
            for league in all_leagues
            if league.get("code") in top_codes
        ]
        
        if not simplified_leagues and all_leagues:
            simplified_leagues = [
                {
                    "id": l.get("code") or l.get("id"),
                    "name": l.get("name"),
                    "emblem": l.get("emblem") or l.get("crest")
                }
                for l in all_leagues[:12]
            ]

        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": simplified_leagues, "timezone": "UTC"}
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": [], "error": str(e), "timezone": "UTC"}
        )


@app.get("/leagues/{competition_id}", tags=["UI"], response_class=HTMLResponse)
async def get_competition_ui(
    request: Request,
    competition_id: str = Path(
        ..., description="The unique code for the league (e.g., 'PL', 'BL1')"
    )
) -> HTMLResponse:
    """
    Fetch standings for a single competition and render the standings UI.
    """
    try:
        # Fetch standings
        standings_data = await football_service.get_data(f"competitions/{competition_id}/standings")
        
        # Fetch upcoming matches specifically
        # We include LIVE and IN_PLAY in case a game is currently happening
        upcoming_data = await football_service.get_data(
            f"competitions/{competition_id}/matches",
            params={"status": "SCHEDULED,TIMED,LIVE,IN_PLAY", "limit": 10}
        )
        upcoming_fixtures = upcoming_data.get("matches", [])
        
        # Take up to 5
        carousel_matches = upcoming_fixtures[:5]
        carousel_title = "Upcoming Fixtures"
        
        # We usually want the "TOTAL" standings type
        standings = next(
            (s for s in standings_data.get("standings", []) if s.get("type") == "TOTAL"), 
            standings_data.get("standings", [{}])[0]
        )
        
        competition_data = standings_data.get("competition", {})
        # Normalize emblem/crest
        if not competition_data.get("emblem") and competition_data.get("crest"):
            competition_data["emblem"] = competition_data.get("crest")
            
        return templates.TemplateResponse(
            request=request,
            name="league_standings.html",
            context={
                "request": request,
                "competition": competition_data,
                "season": standings_data.get("season", {}),
                "standings": standings,
                "carousel_matches": carousel_matches,
                "carousel_title": carousel_title,
                "timezone": "UTC"
            }
        )
    except Exception as e:
        # Fallback or error page
        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": [], "error": str(e)}
        )


@app.get("/api/competitions/{competition_id}", tags=["Football"])
@app.get("/api/leagues/{competition_id}", tags=["Football"])
async def get_competition_api(
    competition_id: str = Path(
        ..., description="The unique code for the league (e.g., 'PL', 'BL1')"
    )
) -> Dict[str, Any]:
    """
    Fetch details for a single competition as JSON.
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
