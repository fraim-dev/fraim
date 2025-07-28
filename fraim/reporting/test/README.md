# Reporting Test Scripts

This directory contains test scripts for the fraim reporting system.

## Usage

**Important**: Run the generation test from the **project root directory** so Python can find the fraim package:

```bash
# Basic usage with a SARIF file
python fraim/reporting/test/generation.py path/to/your/report.sarif

# With custom repository name
python fraim/reporting/test/generation.py path/to/your/report.sarif --repo-name "My Repo"

# Show help
python fraim/reporting/test/generation.py --help
```

This will:
1. Load the specified SARIF file
2. Parse it using the Pydantic SarifReport model
3. Generate an HTML report in `fraim/reporting/test/outputs/`

## Generated Files

All generated HTML files are saved to the `outputs/` directory.
