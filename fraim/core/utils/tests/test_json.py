# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for JSON parsing utility methods"""

import json
from typing import Any

import pytest

from fraim.core.utils.json import is_string_end, parse_json_markdown, parse_json_tolerant


class TestParseJsonTolerant:
    """Test cases for parse_json_tolerant function"""

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"key": "value"}', {"key": "value"}),
            ('{"number": 42}', {"number": 42}),
            ('{"boolean": true}', {"boolean": True}),
            ('{"null": null}', {"null": None}),
            ('{"array": [1, 2, 3]}', {"array": [1, 2, 3]}),
            ('{"nested": {"inner": "value"}}', {"nested": {"inner": "value"}}),
            ("[1, 2, 3]", [1, 2, 3]),
            ("[]", []),
            ("{}", {}),
            ('"simple string"', "simple string"),
            ("42", 42),
            ("true", True),
            ("false", False),
            ("null", None),
        ],
    )
    def test_valid_json_strings(self, json_str: str, expected: Any) -> None:
        """Test that valid JSON strings are parsed correctly"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"message": "foo="bar""}', {"message": 'foo="bar"'}),
        ],
    )
    def test_missing_quote_escapes(self, json_str: str, expected: Any) -> None:
        """Test handling of literal newlines in strings"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"message": "line1\nline2"}', {"message": "line1\nline2"}),
            ('{"multiline": "first\nsecond\nthird"}', {"multiline": "first\nsecond\nthird"}),
            ('["item1\nwith newline", "item2"]', ["item1\nwith newline", "item2"]),
        ],
    )
    def test_missing_newline_escapes(self, json_str: str, expected: Any) -> None:
        """Test handling of literal newlines in strings"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"message": "col1\tcol2"}', {"message": "col1\tcol2"}),
            ('{"indented": "\tindented text"}', {"indented": "\tindented text"}),
            ('["item1\twith tab", "item2"]', ["item1\twith tab", "item2"]),
        ],
    )
    def test_missing_tab_escapes(self, json_str: str, expected: Any) -> None:
        """Test handling of literal tabs in strings"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"key": "value"', {"key": "value"}),
            ('{"outer": {"inner": "value"', {"outer": {"inner": "value"}}),
            ('{"a": 1, "b": {"c": 2', {"a": 1, "b": {"c": 2}}),
        ],
    )
    def test_missing_closing_braces(self, json_str: str, expected: Any) -> None:
        """Test handling of missing closing braces"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ("[1, 2, 3", [1, 2, 3]),
            ('{"array": [1, 2, 3', {"array": [1, 2, 3]}),
            ('[{"key": "value"', [{"key": "value"}]),
            ("[[1, 2], [3, 4", [[1, 2], [3, 4]]),
        ],
    )
    def test_missing_closing_brackets(self, json_str: str, expected: Any) -> None:
        """Test handling of missing closing brackets"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"key": "value', {"key": "value"}),
            ('{"incomplete": "text without end', {"incomplete": "text without end"}),
            ('[1, "incomplete string', [1, "incomplete string"]),
        ],
    )
    def test_missing_closing_quotes(self, json_str: str, expected: Any) -> None:
        """Test handling of missing closing quotes"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str",
        [
            '{"message": "He said "hello""}',
            '{"quote": "She said "yes" to the question"}',
        ],
    )
    def test_quotes_within_strings(self, json_str: str) -> None:
        """Test handling of quotes that should be escaped within strings"""
        result = parse_json_tolerant(json_str)
        # The function should detect that the middle quotes are not string terminators
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            # Missing closing brace + literal newline
            ('{"message": "line1\nline2"', {"message": "line1\nline2"}),
            # Missing closing bracket + literal tab
            ('["item1\titem2"', ["item1\titem2"]),
            # Nested missing delimiters
            ('{"outer": {"inner": [1, 2, 3', {"outer": {"inner": [1, 2, 3]}}),
        ],
    )
    def test_complex_mixed_issues(self, json_str: str, expected: Any) -> None:
        """Test handling of multiple issues in one JSON string"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            # Single quote
            ('"', ""),
            # Single brace
            ("{", {}),
            # Single bracket
            ("[", []),
        ],
    )
    def test_edge_cases_that_parse(self, json_str: str, expected: Any) -> None:
        """Test edge cases that can be fixed and parsed"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str",
        [
            # Empty string
            "",
            # Just whitespace
            "   ",
            # Mismatched delimiters now also raise errors
            '{"key": "value"]',
            '[{"key": "value"})',
        ],
    )
    def test_edge_cases_that_raise_error(self, json_str: str) -> None:
        """Test edge cases that cannot be fixed and raise JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            parse_json_tolerant(json_str)

    @pytest.mark.parametrize(
        "json_str",
        [
            '{"message": "line1\\nline2"}',
            '{"message": "col1\\tcol2"}',
            '{"quote": "He said \\"hello\\""}',
        ],
    )
    def test_already_escaped_content(self, json_str: str) -> None:
        """Test that already properly escaped JSON is not double-escaped"""
        result = parse_json_tolerant(json_str)
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        "json_str",
        [
            "invalid json",
            '{"key": invalid_value}',
            '{key: "value"}',  # unquoted key
            "{'key': 'value'}",  # single quotes
            '{"key": "value",}',  # trailing comma (though some parsers allow this)
        ],
    )
    def test_invalid_json_raises_error(self, json_str: str) -> None:
        """Test that truly invalid JSON raises JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            parse_json_tolerant(json_str)

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('  {"key": "value"}  ', {"key": "value"}),
            ('{\n  "key": "value"\n}', {"key": "value"}),
            ("[\n  1,\n  2,\n  3\n]", [1, 2, 3]),
        ],
    )
    def test_whitespace_handling(self, json_str: str, expected: Any) -> None:
        """Test handling of whitespace in various contexts"""
        result = parse_json_tolerant(json_str)
        assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"message": "Hello 世界"}', {"message": "Hello 世界"}),
            ('{"emoji": "🚀 rocket"}', {"emoji": "🚀 rocket"}),
            ('["café", "naïve"]', ["café", "naïve"]),
        ],
    )
    def test_unicode_content(self, json_str: str, expected: Any) -> None:
        """Test handling of unicode content"""
        result = parse_json_tolerant(json_str)
        assert result == expected


class TestIsStringEnd:
    """Test cases for is_string_end helper function"""

    @pytest.mark.parametrize(
        "test_str,quote_idx,expected",
        [
            # (string, quote_index, expected_result)
            ('{"key": "value"}', 5, True),  # Quote after "key" before colon
            # Quote after "value" before closing brace
            ('{"key": "value"}', 14, True),
            ('["item1", "item2"]', 7, True),  # Quote after "item1" before comma
            # Quote after "item" before closing bracket
            ('["item"]', 6, True),
            ('"text"', 5, True),  # Quote at end of string
            # Quote within string - middle of "hello"
            ('{"text": "He said "hello""}', 18, False),
            # Quote ending the whole string
            ('{"text": "He said "hello""}', 25, True),
        ],
    )
    def test_string_end_detection(self, test_str: str, quote_idx: int, expected: bool) -> None:
        """Test detection of string endings"""
        result = is_string_end(test_str, quote_idx)
        assert result == expected, f"Failed for string {test_str!r} at index {quote_idx}"

    @pytest.mark.parametrize(
        "test_str,quote_idx,expected",
        [
            # Quote after "key" before colon with spaces
            ('{"key" : "value"}', 5, True),
            # Quote after "item" before comma with spaces
            ('["item" , "item2"]', 6, True),
            # Quote after "value" before brace with spaces
            ('{"key": "value" }', 14, True),
            ('"text" ', 5, True),  # Quote at end with trailing space
        ],
    )
    def test_string_end_with_whitespace(self, test_str: str, quote_idx: int, expected: bool) -> None:
        """Test string end detection with whitespace"""
        result = is_string_end(test_str, quote_idx)
        assert result == expected, f"Failed for string {test_str!r} at index {quote_idx}"

    @pytest.mark.parametrize(
        "test_str,quote_idx,expected",
        [
            ('"', 0, True),  # Single quote at end
            ('""', 1, True),  # End of empty string
        ],
    )
    def test_string_end_edge_cases(self, test_str: str, quote_idx: int, expected: bool) -> None:
        """Test edge cases for string end detection"""
        result = is_string_end(test_str, quote_idx)
        assert result == expected, f"Failed for string {test_str!r} at index {quote_idx}"


class TestParseJsonMarkdown:
    """Test cases for parse_json_markdown function"""

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # Plain JSON (should work without markdown)
            ('{"key": "value"}', {"key": "value"}),
            ("[1, 2, 3]", [1, 2, 3]),
            ('"simple string"', "simple string"),
            ("42", 42),
            ("true", True),
            ("null", None),
        ],
    )
    def test_plain_json(self, markdown_str: str, expected: Any) -> None:
        """Test that plain JSON strings are parsed correctly"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # JSON in code blocks without language specifier
            ('```\n{"key": "value"}\n```', {"key": "value"}),
            ("```\n[1, 2, 3]\n```", [1, 2, 3]),
            ('```\n"hello world"\n```', "hello world"),
            ("```\n42\n```", 42),
            ("```\ntrue\n```", True),
            ("```\nnull\n```", None),
        ],
    )
    def test_code_blocks_without_language(self, markdown_str: str, expected: Any) -> None:
        """Test JSON in code blocks without language specifier"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # JSON in code blocks with 'json' language specifier
            ('```json\n{"key": "value"}\n```', {"key": "value"}),
            ("```json\n[1, 2, 3]\n```", [1, 2, 3]),
            ('```json\n"hello world"\n```', "hello world"),
            ("```json\n42\n```", 42),
            ("```json\ntrue\n```", True),
            ("```json\nnull\n```", None),
        ],
    )
    def test_code_blocks_with_json_language(self, markdown_str: str, expected: Any) -> None:
        """Test JSON in code blocks with 'json' language specifier"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # Complex JSON objects
            (
                '```json\n{"name": "John", "age": 30, "city": "New York"}\n```',
                {"name": "John", "age": 30, "city": "New York"},
            ),
            ('```\n{"nested": {"inner": {"deep": "value"}}}\n```', {"nested": {"inner": {"deep": "value"}}}),
            ('```json\n{"array": [{"id": 1}, {"id": 2}]}\n```', {"array": [{"id": 1}, {"id": 2}]}),
        ],
    )
    def test_complex_json_in_code_blocks(self, markdown_str: str, expected: Any) -> None:
        """Test complex JSON structures in code blocks"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # Code blocks with extra whitespace
            ('```   \n  {"key": "value"}  \n  ```', {"key": "value"}),
            ("```json   \n  [1, 2, 3]  \n  ```", [1, 2, 3]),
            ('```\n\n{"spaced": true}\n\n```', {"spaced": True}),
        ],
    )
    def test_code_blocks_with_whitespace(self, markdown_str: str, expected: Any) -> None:
        """Test code blocks with extra whitespace"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str",
        [
            # Invalid JSON in code blocks - these will raise JSONDecodeError
            "```json\n{invalid json}\n```",
            '```\n{key: "value"}\n```',  # unquoted key
            '```json\n{"key": invalid_value}\n```',
            # Empty code blocks - these will raise JSONDecodeError
            "```\n\n```",
            "```json\n\n```",
        ],
    )
    def test_invalid_json_in_code_blocks_raises_error(self, markdown_str: str) -> None:
        """Test invalid JSON in code blocks raises JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            parse_json_markdown(markdown_str)

    @pytest.mark.parametrize(
        "markdown_str",
        [
            # No code blocks - these will raise the original JSONDecodeError
            "just some text",
            "no code blocks here",
        ],
    )
    def test_no_code_blocks_raises_error(self, markdown_str: str) -> None:
        """Test text without code blocks raises JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            parse_json_markdown(markdown_str)

    @pytest.mark.parametrize(
        "markdown_str",
        [
            # Plain invalid JSON (not in code blocks) should raise error
            "invalid json",
            '{"key": invalid_value}',
            '{key: "value"}',  # unquoted key
            "{'key': 'value'}",  # single quotes
        ],
    )
    def test_plain_invalid_json_raises_error(self, markdown_str: str) -> None:
        """Test that plain invalid JSON (not in code blocks) raises JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            parse_json_markdown(markdown_str)

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # Markdown with text around code blocks
            ('Here is some JSON:\n```json\n{"key": "value"}\n```\nEnd of text.', {"key": "value"}),
            ("# Title\n\nSome text\n\n```\n[1, 2, 3]\n```\n\nMore text.", [1, 2, 3]),
            ('Before\n```json\n"hello"\n```\nAfter', "hello"),
        ],
    )
    def test_markdown_with_surrounding_text(self, markdown_str: str, expected: Any) -> None:
        """Test JSON extraction from markdown with surrounding text"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # Multiple code blocks - should find the first one
            ('```json\n{"first": true}\n```\n\n```json\n{"second": true}\n```', {"first": True}),
            ("```\n[1, 2]\n```\nSome text\n```\n[3, 4]\n```", [1, 2]),
        ],
    )
    def test_multiple_code_blocks(self, markdown_str: str, expected: Any) -> None:
        """Test that the first code block is used when multiple exist"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            # Unicode content in code blocks
            ('```json\n{"message": "Hello 世界"}\n```', {"message": "Hello 世界"}),
            ('```\n["café", "naïve"]\n```', ["café", "naïve"]),
            ('```json\n{"emoji": "🚀 rocket"}\n```', {"emoji": "🚀 rocket"}),
        ],
    )
    def test_unicode_in_code_blocks(self, markdown_str: str, expected: Any) -> None:
        """Test Unicode content in code blocks"""
        result = parse_json_markdown(markdown_str)
        assert result == expected

    @pytest.mark.parametrize(
        "markdown_str,expected",
        [
            ('```json\n{"key": "value with "embedded" quotes"}\n```', {"key": 'value with "embedded" quotes'}),
        ],
    )
    def test_tolerant_parsing_of_malformed_json(self, markdown_str: str, expected: Any) -> None:
        """Test tolerant parsing of malformed JSON"""
        result = parse_json_markdown(markdown_str)
        assert result == expected
