# Security Scorer Workflow

## Overview

The Security Scorer workflow analyzes a repository's security hygiene and posture, calculating a comprehensive security score from 1-100. It evaluates multiple security categories independently and aggregates them deterministically to provide an objective assessment of the repository's overall security posture.

## Features

- **Category-Based Analysis**: Evaluates 7 distinct security categories independently
- **Deterministic Aggregation**: Combines category scores using a transparent, reproducible formula
- **Comprehensive Tooling**: Uses LLM with filesystem tools to explore and analyze the codebase
- **Detailed Breakdown**: Provides score, reasoning, findings, and recommendations for each category
- **Evidence-Based**: All scores are backed by concrete findings from the repository

## Security Categories

The workflow evaluates the following categories:

1. **Repository Hygiene (20%)** - SECURITY.md, dependency management, build tools, CI, tests
2. **Dependency Supply Chain (20%)** - Automated updates, SBOM, dependency freshness, provenance
3. **Secrets & Configuration (15%)** - Secret management, environment separation, secure defaults
4. **Application Security Controls (20%)** - Input validation, query safety, crypto, error handling
5. **Memory/Language Safety (10%)** - Memory safety practices, fuzzing, sanitizers
6. **CI/CD Guards (15%)** - Branch protection, code review, release signing, hermetic builds
7. **Adjustments (10%)** - Size normalization, confidence level, operational posture

## Usage

### Basic Usage

```bash
fraim security_scorer --project-path path/to/repo
```

### With Custom Output

```bash
fraim security_scorer \
  --project-path path/to/repo \
  --output-file fraim_output
```

### Programmatic Usage

```python
from fraim.workflows.security_scorer import SecurityScorerWorkflow, SecurityScorerWorkflowOptions

# Configure the workflow
options = SecurityScorerWorkflowOptions(
    project_path="/path/to/repo",
    output_file="fraim_output",
    model="anthropic/claude-sonnet-4-0",
    temperature=0
)

# Run the workflow
workflow = SecurityScorerWorkflow(options)
result = await workflow.run()

# Access the scores
print(f"Overall Score: {result.overall_score}/100")
print(f"Repo Hygiene: {result.category_breakdown.repo_hygiene.score:.1f}/100")
print(f"AppSec Controls: {result.category_breakdown.appsec_controls.score:.1f}/100")
```

## Output

The workflow returns a `SecurityScoreResult` with:

```python
SecurityScoreResult(
    overall_score=78,  # Deterministically calculated from categories
    category_breakdown=CategoryBreakdown(
        repo_hygiene=RepoHygieneScore(
            score=85.0,
            reasoning="Strong SECURITY.md, comprehensive lockfiles, modern CI with linting...",
            key_findings=["SECURITY.md with clear reporting", "All lockfiles present"],
            recommendations=["Add test coverage reporting", "Pin CI tool versions"]
        ),
        dependency_supply_chain=DependencySupplyChainScore(
            score=65.0,
            reasoning="Dependabot configured, but no SBOM generation...",
            key_findings=["Dependabot enabled for npm", "Dependencies mostly fresh"],
            recommendations=["Add SBOM generation", "Enable Dependabot for all ecosystems"]
        ),
        # ... other categories
    ),
    key_factors=[
        "[Repository Hygiene] SECURITY.md with clear reporting",
        "[AppSec Controls] Comprehensive input validation",
        # ... top 10 factors
    ],
    recommendations=[
        "[Dependency Supply Chain] Add SBOM generation",
        "[CI/CD Guards] Enable branch protection",
        # ... top 10 recommendations
    ]
)
```

## Scoring Methodology

### Category Scores (0-100)

Each category is scored independently with clear guidelines:

- **0-40 (Low)**: Critical gaps, minimal security practices
- **41-70 (Medium)**: Basic security with notable gaps
- **71-100 (High)**: Strong security practices with comprehensive controls

Each category prompt includes specific examples of low, medium, and high scores.

### Overall Score Calculation

The overall score is calculated deterministically:

```
Overall = Practices * 0.90 + Adjustments * 0.10

Where Practices = 
  repo_hygiene * 0.18 +
  dependency_supply_chain * 0.18 +
  secrets_config * 0.135 +
  appsec_controls * 0.18 +
  memory_language_safety * 0.09 +
  cicd_guards * 0.135

And Adjustments accounts for:
  - Size normalization (±10 points)
  - Confidence level (±10 points)  
  - Operational posture (±6 points)
```

### Score Ranges

- **90-100**: Excellent security posture with strong practices across all categories
- **75-89**: Good security with minor areas for improvement
- **50-74**: Moderate security with several gaps requiring attention
- **25-49**: Poor security with significant weaknesses
- **1-24**: Critical security gaps requiring immediate remediation

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `project_path` | str | "./" | Path to repository root to analyze |
| `output_file` | str | "fraim_output" | Path to save reports (optional) |
| `model` | str | anthropic/claude-sonnet-4-0 | LLM model to use |
| `temperature` | float | 0 | Temperature for LLM generation |

## Example Output

```
================================================================================
Security Score for myapp: 78/100
================================================================================

────────────────────────────────────────────────────────────────────────────────
CATEGORY BREAKDOWN
────────────────────────────────────────────────────────────────────────────────

Repository Hygiene (20%): 85.0/100
  Reasoning: Comprehensive SECURITY.md present, all dependency lockfiles maintained...

Dependency Supply Chain (20%): 65.0/100
  Reasoning: Dependabot configured for npm, dependencies mostly fresh (<6 months)...

Secrets & Configuration (15%): 90.0/100
  Reasoning: No secrets found in codebase, comprehensive .env.example...

Application Security Controls (20%): 75.0/100
  Reasoning: Input validation present using Zod schemas, parameterized queries...

Memory/Language Safety (10%): 80.0/100
  Reasoning: TypeScript provides type safety, no unsafe operations...

CI/CD Security Guards (15%): 60.0/100
  Reasoning: GitHub Actions with basic branch protection, no release signing...

Adjustments (10%): 55.0/100
  Reasoning: Medium-sized repo (500 files), high confidence in findings...

────────────────────────────────────────────────────────────────────────────────
TOP KEY FACTORS
────────────────────────────────────────────────────────────────────────────────
1. [Repository Hygiene] SECURITY.md with clear vulnerability reporting process
2. [Repository Hygiene] All lockfiles present and up-to-date
3. [Secrets & Config] No hardcoded secrets found in repository
4. [Secrets & Config] Comprehensive .env.example with documentation
...

────────────────────────────────────────────────────────────────────────────────
TOP RECOMMENDATIONS
────────────────────────────────────────────────────────────────────────────────
1. [Dependency Supply Chain] Add SBOM generation to CI pipeline
2. [CI/CD Guards] Enable signed releases with Sigstore
3. [AppSec Controls] Add rate limiting middleware
...
```

## Notes

- **Independent Analysis**: Each category is analyzed separately with dedicated prompts and scoring guidelines
- **Evidence-Based**: All scores must be backed by concrete findings from filesystem exploration
- **Transparent Formula**: The aggregation formula is deterministic and clearly documented
- **Tool Access**: The LLM uses grep, read_file, and list_dir extensively to explore the codebase
- **Category Equality**: Categories have different weights reflecting their relative importance to overall security

## Integration

The security scorer can be used to:
- **Track Security Progress**: Run periodically to measure improvements over time
- **Gate Deployments**: Set minimum score thresholds in CI/CD pipelines
- **Benchmark Repositories**: Compare security posture across projects
- **Identify Priorities**: Use category breakdown to focus security investments
- **Generate Reports**: Export results for stakeholder communication

## Best Practices

1. **Run on Clean Repository**: Ensure the repository is in a consistent state (no uncommitted changes)
2. **Provide Full Context**: Point to the repository root with all dependencies installed
3. **Review Category Details**: Don't just look at overall score - examine each category's reasoning
4. **Act on Recommendations**: Prioritize the top recommendations from low-scoring categories
5. **Track Over Time**: Run regularly and track score trends to measure security improvements
