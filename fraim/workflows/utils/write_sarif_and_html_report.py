# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
"""
Utility for writing SARIF and HTML security scan reports.

This module provides a function to write scan results in both SARIF (JSON) and HTML formats.
It is used by workflows to persist and present vulnerability findings after analysis.
"""

import logging
import os
from datetime import datetime
from typing import List

from fraim.outputs.sarif import Result, create_sarif_report
from fraim.reporting.reporting import Reporting


def write_sarif_and_html_report(results: List[Result], repo_name: str, output_dir: str, logger: logging.Logger) -> None:
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
        logger.error(f"Failed to write SARIF report to {sarif_output_file}: {str(e)}")
    # Write HTML report file (independent of SARIF write)
    try:
        Reporting.generate_html_report(sarif_report=report, repo_name=repo_name, output_path=html_output_file)
        logger.info(f"Wrote HTML report ({total_results} results) to {html_output_file}")
    except Exception as e:
        logger.error(f"Failed to write HTML report to {html_output_file}: {str(e)}")
