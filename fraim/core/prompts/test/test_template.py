# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for PromptTemplate"""

import os
import tempfile

import pytest

from fraim.core.prompts.template import PromptTemplate, PromptTemplateError


class TestPromptTemplate:
    """Test cases for PromptTemplate"""

    def test_from_string_simple(self) -> None:
        """Test creating template from simple string"""
        template = PromptTemplate.from_string("Hello {{ name }}!")
        assert "name" in template.used_variables()

        result, unused = template.render({"name": "World"})
        assert result == "Hello World!"
        assert unused == set()

    def test_from_string_with_inputs(self) -> None:
        """Test creating template with pre-bound inputs"""
        template = PromptTemplate.from_string("Hello {{ name }}!", {"name": "Alice"})

        result, unused = template.render({})
        assert result == "Hello Alice!"
        assert unused == set()

    def test_from_file_success(self) -> None:
        """Test loading template from file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello {{ name }}!")
            temp_path = f.name

        try:
            template = PromptTemplate.from_file(temp_path)
            result, unused = template.render({"name": "File"})
            assert result == "Hello File!"
        finally:
            os.unlink(temp_path)

    def test_from_file_not_found(self) -> None:
        """Test loading non-existent file raises error"""
        with pytest.raises(PromptTemplateError, match="Could not find template file"):
            PromptTemplate.from_file("nonexistent.txt")

    def test_from_string_invalid_syntax(self) -> None:
        """Test invalid Jinja2 syntax raises error"""
        with pytest.raises(PromptTemplateError, match="Invalid syntax"):
            PromptTemplate.from_string("Hello {{ name")

    def test_used_variables(self) -> None:
        """Test used_variables returns correct set"""
        template = PromptTemplate.from_string("{{ a }} and {{ b }} but not {{ c }}")
        assert template.used_variables() == {"a", "b", "c"}

    def test_used_variables_empty(self) -> None:
        """Test template with no variables"""
        template = PromptTemplate.from_string("No variables here")
        assert template.used_variables() == set()

    def test_render_all_variables_provided(self) -> None:
        """Test rendering with all variables provided"""
        template = PromptTemplate.from_string("{{ greeting }} {{ name }}!")

        result, unused = template.render({"greeting": "Hello", "name": "World"})
        assert result == "Hello World!"
        assert unused == set()

    def test_render_extra_variables(self) -> None:
        """Test rendering with extra unused variables"""
        template = PromptTemplate.from_string("Hello {{ name }}!")

        result, unused = template.render({"name": "World", "extra": "unused"})
        assert result == "Hello World!"
        assert unused == {"extra"}

    def test_render_missing_variable(self) -> None:
        """Test rendering with missing required variable raises error"""
        template = PromptTemplate.from_string("Hello {{ name }}!")

        with pytest.raises(PromptTemplateError, match="Missing input"):
            template.render({})

    def test_render_partial(self) -> None:
        """Test partial rendering creates new template"""
        template = PromptTemplate.from_string("{{ a }} {{ b }}")
        partial = template.render_partial({"a": "Hello"})

        # Original template unchanged
        assert template._inputs == {}

        # New template has bound input
        result, unused = partial.render({"b": "World"})
        assert result == "Hello World"
        assert unused == set()

    def test_render_partial_override(self) -> None:
        """Test partial rendering overrides existing inputs"""
        template = PromptTemplate.from_string("{{ name }}", {"name": "Alice"})
        partial = template.render_partial({"name": "Bob"})

        result, unused = partial.render({})
        assert result == "Bob"
        assert unused == set()

    def test_complex_template(self) -> None:
        """Test complex template with loops and conditionals"""
        template_str = """
        {% for item in items %}
        - {{ item }}
        {% endfor %}
        {% if show_footer %}
        Footer: {{ footer }}
        {% endif %}
        """.strip()

        template = PromptTemplate.from_string(template_str)

        result, unused = template.render({"items": ["apple", "banana"], "show_footer": True, "footer": "Done"})

        expected = "\n        - apple\n        \n        - banana\n        \n        \n        Footer: Done\n        "
        assert result == expected
        assert unused == set()

    def test_empty_template(self) -> None:
        """Test empty template"""
        template = PromptTemplate.from_string("")

        result, unused = template.render({})
        assert result == ""
        assert unused == set()

    def test_template_with_whitespace(self) -> None:
        """Test template with only whitespace"""
        template = PromptTemplate.from_string("   \n  \t  ")

        result, unused = template.render({})
        assert result == "   \n  \t  "
        assert unused == set()


class TestMergeInputs:
    """Test cases for merge_inputs helper function"""

    def test_merge_inputs_basic(self) -> None:
        """Test basic merging of inputs"""
        from fraim.core.prompts.template import merge_inputs

        result = merge_inputs({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_inputs_override(self) -> None:
        """Test that new inputs override existing ones"""
        from fraim.core.prompts.template import merge_inputs

        result = merge_inputs({"a": 1, "b": 2}, {"b": 3, "c": 4})
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_inputs_empty(self) -> None:
        """Test merging with empty dictionaries"""
        from fraim.core.prompts.template import merge_inputs

        assert merge_inputs({}, {"a": 1}) == {"a": 1}
        assert merge_inputs({"a": 1}, {}) == {"a": 1}
        assert merge_inputs({}, {}) == {}
