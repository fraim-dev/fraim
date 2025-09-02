# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for the simplify.py module."""

from typing import Any

from fraim.util.jsonschema.simplify import _deep_merge, simplify_json_schema


class TestDeepMerge:
    """Tests for the _deep_merge function."""

    def test_simple_merge(self) -> None:
        """Test basic dictionary merging."""
        base = {"a": 1, "b": 2}
        update = {"b": 3, "c": 4}

        result = _deep_merge(base, update)

        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

        # Ensure original dictionaries are not modified
        assert base == {"a": 1, "b": 2}
        assert update == {"b": 3, "c": 4}

    def test_nested_dict_merge(self) -> None:
        """Test merging of nested dictionaries."""
        base = {"a": 1, "nested": {"x": 10, "y": 20}}
        update = {"a": 2, "nested": {"y": 30, "z": 40}, "c": 3}

        result = _deep_merge(base, update)

        expected = {"a": 2, "nested": {"x": 10, "y": 30, "z": 40}, "c": 3}
        assert result == expected

    def test_deep_copy_behavior(self) -> None:
        """Test that the merge creates deep copies."""
        base = {"nested": {"value": [1, 2, 3]}}
        update = {"other": {"list": [4, 5, 6]}}

        result = _deep_merge(base, update)

        # Modify the original lists
        base["nested"]["value"].append(999)
        update["other"]["list"].append(999)

        # Result should be unaffected
        assert result["nested"]["value"] == [1, 2, 3]
        assert result["other"]["list"] == [4, 5, 6]

    def test_non_dict_values_replaced(self) -> None:
        """Test that non-dict values are replaced, not merged."""
        base = {"a": {"nested": "value1"}}
        update = {"a": "string_value"}

        result = _deep_merge(base, update)

        expected = {"a": "string_value"}
        assert result == expected


class TestSimplifyJsonSchema:
    """Tests for the simplify_json_schema function."""

    def test_no_any_of_returns_unchanged(self) -> None:
        """Test that schemas without anyOf are returned unchanged."""
        schema = {"type": "object", "properties": {"name": {"type": "string", "description": "A name"}}}
        result = simplify_json_schema(schema)
        assert result == schema
        # Ensure it's a copy, not the same object
        assert result is not schema

    def test_single_any_of_item_merged_into_parent(self) -> None:
        """Test that anyOf with single item is merged into parent."""
        schema = {"anyOf": [{"type": "string"}], "description": "A string field", "default": "test"}

        result = simplify_json_schema(schema)

        expected = {"type": "string", "description": "A string field", "default": "test"}
        assert result == expected
        assert "anyOf" not in result

    def test_single_any_of_item_doesnt_overwrite_parent_properties(self) -> None:
        """Test that single anyOf item properties don't overwrite existing parent properties."""
        schema = {
            "anyOf": [{"type": "string", "description": "From anyOf"}],
            "description": "From parent",
            "default": "test",
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "string",
            "description": "From parent",  # Parent wins
            "default": "test",
        }
        assert result == expected

    def test_single_any_of_deep_merge_nested_objects(self) -> None:
        """Test that single anyOf item deep merges nested objects correctly."""
        schema = {
            "anyOf": [
                {"type": "object", "properties": {"field1": {"type": "string"}, "nested": {"existing": "from_anyof"}}}
            ],
            "properties": {"field2": {"type": "integer"}, "nested": {"new": "from_parent"}},
            "description": "Parent description",
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "integer"},
                "nested": {
                    "existing": "from_anyof",
                    "new": "from_parent",  # Both should be present due to deep merge
                },
            },
            "description": "Parent description",
        }
        assert result == expected

    def test_multiple_any_of_items_get_sibling_properties(self) -> None:
        """Test that multiple anyOf items get sibling properties merged in."""
        schema = {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "A nullable string", "default": None}

        result = simplify_json_schema(schema)

        expected = {
            "anyOf": [
                {"type": "string", "description": "A nullable string", "default": None},
                {"type": "null", "description": "A nullable string", "default": None},
            ]
        }
        assert result == expected

    def test_multiple_any_of_deep_merge_nested_objects(self) -> None:
        """Test that multiple anyOf items deep merge nested objects correctly."""
        schema = {
            "anyOf": [
                {"type": "object", "properties": {"field1": {"type": "string"}}},
                {"type": "object", "properties": {"field2": {"type": "integer"}}},
            ],
            "properties": {"common": {"type": "boolean"}},
            "description": "Parent description",
        }

        result = simplify_json_schema(schema)

        expected = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"common": {"type": "boolean"}, "field1": {"type": "string"}},
                    "description": "Parent description",
                },
                {
                    "type": "object",
                    "properties": {"common": {"type": "boolean"}, "field2": {"type": "integer"}},
                    "description": "Parent description",
                },
            ]
        }
        assert result == expected

    def test_nested_any_of_schemas_are_simplified(self) -> None:
        """Test that nested schemas with anyOf are also simplified."""
        schema = {
            "type": "object",
            "properties": {
                "field1": {"anyOf": [{"type": "integer"}], "description": "An integer field"},
                "field2": {
                    "type": "object",
                    "properties": {"nested": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None}},
                },
            },
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "object",
            "properties": {
                "field1": {"type": "integer", "description": "An integer field"},
                "field2": {
                    "type": "object",
                    "properties": {
                        "nested": {"anyOf": [{"type": "string", "default": None}, {"type": "null", "default": None}]}
                    },
                },
            },
        }
        assert result == expected

    def test_any_of_items_are_also_simplified_recursively(self) -> None:
        """Test that anyOf items that themselves contain anyOf are simplified."""
        schema = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"nested": {"anyOf": [{"type": "string"}], "description": "Nested field"}},
                }
            ],
            "description": "Complex nested schema",
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "object",
            "properties": {"nested": {"type": "string", "description": "Nested field"}},
            "description": "Complex nested schema",
        }
        assert result == expected

    def test_arrays_with_schemas_are_simplified(self) -> None:
        """Test that schemas inside arrays are also simplified."""
        schema = {"type": "array", "items": {"anyOf": [{"type": "string"}], "description": "Array item"}}

        result = simplify_json_schema(schema)

        expected = {"type": "array", "items": {"type": "string", "description": "Array item"}}
        assert result == expected

    def test_non_dict_values_returned_unchanged(self) -> None:
        """Test that non-dictionary values are returned unchanged."""
        assert simplify_json_schema("string") == "string"
        assert simplify_json_schema(42) == 42
        assert simplify_json_schema(None) is None
        assert simplify_json_schema([1, 2, 3]) == [1, 2, 3]

    def test_empty_any_of_handled_gracefully(self) -> None:
        """Test that empty anyOf arrays are handled gracefully."""
        schema = {"anyOf": [], "description": "Empty anyOf"}

        result = simplify_json_schema(schema)

        # Empty anyOf should be removed, keeping sibling properties
        expected = {"description": "Empty anyOf"}
        assert result == expected

    def test_deep_copy_ensures_no_mutation(self) -> None:
        """Test that the original schema is never mutated."""
        original_schema: dict[str, Any] = {
            "anyOf": [{"type": "string"}],
            "nested": {"value": [1, 2, 3]},
            "description": "Original",
        }

        # Keep a reference to the nested list
        original_list = original_schema["nested"]["value"]

        result = simplify_json_schema(original_schema)

        # Modify the result
        if "nested" in result and "value" in result["nested"]:
            result["nested"]["value"].append(999)

        # Original should be unchanged
        assert original_list == [1, 2, 3]
        assert original_schema["nested"]["value"] == [1, 2, 3]

    def test_any_of_handling_before_recursive_simplification(self) -> None:
        """Test that anyOf is handled at current level before recursively simplifying nested schemas."""
        # This test ensures that anyOf at the current level is processed first,
        # then nested anyOf structures are processed in the recursive call
        schema = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "nested_field": {
                            "anyOf": [{"type": "string"}],
                            "description": "Should be simplified in recursive call",
                        }
                    },
                }
            ],
            "description": "Parent level",
            "additional_property": "should be merged",
        }

        result = simplify_json_schema(schema)

        # The top-level anyOf should be resolved (single item merged into parent)
        # AND the nested anyOf should also be resolved
        expected = {
            "type": "object",
            "properties": {
                "nested_field": {
                    "type": "string",  # This anyOf should be simplified
                    "description": "Should be simplified in recursive call",
                }
            },
            "description": "Parent level",
            "additional_property": "should be merged",
        }
        assert result == expected

        # Ensure no anyOf remains anywhere
        result_str = str(result)
        assert "anyOf" not in result_str

    def test_complex_nested_any_of_order_of_operations(self) -> None:
        """Test complex nested anyOf structures to verify correct processing order."""
        schema = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "level1": {
                            "anyOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "level2": {"anyOf": [{"type": "string"}], "default": "deep_default"}
                                    },
                                }
                            ],
                            "description": "level1 desc",
                        }
                    },
                }
            ],
            "description": "root desc",
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {"level2": {"type": "string", "default": "deep_default"}},
                    "description": "level1 desc",
                }
            },
            "description": "root desc",
        }
        assert result == expected

        # Verify all anyOf structures are resolved
        result_str = str(result)
        assert "anyOf" not in result_str

    def test_property_named_anyof_not_simplified(self) -> None:
        """Test that object properties named 'anyOf' are not treated as schema anyOf constructs."""
        schema = {
            "type": "object",
            "properties": {
                "anyOf": {
                    "type": "string",
                    "description": "This is just a property named anyOf, not a schema construct",
                },
                "normal_field": {"type": "integer"},
            },
        }

        result = simplify_json_schema(schema)

        # The property named "anyOf" should remain unchanged
        expected = {
            "type": "object",
            "properties": {
                "anyOf": {
                    "type": "string",
                    "description": "This is just a property named anyOf, not a schema construct",
                },
                "normal_field": {"type": "integer"},
            },
        }
        assert result == expected

    def test_nested_object_with_anyof_property_name(self) -> None:
        """Test that deeply nested properties named 'anyOf' are preserved."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "anyOf": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Configuration option named anyOf",
                        }
                    },
                },
                "real_schema_anyof": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "This is a real schema anyOf",
                },
            },
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "anyOf": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Configuration option named anyOf",
                        }
                    },
                },
                "real_schema_anyof": {
                    "anyOf": [
                        {"type": "string", "description": "This is a real schema anyOf"},
                        {"type": "null", "description": "This is a real schema anyOf"},
                    ]
                },
            },
        }
        assert result == expected

    def test_handles_all_json_schema_constructs(self) -> None:
        """Test that all JSON Schema constructs with nested schemas are handled."""
        schema = {
            "type": "object",
            "properties": {"field1": {"anyOf": [{"type": "string"}], "description": "Property with anyOf"}},
            "additionalProperties": {"anyOf": [{"type": "boolean"}], "description": "Additional properties with anyOf"},
            "patternProperties": {
                "^test_": {"anyOf": [{"type": "number"}], "description": "Pattern property with anyOf"}
            },
            "items": {"anyOf": [{"type": "integer"}], "description": "Array items with anyOf"},
            "allOf": [
                {
                    "type": "object",
                    "properties": {"nested": {"anyOf": [{"type": "string"}], "description": "Nested in allOf"}},
                }
            ],
            "not": {"anyOf": [{"type": "null"}], "description": "Not schema with anyOf"},
        }

        result = simplify_json_schema(schema)

        expected = {
            "type": "object",
            "properties": {"field1": {"type": "string", "description": "Property with anyOf"}},
            "additionalProperties": {"type": "boolean", "description": "Additional properties with anyOf"},
            "patternProperties": {"^test_": {"type": "number", "description": "Pattern property with anyOf"}},
            "items": {"type": "integer", "description": "Array items with anyOf"},
            "allOf": [
                {"type": "object", "properties": {"nested": {"type": "string", "description": "Nested in allOf"}}}
            ],
            "not": {"type": "null", "description": "Not schema with anyOf"},
        }
        assert result == expected

    def test_handles_list_input(self) -> None:
        """Test that list inputs are handled correctly."""
        schema_list = [
            {"anyOf": [{"type": "string"}], "description": "First schema"},
            {
                "type": "object",
                "properties": {"field": {"anyOf": [{"type": "integer"}], "description": "Nested anyOf"}},
            },
        ]

        result = simplify_json_schema(schema_list)

        expected = [
            {"type": "string", "description": "First schema"},
            {"type": "object", "properties": {"field": {"type": "integer", "description": "Nested anyOf"}}},
        ]
        assert result == expected
