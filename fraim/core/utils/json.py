# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""JSON parsing utility methods"""

import json
import re
from typing import Any

# Loosely based on https://github.com/OpenInterpreter/open-interpreter/blob/5b6080fae1f8c68938a1e4fa8667e3744084ee21/interpreter/utils/parse_partial_json.py
# MIT License


def parse_json_tolerant(s: str) -> Any:
    """Parse a JSON string, but allowing for
       - missing newline escapes in string literals
       - missing closing delimiters

    Args:
        s: The JSON string to parse

    Returns:
        The parsed JSON object

    Raises:
        json.JSONDecodeError: If the JSON string is invalid and could not be fixed
    """
    # Try to parse as valid JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Walk through the string,
    #   - tracking unclosed delimiters
    #   - in-string context
    #
    # Inside a string, escape any
    #   - literal newlines
    #   - literal tabs
    #   - any quote that does not appear to end the string
    #
    # A quote appears to end the string if the next non-whitespace character is
    # EOF, comma, colon, or a closing delimiter.

    # Initialize the state variables
    stack = []
    in_string = False
    in_escape = False
    new_s = ""

    # Walk through the string
    for idx, char in enumerate(s):
        if in_string:
            # Add escaped if needed
            if char == '"' and not in_escape:
                if is_string_end(s, idx):
                    in_string = False
                else:
                    char = '\\"'
            elif char == "\n" and not in_escape:
                char = "\\n"
            elif char == "\t" and not in_escape:
                char = "\\t"
            elif char == "\\":
                in_escape = not in_escape
            else:
                in_escape = False
        elif char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char == "}" or char == "]":
            if not stack:
                raise json.JSONDecodeError(f"Unexpected closing delimiter ${char}.", s, idx)
            if stack[-1] == char:
                stack.pop()
            else:
                raise json.JSONDecodeError(f"Mismatched closing delimiter ${char}. Expected ${stack[-1]}.", s, idx)

        new_s += char

    # Close any open string
    if in_string:
        new_s += '"'

    # Close any open delimiters
    for char in reversed(stack):
        new_s += char

    # Try to parse the result
    return json.loads(new_s)


_json_code_block_re = re.compile(r"```(json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json_markdown(s: str) -> Any | None:
    """Parse a JSON string that might be embedded in a Markdown code block

    Args:
        s: The JSON string to parse

    Returns:
        The parsed JSON object

    Raises:
        json.JSONDecodeError: If the JSON string is invalid and could not be fixed
    """
    # Try to parse as plain JSON
    try:
        return parse_json_tolerant(s)
    except json.JSONDecodeError as e:
        # Try to find json within the a code block
        match = _json_code_block_re.search(s)
        if match:
            return parse_json_tolerant(match.group(2))
        # Otherwise, re-raise the original error
        raise e


def is_string_end(s: str, i: int) -> bool:
    """Check if the next non-whitespace character is the end of the string"""

    # Find the next non-whitespace character
    i += 1
    while i < len(s) and s[i].isspace():
        i += 1

    # If we're at the end of the string, return True
    if i >= len(s):
        return True

    # Are we followed by a character that is valid after a string in JSON?
    return s[i] in [",", ":", "}", "]"]
