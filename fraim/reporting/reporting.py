# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import base64
import json
import logging
import os
import secrets
from datetime import datetime
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from fraim.outputs.sarif import PhysicalLocation, Region, Result, SarifReport

# TODO: Relate to the config logger
logger = logging.getLogger(__name__)

UNKNOWN = "unknown"

# SARIF severity ordering (most to least severe)
SEVERITY_ORDER = {"error": 1, "warning": 2, "note": 3, "none": 4, UNKNOWN: 5}


class Reporting:
    """Generate HTML reports from security scan results."""

    def __init__(self) -> None:
        self.jinja_env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @classmethod
    def generate_html_report(cls, sarif_report: SarifReport, repo_name: str, output_path: str) -> None:
        reporting = cls()
        html_content = reporting._generate_html_content_from_sarif(sarif_report, repo_name)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_html_content_from_sarif(self, sarif_report: SarifReport, repo_name: str) -> str:
        processed_data = self._process_sarif_data(sarif_report)
        template_context = {
            "repo_name": repo_name or "Unknown Repository",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "script_nonce": self._generate_nonce(),
            "style_nonce": self._generate_nonce(),
            "tab_data": processed_data["tab_data"],
            "detail_contents": processed_data["detail_contents"],
            "severity_options": processed_data["severity_options"],
            "type_options": processed_data["type_options"],
        }
        template = self.jinja_env.get_template("report_template.html")
        return template.render(**template_context)

    def _process_sarif_data(self, sarif_report: SarifReport) -> dict[str, Any]:
        runs = sarif_report.runs
        if not runs:
            raise ValueError("SARIF report must contain at least one run")

        tab_data = []
        detail_contents = {}
        all_severities = set()
        all_types = set()

        result_index = 0
        for run in runs:
            workflow_name = run.tool.driver.name or UNKNOWN
            results = run.results

            # Count severities for this tab
            severity_counts = {"error": 0, "warning": 0, "note": 0, "none": 0, UNKNOWN: 0}
            table_rows = []

            for result in results:
                # Extract basic data directly from SARIF
                severity = self._normalize_severity(result.level)
                vuln_type = result.properties.type or UNKNOWN
                description = result.message.text or "No description available"
                confidence = result.properties.confidence or UNKNOWN
                file_path = self._get_file_path(result)

                # Build table row
                table_rows.append(
                    {
                        "result_index": result_index,
                        "type": vuln_type,
                        "severity": severity,
                        "description": description,
                        "file": file_path,
                        "confidence": confidence,
                    }
                )

                # Build detail content for expanded view
                detail_contents[result_index] = self._build_detail_content(result)

                # Update counts and sets
                severity_counts[severity] += 1
                all_severities.add(severity)
                all_types.add(vuln_type)

                result_index += 1

            # Sort table rows by severity (most severe first)
            table_rows.sort(key=lambda row: SEVERITY_ORDER.get(row["severity"], 999))  # type: ignore[call-overload]

            tab_data.append(
                {
                    "name": workflow_name,
                    "count": len(results),
                    "results": table_rows,
                    "severity_counts": severity_counts,
                }
            )

        return {
            "tab_data": tab_data,
            "detail_contents": detail_contents,
            "severity_options": self._build_filter_options(all_severities, tab_data, "severity"),
            "type_options": self._build_filter_options(all_types, tab_data, "type"),
        }

    def _build_detail_content(self, result: Result) -> dict[str, Any]:
        description = result.message.text or ""
        code_lines = self._get_code_lines(result)
        properties = self._get_additional_properties(result)

        # If we don't have code to show but have line range, add it as a property
        if not code_lines and result.locations:
            location = result.locations[0].physicalLocation
            if location and location.region:
                start_line = location.region.startLine
                end_line = location.region.endLine
                if start_line:
                    is_range = end_line and end_line != start_line
                    range_text = f"{start_line}-{end_line}" if is_range else str(start_line)
                    key_text = "Line Range:" if is_range else "Line:"
                    properties.insert(
                        0, {"formatted_key": key_text, "formatted_value": range_text, "is_complex": False}
                    )

        return {
            "description": description,
            "has_description": bool(description.strip()),
            "has_code": bool(code_lines),
            "has_properties": bool(properties),
            "code_lines_with_metadata": code_lines,
            "formatted_properties": properties,
        }

    def _get_code_lines(self, result: Result) -> list[dict[str, Any]]:
        """Extract code lines with metadata from SARIF result."""
        if not result.locations:
            return []

        location: PhysicalLocation = result.locations[0].physicalLocation
        if not location:
            return []

        # Try contextRegion first, but only if it has a valid snippet
        region: Region | None = None
        if location.contextRegion and location.contextRegion.snippet:
            region = location.contextRegion
        elif location.region and location.region.snippet:
            region = location.region

        if not region:
            return []

        code_text = region.snippet.text if region.snippet and hasattr(region.snippet, "text") else ""
        if not code_text:
            return []

        # Get line numbers
        context_start = region.startLine if hasattr(region, "startLine") and region.startLine else 1
        vuln_start = location.region.startLine if location.region else None
        vuln_end = location.region.endLine if location.region else None

        code_lines = []
        for i, line_text in enumerate(code_text.split("\n")):
            line_number = context_start + i
            is_vulnerable = False

            if vuln_start:
                if vuln_end:
                    is_vulnerable = vuln_start <= line_number <= vuln_end
                else:
                    is_vulnerable = line_number == vuln_start

            code_lines.append({"number": line_number, "text": line_text, "is_vulnerable": is_vulnerable})

        return code_lines

    def _get_additional_properties(self, result: Result) -> list[dict[str, Any]]:
        if not result.properties:
            return []

        # Convert properties to dict and filter out core fields
        props = result.properties.model_dump()
        excluded = {"type", "confidence"}
        formatted_props = []

        for key, value in props.items():
            if key in excluded or not value:
                continue

            formatted_key = key.replace("_", " ").title() + ":"

            # Handle different value types
            if isinstance(value, (str, int, float, bool)):
                formatted_props.append(
                    {"formatted_key": formatted_key, "formatted_value": str(value), "is_complex": False}
                )
            elif isinstance(value, dict):
                if len(value) == 1 and "text" in value:
                    # Simple message object
                    formatted_props.append(
                        {"formatted_key": formatted_key, "formatted_value": value["text"], "is_complex": False}
                    )
                else:
                    # Complex object - JSON format
                    formatted_props.append(
                        {
                            "formatted_key": formatted_key,
                            "formatted_value": json.dumps(value, indent=2),
                            "is_complex": True,
                        }
                    )
            elif isinstance(value, list):
                # Special handling for attack_vectors - format as bulleted list
                if key == "attack_vectors":
                    # Create bulleted list for regular property format
                    bullet_list = "\n".join([f"• {item}" for item in value if item])
                    formatted_props.append(
                        {"formatted_key": formatted_key, "formatted_value": bullet_list, "is_complex": False}
                    )
                else:
                    # Other arrays - JSON format
                    formatted_props.append(
                        {
                            "formatted_key": formatted_key,
                            "formatted_value": json.dumps(value, indent=2),
                            "is_complex": True,
                        }
                    )
            else:
                logger.warning(
                    f"Unexpected property value type for key '{key}': {type(value).__name__}, value: {value}"
                )

        return formatted_props

    def _get_file_path(self, result: Result) -> str:
        """Extract file path from SARIF result."""
        if not result.locations:
            return UNKNOWN

        location = result.locations[0].physicalLocation
        if not location or not location.artifactLocation:
            return UNKNOWN

        file_uri = location.artifactLocation.uri or UNKNOWN

        # Strip file:// prefix and validate
        file_uri = file_uri.removeprefix("file://")

        # Basic security check for path traversal
        if "../" in file_uri or "..\\" in file_uri:
            return UNKNOWN

        return file_uri.replace("\\", "/").lstrip("/") or UNKNOWN

    def _normalize_severity(self, sarif_level: str) -> str:
        level = sarif_level.lower()
        return level if level in ("error", "warning", "note", "none") else UNKNOWN

    def _build_filter_options(self, values: set, tab_data: list[dict], field: str) -> list[dict[str, Any]]:
        options = []

        if field == "severity":
            sorted_values = sorted(values, key=lambda x: SEVERITY_ORDER.get(x, 999))
        else:
            sorted_values = sorted(values)

        for value in sorted_values:
            # Find which tabs contain this value
            applicable_tabs = []
            for tab in tab_data:
                if field == "severity":
                    if tab["severity_counts"].get(value, 0) > 0:
                        applicable_tabs.append(tab["name"])
                else:  # type
                    for result in tab["results"]:
                        if result["type"] == value:
                            applicable_tabs.append(tab["name"])
                            break

            options.append({"value": value, "label": value.capitalize(), "tabs": ",".join(applicable_tabs)})

        return options

    def _generate_nonce(self) -> str:
        return base64.b64encode(secrets.token_bytes(32)).decode("ascii")
