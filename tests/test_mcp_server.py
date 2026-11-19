"""The MCP server, tested through a real in-memory MCP client."""

import pytest
from mcp import Client

from mcp_server.server import INSTRUCTIONS, create_server
from tests.seed import TODAY


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(seeded):
    server = create_server(seeded, today=lambda: TODAY)
    async with Client(server, raise_exceptions=True) as c:
        yield c


async def call(client, name, arguments=None):
    result = await client.call_tool(name, arguments or {})
    assert not result.is_error
    return result.structured_content


@pytest.mark.anyio
async def test_lists_exactly_the_five_read_only_tools(client):
    listed = await client.list_tools()

    assert {t.name for t in listed.tools} == {
        "get_day_summary",
        "get_period_summary",
        "get_weight_trend",
        "get_goals",
        "search_foods",
    }
    for tool in listed.tools:
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.open_world_hint is False


@pytest.mark.anyio
async def test_server_tells_the_model_not_to_invent_values(client):
    assert "Never invent" in INSTRUCTIONS
    assert "not medical advice" in INSTRUCTIONS or "no medical advice" in INSTRUCTIONS


@pytest.mark.anyio
async def test_day_summary_for_a_given_day(client):
    data = await call(client, "get_day_summary", {"date": "2026-01-06"})

    assert data["date"] == "2026-01-06"
    assert data["totals"]["kcal"] == 102.0  # 200 g of 51 kcal / 100 g
    assert data["goal"]["kcal"] == 2000
    assert data["progress"]["kcal"] == {
        "eaten": 102.0,
        "goal": 2000.0,
        "remaining": 1898.0,
        "percent": 5.1,
    }
    (entry,) = data["entries"]
    assert (entry["time"], entry["food"], entry["amount_g"]) == ("08:00", "Kwark magere", 200.0)
    assert data["note"] is None


@pytest.mark.anyio
async def test_day_summary_defaults_to_today(client):
    data = await call(client, "get_day_summary")

    assert data["date"] == "2026-01-12"
    assert data["totals"]["kcal"] == 51.0


@pytest.mark.anyio
async def test_empty_day_explains_that_unlogged_is_not_zero_intake(client):
    data = await call(client, "get_day_summary", {"date": "2026-01-07"})

    assert data["entries"] == []
    assert "does not mean nothing was eaten" in data["note"]


@pytest.mark.anyio
async def test_period_summary_counts_only_logged_days_in_the_average(client):
    data = await call(
        client, "get_period_summary", {"start_date": "2026-01-06", "end_date": "2026-01-12"}
    )

    assert (data["days_in_period"], data["days_logged"]) == (7, 3)
    assert [d["date"] for d in data["daily"]] == ["2026-01-06", "2026-01-08", "2026-01-12"]
    assert data["average_per_logged_day"]["kcal"] == 85.0  # (102 + 102 + 51) / 3, not / 7
    assert data["average_vs_goal"]["kcal"]["goal"] == 2000.0
    assert "3 of 7 days" in data["note"]


@pytest.mark.anyio
async def test_period_summary_defaults_to_the_last_seven_days(client):
    data = await call(client, "get_period_summary")

    assert (data["start_date"], data["end_date"]) == ("2026-01-06", "2026-01-12")


@pytest.mark.anyio
async def test_weight_trend_uses_the_full_history_for_the_window(seeded):
    server = create_server(seeded, today=lambda: TODAY)
    async with Client(server, raise_exceptions=True) as client:
        full = await call(client, "get_weight_trend", {"days": 90})
        window = await call(client, "get_weight_trend", {"days": 5})

    assert [p["date"] for p in full["points"]] == ["2026-01-01", "2026-01-08", "2026-01-12"]
    assert [p["date"] for p in window["points"]] == ["2026-01-08", "2026-01-12"]
    # the trend of a point does not depend on the window
    assert window["points"][-1]["trend_kg"] == full["points"][-1]["trend_kg"]
    assert full["measurements_total"] == 3
    assert full["latest_weight_kg"] == 80.5
    assert full["target_weight_kg"] == 78
    assert full["trend_change_7d_kg"] is not None


@pytest.mark.anyio
async def test_weight_trend_without_data(memory_engine):
    server = create_server(memory_engine, today=lambda: TODAY)
    async with Client(server, raise_exceptions=True) as client:
        data = await call(client, "get_weight_trend")

    assert data["points"] == []
    assert data["latest_weight_kg"] is None
    assert data["trend_change_7d_kg"] is None


@pytest.mark.anyio
async def test_goals(client):
    data = await call(client, "get_goals")

    assert data["current"]["kcal"] == 2000
    assert len(data["history"]) == 1


@pytest.mark.anyio
async def test_search_foods(client):
    data = await call(client, "search_foods", {"query": "banaan", "limit": 3})

    assert data["query"] == "banaan"
    assert data["results"][0]["name"] == "Banaan"
    assert data["results"][0]["kcal"] == 90.0


@pytest.mark.anyio
async def test_invalid_arguments_are_reported_as_tool_errors(seeded):
    server = create_server(seeded, today=lambda: TODAY)
    async with Client(server) as client:  # raise_exceptions off: errors come back as results
        bad_range = await client.call_tool(
            "get_period_summary", {"start_date": "2026-01-12", "end_date": "2026-01-06"}
        )
        bad_limit = await client.call_tool("search_foods", {"query": "x", "limit": 500})
        bad_date = await client.call_tool("get_day_summary", {"date": "yesterday"})

    assert bad_range.is_error
    assert bad_limit.is_error
    assert bad_date.is_error
