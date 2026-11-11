import json
from types import SimpleNamespace

import ollama
import pytest

from core.parsing import ParsedItem, ParseError, parse_meal


class FakeClient:
    """Stands in for ollama.Client; records the request, returns a canned response."""

    def __init__(self, content="", done_reason="stop", error=None):
        self.calls = []
        self._error = error
        self._response = SimpleNamespace(
            message=SimpleNamespace(content=content), done_reason=done_reason
        )

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


def meal_json(*items) -> str:
    return json.dumps({"items": list(items)})


def test_parses_json_into_items():
    client = FakeClient(
        meal_json(
            {"name": "kwark", "quantity": 200, "unit": "g"},
            {"name": "banaan", "quantity": 1, "unit": "piece"},
        )
    )

    meal = parse_meal("200g kwark met een banaan", client=client)

    assert meal.items == [
        ParsedItem(name="kwark", quantity=200, unit="g"),
        ParsedItem(name="banaan", quantity=1, unit="piece"),
    ]


def test_request_is_schema_constrained_and_deterministic():
    client = FakeClient(meal_json())

    parse_meal("niks", client=client, model="some-model")

    request = client.calls[0]
    assert request["model"] == "some-model"
    assert request["format"]["properties"]["items"]  # JSON schema of ParsedMeal
    assert request["options"] == {"temperature": 0}
    assert request["messages"][-1] == {"role": "user", "content": "niks"}


def test_model_comes_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "env-model")
    client = FakeClient(meal_json())

    parse_meal("kwark", client=client)

    assert client.calls[0]["model"] == "env-model"


def test_empty_text_makes_no_call():
    client = FakeClient()

    assert parse_meal("   ", client=client).items == []
    assert client.calls == []


def test_no_food_gives_empty_list():
    assert parse_meal("hallo", client=FakeClient(meal_json())).items == []


def test_connection_error_explains_how_to_start_ollama():
    client = FakeClient(error=ConnectionError("refused"))

    with pytest.raises(ParseError, match="ollama serve"):
        parse_meal("kwark", client=client)


def test_unknown_model_explains_how_to_pull_it():
    client = FakeClient(error=ollama.ResponseError("not found", 404))

    with pytest.raises(ParseError, match="ollama pull"):
        parse_meal("kwark", client=client, model="nope")


def test_other_ollama_errors_become_parse_errors():
    client = FakeClient(error=ollama.ResponseError("boom", 500))

    with pytest.raises(ParseError):
        parse_meal("kwark", client=client)


def test_truncated_response_raises():
    client = FakeClient(meal_json(), done_reason="length")

    with pytest.raises(ParseError):
        parse_meal("kwark", client=client)


@pytest.mark.parametrize(
    "content",
    [
        "not json at all",
        "",
        meal_json({"name": "kwark", "quantity": 200, "unit": "bucket"}),  # unit not allowed
        meal_json({"name": "kwark", "quantity": 0, "unit": "g"}),  # quantity must be > 0
        meal_json({"name": "", "quantity": 1, "unit": "g"}),  # empty name
        meal_json({"name": "kwark", "unit": "g"}),  # missing quantity
    ],
)
def test_invalid_output_raises(content):
    with pytest.raises(ParseError):
        parse_meal("kwark", client=FakeClient(content))
