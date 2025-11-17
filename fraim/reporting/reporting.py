# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import base64
import json
import logging
import os

from fraim.outputs.sarif import SarifReport

logger = logging.getLogger(__name__)


class Reporting:
    """Generate HTML reports from security scan results."""

    def __init__(self) -> None:
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.html_template = os.path.join(self.templates_dir, "report.html")
        self.css_template = os.path.join(self.templates_dir, "report.css")
        self.js_template = os.path.join(self.templates_dir, "report.js")
        self.navbar_security_reports_template = os.path.join(self.templates_dir, "navbar_security_reports.html")
        self.navbar_local_template = os.path.join(self.templates_dir, "navbar_local.html")

    @classmethod
    def generate_html_report(
        cls,
        sarif_report: SarifReport,
        repo_name: str,
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
        reporting = cls()

        # Determine output directory
        output_dir = os.path.dirname(output_path) or "."

        # Read template files
        with open(reporting.html_template, encoding="utf-8") as f:
            html_content = f.read()

        with open(reporting.css_template, encoding="utf-8") as f:
            css_content = f.read()

        with open(reporting.js_template, encoding="utf-8") as f:
            js_content = f.read()

        # Read navbar template based on generation type
        navbar_template_path = (
            reporting.navbar_security_reports_template
            if generation_for_security_reports
            else reporting.navbar_local_template
        )
        with open(navbar_template_path, encoding="utf-8") as f:
            navbar_content = f.read()

        # Read and encode logo file as base64 data URLs
        logo_path = os.path.join(reporting.templates_dir, "assets", "fraim-logo.png")
        with open(logo_path, "rb") as f:
            logo_data = f.read()

        # Create data URLs for favicon and logo image
        logo_base64 = base64.b64encode(logo_data).decode("utf-8")
        favicon_data_url = f"data:image/png;base64,{logo_base64}"
        logo_data_url = f"data:image/png;base64,{logo_base64}"

        # Check for and embed threat model content if provided
        threat_model_data = ""
        if threat_model_content:
            # Base64 encode the markdown content for secure embedding
            threat_model_data = base64.b64encode(threat_model_content.encode("utf-8")).decode("utf-8")

        # Prepare minimized SARIF data
        sarif_dict = sarif_report.model_dump(by_alias=True, exclude_none=True)

        # Minimize SARIF JSON by removing whitespace
        minimized_sarif = json.dumps(sarif_dict, separators=(",", ":"))

        # Base64 encode the JSON for secure embedding (prevents script injection)
        minimized_sarif = base64.b64encode(minimized_sarif.encode("utf-8")).decode("utf-8")

        # Replace logo placeholder in navbar
        navbar_html = navbar_content.replace("__LOGO_DATA__", logo_data_url)

        # Embed CSS, JS, SARIF data, logo data URLs, threat model data, and navbar into HTML
        html_content = html_content.replace("__CSS__", css_content)
        html_content = html_content.replace("__JAVASCRIPT__", js_content)
        html_content = html_content.replace("__SARIF_DATA__", minimized_sarif)
        html_content = html_content.replace("__FAVICON_DATA__", favicon_data_url)
        html_content = html_content.replace("__LOGO_DATA__", logo_data_url)
        html_content = html_content.replace("__THREAT_MODEL_DATA__", threat_model_data)
        html_content = html_content.replace("__NAVBAR__", navbar_html)

        # Write self-contained HTML file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Write SARIF JSON file with same basename as HTML
        html_basename = os.path.splitext(os.path.basename(output_path))[0]
        sarif_filename = f"{html_basename}.sarif"
        sarif_output_path = os.path.join(output_dir, sarif_filename)

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
