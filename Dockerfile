FROM python:3.12-slim

# Pinned uv version, copied from the official image.
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so this layer is cached until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY core ./core
COPY app ./app
COPY scripts ./scripts

# Run as a normal user. /data holds the SQLite database (mount a volume here).
RUN useradd --create-home --uid 1000 appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL=sqlite:////data/openfittrack.db

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app/main.py", \
     "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
