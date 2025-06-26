#!/usr/bin/env python3

import argparse
import sys
from typing import List, Optional, Protocol

from fraim.workflows.test import ExitCode, TestRunner, TestSpecification, WorkflowName

class ParsedArgs(Protocol):
    list: bool
    record: bool
    tests: Optional[List[str]]
    workflows: Optional[List[WorkflowName]]

def get_filtered_test_specs(args: ParsedArgs, runner: TestRunner) -> List[TestSpecification]:
    available_test_specs = runner.get_available_test_specs()
    
    if not available_test_specs:
        TestRunner.log_error("No tests found to run")
        return []
    
    if args.workflows:
        if not runner.verify_workflows_exist(args.workflows, available_test_specs):
            return []
        
        workflow_set = set(args.workflows)
        filtered_specs = [spec for spec in available_test_specs if spec.workflow in workflow_set]
    elif args.tests:
        filtered_specs = [TestSpecification(spec) for spec in args.tests]
    else:
        filtered_specs = available_test_specs
    
    if not filtered_specs:
        TestRunner.log_error("No tests found to run")
        return []
    
    return filtered_specs

def validate_arguments(args: ParsedArgs) -> None:
    if args.list and args.record:
        raise ValueError("argument --record: not allowed with argument --list")

    if args.tests:
        validate_test_specifications(args.tests)

def validate_test_specifications(test_specs: List[str]) -> None:
    for spec in test_specs:
        if not TestSpecification.is_valid(spec):
            raise ValueError(f"Invalid test specification format: '{spec}'. Expected: 'workflow:test_case'.")

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
        TestRunner.log_error(str(e))
        return ExitCode.ERROR
    
    runner = TestRunner()
    
    if args.list:
        runner.list_available_tests()
        return ExitCode.SUCCESS
    
    test_specs = get_filtered_test_specs(args, runner)
    if not test_specs:
        return ExitCode.ERROR
    
    return runner.run_tests(test_specs, record=args.record)

if __name__ == "__main__":
    sys.exit(main()) 