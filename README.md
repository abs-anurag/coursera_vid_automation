# Coursera Video Agent

Local desktop/browser agent that opens Google Chrome, waits for you to log in, locks onto **one named course**, plays that course's videos for real, and skips quizzes, readings, and assignments. It does not answer graded work, seek videos to the end, or call Coursera APIs to fake progress.

## What it does

1. Launches Chrome with a persistent profile.
2. Opens Coursera (or the course URL you configured).
3. Pauses if login is required: *Please log in manually. Press Continue when ready.*
4. Waits until the **configured course name/URL** is open. Any other course is ignored.
5. Scans the outline, finds the next incomplete video, and plays it normally.
6. Watches `currentTime` / `ended` until the video genuinely finishes.
7. Skips quizzes, readings, and assignments without submitting anything.
8. Stops when there are no more videos on that course.

## Architecture

```text
main.py                  CLI + dashboard process
config/settings.py       Pydantic environment settings
browser/                 Playwright Chrome, page helpers, selectors
coursera/                Course lock, lesson classification, video, navigation
agent/                   State machine, decisions, recovery
database/                SQLite progress, events, pause/resume commands
dashboard/               Local FastAPI UI
ai/                      Optional vision classification fallback
tests/                   Mock HTML unit tests
```

Flow for every action: **observe → classify → decide → act → verify**.

The agent only processes the course given via `COURSE_NAME`, `COURSE_URL`, `--course-name`, or `--course`. Outline links from other `/learn/{slug}` paths are never opened.

## Requirements

- Windows, macOS, or Linux
- Python 3.11+
- Google Chrome (preferred) or Playwright Chromium
- A Coursera account (you log in yourself)

## Installation

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## Playwright installation

```bash
playwright install chromium
```

The agent tries Google Chrome first (`channel="chrome"`). If Chrome is missing, it falls back to the Chromium build Playwright just installed.

## Chrome profile setup

Copy `.env.example` to `.env`. `BROWSER_PROFILE_DIR` defaults to `./chrome_profile`. That folder stores cookies so you can stay logged in between runs. Do not commit it.

## Configuration

```text
BROWSER_PROFILE_DIR=./chrome_profile
HEADLESS=false
COURSE_URL=
COURSE_NAME=Entrepreneurial Mindset
LOG_LEVEL=INFO
SCREENSHOT_ON_ERROR=true

AI_ENABLED=false
AI_API_KEY=
AI_MODEL=
```

`COURSE_NAME` and/or `COURSE_URL` **must** identify the only course the agent is allowed to run. Example:

```bash
python main.py --course-name "Entrepreneurial Mindset"
```

or

```bash
python main.py --course "https://www.coursera.org/learn/entrepreneurial-mindset"
```

If both are set, the open course must match the URL slug **and** the name.

## How to run

```bash
python main.py --course-name "Entrepreneurial Mindset"
```

Dashboard: `http://127.0.0.1:8765`

Other commands (second terminal, same project folder):

```bash
python main.py --pause
python main.py --resume
python main.py --stop
python main.py --status
python main.py --dashboard-only
```

## How manual login works

The agent never stores passwords. If it sees a Coursera login page, it waits and shows:

**Please log in manually. Press Continue when ready.**

Log in in the Chrome window, then press **Continue** on the dashboard (or wait until the URL leaves the login page).

## How to pause / resume

Use the dashboard buttons or `python main.py --pause` / `--resume`. STOP cancels the loop. Chrome can remain open until the process exits.

## How progress is stored

SQLite file: `data/progress.db`

Tracked fields: course, course_url, lesson, lesson_url, lesson_type, status (`PENDING`, `PLAYING`, `COMPLETED`, `SKIPPED`, `ERROR`), started_at, completed_at, last_seen.

On resume, completed/skipped items are not replayed. A video left in `PLAYING` is opened again and watched from the live player (the agent does not seek).

## Troubleshooting

| Problem | What to try |
| --- | --- |
| Chrome did not open | Install Google Chrome, or confirm `playwright install chromium` succeeded |
| Stuck on login | Finish login, then Continue |
| Wrong course ignored | Set `COURSE_NAME` to the title shown on Coursera |
| Video never completes | Confirm the tab is audible/visible; the agent will not skip to the end |
| Unknown page | See `logs/screenshots/` and `logs/agent.log` |
| Selectors stale | Update `browser/selectors.py` |

## How to update Coursera selectors

Edit [`browser/selectors.py`](browser/selectors.py). URL regexes are the most stable signal. CSS/text lists are fallbacks. Keep multiple selectors per concept; do not depend on one class name.

## Limitations

- Coursera may change markup; classification can fail and the agent will pause rather than click blindly.
- Quizzes and assignments are never completed. You must do those yourself.
- Completion is based on the in-page media element and visible UI, not Coursera backend APIs.
- Automating a site may conflict with Coursera's terms of use. Use only on courses you are enrolled in, with real playback.
- Optional vision (`AI_ENABLED=true`) only classifies the page type. It never answers questions.

## Tests

```bash
pytest
```

Tests use local HTML fixtures and do not need Coursera access.
