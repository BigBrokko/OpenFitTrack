"""The API: JSON endpoints over `core`. Free of side effects on import; see api/server.py."""

import datetime as dt
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlmodel import Session

from core import reports
from core.db import create_db
from core.report_models import DaySummary, FoodSearchResult, GoalsInfo, PeriodSummary, WeightTrend


def create_app(engine: Engine, today: Callable[[], dt.date] = dt.date.today) -> FastAPI:
    """Build the API around a database engine. `today` can be replaced in tests."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        create_db(engine)  # a fresh database gets its tables instead of "no such table" errors
        yield

    app = FastAPI(
        title="OpenFitTrack API",
        version="0.1.0",
        lifespan=lifespan,
        # Operation ids like "get_day_summary" give a readable generated TypeScript client.
        generate_unique_id_function=lambda route: route.name,
    )

    def get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    SessionDep = Annotated[Session, Depends(get_session)]

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, error: ValueError) -> JSONResponse:
        # core raises ValueError for invalid input (e.g. an end date before the start date)
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.get("/api/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/day")
    def get_day_summary(
        session: SessionDep,
        date: Annotated[dt.date | None, Query(description="YYYY-MM-DD, default today")] = None,
    ) -> DaySummary:
        """One day: logged food, totals, and the totals against that day's goal."""
        return reports.day_summary(session, date or today())

    @app.get("/api/period")
    def get_period_summary(
        session: SessionDep,
        start_date: Annotated[
            dt.date | None, Query(description="YYYY-MM-DD, default 6 days before the end date")
        ] = None,
        end_date: Annotated[dt.date | None, Query(description="YYYY-MM-DD, default today")] = None,
    ) -> PeriodSummary:
        """Daily totals and averages over a period (at most 366 days), against the goal."""
        end = end_date or today()
        return reports.period_summary(session, start_date or end - dt.timedelta(days=6), end)

    @app.get("/api/weight")
    def get_weight_trend(
        session: SessionDep,
        days: Annotated[int, Query(ge=1, le=730, description="How many days back")] = 90,
    ) -> WeightTrend:
        """Weights with an exponential moving average trend and the 7-day change."""
        return reports.weight_summary(session, days, today())

    @app.get("/api/goals")
    def get_goals(session: SessionDep) -> GoalsInfo:
        """The goal that applies today and the goal history."""
        return reports.goals_summary(session, today())

    @app.get("/api/foods/search")
    def search_foods(
        session: SessionDep,
        q: Annotated[str, Query(min_length=1, description="Food name")],
        limit: Annotated[int, Query(ge=1, le=20)] = 5,
    ) -> FoodSearchResult:
        """Find foods in the database. Values are per 100 g."""
        return reports.food_search(session, q, limit)

    return app
