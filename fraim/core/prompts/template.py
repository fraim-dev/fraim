# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError, meta
from jinja2.environment import Template as JinjaTemplate

jinja_env = Environment(
    # raise an error if a variable is not defined
    undefined=StrictUndefined
)


class PromptTemplateError(Exception):
    """An error occurred while loading a prompt template."""


class PromptTemplate:
    @classmethod
    def from_yaml(cls, yaml_path: str, inputs: dict[str, Any] | None = None) -> dict[str, "PromptTemplate"]:
        """Load a set of prompt templates from a YAML file.

        The yaml file should be a dictionary of prompt templates, where the key is
        the name of the prompt template and the value is the template string.

        Args:
            yaml_path: The path to the YAML file.
            inputs: The inputs to bind to the template. This set is optional and may be incomplete.
                    Any inputs not provided will be left as placeholders in the template.

        Returns:
            A dictionary of PromptTemplate objects.
        """
        try:
            with open(yaml_path, encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)

            if not isinstance(yaml_data, dict):
                raise PromptTemplateError(f"YAML file must contain a dictionary, got {type(yaml_data)}")

            templates = {}
            for name, template_str in yaml_data.items():
                if not isinstance(template_str, str):
                    raise PromptTemplateError(f"Template '{name}' must be a string, got {type(template_str)}")
                templates[name] = cls.from_string(template_str, inputs)

            return templates

        except FileNotFoundError as e:
            raise PromptTemplateError(f"Could not find YAML file: {yaml_path}") from e
        except yaml.YAMLError as e:
            raise PromptTemplateError(f"Invalid YAML in file {yaml_path}: {e}") from e

    @classmethod
    def from_file(cls, file_path: str, inputs: dict[str, Any] | None = None) -> "PromptTemplate":
        """
        Load a prompt template from a file.

        Args:
            file_path: The path to the template file.
            inputs: The inputs to bind to the template. This set is optional and may be incomplete.
                    Any inputs not provided will be left as placeholders in the template.

        Returns:
            A PromptTemplate object.

        Raises:
            PromptTemplateError: If the template file does not exist or is invalid.
        """
        try:
            with open(file_path, encoding="utf-8") as file:
                return cls.from_string(file.read(), inputs)
        except FileNotFoundError as e:
            raise PromptTemplateError(f"Could not find template file: {file_path}") from e

    @classmethod
    def from_string(cls, template_str: str, inputs: dict[str, Any] | None = None) -> "PromptTemplate":
        """
        Initialize a prompt template from a string.

        Args:
            template_str: The template string to use.
            inputs: The inputs to bind to the template. This set is optional and may be incomplete.
                    Any inputs not provided will be left as placeholders in the template.

        Returns:
            A PromptTemplate object.

        Raises:
            PromptTemplateError: If the template string is invalid.
        """
        try:
            template = jinja_env.from_string(template_str)
            used_vars = meta.find_undeclared_variables(jinja_env.parse(template_str))
            return cls(template, used_vars, inputs)
        except TemplateSyntaxError as e:
            raise PromptTemplateError(f"Invalid syntax in template string: {template_str}") from e

    def __init__(self, template: JinjaTemplate, used_vars: set[str], inputs: dict[str, Any] | None = None):
        """
        Initialize a prompt template.

        Args:
            template_str: The template string to use.
            inputs: The inputs to bind to the template. This set is optional and may be incomplete.
                    Any inputs not provided will be left as placeholders in the template.

        Raises:
            PromptTemplateError: If the template file does not exist or the template string is invalid.
        """
        self._template = template
        self._used_vars = used_vars

        self._inputs = inputs or {}

    def used_variables(self) -> set[str]:
        return self._used_vars

    def render_partial(self, inputs: dict[str, Any]) -> "PromptTemplate":
        """
        Partially render the prompt template with the given inputs.

        Shallow merges the new inputs with the existing inputs, overriding any that were already set.

        Returns:
            A new PromptTemplate object with the updated inputs.
        """
        return self.__class__(self._template, self._used_vars, merge_inputs(self._inputs, inputs))

    def render(self, inputs: dict[str, Any]) -> tuple[str, set[str]]:
        """
        Render the prompt template with the given inputs.

        Shallow merges the new inputs with the existing inputs, overriding any that were already set.

        Args:
            inputs: The inputs to render the prompt template with.

        Returns:
            A tuple containing the rendered prompt and the unused inputs.

        Raises:
            PromptTemplateError: If any inputs required by the template were not provided.
        """
        try:
            merged_inputs = merge_inputs(self._inputs, inputs)
            rendered = self._template.render(merged_inputs)
            unused_keys = set(merged_inputs.keys()) - self._used_vars

        except UndefinedError as e:
            raise PromptTemplateError(f"Missing input: {e}") from e

        return rendered, unused_keys


def merge_inputs(inputs: dict[str, Any], new_inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Merge the new inputs with the existing inputs, overriding any that were already set.
    """
    merged = inputs.copy()
    merged.update(new_inputs)
    return merged
