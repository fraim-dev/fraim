# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import argparse
import json
import os
import sys
from datetime import datetime

from fraim.outputs.sarif import SarifReport
from fraim.reporting.reporting import Reporting


def main() -> int:
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate HTML report from SARIF file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fraim/reporting/test/generation.py path/to/report.sarif
  python fraim/reporting/test/generation.py path/to/report.sarif --repo-name "My Project"
        """,
    )
    parser.add_argument("sarif_file", help="Path to the SARIF file to process")
    parser.add_argument("--repo-name", default="", help="Repository name", metavar="")

    args = parser.parse_args()

    # Resolve the SARIF file path
    sarif_file_path = os.path.abspath(args.sarif_file)
    if not os.path.exists(sarif_file_path):
        print(f"❌ Error: SARIF file not found: {sarif_file_path}")
        return 1

    # Output path for the HTML report (in test outputs directory)
    test_outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(test_outputs_dir, exist_ok=True)  # Create outputs directory if it doesn't exist

    # Create filename with repo name if provided
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.repo_name:
        # Sanitize repo name for filename (replace spaces and special chars with underscores)
        safe_repo_name = "".join(c if c.isalnum() else "_" for c in args.repo_name).strip("_")
        filename = f"test_security_report_{safe_repo_name}_{timestamp}.html"
    else:
        filename = f"test_security_report_{timestamp}.html"

    output_file = os.path.join(test_outputs_dir, filename)

    print(f"Loading SARIF file: {sarif_file_path}")

    # Load and parse the SARIF file
    try:
        with open(sarif_file_path, encoding="utf-8") as f:
            sarif_data = json.load(f)

        print(f"Loaded SARIF data with {len(sarif_data.get('runs', []))} runs")

        # Parse into Pydantic model
        sarif_report = SarifReport.model_validate(sarif_data)
        print("Successfully parsed SARIF report")

        # Count total results
        total_results = sum(len(run.results) for run in sarif_report.runs)
        print(f"Total results: {total_results}")

    except Exception as e:
        print(f"Error loading SARIF file: {e}")
        return 1

    # Generate HTML report
    try:
        print(f"Generating HTML report: {output_file}")

        Reporting.generate_html_report(sarif_report=sarif_report, repo_name=args.repo_name, output_path=output_file)

        print(f"✅ Successfully generated HTML report: {output_file}")
        print(f"📁 File size: {os.path.getsize(output_file)} bytes")
        print(f"🌐 Open in browser: file://{os.path.abspath(output_file)}")
        return 0

    except Exception as e:
        print(f"❌ Error generating HTML report: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
