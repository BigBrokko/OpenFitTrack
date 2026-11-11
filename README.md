# OpenFitTrack

AI-assisted food and weight tracker. Log meals in plain language
("200g quark with a banana"); an LLM parses the text into structured items,
and nutrition values come from a database (NEVO / Open Food Facts).

**Core principle:** the LLM never invents nutrition values. It only parses text
and optionally picks from database candidates. All kcal/macro math is plain Python.

## Status

Early development. Project skeleton and data model only.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in your own values
uv run pytest
uv run ruff check
```

## Structure

- `core/` – all logic (parsing, matching, calculations, database); no Streamlit imports
- `app/` – Streamlit UI, only calls `core`
- `evals/` – test meals with expected output and an eval script
- `scripts/` – helper scripts (e.g. NEVO import)
- `tests/` – unit tests
