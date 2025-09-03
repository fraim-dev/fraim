# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Functions for simplifying JSON schemas to be compatible with LLM APIs."""

import copy
from typing import Any


def simplify_json_schema(schema: Any) -> dict[str, Any] | Any:
    """Simplify a JSON schema by resolving anyOf constructs.

    Rules:
    - If anyOf has only a single item, merge it into its parent
    - If anyOf has multiple items, merge the sibling properties into each element

    This makes schemas compatible with APIs like Gemini that don't support anyOf alongside
    other fields.

    Args:
        schema: The JSON schema to simplify (can be dict, list, or primitive)

    Returns:
        A simplified copy of the schema
    """
    if isinstance(schema, dict):
        return _simplify_schema_object(schema)
    if isinstance(schema, list):
        # Handle arrays that might contain schemas
        return [simplify_json_schema(item) for item in schema]
    # Primitive values, return as-is
    return schema


def _simplify_schema_object(schema: dict[str, Any]) -> dict[str, Any]:
    """Simplify a JSON schema object (a dictionary that represents a schema).

    This handles the core schema simplification logic including anyOf resolution.

    Args:
        schema: A dictionary representing a JSON schema

    Returns:
        A simplified copy of the schema
    """

    # Create a deep copy to avoid modifying the original
    simplified = copy.deepcopy(schema)

    # First handle anyOf at this level, before recursively simplifying nested schemas
    if "anyOf" in simplified:
        any_of_items = simplified["anyOf"]

        if len(any_of_items) == 0:
            # Empty anyOf - remove it and keep sibling properties
            del simplified["anyOf"]

        elif len(any_of_items) == 1:
            # Rule 1: Single item - merge into parent
            single_item = any_of_items[0]  # Don't simplify yet

            # Remove anyOf and deep merge the single item's properties
            del simplified["anyOf"]

            # Deep merge: parent properties take precedence over single item properties
            simplified = _deep_merge(single_item, simplified)

        else:
            # Rule 2: Multiple items - merge sibling properties into each element
            sibling_properties = {k: v for k, v in simplified.items() if k != "anyOf"}

            # Create new anyOf items with sibling properties merged in
            new_any_of_items = []
            for item in any_of_items:
                # Deep merge sibling properties into this item (item properties take precedence)
                merged_item = _deep_merge(sibling_properties, item)

                new_any_of_items.append(merged_item)

            # Replace the schema with the new anyOf structure
            simplified = {"anyOf": new_any_of_items}

    # Then recursively simplify known JSON Schema constructs
    simplified = _simplify_schema_properties(simplified)

    return simplified


def _simplify_schema_properties(schema: dict[str, Any]) -> dict[str, Any]:
    """Simplify known JSON Schema properties that can contain nested schemas.

    This method knows about JSON Schema structure and only processes schema-relevant fields.

    Args:
        schema: A dictionary representing a JSON schema

    Returns:
        Schema with simplified nested schema properties
    """
    simplified = copy.deepcopy(schema)

    # Handle properties that are maps of schemas
    map_of_schemas_properties = ["properties", "patternProperties", "dependencies", "definitions", "$defs", "defs"]
    for key in map_of_schemas_properties:
        if key in simplified and isinstance(simplified[key], dict):
            simplified_map = {}
            for prop_name, prop_value in simplified[key].items():
                simplified_map[prop_name] = simplify_json_schema(prop_value)
            simplified[key] = simplified_map

    # Handle properties that are direct schemas or arrays of schemas
    direct_schema_properties = [
        "additionalProperties",
        "items",
        "additionalItems",
        "allOf",
        "oneOf",
        "anyOf",
        "not",
        "if",
        "then",
        "else",
    ]
    for key in direct_schema_properties:
        if key in simplified:
            simplified[key] = simplify_json_schema(simplified[key])

    return simplified


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with update values taking precedence.

    Args:
        base: The base dictionary to merge into
        update: The dictionary with values to merge in (takes precedence)

    Returns:
        A new dictionary with deeply merged values
    """
    result = copy.deepcopy(base)

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts - recursively merge
            result[key] = _deep_merge(result[key], value)
        else:
            # Update value takes precedence
            result[key] = copy.deepcopy(value)

    return result
