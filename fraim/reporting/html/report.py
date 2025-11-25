# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import base64
import json
import os

from fraim.outputs.sarif import SarifReport

type HtmlReport = str


def generate_html_report(
    sarif_report: SarifReport,
    threat_model_content: str | None = None,
    for_hosted_reports: bool = False,
) -> HtmlReport:
    """
    Generate an HTML report from a SARIF report and optional threat model content.

    This creates a self-contained HTML report with embedded CSS/JS/logo, minimized SARIF data,
    and optional threat model content. The HTML is returned as a string.

    Args:
        project_name: Name of the project/repository
        sarif_report: The SARIF report data
        threat_model_content: Optional threat model content as markdown string
        for_hosted_reports: If True, use security reports navbar; if False, use local navbar with docs/GitHub links

    Returns:
        HtmlReport: The complete HTML report as a string
    """
    # Get templates directory
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    html_template = os.path.join(templates_dir, "report.html")
    css_template = os.path.join(templates_dir, "report.css")
    js_template = os.path.join(templates_dir, "report.js")
    navbar_security_reports_template = os.path.join(templates_dir, "navbar_security_reports.html")
    navbar_local_template = os.path.join(templates_dir, "navbar_local.html")

    # Read template files
    with open(html_template, encoding="utf-8") as f:
        html_content = f.read()

    with open(css_template, encoding="utf-8") as f:
        css_content = f.read()

    with open(js_template, encoding="utf-8") as f:
        js_content = f.read()

    # Read navbar template based on generation type
    navbar_template_path = navbar_security_reports_template if for_hosted_reports else navbar_local_template
    with open(navbar_template_path, encoding="utf-8") as f:
        navbar_content = f.read()

    # Read and encode logo file as base64 data URLs
    logo_path = os.path.join(templates_dir, "assets", "fraim-logo.png")
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

    return html_content
