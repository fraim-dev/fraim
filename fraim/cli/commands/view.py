# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""View command for generating HTML reports from SARIF files."""

import json
import logging
from pathlib import Path
from typing import Annotated

import typer

from fraim.outputs.sarif import SarifReport
from fraim.reporting.html.report import generate_html_report

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command(name="view")
def view_command(
    sarif_file: Annotated[Path, typer.Argument(help="Path to the SARIF file to view")],
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Output path for HTML report")] = None,
    threat_model: Annotated[
        Path | None, typer.Option(help="Path to threat model markdown file to include in report")
    ] = None,
    for_hosted_reports: Annotated[bool, typer.Option(help="Use hosted navbar (for security reports)")] = False,
) -> None:
    """Generate HTML report from SARIF file."""
    sarif_file_path = sarif_file.resolve()

    if not sarif_file_path.exists():
        logger.error(f"SARIF file not found: {sarif_file_path}")
        raise typer.Exit(code=1)

    # Determine output path
    if output:
        output_path = output
    else:
        output_path = sarif_file_path.with_suffix(".html")

    logger.info(f"Loading SARIF file: {sarif_file_path}")

    try:
        # Load and parse SARIF file
        with open(sarif_file_path, encoding="utf-8") as f:
            sarif_data = json.load(f)

        sarif_report = SarifReport.model_validate(sarif_data)
        logger.info(f"Successfully parsed SARIF report with {len(sarif_report.runs)} run(s)")

        # Load threat model if provided
        threat_model_content = None
        if threat_model:
            threat_model_path = threat_model
            if threat_model_path.exists():
                logger.info(f"Loading threat model: {threat_model_path}")
                threat_model_content = threat_model_path.read_text(encoding="utf-8")
            else:
                logger.warning(f"Threat model file not found: {threat_model_path}")

        # Generate HTML report
        logger.info("Generating HTML report...")
        html_content = generate_html_report(
            sarif_report=sarif_report,
            threat_model_content=threat_model_content,
            for_hosted_reports=for_hosted_reports,
        )

        # Write HTML file
        output_path.write_text(html_content, encoding="utf-8")
        logger.info(f"HTML report written to: {output_path}")
        typer.echo(f"\n✅ HTML report generated: {output_path}")

    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        import traceback

        traceback.print_exc()
        raise typer.Exit(code=1) from e
