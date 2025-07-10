import os
from datetime import datetime
from typing import List

from fraim.config.config import Config
from fraim.outputs import sarif
from fraim.reporting.reporting import Reporting


def write_sarif_report(results: List[sarif.Result], repo_name: str, config: Config) -> None:
    report = sarif.create_sarif_report(results)

    # Create filename with sanitized repo name
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize repo name for filename (replace spaces and special chars with underscores)
    safe_repo_name = "".join(c if c.isalnum() else "_" for c in repo_name).strip("_")
    sarif_filename = f"fraim_report_{safe_repo_name}_{current_time}.sarif"
    html_filename = f"fraim_report_{safe_repo_name}_{current_time}.html"

    sarif_output_file = os.path.join(config.output_dir, sarif_filename)
    html_output_file = os.path.join(config.output_dir, html_filename)

    total_results = len(results)

    # Write SARIF JSON file
    try:
        with open(sarif_output_file, "w") as f:
            f.write(report.model_dump_json(by_alias=True, indent=2, exclude_none=True))
        config.logger.info(f"Wrote SARIF report ({total_results} results) to {sarif_output_file}")
    except Exception as e:
        config.logger.error(f"Failed to write SARIF report to {sarif_output_file}: {str(e)}")
    # Write HTML report file (independent of SARIF write)
    try:
        Reporting.generate_html_report(sarif_report=report, repo_name=repo_name, output_path=html_output_file)
        config.logger.info(f"Wrote HTML report ({total_results} results) to {html_output_file}")
    except Exception as e:
        config.logger.error(f"Failed to write HTML report to {html_output_file}: {str(e)}")
