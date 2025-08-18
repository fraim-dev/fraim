#!/usr/bin/env python3
"""
CVE Data Generator for Fraim DSPy Training Data

This CLI delegates to the refactored modules:
- models.py: dataclasses
- git.py: Git operations and diff parsing
- fetcher.py: NVD fetching and parsing
- generator.py: building training examples
- writers.py: CSV/YAML serialization
- manager.py: orchestration
"""

import argparse
import logging
from pathlib import Path

from .manager import CVETrainingDataManager


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate Fraim DSPy training data from CVE database')
    parser.add_argument('--vulnerability-types', nargs='+',
                        default=['SQL Injection', 'XSS', 'Path Traversal', 'Command Injection'],
                        help='Vulnerability types to generate training data for')
    parser.add_argument('--output-dir', type=Path, default='./training_data_generation/generated_training_data',
                        help='Output directory for training data files')
    parser.add_argument('--max-cves-per-type', type=int, default=10,
                        help='Maximum CVEs to fetch per vulnerability type')
    parser.add_argument('--severity', choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
                        help='CVSS severity filter', default='CRITICAL')
    parser.add_argument('--api-key', help='NIST NVD API key for higher rate limits')
    parser.add_argument('--no-code-extraction', action='store_true',
                        help='Disable real code extraction from CVE references (use templates only)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    extract_code = not args.no_code_extraction
    manager = CVETrainingDataManager(api_key=args.api_key, extract_code=extract_code)
    logger.info("Code extraction from CVE references enabled" if extract_code else "Code extraction disabled, using templates only")

    try:
        manager.generate_training_data(
            vulnerability_types=args.vulnerability_types,
            output_dir=args.output_dir,
            max_cves_per_type=args.max_cves_per_type,
            severity=args.severity,
        )
        print("✅ Training data generation completed successfully!")
        print(f"📁 Files saved to: {args.output_dir}")
    except Exception as e:
        logger.error(f"Error generating training data: {e}")
        return 1
    return 0


if __name__ == '__main__':
    exit(main())

