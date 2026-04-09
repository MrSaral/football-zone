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
    await football_service.start()
    yield
    await football_service.close()


app = FastAPI(
    title="Football Zone",
    description="Simple App to explore football leagues and teams.",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", tags=["UI"])
async def home(request: Request) -> HTMLResponse:
    """Redirects to the leagues UI page."""
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


@app.get("/leagues", tags=["UI"], response_class=HTMLResponse)
async def list_competitions_ui(request: Request) -> HTMLResponse:
    """Returns all available football leagues in a beautiful UI."""
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
    competition_id: str = Path(..., description="The unique code for the league (e.g., 'PL', 'BL1')")
) -> HTMLResponse:
    """Fetch standings and upcoming fixtures for a league and render the UI."""
    try:
        standings_data = await football_service.get_data(f"competitions/{competition_id}/standings")
        
        # Fetch all matches for the competition and filter locally for robustness
        all_matches_data = await football_service.get_data(f"competitions/{competition_id}/matches")
        all_matches = all_matches_data.get("matches", [])
        
        upcoming_fixtures = [m for m in all_matches if m.get("status") in ["SCHEDULED", "TIMED", "LIVE", "IN_PLAY"]][:5]
        recent_results = [m for m in all_matches if m.get("status") == "FINISHED"]
        recent_results = recent_results[-5:]
        recent_results.reverse()
        
        carousel_matches = upcoming_fixtures if upcoming_fixtures else recent_results
        carousel_title = "Upcoming Fixtures" if upcoming_fixtures else "Recent Results"
        
        standings = next(
            (s for s in standings_data.get("standings", []) if s.get("type") == "TOTAL"), 
            standings_data.get("standings", [{}])[0]
        )
        
        competition_data = standings_data.get("competition", {})
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
        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": [], "error": str(e)}
        )


@app.get("/teams/{team_id}", response_class=HTMLResponse, tags=["UI"])
async def get_team_ui(
    request: Request,
    team_id: int = Path(..., gt=0)
) -> HTMLResponse:
    """Fetch comprehensive details for a specific team and render the UI."""
    try:
        team = await football_service.get_data(f"teams/{team_id}")
        
        comp_id = None
        competitions = team.get("runningCompetitions", [])
        if competitions:
            comp_id = competitions[0].get("code") or competitions[0].get("id")

        standings_context = []
        competition_name = "N/A"
        if comp_id:
            try:
                standings_data = await football_service.get_data(f"competitions/{comp_id}/standings")
                competition_name = standings_data.get("competition", {}).get("name", "League")
                table = next(
                    (s.get("table", []) for s in standings_data.get("standings", []) if s.get("type") == "TOTAL"),
                    []
                )
                
                team_idx = -1
                for i, row in enumerate(table):
                    if row.get("team", {}).get("id") == team_id:
                        team_idx = i
                        break
                
                if team_idx != -1:
                    start = max(0, team_idx - 2)
                    end = min(len(table), team_idx + 3)
                    standings_context = table[start:end]
            except Exception:
                pass

        matches_data = await football_service.get_data(f"teams/{team_id}/matches")
        all_matches = matches_data.get("matches", [])
        recent_results = [m for m in all_matches if m.get("status") == "FINISHED"][-3:]
        recent_results.reverse()
        upcoming_fixtures = [m for m in all_matches if m.get("status") in ["SCHEDULED", "TIMED", "LIVE", "IN_PLAY"]][:3]
        
        return templates.TemplateResponse(
            request=request,
            name="team_details.html",
            context={
                "request": request,
                "team": team,
                "competition_name": competition_name,
                "standings": standings_context,
                "recent_results": recent_results,
                "upcoming_fixtures": upcoming_fixtures,
                "timezone": "UTC"
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="leagues.html",
            context={"request": request, "leagues": [], "error": f"Error loading team: {str(e)}"}
        )


@app.get("/api/teams/{team_id}", tags=["Football"])
async def get_team_api(team_id: int = Path(..., gt=0)) -> Dict[str, Any]:
    """Fetch details for a specific football team as JSON."""
    return await football_service.get_data(f"teams/{team_id}")


@app.get("/api/teams/{team_id}/matches", tags=["Football"])
async def get_team_matches_api(
    team_id: int = Path(..., gt=0),
    status: Optional[str] = Query(None, description="Filter by: SCHEDULED, LIVE, FINISHED")
) -> Dict[str, Any]:
    """Fetch recent or upcoming matches for a specific team as JSON."""
    params = {"status": status} if status else None
    return await football_service.get_data(f"teams/{team_id}/matches", params=params)


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Simple endpoint to verify the API is running."""
    return {"status": "online", "message": "Welcome to Football Zone"}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
