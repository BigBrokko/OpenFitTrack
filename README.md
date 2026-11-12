# OpenFitTrack

Self-hosted food and weight tracker. You log what you eat by searching a food database
that you import yourself from a CSV file (any country, any language) or fill by hand.
A read-only MCP server lets you connect your own Claude and ask it for tips based on your
own numbers.

**Core principle:** an AI model never invents nutrition values. All kcal/macro math is plain
Python, and a connected model can only read the data.

## Status

Working: food logging by search, CSV food import, your own foods, daily overview against
goals, weight with an EMA trend line, goals, and a read-only MCP server (stdio). Not yet:
MCP over HTTPS for ChatGPT and claude.ai (that needs authentication).

## Setup

```bash
uv sync
cp .env.example .env
uv run pytest
uv run ruff check
uv run streamlit run app/main.py
```

## Food data

The app starts with an empty food database. Add foods in the app:

- **Importeren:** upload a CSV file, check the suggested column mapping and import it.
  Values must be per 100 g; semicolon or comma separated, decimal comma or point are
  detected. Importing the same file again updates instead of duplicating.
- **Eten loggen:** search a food and log an amount in grams. You can also create your
  own foods there, and edit them later.

The UI itself is Dutch for now.

Optional, for Dutch users: the [NEVO table](https://www.rivm.nl/nevo) can be imported with
`uv run python scripts/import_nevo.py <path to NEVO csv>` (it has its own license, so it is
not included here).

## Connect your AI (MCP)

The MCP server gives an AI assistant read access to your data, so it can answer things like
"how was my week?" and give tips. It has five tools, all read-only:

| Tool | What it returns |
|---|---|
| `get_day_summary` | one day: logged food, totals, and the totals against that day's goal |
| `get_period_summary` | daily totals and averages over a period (max 366 days) against the goal |
| `get_weight_trend` | weights with an EMA trend line and the 7-day change |
| `get_goals` | your current goal and the goal history |
| `search_foods` | foods in your database with values per 100 g |

It opens the database **read-only** (SQLite itself rejects writes), has no write tools, and
runs on your machine over stdio: no network port. Days without logged food are not counted
as zero intake; the tools report `days_logged` so the model can tell when logging looks
incomplete. Whatever the model sees in a tool result goes to its provider (Anthropic,
OpenAI), so connect only an assistant you are comfortable sharing this data with.

Check that it works before you connect anything (uses `DATABASE_URL` or `.env`):

```bash
uv run python scripts/mcp_smoke.py
```

**Claude Code:**

```bash
claude mcp add --transport stdio openfittrack -- uv --directory /path/to/OpenFitTrack run python -m mcp_server
```

**Claude Desktop:** open Settings, Developer, Edit Config and add the server to
`claude_desktop_config.json`, then restart Claude Desktop completely. Use absolute paths
(and the full path to `uv` if Claude cannot find it):

```json
{
  "mcpServers": {
    "openfittrack": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\OpenFitTrack", "run", "python", "-m", "mcp_server"],
      "env": { "DATABASE_URL": "sqlite:///C:/path/to/OpenFitTrack/openfittrack.db" }
    }
  }
}
```

**With the Docker setup** the database lives in a volume. `docker run -i` mounts it
read-only and works without extra environment variables (with the default project name the
image is `openfittrack-app` and the volume `openfittrack_oft-data`):

```bash
docker run -i --rm -v openfittrack_oft-data:/data:ro openfittrack-app python -m mcp_server
```

Use that as the command in the Claude configuration (`"command": "docker"`, the rest as
`args`). Docker Desktop must be running.

## API (work in progress)

A FastAPI API over the same data is the base for a phone-friendly React web app (see the
project plan). For now it is read-only and listens on `127.0.0.1` only. Every endpoint except
`/api/health` and the login endpoints needs a login.

**Set a password first.** The API refuses to start without one. Run this yourself and paste
the two lines it prints into your `.env` (your password is never stored, only its Argon2 hash):

```bash
uv run python scripts/create_credentials.py
```

Then start the API:

```bash
uv run uvicorn api.server:app --reload
```

- **Login:** `POST /api/login` with `{"password": "..."}` returns 204 and sets a session
  cookie (HttpOnly, SameSite=Strict, Secure, valid for 14 days). `POST /api/logout` ends it
  and `GET /api/me` tells whether you are logged in.
- **Failed attempts:** after 5 wrong passwords within 15 minutes a client gets `429` with a
  `Retry-After` header. The counters live in memory, so a restart resets them.
- **HTTPS:** the cookie is `Secure`, so it is only sent over HTTPS (browsers make an
  exception for `localhost`, Safari does not). To try the API over plain http, set
  `OFT_COOKIE_SECURE=false`; never do that on a network you do not control.
- **Docs:** `http://127.0.0.1:8000/docs` stays open (it contains no data). Log in with the
  login endpoint there first to try the others.
- **Endpoints:** `/api/day`, `/api/period`, `/api/weight`, `/api/goals` and
  `/api/foods/search`. They return the same numbers as the MCP tools, because both use
  `core/reports.py`.
- **Changing the password** means running the script again and replacing both lines. A new
  `OFT_SESSION_SECRET` logs every existing session out.

## Run with Docker

The app runs in a container; the database lives in a Docker volume, so it survives restarts.

```bash
docker compose up -d --build  # app on http://localhost:8501
```

Add foods through the app's **Importeren** page (upload a CSV, no mounting needed).
For the Dutch NEVO table you can also use the script; put the download under `data/`, which
is mounted read-only at `/nevo` (the path below is inside the container):

```bash
docker compose run --rm app python scripts/import_nevo.py /nevo/NEVO2025_v9.0/NEVO2025_v9.0.csv
```

Git Bash on Windows rewrites paths that start with `/`; prefix the command with
`MSYS_NO_PATHCONV=1`, or use PowerShell.

Stop with `docker compose down` (your data stays); `docker compose down -v` also deletes it.

## Structure

- `core/` – all logic (matching, calculations, statistics, reports, CSV import, database); no framework imports
- `api/` – FastAPI API, only calls `core`
- `app/` – Streamlit UI (temporary, until the React frontend replaces it), only calls `core`
- `mcp_server/` – read-only MCP server, only calls `core`
- `scripts/` – helper scripts (NEVO import, demo data, MCP smoke test)
- `tests/` – unit tests
