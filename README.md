# OpenFitTrack

AI-assisted food and weight tracker. Log meals in plain language
("200g quark with a banana"); an LLM parses the text into structured items,
and nutrition values come from a food database that you import yourself from a CSV file
(any country, any language), or add by hand.

**Core principle:** the LLM never invents nutrition values. It only parses text
and optionally picks from database candidates. All kcal/macro math is plain Python.

## Status

Working MVP: meal logging with a confirmation step, manual search, CSV food import,
daily overview against goals, weight with an EMA trend line, goals and an eval suite.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in your own values
uv run pytest
uv run ruff check
uv run streamlit run app/main.py
```

## Food data

The app starts with an empty food database. Add foods in the app:

- **Importeren:** upload a CSV file, check the suggested column mapping and import it.
  Values must be per 100 g; semicolon or comma separated, decimal comma or point are
  detected. Importing the same file again updates instead of duplicating.
- **Handmatig toevoegen:** create and edit your own foods.

Write your meals in the same language as your food database: the parser keeps food names
in the language you type them in, and the search compares them with the names in the
database. The UI itself is Dutch for now.

Optional, for Dutch users: the [NEVO table](https://www.rivm.nl/nevo) can be imported with
`uv run python scripts/import_nevo.py <path to NEVO csv>` (it has its own license, so it is
not included here).

## Run with Docker

The app runs in a container; the database lives in a Docker volume, so it survives restarts.
Meal parsing uses [Ollama](https://ollama.com): by default the one running on your own machine.

```bash
cp .env.example .env          # optional: set OLLAMA_MODEL
ollama pull gemma3:12b        # the default model
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

**Ollama in a container instead** (needs an NVIDIA GPU and its Docker support). Set
`OLLAMA_HOST_DOCKER=http://ollama:11434` in `.env`, then:

```bash
docker compose --profile ollama up -d --build
docker compose exec ollama ollama pull gemma3:12b
```

## Structure

- `core/` – all logic (parsing, matching, calculations, database); no Streamlit imports
- `app/` – Streamlit UI, only calls `core`
- `evals/` – test meals with expected output and an eval script
- `scripts/` – helper scripts (NEVO import, demo data, parse smoke test)
- `tests/` – unit tests
