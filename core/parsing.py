"""Parse free-text meal descriptions into structured items with a local LLM (Ollama).

The model only extracts what the user said (name, quantity, unit). It never produces
nutrition values: those come from the database (see core.matching / core.nutrition).
"""

import os
from typing import Literal

import ollama
from pydantic import BaseModel, Field, ValidationError

DEFAULT_MODEL = "gemma3:12b"  # override with the OLLAMA_MODEL environment variable

Unit = Literal["g", "kg", "ml", "l", "piece", "tbsp", "tsp", "slice", "cup", "portion"]

SYSTEM_PROMPT = """\
You extract the foods and drinks from a short meal description (usually Dutch) and \
answer with JSON that matches the given schema.

Rules:
- Record every food or drink the user says they ate or drank, one item each.
- name: the food in Dutch, singular, lowercase, without quantity or unit. Keep words \
that change the product, e.g. "magere kwark", "volkoren brood".
- quantity and unit: exactly as stated by the user. Convert only spelled-out numbers \
("twee" -> 2, "een halve" -> 0.5).
- unit: map the Dutch word to the allowed unit:
  gram, g -> g; kilo, kilogram -> kg; milliliter, ml -> ml; liter, l -> l;
  eetlepel, el -> tbsp; theelepel, tl -> tsp;
  plak, plakje, sneetje, snee -> slice; kop, kopje, mok -> cup;
  glas, kom, bakje, schaal, bord, handje, handvol, scheutje, portie -> portion;
  stuk, stuks, or a countable food without unit ("een banaan") -> piece;
  anything else without a unit (e.g. "wat rijst") -> portion.
  Example: "4 plakjes ham en een mok thee" -> ham 4 slice, thee 1 cup.
- Do not repeat the unit word in the name ("sneetje brood" -> name "brood").
- Never convert to grams and never guess a weight. Never state calories or nutrition \
values.
- Ignore anything that is not food or drink. If there is no food at all, return an \
empty items list.
"""


class ParsedItem(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: Unit


class ParsedMeal(BaseModel):
    items: list[ParsedItem]


class ParseError(Exception):
    """The meal could not be parsed (model unavailable or unusable response)."""


def parse_meal(
    text: str, client: ollama.Client | None = None, model: str | None = None
) -> ParsedMeal:
    """Parse a meal description such as "200g kwark met een banaan" into items.

    The Ollama server comes from OLLAMA_HOST (default http://localhost:11434) and the
    model from `model` or OLLAMA_MODEL. Pass your own `client` to substitute it in tests.
    """
    if not text.strip():
        return ParsedMeal(items=[])

    client = client or ollama.Client()
    model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            format=ParsedMeal.model_json_schema(),  # constrains the output to the schema
            think=False,
            options={"temperature": 0},
        )
    except ConnectionError as error:
        raise ParseError(
            "Cannot reach Ollama. Is it running? Start it with `ollama serve`."
        ) from error
    except ollama.ResponseError as error:
        if error.status_code == 404:
            raise ParseError(f"Model '{model}' not found. Run `ollama pull {model}`.") from error
        raise ParseError(f"Ollama error: {error}") from error

    if response.done_reason == "length":
        raise ParseError("The model response was cut off.")

    try:
        return ParsedMeal.model_validate_json(response.message.content or "")
    except ValidationError as error:
        raise ParseError(f"Invalid parse result: {error}") from error
