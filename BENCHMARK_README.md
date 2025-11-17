# Fraim Benchmark Script

This script benchmarks Fraim's code workflow against known security vulnerabilities from the training dataset.

## What it does

1. **Runs Fraim on vulnerable code**: Analyzes benchmark directories from `training/benchmarks/`
2. **Compares with expected vulnerabilities**: Checks findings against ground truth in `training/rules/`
3. **Tests patched versions**: Runs on `training/benchmarks_patched/` to detect false positives
4. **Calculates metrics**: Computes detection rate, precision, recall, and F1 score

## Quick Start

### Basic Test (3 benchmarks)

```bash
uv run python benchmark_fraim.py
```

This runs on a small subset for quick testing:
- XBEN-001-24: IDOR in Order Receipts
- XBEN-002-24: IDOR in Order Archiving  
- XBEN-003-24: IDOR via X-UserId Header

### Specify LLM Model

```bash
uv run python benchmark_fraim.py --model claude-3-5-sonnet-20241022
```

Or use a different model:

```bash
uv run python benchmark_fraim.py --model gpt-4o
```

### Testing More Benchmarks

Edit `benchmark_fraim.py` and modify the `TEST_BENCHMARKS` list:

```python
TEST_BENCHMARKS = [
    "XBEN-001-24",
    "XBEN-002-24",
    "XBEN-003-24",
    "XBEN-004-24",  # Add more as needed
    "XBEN-005-24",
]
```

## Output

Each benchmark run creates a timestamped directory with all outputs:

```
benchmark_output/
└── 20251106_154530/           # Run ID (timestamp)
    ├── benchmark_results.json  # Summary with metrics
    ├── XBEN-001-24_vulnerable/ # Fraim output for vulnerable code
    │   ├── *.sarif
    │   ├── *.html
    │   └── *_threat_model_*.md
    ├── XBEN-001-24_patched/    # Fraim output for patched code
    ├── XBEN-002-24_vulnerable/
    ├── XBEN-002-24_patched/
    └── ...
```

The script produces:

1. **Console output**: Real-time progress and summary metrics
2. **SARIF files**: Detailed Fraim findings in each benchmark subdirectory
3. **JSON summary**: `benchmark_results.json` with run metadata and metrics

### Sample Output

```
Starting Fraim Benchmark
Run ID: 20251106_154530
Output directory: /path/to/fraim/benchmark_output/20251106_154530
Testing 3 benchmarks
Using model: claude-3-5-sonnet-20241022
================================================================================
...

OVERALL METRICS
================================================================================
Total Expected Vulnerabilities: 3
Total True Positives:  2
Total False Negatives: 1
Total False Positives: 0

Detection Rate: 66.7%
Precision: 100.0%
Recall: 66.7%
F1 Score: 0.800

Run ID: 20251106_154530
Output directory: /path/to/fraim/benchmark_output/20251106_154530
Detailed results saved to: benchmark_results.json
```

### JSON Summary

The `benchmark_results.json` file contains:

```json
{
  "run_id": "20251106_154530",
  "model": "claude-3-5-sonnet-20241022",
  "timestamp": "2025-11-06T15:45:30.123456",
  "benchmarks": [
    {
      "id": "XBEN-001-24",
      "expected_count": 1,
      "found_count": 1,
      "patched_found_count": 0,
      "true_positives": 1,
      "false_negatives": 0,
      "false_positives": 0
    }
  ]
}
```

## Metrics Explained

- **True Positives (TP)**: Vulnerabilities correctly identified by Fraim
- **False Negatives (FN)**: Expected vulnerabilities missed by Fraim
- **False Positives (FP)**: Issues flagged in patched (fixed) code
- **Detection Rate**: TP / Expected (what % of vulns we found)
- **Precision**: TP / (TP + FP) (how accurate our findings are)
- **Recall**: TP / (TP + FN) (how complete our detection is)
- **F1 Score**: Harmonic mean of precision and recall

## Matching Criteria

A Fraim finding matches an expected vulnerability when:
1. **File path matches**: Same relative path within the benchmark
2. **Line ranges overlap**: Any overlap between reported and expected line numbers

This allows for some flexibility in exact line number reporting while ensuring we're identifying the right issue.

## Directory Structure

```
training/
├── benchmarks/           # Vulnerable code
│   ├── XBEN-001-24/
│   ├── XBEN-002-24/
│   └── ...
├── benchmarks_patched/   # Fixed code (should have no findings)
│   ├── XBEN-001-24/
│   ├── XBEN-002-24/
│   └── ...
└── rules/                # Expected vulnerabilities
    ├── XBEN-001-000_vulns.json
    ├── XBEN-002-000_vulns.json
    └── ...
```

## Troubleshooting

### Script times out
- Default timeout is 20 minutes per benchmark
- Increase in `run_fraim()` function: `timeout=1800`

### Missing SARIF output
- Check `benchmark_output/{RUN_ID}/{BENCHMARK_ID}_vulnerable/` for errors
- Look for Fraim error messages in console output

### No matches found
- Verify file paths in rules JSON match actual file structure
- Check that line numbers overlap (exact matches not required)

## Command Line Options

```
usage: benchmark_fraim.py [-h] [--model MODEL]

Benchmark Fraim's code workflow against known vulnerabilities

optional arguments:
  -h, --help     show this help message and exit
  --model MODEL  LLM model to use (e.g., claude-3-5-sonnet-20241022, gpt-4, etc.)
```

## Extending the Script

### Add more benchmarks
Modify `TEST_BENCHMARKS` list at the top of `benchmark_fraim.py`

### Change Fraim parameters
Edit the `run_fraim()` function to adjust:
- `--confidence` level
- `--max-concurrent-chunks`
- Other Fraim CLI options

### Customize matching logic
Modify `matches_expected()` function to change how findings are matched to expected vulnerabilities

## Requirements

- Python 3.8+
- Fraim installed and working
- Training dataset in `training/` directory

