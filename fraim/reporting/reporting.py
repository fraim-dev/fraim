# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import json
import logging
import os

from fraim.outputs.sarif import SarifReport
from fraim.reporting.html.report import generate_html_report as generate_html_report_content

logger = logging.getLogger(__name__)


class Reporting:
    """Generate HTML reports from security scan results."""

    @classmethod
    def generate_html_report(
        cls,
        sarif_report: SarifReport,
        output_path: str,
        threat_model_content: str | None = None,
        generation_for_security_reports: bool = False,
    ) -> None:
        """
        Generate a self-contained HTML report with embedded data and separate files.

        This creates up to three files:
        - report.html (self-contained HTML with embedded CSS/JS/logo, minimized SARIF data, and threat model)
        - report.sarif (SARIF JSON data for external use)
        - report.md (threat model markdown, if provided)

        The HTML file contains all assets embedded for portability, while the separate files
        allow the data to be used by other tools.

        Args:
            sarif_report: The SARIF report data
            repo_name: Name of the repository
            output_path: Path where the HTML file should be created
            threat_model_content: Optional threat model content as markdown string
            generation_for_security_reports: If True, use security reports navbar; if False, use local navbar with docs/GitHub links
        """
        # Generate the HTML content using the new function
        html_content = generate_html_report_content(
            sarif_report=sarif_report,
            threat_model_content=threat_model_content,
            for_hosted_reports=generation_for_security_reports,
        )

        # Determine output directory
        output_dir = os.path.dirname(output_path) or "."

        # Write self-contained HTML file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Write SARIF JSON file with same basename as HTML
        html_basename = os.path.splitext(os.path.basename(output_path))[0]
        sarif_filename = f"{html_basename}.sarif"
        sarif_output_path = os.path.join(output_dir, sarif_filename)

        # Prepare SARIF data for writing
        sarif_dict = sarif_report.model_dump(by_alias=True, exclude_none=True)

        with open(sarif_output_path, "w", encoding="utf-8") as f:
            json.dump(sarif_dict, f, indent=2)

        # Write threat model markdown file if content was provided
        threat_model_output_path = ""
        if threat_model_content:
            threat_model_filename = f"{html_basename}.md"
            threat_model_output_path = os.path.join(output_dir, threat_model_filename)

            with open(threat_model_output_path, "w", encoding="utf-8") as f:
                f.write(threat_model_content)

        logger.info(f"HTML report created: {output_path}")
        logger.info(f"SARIF file created: {sarif_output_path}")
        logger.info(f"Threat model file created: {threat_model_output_path}") if threat_model_output_path else None
