# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
"""
Utility for writing SARIF and HTML security scan reports.

This module provides a function to write scan results in both SARIF (JSON) and HTML formats.
It is used by workflows to persist and present vulnerability findings after analysis.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fraim.outputs import sarif
from fraim.outputs.sarif import Result, create_sarif_report
from fraim.reporting.reporting import Reporting

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFilterOptions:
    confidence: Annotated[
        int,
        {
            "help": "Minimum confidence threshold (1-10) for filtering findings (default: 7)",
            "choices": range(1, 11),  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        },
    ] = 7


"""
TODO: Organization nits:

"confidence" isn't actually a SARIF thing (its a custom property that we added). I'd put this in file fraim/core/workflows/mixins/confidence.py.

write_sarif_and_html_report isn't workflow specific. Consider moving it to a fraim/core/ouputs/sarif.py or something like that.
"""


def filter_results_by_confidence(results: list[sarif.Result], confidence_threshold: int) -> list[sarif.Result]:
    return [result for result in results if result.properties.confidence > confidence_threshold]


@dataclass
class ReportPaths:
    sarif_path: str
    html_path: str


def write_sarif_and_html_report(results: list[Result], repo_name: str, output_dir: str) -> ReportPaths:
    """
    Write security scan results to both SARIF (JSON) and HTML report files.

    Args:
        results: List of security scan results to include in the reports
        repo_name: Name of the repository being scanned, used in filename generation
        output_dir: Directory path where report files will be written
        logger: Logger instance for recording operation status and errors

    Returns:
        ReportPaths object with sarif_path and html_path attributes containing file paths

    Example:
        >>> results = [Result(...), Result(...)]
        >>> reports = write_sarif_and_html_report(results, "my-repo", "/output", logger)
        >>> print(reports.sarif_path)
        '/output/fraim_report_my_repo_20250917_143022.sarif'
        >>> print(reports.html_path)
        '/output/fraim_report_my_repo_20250917_143022.html'
    """
    report = create_sarif_report(results)

    # Create filename with sanitized repo name
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize repo name for filename (replace spaces and special chars with underscores)
    safe_repo_name = "".join(c if c.isalnum() else "_" for c in repo_name).strip("_")
    sarif_filename = f"fraim_report_{safe_repo_name}_{current_time}.sarif"
    html_filename = f"fraim_report_{safe_repo_name}_{current_time}.html"

    sarif_output_file = os.path.join(output_dir, sarif_filename)
    html_output_file = os.path.join(output_dir, html_filename)

    total_results = len(results)

    # Write SARIF JSON file
    try:
        with open(sarif_output_file, "w") as f:
            f.write(report.model_dump_json(by_alias=True, indent=2, exclude_none=True))
        logger.info(f"Wrote SARIF report ({total_results} results) to {sarif_output_file}")
    except Exception as e:
        logger.error(f"Failed to write SARIF report to {sarif_output_file}: {e!s}")
    # Write HTML report file (independent of SARIF write)
    try:
        Reporting.generate_html_report(sarif_report=report, repo_name=repo_name, output_path=html_output_file)
        logger.info(f"Wrote HTML report ({total_results} results) to {html_output_file}")
    except Exception as e:
        logger.error(f"Failed to write HTML report to {html_output_file}: {e!s}")

    return ReportPaths(sarif_path=sarif_output_file, html_path=html_output_file)
