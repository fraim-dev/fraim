#!/usr/bin/env python3
"""
Validate benchmark setup without running Fraim.

Checks that all necessary files and directories exist.
"""

import json
from pathlib import Path

TEST_BENCHMARKS = [
    "XBEN-001-24",
    "XBEN-002-24",
    "XBEN-003-24",
]


def main():
    script_dir = Path(__file__).parent.resolve()
    training_dir = script_dir / "training"
    benchmarks_dir = training_dir / "benchmarks"
    benchmarks_patched_dir = training_dir / "benchmarks_patched"
    rules_dir = training_dir / "rules"
    
    print("Validating Benchmark Setup")
    print("=" * 80)
    
    # Check main directories
    all_valid = True
    
    for name, path in [
        ("Training directory", training_dir),
        ("Benchmarks directory", benchmarks_dir),
        ("Patched benchmarks", benchmarks_patched_dir),
        ("Rules directory", rules_dir),
    ]:
        if path.exists():
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name}: {path} NOT FOUND")
            all_valid = False
    
    print("\n" + "=" * 80)
    print("Checking Test Benchmarks")
    print("=" * 80)
    
    for benchmark_id in TEST_BENCHMARKS:
        print(f"\n{benchmark_id}:")
        
        # Check vulnerable version
        vulnerable_path = benchmarks_dir / benchmark_id
        if vulnerable_path.exists():
            print(f"  ✓ Vulnerable code: {vulnerable_path}")
        else:
            print(f"  ✗ Vulnerable code: {vulnerable_path} NOT FOUND")
            all_valid = False
        
        # Check patched version
        patched_path = benchmarks_patched_dir / benchmark_id
        if patched_path.exists():
            print(f"  ✓ Patched code: {patched_path}")
        else:
            print(f"  ⚠ Patched code: {patched_path} NOT FOUND (optional)")
        
        # Check rules
        base_id = "-".join(benchmark_id.split("-")[:2])
        rule_file = rules_dir / f"{base_id}-000_vulns.json"
        
        if rule_file.exists():
            print(f"  ✓ Rules file: {rule_file}")
            
            # Parse and show expected vulnerabilities
            try:
                with open(rule_file) as f:
                    data = json.load(f)
                
                vuln_count = len(data.get("vulnerabilities", []))
                print(f"    Expected vulnerabilities: {vuln_count}")
                
                for vuln in data.get("vulnerabilities", []):
                    print(f"    - {vuln.get('vuln_name', 'Unknown')}")
                    for valid_vuln in vuln.get("valid_vulns", []):
                        file_path = valid_vuln.get("file_path", "")
                        lines = f"{valid_vuln.get('start_line')}-{valid_vuln.get('end_line')}"
                        print(f"      {file_path}:{lines}")
                        
            except Exception as e:
                print(f"  ✗ Error parsing rules file: {e}")
                all_valid = False
        else:
            print(f"  ✗ Rules file: {rule_file} NOT FOUND")
            all_valid = False
    
    print("\n" + "=" * 80)
    
    if all_valid:
        print("✓ All validation checks passed!")
        print("\nYou can now run: uv run python benchmark_fraim.py")
        return 0
    else:
        print("✗ Some validation checks failed")
        print("Please ensure the training dataset is in the correct location")
        return 1


if __name__ == "__main__":
    exit(main())

