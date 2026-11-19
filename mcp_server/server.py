"""The MCP server: five read-only tools over the user's own data."""

import datetime as dt
from collections.abc import Callable
from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from core import reports
from core.report_models import DaySummary, FoodSearchResult, GoalsInfo, PeriodSummary, WeightTrend

INSTRUCTIONS = (
    "OpenFitTrack is the user's own food, weight and goal log. Every value comes from the "
    "user's own database and is calculated by this server; food values are per 100 g. Never "
    "invent or estimate nutrition values that are not in a tool result. A day without logged "
    "food does not mean the user ate nothing: check days_logged and say so when logging looks "
    "incomplete. Give practical, cautious tips and no medical advice."
)

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def create_server(engine: Engine, today: Callable[[], dt.date] = dt.date.today) -> MCPServer:
    """Build the server around a database engine (the real one is opened read-only)."""
    server = MCPServer("openfittrack", title="OpenFitTrack", instructions=INSTRUCTIONS)

    @server.tool(title="Daily overview", annotations=READ_ONLY)
    def get_day_summary(
        date: Annotated[
            dt.date | None, Field(description="Day as YYYY-MM-DD. Defaults to today.")
        ] = None,
    ) -> DaySummary:
        """One day: everything logged, the totals, and the totals compared to that day's goal."""
        with Session(engine) as session:
            return reports.day_summary(session, date or today())

    @server.tool(title="Period overview", annotations=READ_ONLY)
    def get_period_summary(
        start_date: Annotated[
            dt.date | None,
            Field(description="First day, YYYY-MM-DD. Defaults to 6 days before the end date."),
        ] = None,
        end_date: Annotated[
            dt.date | None, Field(description="Last day, YYYY-MM-DD. Defaults to today.")
        ] = None,
    ) -> PeriodSummary:
        """Daily totals and averages over a period (at most 366 days), compared to the goal.

        Averages only use days that have logged food; see days_logged and note.
        """
        end = end_date or today()
        with Session(engine) as session:
            return reports.period_summary(session, start_date or end - dt.timedelta(days=6), end)

    @server.tool(title="Weight trend", annotations=READ_ONLY)
    def get_weight_trend(
        days: Annotated[
            int, Field(ge=1, le=730, description="How many days back to include.")
        ] = 90,
    ) -> WeightTrend:
        """Weight measurements with an exponential moving average trend and the 7-day change."""
        with Session(engine) as session:
            return reports.weight_summary(session, days, today())

    @server.tool(title="Goals", annotations=READ_ONLY)
    def get_goals() -> GoalsInfo:
        """The goal that applies today and the history of all goals."""
        with Session(engine) as session:
            return reports.goals_summary(session, today())

    @server.tool(title="Search foods", annotations=READ_ONLY)
    def search_foods(
        query: Annotated[str, Field(description="Food name, in the language of the database.")],
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> FoodSearchResult:
        """Find foods in the user's database. Values are per 100 g."""
        with Session(engine) as session:
            return reports.food_search(session, query, limit)

    return server
