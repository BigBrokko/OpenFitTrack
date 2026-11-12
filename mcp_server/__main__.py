"""Run the MCP server over stdio: `python -m mcp_server`.

The database comes from DATABASE_URL (also read from a .env in the working directory) and
is opened read-only. Over stdio, stdout is the protocol channel: never print to it.
"""

import sys

from dotenv import load_dotenv

from core.db import get_readonly_engine
from mcp_server.server import create_server


def main() -> None:
    load_dotenv()
    try:
        engine = get_readonly_engine()
    except (ValueError, FileNotFoundError) as error:
        sys.exit(f"openfittrack MCP server: {error}")  # goes to stderr
    create_server(engine).run()


if __name__ == "__main__":
    main()
