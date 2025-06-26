"""
Workflow testing framework for Fraim.
"""

from typing import List

ExitCode = int
WorkflowName = str
TestSpecification = str


class TestRunner:
    """Main interface for running workflow tests."""
    
    def __init__(self) -> None:
        pass
    
    def list_available_tests(self) -> None:
        # TODO: Implement workflow and test case discovery
        print("Test discovery not implemented yet")
    
    def run_all_tests(self, record: bool = False) -> ExitCode:
        # TODO: Implement running all tests
        print(f"Running all tests (record={record})")
        return 0
    
    def run_workflow_tests(self, workflows: List[WorkflowName], record: bool = False) -> ExitCode:
        # TODO: Implement workflow-specific test running
        print(f"Running tests for workflows: {workflows} (record={record})")
        return 0
    
    def run_specific_tests(self, test_specs: List[TestSpecification], record: bool = False) -> ExitCode:
        # TODO: Implement specific test running
        print(f"Running specific tests: {test_specs} (record={record})")
        return 0 