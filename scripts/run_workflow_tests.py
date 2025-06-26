#!/usr/bin/env python3

import argparse
import re
import sys
from typing import List, Optional, Protocol

from fraim.workflows.test import TestRunner, ExitCode, WorkflowName, TestSpecification

class ParsedArgs(Protocol):
    list: bool
    record: bool
    tests: Optional[List[TestSpecification]]
    workflows: Optional[List[WorkflowName]]

def validate_test_specifications(test_specs: List[TestSpecification]) -> None:
    test_spec_pattern = re.compile(r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$')
    
    for spec in test_specs:
        if not test_spec_pattern.match(spec):
            raise ValueError(
                f"Invalid test specification format: '{spec}'. Expected: 'workflow:test_case'."
            )

def validate_arguments(args: ParsedArgs) -> None:
    if args.list and args.record:
        raise ValueError("argument --record: not allowed with argument --list")

    if args.tests:
        validate_test_specifications(args.tests)

def main() -> ExitCode:
    parser = argparse.ArgumentParser(
        description="Run workflow tests for Fraim"
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--workflows",
        nargs="+",
        help="Run tests for specific workflows (e.g., 'code', 'iac')"
    )
    group.add_argument(
        "--tests",
        nargs="+",
        help="Run specific tests (e.g., 'code:python_command_injection')"
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List available workflows and test cases"
    )
    
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record new test fixtures instead of running tests"
    )
    
    args = parser.parse_args()
    
    try:
        validate_arguments(args)
    except ValueError as e:
        print(f"run_workflow_tests.py: error: {e}", file=sys.stderr)
        return 1
    
    runner = TestRunner()
    
    if args.list:
        runner.list_available_tests()
        return 0
    
    if args.workflows:
        return runner.run_workflow_tests(args.workflows, record=args.record)
    elif args.tests:
        return runner.run_specific_tests(args.tests, record=args.record)
    else:
        return runner.run_all_tests(record=args.record)

if __name__ == "__main__":
    sys.exit(main()) 