# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import json
import logging
from pathlib import Path

from fraim.outputs import sarif
from fraim.outputs.sarif import Result
from fraim.reporting.html.report import generate_html_report
from fraim.reporting.reporting import Reporting

logger = logging.getLogger(__name__)


class SarifReporting(Reporting):
    """Specialized reporting for SARIF-based workflows."""

    def write_sarif(
        self,
        results: list[Result],
        project_name: str,
        total_cost: float | None = None,
        threat_model_content: str | None = None,
        write_html: bool = False,
        for_hosted_reports: bool = False,
        sarif_filename: str = "report.sarif",
        html_filename: str = "report.html",
    ) -> dict[str, Path]:
        """
        Create and write SARIF report and optionally generate HTML.

        Args:
            results: List of SARIF Result objects
            repo_name: Name of the repository being analyzed
            total_cost: Optional total cost in USD for all LLM operations in this run
            write_html: If True, also generate and write HTML report
            threat_model_content: Optional threat model to embed in HTML
            for_hosted_reports: Use hosted navbar in HTML (vs local navbar)
            sarif_filename: Filename for SARIF output
            html_filename: Filename for HTML output (if write_html=True)

        Returns:
            Dictionary with 'sarif' (and optionally 'html') keys mapping to written paths
        """
        paths = {}

        # Create SARIF report
        sarif_report = sarif.create_sarif_report(
            results=results,
            repo_name=project_name,
            total_cost=total_cost,
        )

        # Write SARIF
        sarif_dict = sarif_report.model_dump(by_alias=True, exclude_none=True)
        sarif_content = json.dumps(sarif_dict, indent=2)
        paths["sarif"] = self.write(sarif_filename, sarif_content)

        # Optionally write HTML
        if write_html:
            html_content = generate_html_report(
                sarif_report=sarif_report,
                threat_model_content=threat_model_content,
                for_hosted_reports=for_hosted_reports,
            )
            paths["html"] = self.write(html_filename, html_content)

        return paths
