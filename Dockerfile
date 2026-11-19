# One image for the website and the API. Three stages: Node and uv are only needed to build,
# so the final image has neither of them.

# --- Stage 1: build the React app ---------------------------------------------------------
FROM node:24-slim AS web
WORKDIR /web
# Dependencies first, so this layer is cached until package.json or package-lock.json change.
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- Stage 2: install the Python dependencies ---------------------------------------------
FROM python:3.12-slim AS python-deps
# Pinned uv version, copied from the official image.
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# --- Stage 3: the image that runs ---------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# The virtual environment keeps its path (/app/.venv) and uses the same Python as above.
COPY --from=python-deps /app/.venv ./.venv
COPY core ./core
COPY api ./api
COPY mcp_server ./mcp_server
COPY scripts ./scripts
COPY --from=web /web/dist ./web-dist

# Run as a normal user. /data holds the SQLite database (mount a volume here).
RUN useradd --create-home --uid 1000 appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL=sqlite:////data/openfittrack.db \
    OFT_WEB_DIR=/app/web-dist

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

# Login settings (OFT_PASSWORD_HASH, OFT_SESSION_SECRET) come from the environment at run time.
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
