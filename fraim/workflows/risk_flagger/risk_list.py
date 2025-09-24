# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Risk list management module for the Risk Flagger workflow.
Handles loading, parsing, and managing lists of risks to be analyzed.
"""

import json
import os

import yaml


def load_risks_from_file(filepath: str) -> dict[str, str]:
    """Load risks from a JSON or YAML file.

    Args:
        filepath: Path to the JSON or YAML file containing risk name to description mappings

    Returns:
        Dictionary of risk name to description mappings

    Raises:
        FileNotFoundError: If the specified file does not exist
        ValueError: If the file format is not supported or content is invalid
        Exception: If there are any other errors reading the file
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read().strip()

        # Determine file format from extension
        file_ext = os.path.splitext(filepath)[1].lower()

        if file_ext == ".json":
            return parse_risks_from_text(content)
        if file_ext in [".yaml", ".yml"]:
            try:
                risks = yaml.safe_load(content)
                if not isinstance(risks, dict):
                    raise ValueError("YAML must contain a dictionary/mapping")

                # Ensure all keys and values are strings
                result = {}
                for key, value in risks.items():
                    if not isinstance(key, str):
                        raise ValueError(f"All risk names must be strings, got {type(key)} for key {key}")
                    if not isinstance(value, str):
                        raise ValueError(f"All risk descriptions must be strings, got {type(value)} for key {key}")
                    result[key] = value

                return result
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {e}")
        else:
            # Try to parse as JSON if no recognized extension
            return parse_risks_from_text(content)

    except FileNotFoundError:
        raise FileNotFoundError(f"Risk file not found: {filepath}")
    except Exception as e:
        raise Exception(f"Error reading risk file {filepath}: {e}")


def parse_risks_from_text(text: str) -> dict[str, str]:
    """Parse risks from raw JSON text.

    Args:
        text: Raw JSON string containing risk name to description mappings

    Returns:
        Dictionary of risk name to description mappings

    Raises:
        json.JSONDecodeError: If the text is not valid JSON
        ValueError: If the JSON doesn't contain a dictionary of strings
    """
    text = text.strip()
    if not text:
        return {}

    try:
        risks = json.loads(text)
        if not isinstance(risks, dict):
            raise ValueError("JSON must contain a dictionary/object")

        # Ensure all keys and values are strings
        result = {}
        for key, value in risks.items():
            if not isinstance(key, str):
                raise ValueError(f"All risk names must be strings, got {type(key)} for key {key}")
            if not isinstance(value, str):
                raise ValueError(f"All risk descriptions must be strings, got {type(value)} for key {key}")
            result[key] = value

        return result
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON format: {e}", e.doc, e.pos)


def build_risks_list(
    default_risks: dict[str, str],
    custom_risk_list_action: str = "append",
    custom_risk_list_filepath: str | None = None,
    custom_risk_list_json: str | None = None,
) -> dict[str, str]:
    """Build the final dictionary of risks to consider based on input configuration.

    Args:
        default_risks: Base dictionary of risks to start with
        custom_risk_list_action: Whether to 'append' or 'replace' the default risks
        custom_risk_list_filepath: Optional path to JSON/YAML file containing additional risks
        custom_risk_list_json: Optional JSON string containing additional risks

    Returns:
        Final dictionary of risks with duplicates removed (case-insensitive)
    """
    # Start with default risks
    risks = default_risks.copy()

    # Get additional risks from file or text
    additional_risks = {}
    if custom_risk_list_filepath:
        additional_risks.update(load_risks_from_file(custom_risk_list_filepath))

    if custom_risk_list_json:
        additional_risks.update(parse_risks_from_text(custom_risk_list_json))

    # Apply the custom_risk_list action
    if custom_risk_list_action == "replace" and additional_risks:
        risks = additional_risks
    elif custom_risk_list_action == "append":
        risks.update(additional_risks)

    # Remove duplicates while preserving order (case-insensitive)
    unique_risks = {}
    seen_names = set()
    for name, description in risks.items():
        name_lower = name.lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_risks[name] = description

    return unique_risks


def format_risks_for_prompt(risks: dict[str, str]) -> str:
    """Format risks dictionary for inclusion in the prompt using XML-style tags.

    Args:
        risks: Dictionary of risk names to descriptions

    Returns:
        Formatted string with each risk in XML format: <risk_name>description</risk_name>
    """
    formatted_risks = []
    for name, description in risks.items():
        formatted_risks.append(f"  <{name}>\n    {description}\n  </{name}>")
    return "\n".join(formatted_risks)
