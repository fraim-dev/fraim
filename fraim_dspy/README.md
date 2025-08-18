# DSPy Prompt Optimization for Fraim

This directory contains DSPy-powered prompt optimization for Fraim's code security analysis workflows. DSPy is used to automatically improve the prompts used in the code scanner and triager components.

## Overview

The DSPy integration provides:

1. **Automated Prompt Optimization**: Uses DSPy's optimization algorithms to improve prompt performance
2. **Training Data Management**: CSV-based training data for reproducible optimization
3. **Modular Architecture**: Separate optimization for scanner and triager components
4. **Evaluation Metrics**: Custom metrics for vulnerability detection and triage quality
5. **CLI Interface**: Easy-to-use command-line tools for running optimization

## Quick Start

### 1. Install Dependencies

Add the DSPy dependency group to your environment:

```bash
uv sync --group dspy
```

### 2. Create Training Data Files

Create empty CSV files with the proper headers:

```bash
uv run -m fraim_dspy.cli create-training-files --data-dir ./fraim_dspy/training_data
```

This creates two files:
- `scanner_training_data.csv`: For training the vulnerability scanner
- `triager_training_data.csv`: For training the vulnerability triager

### 3. Populate Training Data

You have two options for populating training data:

#### Option A: Automatic Generation from CVE Database (Recommended)

Generate training data automatically from real vulnerability data:

```bash
cd fraim_dspy/training_data_generation
python cve_data_generator.py --vulnerability-types "SQL Injection" "XSS" "Path Traversal" --max-cves-per-type 10
```

This will populate the CSV files with real-world vulnerability examples. See the [Training Data Generation README](./training_data_generation/README.md) for detailed usage.

#### Option B: Manual Training Data

Edit the CSV files manually to add your training examples (see [Training Data Format](#training-data-format) below).

### 4. Run Optimization

Run the full optimization pipeline:

```bash
uv run -m fraim_dspy.cli optimize \
    --data-dir ./fraim_dspy/training_data \
    --output-dir ./fraim_dspy/output \
    --model gpt-4o-mini
```

## Training Data Format

### Scanner Training Data (`scanner_training_data.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| `code_chunk` | Source code to analyze | `"def execute_query(sql): cursor.execute(sql)"` |
| `file_path` | Path to the file | `"src/database.py"` |
| `language` | Programming language | `"python"` |
| `expected_vulnerabilities` | JSON array of expected vulnerabilities | `"[{\"rule_id\": \"sql-injection\", \"message\": \"SQL injection vulnerability\", \"level\": \"error\", \"vulnerability_type\": \"SQL Injection\", \"start_line\": 1, \"confidence\": 0.9}]"` |

### Triager Training Data (`triager_training_data.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| `vulnerability` | JSON of vulnerability to triage | `"{\"rule_id\": \"sql-injection\", \"message\": \"SQL injection\", ...}"` |
| `code_chunk` | Source code containing vulnerability | `"def execute_query(sql): cursor.execute(sql)"` |
| `file_path` | Path to the file | `"src/database.py"` |
| `project_context` | Additional project context | `"Flask web application with user authentication"` |
| `expected_triaged_result` | JSON of expected triage result | `"{\"exploitability\": \"HIGH\", \"external_input_source\": \"HTTP\", ...}"` |

### Vulnerability JSON Schema

Scanner vulnerabilities should include:

```json
{
  "rule_id": "string",
  "message": "string", 
  "level": "error|warning|info",
  "vulnerability_type": "SQL Injection|XSS|CSRF|...",
  "start_line": "number",
  "end_line": "number (optional)",
  "confidence": "number (0-1)"
}
```

Triager results should include:

```json
{
  "rule_id": "string",
  "message": "string",
  "level": "error|warning|info", 
  "vulnerability_type": "string",
  "start_line": "number",
  "end_line": "number (optional)",
  "confidence": "number (0-1)",
  "exploitability": "HIGH|MEDIUM|LOW|NONE",
  "impact_analysis": "string",
  "attack_vectors": "string",
  "remediation": "string",
  "data_flow_trace": "string",
  "external_input_source": "HTTP|CLI|FILE|ENV|CONFIG|NONE"
}
```

## CLI Commands

### Create Training Files

```bash
uv run -m fraim_dspy.cli create-training-files --data-dir ./fraim_dspy/training_data
```

### Validate Training Data

```bash
uv run -m fraim_dspy.cli validate --data-dir ./fraim_dspy/training_data
```

### Show Training Statistics

```bash
uv run -m fraim_dspy.cli stats --data-dir ./fraim_dspy/training_data
```

### Run Full Optimization

```bash
uv run -m fraim_dspy.cli optimize \
    --data-dir ./fraim_dspy/training_data \
    --output-dir ./fraim_dspy/output \
    --model gpt-4o-mini \
    --method bootstrap \
    --threads 4
```

### Optimize Scanner Only

```bash
uv run -m fraim_dspy.cli optimize-scanner \
    --data-dir ./fraim_dspy/training_data \
    --output-dir ./fraim_dspy/output
```

### Optimize Triager Only

```bash
uv run -m fraim_dspy.cli optimize-triager \
    --data-dir ./fraim_dspy/training_data \
    --output-dir ./fraim_dspy/output
```

## Optimization Methods

### Bootstrap Few-Shot

Uses DSPy's `BootstrapFewShot` optimizer to automatically generate few-shot examples:

```bash
uv run -m fraim_dspy.cli optimize --method bootstrap --max-demos 4
```

### MIPRO

Uses DSPy's `MIPRO` optimizer for more sophisticated prompt optimization:

```bash
uv run -m fraim_dspy.cli optimize --method mipro --max-labeled-demos 16
```

## Evaluation Metrics

### Scanner Metric

The scanner is evaluated using F1 score based on:
- Vulnerability type matching
- Line number accuracy
- Overall precision and recall

### Triager Metric

The triager is evaluated using a weighted score based on:
- Exploitability assessment accuracy (40% weight)
- External input source identification (30% weight)
- Confidence score accuracy (20% weight)
- Required field completeness (10% weight)

## Output Files

After optimization, the following files are generated in the output directory:

- `optimized_scanner_prompts.json`: Optimized prompts for the scanner
- `optimized_triager_prompts.json`: Optimized prompts for the triager
- `optimization_results.json`: Summary of optimization results and statistics

## Integration with Fraim

The optimized prompts can be integrated back into Fraim by:

1. Extracting the optimized prompt text from the JSON output files
2. Updating the YAML prompt files in `fraim/workflows/code/`
3. Testing the improved prompts with your specific codebase

## Advanced Usage

### Custom Models

Use different language models:

```bash
uv run -m fraim_dspy.cli optimize --model gpt-4 --api-key your-api-key
```

### Parallel Processing

Speed up optimization with multiple threads:

```bash
uv run -m fraim_dspy.cli optimize --threads 8
```

### Large Training Sets

For large training datasets, use MIPRO with more labeled examples:

```bash
uv run -m fraim_dspy.cli optimize --method mipro --max-labeled-demos 50
```

## Best Practices

1. **Start Small**: Begin with 10-20 high-quality training examples per component
2. **Diverse Examples**: Include examples from different programming languages and vulnerability types
3. **Quality over Quantity**: Well-labeled examples are more valuable than many poor examples
4. **Iterative Improvement**: Run optimization, evaluate results, add more training data, repeat
5. **Validation**: Always validate your training data before running optimization

## Troubleshooting

### No Training Examples Found

- Ensure CSV files exist in the data directory
- Check that CSV files have the correct headers
- Verify that training examples are properly formatted

### JSON Parsing Errors

- Validate JSON formatting in your training data
- Use the `validate` command to check for issues
- Escape quotes properly in CSV files

### Low Optimization Scores

- Add more diverse training examples
- Check that expected outputs match the actual task requirements
- Consider using a more powerful language model
- Try different optimization methods

### Memory Issues

- Reduce the number of training examples
- Use fewer threads
- Consider using a smaller language model for initial experiments

## Training Data Generation

The `training_data_generation/` directory contains tools for automatically generating training data from CVE databases:

- **CVE Data Generator**: Fetches real vulnerability data from NIST NVD
- **Automatic Code Examples**: Generates code snippets for different vulnerability types  
- **Multiple Formats**: Creates both scanner and triager training examples
- **Configurable**: Filter by vulnerability type, severity, and date range

See the [Training Data Generation README](./training_data_generation/README.md) for detailed usage instructions.

## Contributing

When contributing training data or improvements:

1. Follow the established CSV format
2. Include diverse, real-world examples
3. Validate all training data before submitting
4. Document any new vulnerability types or patterns
5. Test optimized prompts against held-out evaluation sets
6. Consider using the CVE data generator for consistent, real-world examples 