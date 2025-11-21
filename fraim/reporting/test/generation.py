# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
DEPRECATED: Use `fraim view` command instead.

This script is maintained for backwards compatibility only.
Please use the new CLI command:

    fraim view <sarif_file> [options]

Examples:
    fraim view path/to/report.sarif
    fraim view path/to/report.sarif -o output.html
    fraim view path/to/report.sarif --threat-model threat_model.md
    fraim view path/to/report.sarif --for-hosted-reports

See `fraim view --help` for more information.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from fraim.outputs.sarif import SarifReport
from fraim.reporting.html.report import generate_html_report


def main() -> int:
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Generate HTML report from SARIF file. Use `fraim view` instead.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DEPRECATED: Use `fraim view` command instead.

Examples (new command):
  fraim view path/to/report.sarif
  fraim view path/to/report.sarif -o output.html
  fraim view path/to/report.sarif --for-hosted-reports
        """,
    )
    parser.add_argument("sarif_file", help="Path to the SARIF file to process")
    parser.add_argument("--repo-name", default="", help="Repository name (deprecated)", metavar="")
    parser.add_argument(
        "--for-security-reports",
        action="store_true",
        help="Generate report for security reports (full navbar)",
        default=False,
    )

    args = parser.parse_args()

    print("⚠️  DEPRECATED: This script is deprecated. Please use `fraim view` command instead.")
    print(f"   Example: fraim view {args.sarif_file}\n")

    # Resolve the SARIF file path
    sarif_file_path = Path(args.sarif_file).resolve()
    if not sarif_file_path.exists():
        print(f"❌ Error: SARIF file not found: {sarif_file_path}")
        return 1

    # Output path for the HTML report (in test outputs directory)
    test_outputs_dir = Path(__file__).parent / "outputs"
    test_outputs_dir.mkdir(exist_ok=True)

    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_security_report_{timestamp}.html"
    output_file = test_outputs_dir / filename

    print(f"Loading SARIF file: {sarif_file_path}")

    # Load and parse the SARIF file
    try:
        sarif_data = json.loads(sarif_file_path.read_text(encoding="utf-8"))
        print(f"Loaded SARIF data with {len(sarif_data.get('runs', []))} runs")

        # Parse into Pydantic model
        sarif_report = SarifReport.model_validate(sarif_data)
        print("Successfully parsed SARIF report")

        # Count total results
        total_results = sum(len(run.results) for run in sarif_report.runs)
        print(f"Total results: {total_results}")

    except Exception as e:
        print(f"❌ Error loading SARIF file: {e}")
        return 1

    # Check for threat model file
    threat_model_content = None
    threat_model_path = sarif_file_path.parent / "threat_model.md"
    if threat_model_path.exists():
        print(f"Loading threat model file: {threat_model_path}")
        threat_model_content = threat_model_path.read_text(encoding="utf-8")
        print(f"Loaded threat model content ({len(threat_model_content)} characters)")

    # Generate HTML report
    try:
        html_content = generate_html_report(
            sarif_report=sarif_report,
            threat_model_content=threat_model_content,
            for_hosted_reports=args.for_security_reports,
        )
        output_file.write_text(html_content, encoding="utf-8")
        print(f"✅ HTML report written to: {output_file}")
        return 0

    except Exception as e:
        print(f"❌ Error generating HTML report: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
