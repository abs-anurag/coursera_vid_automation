from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database.database import Database
from database.models import ControlCommand
from utils.helpers import format_elapsed

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(database: Database) -> FastAPI:
    app = FastAPI(title="Coursera Video Agent")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/status")
    async def status():
        runtime = database.get_runtime()
        elapsed = format_elapsed(float(runtime.get("elapsed_seconds") or 0))
        completed = int(runtime.get("videos_completed") or 0)
        total = int(runtime.get("videos_total") or 0)
        percent = int((completed / total) * 100) if total else 0
        return {
            "course": runtime.get("course") or "",
            "course_url": runtime.get("course_url") or "",
            "current": runtime.get("current_lesson") or "",
            "type": runtime.get("current_type") or "",
            "status": runtime.get("agent_state") or "STOPPED",
            "videos_completed": completed,
            "videos_total": total,
            "percent": percent,
            "elapsed": elapsed,
        }

    @app.get("/api/events")
    async def events():
        return {"events": list(reversed(database.recent_events(80)))}

    @app.post("/api/pause")
    async def pause():
        database.set_command(ControlCommand.PAUSE)
        return {"ok": True}

    @app.post("/api/resume")
    async def resume():
        database.set_command(ControlCommand.RESUME)
        return {"ok": True}

    @app.post("/api/stop")
    async def stop():
        database.set_command(ControlCommand.STOP)
        return {"ok": True}

    @app.post("/api/continue")
    async def continue_flow():
        database.set_command(ControlCommand.CONTINUE)
        return {"ok": True}

    return app
