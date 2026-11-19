"""Start the MCP server as a separate process over stdio (like Claude does) and call it.

Use it to check your setup before you connect Claude. It uses DATABASE_URL from your
environment (or .env) and prints what each tool returns.

  uv run python scripts/mcp_smoke.py
  uv run python scripts/mcp_smoke.py -- docker run -i --rm \
      -v openfittrack_oft-data:/data:ro openfittrack-app python -m mcp_server

Everything after `--` is the command that starts the server; the default is
`python -m mcp_server`. The server process only gets a small set of environment variables
(plus DATABASE_URL), like it does from an MCP client.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from mcp import Client, StdioServerParameters  # noqa: E402

CALLS = [
    ("get_goals", {}),
    ("get_day_summary", {}),
    ("get_period_summary", {}),
    ("get_weight_trend", {"days": 30}),
    ("search_foods", {"query": "a", "limit": 3}),
]


def shorten(data: dict, width: int = 300) -> str:
    text = json.dumps(data, ensure_ascii=False)
    return text if len(text) <= width else text[:width] + " ..."


async def run(command: list[str]) -> int:
    env = {k: v for k in ("DATABASE_URL",) if (v := os.environ.get(k))}
    server = StdioServerParameters(command=command[0], args=command[1:], env=env)
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
        print("tools:", ", ".join(t.name for t in tools))
        failed = 0
        for name, arguments in CALLS:
            result = await client.call_tool(name, arguments)
            status = "ERROR" if result.is_error else "ok"
            failed += bool(result.is_error)
            body = result.structured_content if not result.is_error else result.content
            print(f"\n[{status}] {name} {arguments or ''}")
            print(shorten(body) if isinstance(body, dict) else body)
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", nargs="*", help="command that starts the server (after --)")
    args = parser.parse_args()

    load_dotenv()
    command = args.command or [sys.executable, "-m", "mcp_server"]
    sys.exit(asyncio.run(run(command)))


if __name__ == "__main__":
    main()
