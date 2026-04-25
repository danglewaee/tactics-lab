from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from routers.health import router as health_router
from routers.matches import router as matches_router
from routers.teams import router as teams_router


settings = get_settings()
static_dir = Path(__file__).resolve().parents[1] / "static"

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="Bootstrap API for the Tactics Lab project.",
)


@app.get("/", tags=["meta"])
def root() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "api_prefix": settings.api_prefix,
        "editorial_focus": settings.editorial_team_slugs,
    }


@app.get("/preview", include_in_schema=False)
def preview() -> FileResponse:
    return FileResponse(static_dir / "index.html")


app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(teams_router, prefix=settings.api_prefix)
app.include_router(matches_router, prefix=settings.api_prefix)
