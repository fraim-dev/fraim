# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for PydanticOutputParser"""

import pytest
from pydantic import BaseModel

from fraim.core.parsers.base import OutputParserError
from fraim.core.parsers.pydantic import PydanticOutputParser


class SimpleModel(BaseModel):
    name: str
    age: int


class NestedModel(BaseModel):
    user: SimpleModel
    active: bool


class OptionalFieldsModel(BaseModel):
    required_field: str
    optional_field: str = "default"


class TestPydanticOutputParser:
    """Test cases for PydanticOutputParser"""

    def test_init(self) -> None:
        """Test parser initialization"""
        parser = PydanticOutputParser(SimpleModel)
        assert parser.model == SimpleModel

    def test_output_prompt_instructions(self) -> None:
        """Test that output prompt instructions include the model schema"""
        parser = PydanticOutputParser(SimpleModel)
        instructions = parser.output_prompt_instructions()

        assert "Format your response as a JSON object" in instructions
        assert "name" in instructions
        assert "age" in instructions
        assert "string" in instructions
        assert "integer" in instructions

    def test_parse_valid_json_simple_model(self) -> None:
        """Test parsing valid JSON that matches the model schema"""
        parser = PydanticOutputParser(SimpleModel)
        json_text = '{"name": "John", "age": 30}'

        result = parser.parse_sync(json_text)

        assert isinstance(result, SimpleModel)
        assert result.name == "John"
        assert result.age == 30

    def test_parse_valid_json_with_markdown_formatting(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks"""
        parser = PydanticOutputParser(SimpleModel)
        json_text = """```json
        {"name": "Alice", "age": 25}
        ```"""

        result = parser.parse_sync(json_text)

        assert isinstance(result, SimpleModel)
        assert result.name == "Alice"
        assert result.age == 25

    def test_parse_nested_model(self) -> None:
        """Test parsing with nested Pydantic models"""
        parser = PydanticOutputParser(NestedModel)
        json_text = '{"user": {"name": "Bob", "age": 35}, "active": true}'

        result = parser.parse_sync(json_text)

        assert isinstance(result, NestedModel)
        assert isinstance(result.user, SimpleModel)
        assert result.user.name == "Bob"
        assert result.user.age == 35
        assert result.active is True

    def test_parse_with_optional_fields(self) -> None:
        """Test parsing model with optional fields"""
        parser = PydanticOutputParser(OptionalFieldsModel)

        # Test with only required field
        json_text = '{"required_field": "test"}'
        result = parser.parse_sync(json_text)

        assert isinstance(result, OptionalFieldsModel)
        assert result.required_field == "test"
        assert result.optional_field == "default"

        # Test with both fields
        json_text = '{"required_field": "test", "optional_field": "custom"}'
        result = parser.parse_sync(json_text)

        assert result.required_field == "test"
        assert result.optional_field == "custom"

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)
        invalid_json = '{"name": "John", "age":}'

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync(invalid_json)

        assert exc_info.value.raw_output == invalid_json
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_json_missing_required_field(self) -> None:
        """Test parsing JSON missing required fields raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)
        json_text = '{"name": "John"}'  # Missing required 'age' field

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync(json_text)

        assert exc_info.value.raw_output == json_text
        assert "Could not parse JSON into SimpleModel" in str(exc_info.value)

    def test_parse_json_wrong_field_type(self) -> None:
        """Test parsing JSON with wrong field types raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)
        json_text = '{"name": "John", "age": "thirty"}'  # age should be int

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync(json_text)

        assert exc_info.value.raw_output == json_text
        assert "Could not parse JSON into SimpleModel" in str(exc_info.value)

    def test_parse_json_extra_fields(self) -> None:
        """Test parsing JSON with extra fields (should be ignored by default)"""
        parser = PydanticOutputParser(SimpleModel)
        json_text = '{"name": "John", "age": 30, "extra": "ignored"}'

        result = parser.parse_sync(json_text)

        assert isinstance(result, SimpleModel)
        assert result.name == "John"
        assert result.age == 30
        # Extra field should be ignored

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync("")

        assert exc_info.value.raw_output == ""
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_whitespace_only(self) -> None:
        """Test parsing whitespace-only string raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)
        whitespace_text = "   \n\t   "

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync(whitespace_text)

        assert exc_info.value.raw_output == whitespace_text
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_no_code_blocks(self) -> None:
        """Test parsing text without code blocks raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)
        text = "just some random text"

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync(text)

        assert exc_info.value.raw_output == text
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_invalid_json_in_code_block(self) -> None:
        """Test parsing invalid JSON in code block raises OutputParserError"""
        parser = PydanticOutputParser(SimpleModel)
        text = "```json\n{invalid json}\n```"

        with pytest.raises(OutputParserError) as exc_info:
            parser.parse_sync(text)

        assert exc_info.value.raw_output == text
        assert "Invalid JSON" in str(exc_info.value)
