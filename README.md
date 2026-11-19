# OpenFitTrack

Self-hosted food and weight tracker. You log what you eat by searching a food database
that you import yourself from a CSV file (any country, any language) or fill by hand.
A read-only MCP server lets you connect your own Claude and ask it for tips based on your
own numbers.

**Core principle:** an AI model never invents nutrition values. All kcal/macro math is plain
Python, and a connected model can only read the data.

## Status

Working: food logging by search, CSV food import, your own foods, daily overview against
goals, weight with an EMA trend line, goals, a read-only MCP server (stdio), a phone-friendly
web app (PWA) and a Docker image, reachable from your phone over Tailscale. Not yet: MCP over
HTTPS for ChatGPT and claude.ai (that needs a public address and its own authentication).

## Setup

```bash
uv sync
cp .env.example .env
uv run pytest
uv run ruff check
```

To use the app, set a password (see "API" below) and run the API and the web app, or run it
all in one container (see "Run with Docker").

## Food data

The app starts with an empty food database. Add foods in two ways:

- **Your own foods:** in the app, on **Dag** → **Eten toevoegen** → **Nieuw product maken**.
  You can edit them later.
- **Import a CSV file** (a food table of your own country, any language) with
  `scripts/import_csv.py`. Values must be per 100 g; semicolon or comma separated, decimal
  comma or point are detected, and the columns are guessed from the header names. Without
  `--per-100g` it only shows what it would import; importing the same file again updates
  instead of duplicating.

```bash
uv run python scripts/import_csv.py foods.csv             # preview, imports nothing
uv run python scripts/import_csv.py foods.csv --per-100g  # import
uv run python scripts/import_csv.py --help                # choose columns yourself
```

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
project plan). It listens on `127.0.0.1` only. Every endpoint except
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
- **Writing:** `POST /api/entries` (log a food by id and grams), `PATCH`/`DELETE
  /api/entries/{id}`, `POST /api/foods` and `PATCH /api/foods/{id}` (your own foods),
  `PUT /api/weight` and `PUT /api/goals`. Invalid values give `400`, an unknown id `404`.
  The MCP server stays read-only; only the logged-in web app writes.
- **Changing the password** means running the script again and replacing both lines. A new
  `OFT_SESSION_SECRET` logs every existing session out.

## Web app (work in progress)

`web/` holds a mobile-first React + TypeScript app (Vite, Tailwind, TanStack Query) that
talks to the API and can be installed as a PWA. It has a login screen and three pages:
**Dag** (the day against your goal, with arrows to other days; log food by searching, correct
or delete a line, create and edit your own foods), **Gewicht** (log your weight; trend line
and target over 30 to 365 days) and **Doelen** (set a goal; current goal and history).
Importing a CSV file is a script for now (see "Food data"). It needs Node 22.12 or newer.

```bash
cd web
npm install
```

Run the API (see above) in one terminal and the web app in another:

```bash
npm run dev
```

Open `http://localhost:5173`. Vite forwards `/api` to the API on port 8000, so the login
cookie works without CORS settings.

| Command | What it does |
|---|---|
| `npm run lint` | ESLint |
| `npm test` | Vitest tests |
| `npm run build` | type check and production build into `web/dist` |
| `npm run preview` | serve the production build on `http://localhost:4173` |
| `npm run gen:api` | regenerate the TypeScript API types after an API change |
| `npm run gen:icons` | regenerate the PWA icons from `public/icon.svg` |

- **API types:** `web/openapi.json` is a snapshot of the API description and
  `src/api/schema.d.ts` is generated from it. A Python test fails when the snapshot is
  out of date: run `npm run gen:api` and commit the result.
- **PWA:** the service worker only stores the app shell (code, styles, icons). It never
  caches `/api`, so without a connection you see "no connection" instead of old health data.
- **Installing on a phone needs HTTPS.** Browsers only allow installing a web app and
  registering a service worker on HTTPS (or `localhost`). Plain `http://192.168...` over
  Wi-Fi therefore cannot install the app, and logging in there also fails because the
  cookie is `Secure` (unless `OFT_COOKIE_SECURE=false`, for a short test only). See
  "Reach the app from your phone" for a trusted HTTPS address.

## Run with Docker

One container serves the website and the API (the image is built in three stages: Node builds
the web app, uv installs the Python packages, and the final image has neither). The database
lives in a Docker volume, so it survives restarts.

Create the login first (see "API" above) so that `.env` has `OFT_PASSWORD_HASH` and
`OFT_SESSION_SECRET`; compose passes `.env` to the container, the image contains no secrets.

```bash
docker compose up -d --build  # app on http://localhost:8000
```

It listens on `127.0.0.1` only. The login cookie is `Secure`, which browsers accept on
`localhost`; for your phone you need HTTPS (see "Reach the app from your phone").

Add foods with the CSV script; put the file under `data/`, which is mounted read-only at
`/import` (the path below is inside the container):

```bash
docker compose run --rm app python scripts/import_csv.py /import/foods.csv --per-100g
```

For the Dutch NEVO table use `scripts/import_nevo.py` in the same way.

Git Bash on Windows rewrites paths that start with `/`; prefix the command with
`MSYS_NO_PATHCONV=1`, or use PowerShell.

Stop with `docker compose down` (your data stays); `docker compose down -v` also deletes it.

## Reach the app from your phone (Tailscale)

[Tailscale](https://tailscale.com) is a private network (a VPN) between your own devices.
With *Tailscale Serve* your computer gives the app a real HTTPS address that only your own
devices can open. Nothing is made public. HTTPS is what lets the login cookie, the service
worker and "install as app" work on a phone.

**One-time setup** (accounts and network settings are yours to change, not the project's):

1. Install Tailscale on the computer that runs the app and on your phone, and log in to the
   same account on both. Turn on two-factor authentication for that account.
2. In the [Tailscale admin console](https://login.tailscale.com/admin/dns), under **DNS**,
   check that **MagicDNS** is on, then press **Enable HTTPS** under *HTTPS Certificates*.
   Certificates are listed in public Certificate Transparency logs, **including the machine
   name**, so give your computer a neutral name first (for example `fit-pc`, not your own
   name).
3. Start the app (`docker compose up -d`, see above) and, on the computer, run:

```bash
tailscale serve --bg --https=443 127.0.0.1:8000
tailscale serve status        # shows your address, https://<machine>.<tailnet>.ts.net
```

Open that address on your phone with Tailscale switched on and log in. The `--bg` setting
survives restarts of Tailscale and the computer. Do **not** use `tailscale funnel`: that
makes the app public on the internet.

**Install it as an app:** on iPhone open the address in Safari, then Share → *Add to Home
Screen*. On Android open it in Chrome, then menu → *Install app*.

**Check that it works:**

- on your phone, switch off Wi-Fi (mobile data only) with Tailscale on: the app loads and
  you can log in;
- switch Tailscale off on the phone: the address no longer opens, which is the point;
- log a meal on the phone and see it on the computer.

**Good to know:**

- The computer must be on, Docker running, and Tailscale connected. Docker restarts the
  container by itself (`restart: unless-stopped`) once Docker Desktop is running; let
  Docker Desktop start at login if you want that automatic.
- The container still listens on `127.0.0.1` only. Tailscale on the same computer is the
  only way in; do not change the port mapping to `0.0.0.0`.
- The limit of 5 wrong passwords counts per address, and behind Tailscale and Docker every
  request looks the same. After 5 wrong attempts the login is closed for 15 minutes for all
  your devices. Only your own devices are on the network, so this is fine in practice.
- **Lost phone:** remove the device in the Tailscale admin console (*Machines*), and replace
  `OFT_SESSION_SECRET` in `.env` (run `scripts/create_credentials.py` again) and restart the
  container: that logs out every session.
- Turn the address off with `tailscale serve --https=443 off` (or `tailscale serve reset`).
- Running the app on a NAS or a Raspberry Pi instead of your computer? Then run Tailscale
  as a second container next to the app (Tailscale publishes an official image and a
  `TS_SERVE_CONFIG` setting for this) so the app stays reachable while your computer is off.

## Structure

- `core/` – all logic (matching, calculations, statistics, reports, CSV import, database); no framework imports
- `api/` – FastAPI API, only calls `core`
- `web/` – React frontend, only talks to the API
- `mcp_server/` – read-only MCP server, only calls `core`
- `scripts/` – helper scripts (CSV and NEVO import, demo data, credentials, MCP smoke test)
- `tests/` – unit tests
