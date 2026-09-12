from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

from agent.agent import CourseraVideoAgent
from config.settings import get_settings
from database.database import Database
from database.models import ControlCommand
from dashboard.server import create_app
from utils.helpers import format_elapsed
from utils.logger import get_logger, setup_logging

log = get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coursera video automation agent")
    parser.add_argument("--course", default="", help="Target Coursera course URL")
    parser.add_argument("--course-name", default="", help="Exact course the agent is allowed to process")
    parser.add_argument("--pause", action="store_true", help="Pause a running agent")
    parser.add_argument("--resume", action="store_true", help="Resume a paused agent")
    parser.add_argument("--stop", action="store_true", help="Stop a running agent")
    parser.add_argument("--status", action="store_true", help="Print current progress")
    parser.add_argument("--dashboard-only", action="store_true", help="Serve the dashboard without starting the agent")
    return parser.parse_args()


def apply_args(args: argparse.Namespace) -> None:
    settings = get_settings()
    if args.course:
        settings.course_url = args.course
    if args.course_name:
        settings.course_name = args.course_name


def print_status(database: Database) -> None:
    runtime = database.get_runtime()
    print("Coursera Video Agent")
    print(f"Course: {runtime.get('course') or '—'}")
    print(f"Videos completed: {runtime.get('videos_completed') or 0} / {runtime.get('videos_total') or 0}")
    print(f"Current video: {runtime.get('current_lesson') or '—'}")
    print(f"Type: {runtime.get('current_type') or '—'}")
    print(f"Status: {runtime.get('agent_state') or 'STOPPED'}")
    print(f"Elapsed: {format_elapsed(float(runtime.get('elapsed_seconds') or 0))}")


async def run_dashboard(database: Database, settings) -> None:
    app = create_app(database)
    config = uvicorn.Config(
        app,
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_agent_and_dashboard() -> None:
    settings = get_settings()
    database = Database(settings.database_path)
    agent = CourseraVideoAgent(settings, database)
    dashboard_task = asyncio.create_task(run_dashboard(database, settings))
    try:
        log.info(
            "Dashboard: http://%s:%s",
            settings.dashboard_host,
            settings.dashboard_port,
        )
        await agent.run()
    finally:
        dashboard_task.cancel()
        try:
            await dashboard_task
        except asyncio.CancelledError:
            pass
        database.close()


def main() -> None:
    setup_logging()
    args = parse_args()
    apply_args(args)
    settings = get_settings()
    database = Database(settings.database_path)

    if args.pause:
        database.set_command(ControlCommand.PAUSE)
        print("Pause command sent.")
        database.close()
        return
    if args.resume:
        database.set_command(ControlCommand.RESUME)
        print("Resume command sent.")
        database.close()
        return
    if args.stop:
        database.set_command(ControlCommand.STOP)
        print("Stop command sent.")
        database.close()
        return
    if args.status:
        print_status(database)
        database.close()
        return

    database.close()
    if args.dashboard_only:
        settings = get_settings()
        database = Database(settings.database_path)
        asyncio.run(run_dashboard(database, settings))
        return

    asyncio.run(run_agent_and_dashboard())


if __name__ == "__main__":
    main()
