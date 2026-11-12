"""Entry point for uvicorn: uv run uvicorn api.server:app --reload

Reads DATABASE_URL (also from a .env in the working directory). uvicorn listens on
127.0.0.1 by default, so the API is not reachable from other devices. There is no login yet:
do not expose it before the login card is done.
"""

from dotenv import load_dotenv

from api.main import create_app
from core.db import get_engine

load_dotenv()
app = create_app(get_engine())
