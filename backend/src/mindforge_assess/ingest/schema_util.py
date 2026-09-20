"""Helpers for building strict tool schemas.

Strict tool use requires `additionalProperties: false` and a `required` array listing
*every* property. Optional values are therefore expressed as nullable types rather than
as absent keys, and extractors are told to return null instead of guessing.
"""

from __future__ import annotations

from typing import Any

Schema = dict[str, Any]


def obj(properties: dict[str, Schema], *, description: str | None = None) -> Schema:
    """An object schema with every property required and no extras allowed."""
    schema: Schema = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    if description:
        schema["description"] = description
    return schema


def arr(items: Schema, *, description: str | None = None) -> Schema:
    schema: Schema = {"type": "array", "items": items}
    if description:
        schema["description"] = description
    return schema


def string(description: str) -> Schema:
    return {"type": "string", "description": description}


def integer(description: str) -> Schema:
    return {"type": "integer", "description": description}


def nullable_string(description: str) -> Schema:
    return {"type": ["string", "null"], "description": description}


def nullable_integer(description: str) -> Schema:
    return {"type": ["integer", "null"], "description": description}


def enum(values: list[str], description: str) -> Schema:
    return {"type": "string", "enum": values, "description": description}


def tool(name: str, description: str, schema: Schema) -> Schema:
    """A tool definition with strict validation of its arguments."""
    return {
        "name": name,
        "description": description,
        "input_schema": schema,
        "strict": True,
    }
