# Training Data Generation

This directory contains tools for automatically generating training data from CVE (Common Vulnerabilities and Exposures) databases to populate Fraim's DSPy training datasets.

## Overview

The CVE data generator fetches real vulnerability data from the NIST National Vulnerability Database (NVD) and transforms it into training examples for Fraim's AI-powered security analysis. This allows you to:

1. **Automatically populate training data** from real-world vulnerabilities
2. **Extract actual vulnerable and fixed code** from Git repositories linked in CVE references
3. **Filter by specific vulnerability types** (SQL Injection, XSS, etc.)
4. **Generate both scanner and triager training examples**
5. **Use real CVE fixes for remediation training**
6. **Customize the number of examples** per vulnerability type

## Files

- `cve_data_generator.py` - Main script for fetching and transforming CVE data
- `test_cve_generator.py` - Test script with mock data examples
- `README.md` - This documentation file

## Quick Start

### 1. Install Dependencies

Ensure you have the DSPy dependency group installed:

```bash
cd /Users/prestonprice/Code/fraim
uv sync --group dspy
```

### 2. Basic Usage

Generate training data for common vulnerability types with real code extraction:

```bash
cd fraim_dspy/training_data_generation
python cve_data_generator.py --vulnerability-types "SQL Injection" "XSS" "Path Traversal" --max-cves-per-type 10
```

To use templates only (no code extraction):

```bash
python cve_data_generator.py --vulnerability-types "SQL Injection" "XSS" --no-code-extraction
```

### 3. With API Key (Recommended)

For better rate limits, get a free API key from [NIST NVD](https://nvd.nist.gov/developers/request-an-api-key):

```bash
python cve_data_generator.py \
    --api-key YOUR_API_KEY \
    --vulnerability-types "SQL Injection" "XSS" \
    --max-cves-per-type 15 \
    --severity HIGH
```

### 4. Custom Output Directory

Specify where to save the training data files:

```bash
python cve_data_generator.py \
    --vulnerability-types "Command Injection" "Insecure Deserialization" \
    --output-dir ../training_data \
    --max-cves-per-type 5
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--vulnerability-types` | List of vulnerability types to generate data for | `['SQL Injection', 'XSS', 'Path Traversal', 'Command Injection']` |
| `--output-dir` | Directory to save training data files | `./training_data` |
| `--max-cves-per-type` | Maximum CVEs to fetch per vulnerability type | `10` |
| `--severity` | CVSS severity filter (LOW, MEDIUM, HIGH, CRITICAL) | None (all severities) |
| `--api-key` | NIST NVD API key for higher rate limits | None |
| `--no-code-extraction` | Disable real code extraction (use templates only) | False |
| `--verbose` | Enable verbose logging | False |

## Supported Vulnerability Types

The generator currently supports these vulnerability types:

- **SQL Injection** - Database query injection vulnerabilities
- **XSS** - Cross-site scripting vulnerabilities  
- **Path Traversal** - Directory traversal and path manipulation
- **Command Injection** - System command execution vulnerabilities
- **Insecure Deserialization** - Unsafe object deserialization
- **SSRF** - Server-side request forgery
- **CSRF** - Cross-site request forgery
- **Hardcoded Credentials** - Embedded secrets and credentials

## Output Format

The generator creates two CSV files:

### scanner_training_data.csv
Contains training examples for the vulnerability scanner with columns:
- `code_chunk` - Source code to analyze (real vulnerable code when available)
- `file_path` - Path to the file
- `language` - Programming language
- `expected_vulnerabilities` - JSON array of expected vulnerabilities
- `cve_id` - CVE identifier for traceability
- `source` - Data source ("real_cve" or "template")

### triager_training_data.csv  
Contains training examples for the vulnerability triager with columns:
- `vulnerability` - JSON of vulnerability to triage
- `code_chunk` - Source code containing vulnerability (real vulnerable code when available)
- `file_path` - Path to the file
- `project_context` - Additional project context
- `expected_triaged_result` - JSON of expected triage result (includes actual fix when available)
- `cve_id` - CVE identifier for traceability
- `source` - Data source ("real_cve" or "template")

## Testing

Run the test script to verify functionality without making API calls:

```bash
python test_cve_generator.py
```

This uses mock CVE data to demonstrate the generation process.

## Rate Limiting

The NIST NVD API has rate limits:
- **Without API key**: 5 requests per 30 seconds
- **With API key**: 50 requests per 30 seconds

The generator automatically handles rate limiting with appropriate delays.

## Example Output

When you run the generator, you'll see output like:

```
INFO - Code extraction from CVE references enabled
INFO - Fetching CVEs for SQL Injection...
INFO - Extracting code changes for CVE-2023-1234...
INFO - Found 2 code changes for CVE-2023-1234
INFO - Fetched 8 CVEs
INFO - Generated 8 scanner examples and 8 triager examples for SQL Injection
INFO - Fetching CVEs for XSS...
INFO - Extracting code changes for CVE-2023-5678...
INFO - Found 1 code changes for CVE-2023-5678
INFO - Fetched 12 CVEs  
INFO - Generated 12 scanner examples and 12 triager examples for XSS
INFO - Wrote 20 scanner training examples to ./training_data/scanner_training_data.csv
INFO - Wrote 20 triager training examples to ./training_data/triager_training_data.csv
INFO - Training data saved to ./training_data
INFO - Real CVE data: 15 scanner examples, 15 triager examples
INFO - Template data: 5 scanner examples, 5 triager examples
✅ Training data generation completed successfully!
📁 Files saved to: ./training_data
```

## Integration with DSPy Optimization

Once you've generated training data, you can use it with the DSPy optimization pipeline:

```bash
cd ..  # back to fraim_dspy directory
uv run -m fraim_dspy.cli optimize \
    --data-dir ./training_data \
    --output-dir ./output \
    --model gpt-4o-mini
```

## Code Extraction Features

### Real Vulnerability Code

The enhanced generator can extract actual vulnerable and fixed code from CVE references. It supports:

- **GitHub commit URLs** - Extracts code changes from specific commits
- **GitHub pull request URLs** - Extracts code changes from PRs
- **Patch files** - Parses .patch files for code differences

When real code is found, the training data includes:
- The actual vulnerable code before the fix
- The fixed code after remediation 
- Commit metadata (hash, URL)
- File path and programming language
- Line number information

### Code Extraction Process

1. **CVE Reference Analysis** - Scans CVE references for Git repository links
2. **Repository Cloning** - Clones relevant repositories (shallow clone for speed)
3. **Diff Parsing** - Extracts vulnerable and fixed code from commit diffs
4. **Language Detection** - Determines programming language from file extensions
5. **Quality Filtering** - Filters out changes that are too small/large

### Benefits of Real Code

Using actual CVE fixes provides several advantages:
- **Real-world examples** instead of synthetic templates
- **Authentic code patterns** from production systems
- **Actual remediation strategies** used by developers
- **Better training data diversity** across projects and languages

## Advanced Usage

### Filtering by Date Range

Add date range filtering to focus on recent vulnerabilities:

```python
# In the script, modify the fetch_cves call:
cves = self.fetcher.fetch_cves(
    keywords=keywords,
    severity=severity, 
    start_date="2023-01-01",
    end_date="2024-01-01",
    max_results=max_cves_per_type
)
```

## Troubleshooting

### API Key Issues
- Ensure your API key is valid and has not expired
- Check rate limits if you're seeing 403 errors

### No CVEs Found
- Try different keywords or vulnerability types
- Remove severity filters to get more results
- Check if the vulnerability type exists in recent CVE data

### CSV Format Issues
- Ensure proper JSON escaping in vulnerability data
- Validate CSV output with `pandas.read_csv()` before using

## Contributing

When adding new vulnerability types or improving the generator:

1. Add code templates for the new vulnerability type
2. Update the vulnerability type mappings
3. Test with mock data first
4. Update this documentation
5. Ensure generated data follows the expected schema
