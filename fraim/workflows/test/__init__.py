from pathlib import Path
from typing import List

from fraim.workflows.registry import get_available_workflows

ExitCode = int
WorkflowName = str
TestSpecification = str


class TestRunner:
    """Main interface for running workflow tests."""
    
    def __init__(self) -> None:
        pass
    
    def list_available_tests(self) -> None:
        available_workflows = get_available_workflows()
        
        test_dir = Path(__file__).parent
        
        print("=" * 50)
        print("Available tests:")
        
        for workflow in sorted(available_workflows):
            workflow_test_dir = test_dir / workflow
            
            if workflow_test_dir.exists() and workflow_test_dir.is_dir():
                test_cases = [
                    d.name for d in workflow_test_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.')
                ]
                
                if test_cases:
                    print(f"\n{workflow}:")
                    for test_case in sorted(test_cases):
                        print(f"  - {test_case}")
                else:
                    print(f"\n{workflow}: (no tests found)")
            else:
                print(f"\n{workflow}: (no test directory)")
        
        print("=" * 50)
    
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