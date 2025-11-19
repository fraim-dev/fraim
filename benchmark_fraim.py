#!/usr/bin/env python3
"""
Benchmark Fraim's code workflow against known vulnerabilities.

This script:
1. Runs Fraim on vulnerable benchmark directories
2. Compares findings with expected vulnerabilities from training/rules
3. Runs Fraim on patched versions to detect false positives
4. Calculates and displays performance metrics
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Start with a small subset for testing
TEST_BENCHMARKS = [
    "XBEN-001-24",
    "XBEN-002-24",
    "XBEN-003-24",
    "XBEN-004-24",
    "XBEN-005-24",
    "XBEN-006-24",
    "XBEN-007-24",
    "XBEN-008-24",
    "XBEN-009-24",
    "XBEN-010-24",
    "XBEN-011-24",
    "XBEN-012-24",
    "XBEN-013-24",
    "XBEN-014-24",
    "XBEN-015-24",
    "XBEN-016-24",
    "XBEN-017-24",
    "XBEN-018-24",
    "XBEN-019-24",
    "XBEN-020-24",
    "XBEN-021-24",
    "XBEN-022-24",
    "XBEN-023-24",
    "XBEN-024-24",
    "XBEN-025-24",
    "XBEN-026-24",
    "XBEN-027-24",
    "XBEN-032-24",
    "XBEN-033-24",
    "XBEN-036-24",
    "XBEN-037-24",
    "XBEN-038-24",
    "XBEN-042-24",
    "XBEN-043-24",
    "XBEN-045-24",
    "XBEN-046-24",
    "XBEN-047-24",
    "XBEN-048-24",
    "XBEN-049-24",
    "XBEN-050-24",
    "XBEN-051-24",
]


@dataclass
class ExpectedVulnerability:
    """Expected vulnerability from rules."""
    vuln_name: str
    file_path: str
    start_line: int
    end_line: int
    description: str


@dataclass
class FraimFinding:
    """Finding from Fraim SARIF output."""
    rule_id: str
    message: str
    file_path: str
    start_line: int
    end_line: int


@dataclass
class BenchmarkResult:
    """Results for a single benchmark."""
    benchmark_id: str
    expected_vulns: List[ExpectedVulnerability]
    found_vulns: List[FraimFinding]
    patched_vulns: List[FraimFinding]
    true_positives: int
    false_negatives: int
    false_positives: int


def load_expected_vulnerabilities(rules_path: Path, benchmark_id: str) -> List[ExpectedVulnerability]:
    """Load expected vulnerabilities from the rules JSON file."""
    # Extract the base ID (e.g., XBEN-001 from XBEN-001-24)
    base_id = "-".join(benchmark_id.split("-")[:2])
    rule_file = rules_path / f"{base_id}-000_vulns.json"
    
    if not rule_file.exists():
        print(f"Warning: Rule file not found: {rule_file}")
        return []
    
    with open(rule_file) as f:
        data = json.load(f)
    
    expected = []
    for vuln in data.get("vulnerabilities", []):
        for valid_vuln in vuln.get("valid_vulns", []):
            # Normalize the file path to be relative to the benchmark directory
            file_path = valid_vuln["file_path"]
            # Remove the "benchmarks/XBEN-XXX-XX/" prefix if present
            if file_path.startswith("benchmarks/"):
                file_path = "/".join(file_path.split("/")[2:])
            
            expected.append(ExpectedVulnerability(
                vuln_name=vuln["vuln_name"],
                file_path=file_path,
                start_line=valid_vuln["start_line"],
                end_line=valid_vuln["end_line"],
                description=vuln.get("description_of_vuln", "")
            ))
    
    return expected


def run_fraim(benchmark_path: Path, output_dir: Path, model: Optional[str] = None) -> Optional[Path]:
    """Run Fraim code workflow on a benchmark directory."""
    print(f"  Running Fraim on {benchmark_path.name}...")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run Fraim CLI using uv
    cmd = [
        "uv", "run", "fraim",
        "--show-rich-display",
        "run", "code",
        "--location", str(benchmark_path),
        "--output", str(output_dir),
        "--confidence", "9",
    ]
    
    # Add model if specified
    if model:
        cmd.extend(["--model", model])
    
    try:
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            timeout=1200  # 20 minute timeout
        )
        
        if result.returncode != 0:
            print(f"    Warning: Fraim exited with code {result.returncode}")
        
        # Find the SARIF file in the output directory
        sarif_files = list(output_dir.glob("*.sarif"))
        if sarif_files:
            return sarif_files[0]
        else:
            print(f"    Warning: No SARIF file found in {output_dir}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"    Error: Fraim timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"    Error running Fraim: {e}")
        return None


def parse_sarif_findings(sarif_path: Optional[Path], benchmark_path: Path) -> List[FraimFinding]:
    """Parse findings from Fraim SARIF output."""
    if not sarif_path or not sarif_path.exists():
        return []
    
    try:
        with open(sarif_path) as f:
            sarif = json.load(f)
        
        findings = []
        for run in sarif.get("runs", []):
            for result in run.get("results", []):
                # Extract location information
                locations = result.get("locations", [])
                if not locations:
                    continue
                
                location = locations[0]
                physical_location = location.get("physicalLocation", {})
                artifact_location = physical_location.get("artifactLocation", {})
                region = physical_location.get("region", {})
                
                file_path = artifact_location.get("uri", "")
                start_line = region.get("startLine", 0)
                end_line = region.get("endLine", start_line)
                
                findings.append(FraimFinding(
                    rule_id=result.get("ruleId", ""),
                    message=result.get("message", {}).get("text", ""),
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line
                ))
        
        return findings
        
    except Exception as e:
        print(f"    Error parsing SARIF: {e}")
        return []


def matches_expected(finding: FraimFinding, expected: ExpectedVulnerability) -> bool:
    """Check if a finding matches an expected vulnerability."""
    # Normalize file paths for comparison
    finding_path = finding.file_path.lstrip("/")
    expected_path = expected.file_path.lstrip("/")
    
    # Check if paths match
    if finding_path != expected_path:
        return False
    
    # Check if line ranges overlap
    # A match occurs if there's any overlap between the ranges
    finding_range = set(range(finding.start_line, finding.end_line + 1))
    expected_range = set(range(expected.start_line, expected.end_line + 1))
    
    return bool(finding_range & expected_range)


def score_benchmark(
    benchmark_id: str,
    expected: List[ExpectedVulnerability],
    found: List[FraimFinding],
    patched_found: List[FraimFinding]
) -> BenchmarkResult:
    """Score a benchmark run."""
    true_positives = 0
    matched_expected = set()
    
    # Count true positives (findings that match expected vulnerabilities)
    for finding in found:
        for i, exp in enumerate(expected):
            if i not in matched_expected and matches_expected(finding, exp):
                true_positives += 1
                matched_expected.add(i)
                break
    
    # False negatives are expected vulnerabilities that weren't found
    false_negatives = len(expected) - true_positives
    
    # False positives are any findings in the patched version
    false_positives = len(patched_found)
    
    return BenchmarkResult(
        benchmark_id=benchmark_id,
        expected_vulns=expected,
        found_vulns=found,
        patched_vulns=patched_found,
        true_positives=true_positives,
        false_negatives=false_negatives,
        false_positives=false_positives
    )


def print_results(results: List[BenchmarkResult]):
    """Print benchmark results."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    
    total_tp = 0
    total_fn = 0
    total_fp = 0
    total_expected = 0
    
    for result in results:
        print(f"\n{result.benchmark_id}:")
        print(f"  Expected vulnerabilities: {len(result.expected_vulns)}")
        print(f"  Found in vulnerable code: {len(result.found_vulns)}")
        print(f"  Found in patched code: {len(result.patched_vulns)}")
        print(f"  True Positives:  {result.true_positives}")
        print(f"  False Negatives: {result.false_negatives}")
        print(f"  False Positives: {result.false_positives}")
        
        total_tp += result.true_positives
        total_fn += result.false_negatives
        total_fp += result.false_positives
        total_expected += len(result.expected_vulns)
    
    print("\n" + "=" * 80)
    print("OVERALL METRICS")
    print("=" * 80)
    print(f"Total Expected Vulnerabilities: {total_expected}")
    print(f"Total True Positives:  {total_tp}")
    print(f"Total False Negatives: {total_fn}")
    print(f"Total False Positives: {total_fp}")
    
    # Calculate metrics
    if total_expected > 0:
        detection_rate = (total_tp / total_expected) * 100
        print(f"\nDetection Rate: {detection_rate:.1f}%")
    
    if (total_tp + total_fp) > 0:
        precision = (total_tp / (total_tp + total_fp)) * 100
        print(f"Precision: {precision:.1f}%")
    
    if (total_tp + total_fn) > 0:
        recall = (total_tp / (total_tp + total_fn)) * 100
        print(f"Recall: {recall:.1f}%")
    
    if (total_tp + total_fp + total_fn) > 0:
        f1_denominator = (total_tp + total_fp) * (total_tp + total_fn)
        if f1_denominator > 0:
            f1 = (2 * total_tp * total_tp) / f1_denominator
            print(f"F1 Score: {f1:.3f}")


def main():
    """Main benchmark runner."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Benchmark Fraim's code workflow against known vulnerabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--model",
        type=str,
        help="LLM model to use (e.g., claude-3-5-sonnet-20241022, gpt-4, etc.)"
    )
    
    args = parser.parse_args()
    
    # Generate run ID based on timestamp
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get paths
    script_dir = Path(__file__).parent.resolve()
    training_dir = script_dir / "training"
    benchmarks_dir = training_dir / "benchmarks"
    benchmarks_patched_dir = training_dir / "benchmarks_patched"
    rules_dir = training_dir / "rules"
    output_base_dir = script_dir / "benchmark_output" / run_id
    
    # Create output directory
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    # Verify directories exist
    if not benchmarks_dir.exists():
        print(f"Error: Benchmarks directory not found: {benchmarks_dir}")
        sys.exit(1)
    
    if not rules_dir.exists():
        print(f"Error: Rules directory not found: {rules_dir}")
        sys.exit(1)
    
    print("Starting Fraim Benchmark")
    print(f"Run ID: {run_id}")
    print(f"Output directory: {output_base_dir}")
    print(f"Testing {len(TEST_BENCHMARKS)} benchmarks")
    if args.model:
        print(f"Using model: {args.model}")
    print("=" * 80)
    
    results = []
    
    for benchmark_id in TEST_BENCHMARKS:
        print(f"\nProcessing {benchmark_id}...")
        
        # Load expected vulnerabilities
        expected = load_expected_vulnerabilities(rules_dir, benchmark_id)
        print(f"  Expected vulnerabilities: {len(expected)}")
        
        # Run on vulnerable version
        vulnerable_path = benchmarks_dir / benchmark_id
        vulnerable_output = vulnerable_path
        
        if not vulnerable_path.exists():
            print(f"  Warning: Benchmark not found: {vulnerable_path}")
            continue
        
        found_vulns = []
        # vulnerable_sarif = run_fraim(vulnerable_path, vulnerable_output, model=args.model)
        # found_vulns = parse_sarif_findings(vulnerable_sarif, vulnerable_path)
        
        # Run on patched version
        patched_path = benchmarks_patched_dir / benchmark_id
        patched_output = patched_path
        
        patched_found = []
        # skip patched for now
        if patched_path.exists():
            patched_sarif = run_fraim(patched_path, patched_output, model=args.model)
            patched_found = parse_sarif_findings(patched_sarif, patched_path)
        else:
            print(f"  Warning: Patched benchmark not found: {patched_path}")
        
        # Score the results
        result = score_benchmark(benchmark_id, expected, found_vulns, patched_found)
        results.append(result)
    
    # Print results
    print_results(results)
    
    # Save detailed results to JSON
    results_file = output_base_dir / "benchmark_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "run_id": run_id,
            "model": args.model,
            "timestamp": datetime.now().isoformat(),
            "benchmarks": [
                {
                    "id": r.benchmark_id,
                    "expected_count": len(r.expected_vulns),
                    "found_count": len(r.found_vulns),
                    "patched_found_count": len(r.patched_vulns),
                    "true_positives": r.true_positives,
                    "false_negatives": r.false_negatives,
                    "false_positives": r.false_positives,
                }
                for r in results
            ]
        }, f, indent=2)
    
    print(f"\nRun ID: {run_id}")
    print(f"Output directory: {output_base_dir}")
    print(f"Detailed results saved to: {results_file}")


if __name__ == "__main__":
    main()

